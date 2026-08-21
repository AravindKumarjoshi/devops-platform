# Jenkins on GKE — Kubernetes Manifests

This page contains all Kubernetes manifests needed to run Jenkins as a production-grade CI/CD controller on GKE. The deployment follows a **controller-only model**: Jenkins itself never runs builds. It delegates all build work to ephemeral agent pods spawned dynamically in a separate namespace, using the Kubernetes Cloud plugin.

!!! info "Deployment Philosophy"
    - **Jenkins Controller** = long-lived, stateful, needs SSD persistent storage
    - **Jenkins Agents** = ephemeral, stateless, spawned per build, destroyed after
    - **Namespaces** = strict isolation between controller and agents via NetworkPolicy
    - **Workload Identity** = no service account key files anywhere in the cluster

## Apply Order
Manifests must be applied in this order to satisfy dependencies:
```bash
kubectl apply -f namespace.yaml        # 1. Create namespaces first
kubectl apply -f storageclass.yaml     # 2. Storage class before PVC
kubectl apply -f pvc.yaml              # 3. PVC before Deployment mounts it
kubectl apply -f serviceaccount.yaml   # 4. SA before Deployment references it
kubectl apply -f rbac.yaml             # 5. RBAC before Controller tries to spawn pods
kubectl apply -f deployment.yaml       # 6. Controller Deployment
kubectl apply -f service.yaml          # 7. Services before Ingress
kubectl apply -f ingress.yaml          # 8. Ingress last
kubectl apply -f jenkins-agent-pod-template.yaml  # 9. JCasC ConfigMap (triggers reload)
```

---

## 1. Namespaces & Resource Quotas

### What is `namespace.yaml`?

This manifest creates **two Kubernetes namespaces** and attaches hard resource limits and network isolation policies to each.

| Namespace | Purpose | Who lives here |
|-----------|---------|---------------|
| `jenkins-prod` | Jenkins Controller | Controller Pod, Services, Ingress, PVC |
| `jenkins-agents` | Build Agents | Dynamically spawned agent pods (Kaniko, Maven, etc.) |

**Why separate namespaces?**
- **ResourceQuota** on `jenkins-agents` caps the blast radius if a runaway build spawns too many pods — it can't consume cluster-wide resources
- **NetworkPolicy** ensures agent pods can only reach the controller on port 50000 (JNLP) — they can't reach other services in the cluster
- **RBAC** is scoped per-namespace, so the controller's service account only has pod management rights in `jenkins-agents`, not cluster-wide

**What breaks without it?**
Agent pods could be scheduled in any namespace, resource quotas wouldn't apply, and network isolation between Jenkins and other workloads would be lost.

### `namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: jenkins-prod
  labels:
    app.kubernetes.io/name: jenkins
    environment: production
    team: sre-platform
    cost-center: CC-1042
---
apiVersion: v1
kind: Namespace
metadata:
  name: jenkins-agents
  labels:
    app.kubernetes.io/name: jenkins-agent
    environment: production
    team: sre-platform
    cost-center: CC-1042
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: jenkins-prod-quota
  namespace: jenkins-prod
spec:
  hard:
    requests.cpu: "8"
    requests.memory: 16Gi
    limits.cpu: "16"
    limits.memory: 32Gi
    count/persistentvolumeclaims: "5"
    count/pods: "20"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: jenkins-agents-quota
  namespace: jenkins-agents
spec:
  hard:
    requests.cpu: "64"
    requests.memory: 128Gi
    limits.cpu: "128"
    limits.memory: 256Gi
    count/pods: "100"
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: jenkins-prod-network-policy
  namespace: jenkins-prod
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: jenkins-agents
    ports:
    - protocol: TCP
      port: 50000
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to: []
```

---

## 2. StorageClass — GCP SSD Regional Persistent Disk

### What is `storageclass.yaml`?

Defines a custom **StorageClass** called `enterprise-ssd` that provisions GCP **regional SSD persistent disks**.

| Field | Value | Why |
|-------|-------|-----|
| `provisioner` | `pd.csi.storage.gke.io` | GKE's native CSI driver for GCP persistent disks |
| `type: pd-ssd` | NVMe SSD | Jenkins home dir does heavy small-file I/O (plugin reads, job configs). HDD is too slow. |
| `replication-type: regional-pd` | Replicated across 2 zones | If a GKE node in zone A fails, the pod reschedules in zone B and attaches the same disk |
| `reclaimPolicy: Retain` | Disk survives pod/PVC deletion | Protects against accidental `kubectl delete pvc` wiping 2 years of job history |
| `allowVolumeExpansion: true` | Grow disk online | Resize from 100Gi → 200Gi without downtime when Jenkins accumulates more job data |
| `volumeBindingMode: WaitForFirstConsumer` | Defer provisioning | Disk is created in the same zone the pod lands in — avoids cross-zone disk attachment failures |

**What breaks without it?**
The PVC in the next step would use the cluster's default StorageClass (usually `standard` HDD), which is too slow for Jenkins and not regional, meaning disk loss if the controller node fails.

### `storageclass.yaml`
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: enterprise-ssd
  labels:
    managed-by: platform-sre
provisioner: pd.csi.storage.gke.io
parameters:
  type: pd-ssd
  replication-type: regional-pd
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

---

## 3. Persistent Volume Claim — Jenkins Home

### What is `pvc.yaml`?

Requests a **100 GiB SSD regional persistent disk** to store the Jenkins home directory (`/var/jenkins_home`).

The Jenkins home directory contains:
- **All job definitions** (Jenkinsfiles are cached here)
- **Build history and logs** (by default, last N builds per job)
- **Plugin installations** (`.jar` files for 200+ plugins)
- **Credentials store** (encrypted, but backed by disk)
- **JCasC reload state**

**Why 100 GiB?**
A medium-sized Jenkins instance with ~50 jobs, 30-day log retention, and a full plugin set typically uses 20-40 GiB. 100 GiB gives 2-3x headroom before needing to resize.

**Why `ReadWriteOnce`?**
Jenkins is not designed for multi-writer disk access. Only one controller pod should mount this volume at a time. The PodDisruptionBudget in `deployment.yaml` ensures this.

**What breaks without it?**
Jenkins home uses the pod's ephemeral filesystem. Every pod restart loses all jobs, plugins, and history. Total data loss on restart.

### `pvc.yaml`
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: jenkins-home
  namespace: jenkins-prod
  labels:
    app.kubernetes.io/name: jenkins
    environment: production
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: enterprise-ssd
  resources:
    requests:
      storage: 100Gi
```

---

## 4. Service Accounts — Workload Identity

### What is `serviceaccount.yaml`?

Creates two Kubernetes ServiceAccounts (KSA), each **annotated with a GCP Service Account (GSA)** to enable Workload Identity.

**How Workload Identity works:**
```
Pod → KSA (Kubernetes SA) → WI Binding → GSA (GCP SA) → GCP API
```
No JSON key file is ever created or mounted. The GKE metadata server intercepts API calls and exchanges the pod's identity for a short-lived GCP access token automatically.

| KSA | Namespace | Maps to GSA | Permissions |
|-----|-----------|-------------|-------------|
| `jenkins-controller` | `jenkins-prod` | `jenkins-controller@enterprise-platform-prod.iam.gserviceaccount.com` | `roles/container.developer` (spawn pods), `roles/artifactregistry.reader` |
| `jenkins-agent` | `jenkins-agents` | `jenkins-agent@enterprise-platform-prod.iam.gserviceaccount.com` | `roles/artifactregistry.writer` (push images), `roles/storage.objectAdmin` (build cache) |

**What breaks without it?**
Pods fall back to the GCE default service account (which has broad project-level access) or fail to authenticate to GCP APIs entirely.

### `serviceaccount.yaml`
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-controller
  namespace: jenkins-prod
  annotations:
    iam.gke.io/gcp-service-account: jenkins-controller@enterprise-platform-prod.iam.gserviceaccount.com
  labels:
    app.kubernetes.io/name: jenkins
    environment: production
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-agent
  namespace: jenkins-agents
  annotations:
    iam.gke.io/gcp-service-account: jenkins-agent@enterprise-platform-prod.iam.gserviceaccount.com
  labels:
    app.kubernetes.io/name: jenkins-agent
    environment: production
```

---

## 5. RBAC — Kubernetes API Permissions

### What is `rbac.yaml`?

Grants the Jenkins Controller the Kubernetes API permissions needed to **dynamically create and manage agent pods**. This is what the **Kubernetes Cloud plugin** uses at runtime.

**What does Jenkins need to do via the K8s API?**

| Operation | API Resource | Why Jenkins needs it |
|-----------|-------------|---------------------|
| `create` pods | `pods` | Spawn a new agent pod when a build starts |
| `delete` pods | `pods` | Clean up agent pod when build finishes |
| `get/list` pods | `pods` | Check if agent pod is running/ready |
| `get` pods/log | `pods/log` | Stream agent logs to Jenkins UI |
| `exec` pods | `pods/exec` | Some pipeline steps exec into the agent |
| `list` nodes | `nodes` | For node affinity / pool selection logic |
| `get` secrets | `secrets` | Read image pull secrets for private registries |

**Scope:** The `ClusterRole` is bound **only to the `jenkins-agents` namespace** via a `RoleBinding`. Jenkins cannot touch pods in `kube-system`, `monitoring`, or any other namespace.

**What breaks without it?**
The Kubernetes Cloud plugin throws `403 Forbidden` when trying to create agent pods. All dynamic agent builds fail. Only static agents (if any) would work.

### `rbac.yaml`
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: jenkins-controller
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/exec", "pods/log", "secrets", "configmaps"]
    verbs: ["get", "list", "watch", "create", "update", "delete", "patch"]
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: jenkins-controller-binding
  namespace: jenkins-prod
subjects:
  - kind: ServiceAccount
    name: jenkins-controller
    namespace: jenkins-prod
roleRef:
  kind: ClusterRole
  name: jenkins-controller
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: jenkins-agent-manager
  namespace: jenkins-agents
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/exec", "pods/log"]
    verbs: ["get", "list", "watch", "create", "update", "delete", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: jenkins-agent-manager-binding
  namespace: jenkins-agents
subjects:
  - kind: ServiceAccount
    name: jenkins-controller
    namespace: jenkins-prod
roleRef:
  kind: Role
  name: jenkins-agent-manager
  apiGroup: rbac.authorization.k8s.io
```

---

## 6. Jenkins Controller Deployment

### What is `deployment.yaml`?

The core Deployment manifest for the Jenkins Controller pod. This is the most complex manifest — it encodes the operational requirements of running a stateful, mission-critical application on Kubernetes.

**Key design decisions explained:**

#### Image & Version Pinning
```yaml
image: jenkins/jenkins:2.462.3-lts-jdk17
imagePullPolicy: Always
```
LTS (Long Term Support) release — security patches backported for 12 months. JDK 17 is required for modern Jenkins plugins. `imagePullPolicy: Always` ensures the digest is verified on every start.

#### Resource Requests vs Limits
```yaml
requests: { cpu: 2000m, memory: 4Gi }
limits:   { cpu: 4000m, memory: 8Gi }
```
- **Requests** = what the node scheduler reserves. Jenkins gets 2 cores and 4 GiB guaranteed.
- **Limits** = hard ceiling. The pod is OOM-killed if it exceeds 8 GiB. Set the JVM `-XX:MaxRAMPercentage=70.0` so the JVM heap stays within limits.

#### Liveness vs Readiness Probes
| Probe | Path | Purpose |
|-------|------|---------|
| **Readiness** | `/login` (90s delay) | Tells Kubernetes when Jenkins has finished loading plugins and is ready to serve traffic. Traffic is held until this passes. |
| **Liveness** | `/login` (120s delay) | Tells Kubernetes if Jenkins is dead/hung. If it fails 10 times, the pod is restarted. The longer delay prevents restart loops during slow plugin loads. |

#### InitContainer: fix-permissions
```yaml
initContainers:
- name: fix-permissions
  command: ["chown", "-R", "1000:1000", "/var/jenkins_home"]
```
GCP regional persistent disks are provisioned with `root` ownership. Jenkins runs as UID 1000. This init container fixes ownership before the main container starts.

#### PodDisruptionBudget
```yaml
minAvailable: 1
```
Prevents `kubectl drain` (node maintenance, upgrades) from evicting the Jenkins pod unless a replacement is already running. Ensures zero downtime during GKE node upgrades.

#### Node Pool Affinity
```yaml
nodeSelector:
  cloud.google.com/gke-nodepool: jenkins-controller-pool
tolerations:
- key: dedicated
  value: jenkins
  effect: NoSchedule
```
The `jenkins-controller-pool` node has a taint `dedicated=jenkins:NoSchedule`. Only pods with this toleration land there. This prevents noisy-neighbor agent pods from competing with the controller for CPU/memory.

**What breaks without it?**
Without probes: traffic hits Jenkins before it's ready, causing 502 errors during startup. Without resource limits: a runaway JVM OOM can starve other pods on the node. Without node affinity: agents and controller compete on the same node.

### `deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jenkins
  namespace: jenkins-prod
  labels:
    app.kubernetes.io/name: jenkins
    environment: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: jenkins
  template:
    metadata:
      labels:
        app.kubernetes.io/name: jenkins
        environment: production
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/path: "/prometheus"
        prometheus.io/port: "8080"
    spec:
      serviceAccountName: jenkins-controller
      securityContext:
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        runAsNonRoot: true
      initContainers:
        - name: fix-permissions
          image: busybox:1.36
          command: ["sh", "-c", "chown -R 1000:1000 /var/jenkins_home"]
          volumeMounts:
            - name: jenkins-home
              mountPath: /var/jenkins_home
      containers:
        - name: jenkins
          image: jenkins/jenkins:2.462.3-lts-jdk17
          imagePullPolicy: Always
          ports:
            - containerPort: 8080
              name: web
            - containerPort: 50000
              name: jnlp
          resources:
            requests:
              cpu: 2000m
              memory: 4Gi
            limits:
              cpu: 4000m
              memory: 8Gi
          env:
            - name: JAVA_OPTS
              value: "-Djenkins.install.runSetupWizard=false -Dhudson.model.DirectoryBrowserSupport.CSP= -XX:+UseG1GC -XX:MaxRAMPercentage=70.0 -Djava.awt.headless=true"
            - name: JENKINS_OPTS
              value: "--httpPort=8080"
            - name: CASC_JENKINS_CONFIG
              value: "/var/jenkins_casc"
          livenessProbe:
            httpGet:
              path: /login
              port: 8080
            initialDelaySeconds: 120
            periodSeconds: 10
            failureThreshold: 10
            timeoutSeconds: 5
          readinessProbe:
            httpGet:
              path: /login
              port: 8080
            initialDelaySeconds: 90
            periodSeconds: 5
            failureThreshold: 5
            timeoutSeconds: 3
          volumeMounts:
            - name: jenkins-home
              mountPath: /var/jenkins_home
            - name: casc-config
              mountPath: /var/jenkins_casc
      volumes:
        - name: jenkins-home
          persistentVolumeClaim:
            claimName: jenkins-home
        - name: casc-config
          configMap:
            name: jenkins-casc
      nodeSelector:
        cloud.google.com/gke-nodepool: jenkins-controller-pool
      tolerations:
        - key: dedicated
          operator: Equal
          value: jenkins
          effect: NoSchedule
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app.kubernetes.io/name
                      operator: In
                      values:
                        - jenkins
                topologyKey: kubernetes.io/hostname
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: jenkins-pdb
  namespace: jenkins-prod
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: jenkins
```

---

## 7. Services — Exposing Jenkins Internally

### What is `service.yaml`?

Creates **two ClusterIP services** and a **BackendConfig** for the Jenkins Controller. Services give the controller a stable DNS name inside the cluster.

| Service | Port | DNS Name | Purpose |
|---------|------|----------|---------|
| `jenkins-ui` | 8080 | `jenkins-ui.jenkins-prod.svc.cluster.local` | Routes browser traffic from Ingress to Controller |
| `jenkins-jnlp` | 50000 | `jenkins-jnlp.jenkins-prod.svc.cluster.local` | Agent pods connect back to controller via JNLP protocol |

**Why JNLP port 50000?**
Jenkins uses the **JNLP protocol** (Java Network Launch Protocol) for the agent-to-controller communication channel. Agents initiate the connection outbound (controller doesn't need to reach into the agents namespace), so port 50000 only needs to be open inbound on the controller side.

**BackendConfig:**
The `BackendConfig` resource tells the GCP HTTPS Load Balancer how to health-check Jenkins. It polls `GET /login` every 15 seconds. If Jenkins stops responding, the LB marks it unhealthy and stops routing traffic.

**What breaks without it?**
Without `jenkins-ui`: Ingress has no backend to route to, all browser traffic gets 502. Without `jenkins-jnlp`: agents can't connect to the controller, all dynamic build agents fail silently.

### `service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: jenkins-ui
  namespace: jenkins-prod
  annotations:
    cloud.google.com/backend-config: '{"default": "jenkins-backendconfig"}'
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: jenkins
  ports:
    - port: 8080
      targetPort: web
---
apiVersion: v1
kind: Service
metadata:
  name: jenkins-jnlp
  namespace: jenkins-prod
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: jenkins
  ports:
    - port: 50000
      targetPort: jnlp
---
apiVersion: cloud.google.com/v1
kind: BackendConfig
metadata:
  name: jenkins-backendconfig
  namespace: jenkins-prod
spec:
  healthCheck:
    checkIntervalSec: 15
    port: 8080
    type: HTTP
    requestPath: /login
```

---

## 8. Ingress — HTTPS Access with Managed Certificate

### What is `ingress.yaml`?

Exposes Jenkins to internal corporate users via a GCP-managed **HTTPS Load Balancer** with an automatically provisioned TLS certificate.

**Components:**

| Resource | Purpose |
|----------|---------|
| `ManagedCertificate` | GCP automatically provisions, renews, and manages the TLS cert for `jenkins.internal.enterprise.com`. No manual cert rotation needed. |
| `Ingress` | Configures the GCP HTTPS LB: terminates TLS, routes `jenkins.internal.enterprise.com/*` to the `jenkins-ui` service on port 8080 |

**Key annotations:**
```yaml
kubernetes.io/ingress.allow-http: "false"   # Force HTTPS — HTTP returns 301 redirect
nnetworking.gke.io/managed-certificates: jenkins-tls  # Attach the ManagedCertificate
cloud.google.com/backend-config: ...         # Attach health check config
```

**DNS requirement:** You must create a DNS A record:
```
jenkni.internal.enterprise.com → <LB external IP>
```
Get the IP with: `kubectl get ingress jenkins -n jenkins-prod -o jsonpath='{.status.loadBalancer.ingress[0].ip}'`

**What breaks without it?**
Jenkins is only reachable from inside the cluster. No browser access. The JNLP service still works (it's ClusterIP), but no human can use the Jenkins UI.

### `ingress.yaml`
```yaml
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: jenkins-tls
  namespace: jenkins-prod
spec:
  domains:
    - jenkins.internal.enterprise.com
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: jenkins
  namespace: jenkins-prod
  annotations:
    kubernetes.io/ingress.class: "gce"
    networking.gke.io/managed-certificates: "jenkins-tls"
    kubernetes.io/ingress.allow-http: "false"
spec:
  rules:
    - host: jenkins.internal.enterprise.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: jenkins-ui
                port:
                  number: 8080
```

---

## 9. Agent Pod Templates — JCasC ConfigMap

### What is `jenkins-agent-pod-template.yaml`?

A **ConfigMap** containing the Jenkins Configuration as Code (JCasC) YAML. Jenkins reads this on startup (and can reload it without restart) to configure the Kubernetes Cloud plugin with **5 pre-defined agent pod templates**.

**Why JCasC instead of clicking in the UI?**
- **Version controlled** — changes go through GitHub PRs
- **Auditable** — who changed what agent template and when
- **Reproducible** — destroy and recreate the Jenkins pod, configuration is identical
- **No UI drift** — the ConfigMap is the single source of truth

**The 5 Agent Pod Templates:**

| Template Label | Container Image | Used For | Key Resources |
|---------------|-----------------|----------|--------------|
| `kaniko` | `gcr.io/kaniko-project/executor:v1.23.0-debug` | Building Docker images **without Docker daemon**. Kaniko runs as non-root and doesn't need privileged mode. | CPU: 1-2, RAM: 2-4 Gi |
| `maven` | `maven:3.9.8-eclipse-temurin-17` | Java/Maven builds. Local `.m2` repo cached on emptyDir for faster dependency downloads. | CPU: 2-4, RAM: 4-8 Gi |
| `nodejs` | `node:20.17.0-bullseye-slim` | Node.js / npm / yarn builds and tests. | CPU: 1-2, RAM: 1-2 Gi |
| `sonarscanner` | `sonarsource/sonar-scanner-cli:11` | Running SonarQube SAST scans. `SONAR_HOST_URL` and `SONAR_TOKEN` injected from K8s Secret. | CPU: 0.5-1, RAM: 1-2 Gi |
| `terraform` | `hashicorp/terraform:1.9.5` | Running `terraform plan/apply` from pipeline. Uses Workload Identity for GCP authentication. | CPU: 0.5-1, RAM: 512Mi-1Gi |

**Why Kaniko instead of Docker-in-Docker (DinD)?**
DinD requires `privileged: true` on the pod, which is a critical security risk (privileged containers can escape to the host). Kaniko builds images directly from a Dockerfile into a registry without needing the Docker daemon or any elevated privileges.

**What breaks without it?**
Jenkins starts with no Kubernetes Cloud configuration. The `kubernetes` cloud doesn't exist in Jenkins. All `agent { label 'kaniko' }` pipeline declarations fail with "No such label" errors. All CI builds break.

!!! warning "Workload Identity Note"
    Agent pods authenticate to GCP APIs (Artifact Registry, GCS) via the `jenkins-agent` KSA's Workload Identity binding. No `key.json` files are mounted. If you see `UNAUTHENTICATED` errors in agent builds, check that the WI binding between `jenkins-agent` KSA and the GSA is correctly set up with:
    ```bash
    gcloud iam service-accounts add-iam-policy-binding \
      jenkins-agent@enterprise-platform-prod.iam.gserviceaccount.com \
      --role roles/iam.workloadIdentityUser \
      --member "serviceAccount:enterprise-platform-prod.svc.id.goog[jenkins-agents/jenkins-agent]"
    ```

!!! tip "Scaling Agent Pools"
    The `jenkins-agents-pool` node pool should have **cluster autoscaler enabled** with `minNodeCount=0` and `maxNodeCount=20`. When no builds are queued, the pool scales to zero nodes (saving ~$200/day on n2-standard-8 instances). New build requests trigger node provisioning in ~90 seconds.

### `jenkins-agent-pod-template.yaml`
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jenkins-casc
  namespace: jenkins-prod
data:
  jenkins.yaml: |
    jenkins:
      clouds:
        - kubernetes:
            name: "kubernetes"
            serverUrl: "https://kubernetes.default.svc"
            namespace: "jenkins-agents"
            jenkinsTunnel: "jenkins-jnlp.jenkins-prod.svc.cluster.local:50000"
            jenkinsUrl: "http://jenkins-ui.jenkins-prod.svc.cluster.local:8080"
            maxRequestsPerHostStr: "32"
            podTemplates:
              - name: "kaniko-agent"
                label: "kaniko"
                serviceAccount: "jenkins-agent"
                nodeSelector: "cloud.google.com/gke-nodepool=jenkins-agents-pool"
                containers:
                  - name: "kaniko"
                    image: "gcr.io/kaniko-project/executor:v1.23.0-debug"
                    command: "/busybox/cat"
                    ttyEnabled: true
                    resourceRequestCpu: "1000m"
                    resourceRequestMemory: "2Gi"
                    resourceLimitCpu: "2000m"
                    resourceLimitMemory: "4Gi"
                  - name: "jnlp"
                    image: "jenkins/inbound-agent:3256.v88a_f6e922152-1"
                    resourceRequestCpu: "500m"
                    resourceRequestMemory: "512Mi"
                volumes:
                  - secretVolume:
                      secretName: "kaniko-docker-config"
                      mountPath: "/kaniko/.docker"

              - name: "maven-agent"
                label: "maven"
                serviceAccount: "jenkins-agent"
                containers:
                  - name: "maven"
                    image: "maven:3.9.8-eclipse-temurin-17"
                    command: "cat"
                    ttyEnabled: true
                    resourceRequestCpu: "2000m"
                    resourceRequestMemory: "4Gi"
                    resourceLimitCpu: "4000m"
                    resourceLimitMemory: "8Gi"
                    envVars:
                      - envVar:
                          key: "MAVEN_OPTS"
                          value: "-Xmx3g -XX:+UseG1GC"
                  - name: "jnlp"
                    image: "jenkins/inbound-agent:3256.v88a_f6e922152-1"
                volumes:
                  - emptyDirVolume:
                      mountPath: "/root/.m2/repository"
                      memory: false

              - name: "nodejs-agent"
                label: "nodejs"
                containers:
                  - name: "node"
                    image: "node:20.17.0-bullseye-slim"
                    command: "cat"
                    ttyEnabled: true
                    resourceRequestCpu: "1000m"
                    resourceRequestMemory: "2Gi"
                    resourceLimitCpu: "2000m"
                    resourceLimitMemory: "4Gi"
                  - name: "jnlp"
                    image: "jenkins/inbound-agent:3256.v88a_f6e922152-1"

              - name: "sonarscanner-agent"
                label: "sonarscanner"
                containers:
                  - name: "sonar-scanner"
                    image: "sonarsource/sonar-scanner-cli:11"
                    command: "cat"
                    ttyEnabled: true
                    resourceRequestCpu: "1000m"
                    resourceRequestMemory: "2Gi"
                    resourceLimitCpu: "2000m"
                    resourceLimitMemory: "4Gi"
                    envVars:
                      - secretEnvVar:
                          key: "SONAR_HOST_URL"
                          secretName: "sonarqube-credentials"
                          secretKey: "url"
                      - secretEnvVar:
                          key: "SONAR_TOKEN"
                          secretName: "sonarqube-credentials"
                          secretKey: "token"
                  - name: "jnlp"
                    image: "jenkins/inbound-agent:3256.v88a_f6e922152-1"

              - name: "terraform-agent"
                label: "terraform"
                containers:
                  - name: "terraform"
                    image: "hashicorp/terraform:1.9.5"
                    command: "cat"
                    ttyEnabled: true
                    resourceRequestCpu: "1000m"
                    resourceRequestMemory: "2Gi"
                    resourceLimitCpu: "2000m"
                    resourceLimitMemory: "4Gi"
                    envVars:
                      - envVar:
                          key: "GOOGLE_APPLICATION_CREDENTIALS"
                          value: "/var/secrets/google/key.json"
                  - name: "jnlp"
                    image: "jenkins/inbound-agent:3256.v88a_f6e922152-1"
```
