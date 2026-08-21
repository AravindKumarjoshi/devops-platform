# Jenkins on GKE — Kubernetes Manifests

This documentation page details the Kubernetes manifests used to deploy Jenkins 2.462.3 LTS on Google Kubernetes Engine (GKE). The deployment leverages Jenkins Configuration as Code (JCasC) to automate and manage the setup, ensuring reproducible builds. It utilizes Workload Identity for a zero static keys approach, eliminating the need to manage and rotate long-lived service account keys. The Kubernetes Cloud plugin is configured to provision dynamic, ephemeral agents on-demand. Additionally, a regional SSD persistent volume is employed for the Jenkins home directory to provide high performance and data resilience across zones.

!!! info "Namespace Strategy"
    This architecture utilizes two dedicated namespaces: `jenkins-prod` for the Jenkins controller and associated resources, and `jenkins-agents` exclusively for dynamic, ephemeral build pods. This isolation improves security and manageability while allowing distinct resource quotas and network policies to be enforced for controller stability and build predictability.

## 1. Namespaces & Resource Quotas
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

## 2. StorageClass (GCP SSD Regional PD)
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

## 3. Persistent Volume Claim
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

## 4. Service Accounts (Workload Identity)
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

## 5. RBAC — ClusterRole & Bindings
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

## 6. Jenkins Controller Deployment
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

## 7. Services
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

## 8. Ingress (GKE HTTPS LB + Managed Certificate)
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

## 9. Agent Pod Templates (JCasC ConfigMap)
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

!!! warning "Workload Identity Note"
    Agent pods use Workload Identity via the `serviceAccount` annotation. No physical `key.json` files are mounted in production. The `GOOGLE_APPLICATION_CREDENTIALS` reference in the `terraform-agent` is for illustration of the environment variable pattern — Workload Identity is the actual mechanism seamlessly providing credentials to the Google Cloud SDKs.

!!! tip "Scaling Agent Pools"
    It is highly recommended to use separate GKE node pools with taints and tolerations specifically for agent workloads. Enabling the cluster autoscaler on these agent pools ensures dynamic provisioning of resources when builds queue up, and automatic downscaling when idle to save costs.
