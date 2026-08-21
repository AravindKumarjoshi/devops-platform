# Architecture Diagrams

This page documents the five core architectural flows of the Enterprise GCP DevOps & SRE Platform. Each diagram is split into focused views using tabs — start with the **Overview** tab, then drill into sub-components. All diagrams use [Mermaid.js](https://mermaid.js.org/) and can be scrolled horizontally if needed.

---

## 1. GCP Centralized Shared VPC — Platform Overview

### What this diagram shows
The platform is built on GCP's **Shared VPC** model. A single **Host Project** owns all network resources (subnets, Cloud NAT, Cloud Router, VPN/Interconnect to on-premises). Three **Service Projects** attach to it and consume the shared network without owning it. This centralizes network policy, firewall rules, and egress control in one place.

**Why Shared VPC?** It gives the Security team full control over all network egress and ingress through a single pane, while allowing individual product teams to manage their own compute resources independently.

=== "Network Foundation"

    ### Network Foundation — Host Project
    This view shows the Host Project networking core: the shared VPC, Cloud NAT for outbound internet access, Cloud Router for BGP peering, and the Interconnect/VPN that bridges GCP with your on-premises data center.

    ```mermaid
    graph LR
        subgraph OnPrem["🏢 On-Premises Data Center"]
            DC[Corporate Network]
            SNOW_OP[ServiceNow Instance]
            GHE_OP[GitHub Enterprise Server]
        end

        subgraph HostProject["🔵 Shared VPC Host Project<br>(enterprise-vpc-host)"]
            SVPC[shared-vpc Network<br>10.0.0.0/8]
            CR[Cloud Router<br>ASN 65001]
            NAT[Cloud NAT<br>Shared IP Pool]
            VPN[Cloud VPN / Interconnect<br>10Gbps Dedicated]
            FW[Cloud Firewall Rules<br>Centralized Policy]
        end

        DC <-->|"Encrypted Tunnel"| VPN
        VPN --> CR
        CR --> SVPC
        SVPC --> NAT
        NAT -->|"Outbound Internet<br>(No external IPs needed)"| Internet((Internet))
        SVPC --> FW
        SNOW_OP -->|"HTTPS"| VPN
        GHE_OP -->|"HTTPS"| VPN
    ```

    !!! info "Key Design: No External IPs"
        All GCE VMs, GKE nodes, and Cloud Build workers use **Cloud NAT** for outbound internet access. No resource has a public external IP. Inbound access is only via IAP (Identity-Aware Proxy) tunnel or Internal Load Balancers.

=== "Service Projects"

    ### Service Project Topology
    Three Service Projects attach to the Host Project and inherit its subnets. Each project is owned by a different team but all traffic flows through the centrally managed network.

    ```mermaid
    graph LR
        SVPC["Shared VPC<br>(Host Project)"] 

        subgraph GKE_PROJ["🟢 GKE Platform Project<br>(enterprise-platform-prod)"]
            GKE[GKE Cluster<br>gke-prod-us-central1]
            AR[Artifact Registry]
            CB[Cloud Build]
        end

        subgraph DATA_PROJ["🟡 Data Platform Project<br>(enterprise-data-prod)"]
            BQ[BigQuery<br>Data Warehouse]
            DP[Dataproc<br>Spark/Hadoop]
            GCS[Cloud Storage<br>Data Lake]
        end

        subgraph APP_PROJ["🟠 App Platform Project<br>(enterprise-app-prod)"]
            CF_SNOW[Cloud Function<br>ServiceNow Webhook]
            CF_SLACK[Cloud Function<br>Slack PagerDuty Bot]
            CR_RUN[Cloud Run<br>App Services]
        end

        SVPC -->|"Subnet: gke-nodes-subnet"| GKE_PROJ
        SVPC -->|"Subnet: data-subnet"| DATA_PROJ
        SVPC -->|"Subnet: app-subnet"| APP_PROJ
    ```

=== "Security Perimeter"

    ### VPC Service Controls & IAM
    **VPC Service Controls** wraps all three service projects in a security perimeter. API calls that would move data outside the perimeter (e.g., a BigQuery export to an external GCS bucket) are automatically blocked.

    ```mermaid
    graph TD
        subgraph VPC_SC["🔒 VPC Service Controls Perimeter"]
            subgraph PROJECTS["Protected Projects"]
                P1[GKE Platform Project]
                P2[Data Platform Project]
                P3[App Platform Project]
            end
            KMS[Cloud KMS<br>Key Management]
            SM[Secret Manager<br>Credentials Store]
        end

        IAM["Cloud IAM<br>Workload Identity<br>Least Privilege"] 
        CALOG["Cloud Audit Logs<br>All Admin Activity"]
        SCC["Security Command Center<br>Threat Detection"]

        IAM -->|"Controls access to"| VPC_SC
        PROJECTS -->|"All actions logged"| CALOG
        CALOG --> SCC
        KMS -->|"Encrypts data at rest<br>in all projects"| PROJECTS
        SM -->|"Injects secrets at runtime<br>(no hardcoded creds)"| PROJECTS
    ```

    !!! warning "VPC-SC Access Policy"
        Any new GCP API that a service project needs must be added to the VPC-SC **access policy** via a PR in the `terraform/vpc-service-controls/` directory. Requests go through SecOps review.

=== "External Integrations"

    ### External System Integration Points
    ServiceNow (on-prem ITSM) and GitHub Enterprise connect to GCP through the VPN tunnel, hitting API Gateway and Cloud Build respectively.

    ```mermaid
    graph LR
        subgraph External["🌐 External Systems"]
            SNOW[ServiceNow<br>On-Premises]
            GHE[GitHub Enterprise<br>On-Premises]
            PD[PagerDuty<br>SaaS]
            DD[Datadog<br>SaaS]
        end

        subgraph GCP["☁️ GCP Entry Points"]
            APIGW[API Gateway<br>OpenAPI spec<br>Auth + Rate limiting]
            CBT[Cloud Build Trigger<br>GitHub App]
            CF_SNOW[Cloud Function<br>SNOW Webhook Handler]
            CF_SLACK[Cloud Function<br>Slack → PD Bot]
        end

        SNOW -->|"Outbound REST<br>HMAC-SHA256 signed"| APIGW
        APIGW --> CF_SNOW
        CF_SNOW -->|"IAM grants /<br>VM creation"| GCP

        GHE -->|"Webhook push event"| CBT
        CBT -->|"Triggers pipeline"| GCP

        CF_SLACK -->|"POST /incidents"| PD
        GCP -->|"Agent metrics/logs"| DD
    ```

---

## 2. Jenkins on GKE — Controller & Dynamic Agent Architecture

### What this diagram shows
Jenkins runs as a single **Controller Pod** in the `jenkins-prod` namespace. It never executes builds itself. Instead, it uses the **Kubernetes Cloud plugin** to dynamically spawn ephemeral **Agent Pods** in the `jenkins-agents` namespace — one pod per build stage. When the stage finishes, the pod is destroyed. This means:
- **Zero idle agents** wasting resources
- **Each build gets a clean, fresh environment**
- **Different build types get different pod templates** (Maven ≠ Node.js ≠ Kaniko)

=== "Cluster Overview"

    ### GKE Cluster Layout
    The cluster uses dedicated **Node Pools** — the Controller runs on a small stable pool, agents run on a larger auto-scaling pool with different machine types.

    ```mermaid
    graph TD
        subgraph GKE["☸️ GKE Cluster: enterprise-gke-prod-us-central1"]
            subgraph NP1["Node Pool: jenkins-controller-pool<br>n2-standard-4 × 1-2 nodes"]
                JC["Jenkins Controller Pod<br>jenkins/jenkins:2.462.3-lts-jdk17<br>CPU: 2-4 cores | RAM: 4-8 Gi"]
            end
            subgraph NP2["Node Pool: jenkins-agents-pool<br>n2-standard-8 × 0-20 nodes (autoscaled)"]
                AG1[Kaniko Agent Pod]
                AG2[Maven Agent Pod]
                AG3[NodeJS Agent Pod]
                AG4[SonarScanner Pod]
                AG5[Terraform Pod]
            end
        end

        JC -->|"K8s API: create pod"| AG1
        JC -->|"K8s API: create pod"| AG2
        JC -->|"K8s API: create pod"| AG3
        JC -->|"K8s API: create pod"| AG4
        JC -->|"K8s API: create pod"| AG5
    ```

    !!! tip "Cluster Autoscaler"
        The `jenkins-agents-pool` has **min=0, max=20 nodes**. When no builds are running, the pool scales to zero, saving cost. Scale-up takes ~90 seconds for a new GCE node.

=== "Networking & Storage"

    ### How traffic reaches Jenkins & how agents connect back

    ```mermaid
    graph LR
        DEV(["👤 Developer Browser"])
        
        subgraph GCP_LB["GCP Load Balancing"]
            HTTPS_LB["Internal HTTPS LB<br>(GCP managed cert)"]
        end

        subgraph NS_INGRESS["Namespace: ingress-nginx"]
            ING[Ingress Resource<br>Host: jenkins.internal.enterprise.com]
        end

        subgraph NS_PROD["Namespace: jenkins-prod"]
            SVC_UI["Service: jenkins-ui<br>ClusterIP :8080"]
            SVC_JNLP["Service: jenkins-jnlp<br>ClusterIP :50000"]
            JC_POD[Jenkins Controller Pod]
            PVC[("PVC: jenkins-home<br>100 Gi SSD Regional-PD")]
        end

        subgraph NS_AGENTS["Namespace: jenkins-agents"]
            AGENT[Agent Pod<br>(ephemeral)]
        end

        DEV --> HTTPS_LB
        HTTPS_LB --> ING
        ING --> SVC_UI
        SVC_UI --> JC_POD
        JC_POD --- PVC
        AGENT -->|"JNLP connect-back<br>port 50000"| SVC_JNLP
        SVC_JNLP --> JC_POD
    ```

=== "Workload Identity"

    ### Zero Static Keys — Workload Identity Flow
    No service account JSON keys exist anywhere. Pods authenticate to GCP APIs via **Workload Identity**, which maps a Kubernetes ServiceAccount to a GCP Service Account.

    ```mermaid
    graph LR
        subgraph K8S["Kubernetes"]
            KSA_C["KSA: jenkins-controller<br>Namespace: jenkins-prod"]
            KSA_A["KSA: jenkins-agent<br>Namespace: jenkins-agents"]
        end

        subgraph GCP_IAM["GCP IAM"]
            GSA_C["GSA: jenkins-controller<br>@enterprise-platform-prod"]
            GSA_A["GSA: jenkins-agent<br>@enterprise-platform-prod"]
        end

        subgraph GCP_APIS["GCP APIs"]
            AR["Artifact Registry<br>roles/artifactregistry.writer"]
            GKE_API["GKE API<br>roles/container.developer"]
            GCS["Cloud Storage<br>roles/storage.objectAdmin"]
        end

        KSA_C -->|"WI annotation binding"| GSA_C
        KSA_A -->|"WI annotation binding"| GSA_A
        GSA_C --> GKE_API
        GSA_A --> AR
        GSA_A --> GCS
    ```

    !!! success "Security Benefit"
        Workload Identity tokens are **short-lived** (1 hour), **automatically rotated**, and **scoped to the pod's service account**. A compromised agent pod cannot access resources beyond its GSA's permissions.

---

## 3. CI/CD Pipeline — Git to Genesis Platform (GKE)

### What this diagram shows
The end-to-end journey of a code change from a developer's laptop to the production **Genesis GKE** cluster. The pipeline enforces three hard gates:
1. **SonarQube Quality Gate** — SAST scan + coverage threshold (blocks on failure)
2. **Artifactory upload** — artifact must be stored and immutable before deploy
3. **Manual approval** — a human (or policy engine) must approve production deploys

=== "Pipeline Stages"

    ```mermaid
    sequenceDiagram
        autonumber
        participant Dev as "👤 Developer"
        participant GH as "GitHub Enterprise"
        participant JK as "Jenkins"
        participant SQ as "SonarQube"
        participant ART as "Artifactory"

        Dev->>GH: git push / open PR
        GH->>JK: Webhook: push event + commit SHA
        JK->>JK: Stage 1 — Checkout & lint<br>(Dockerfile, YAML, shellcheck)
        JK->>JK: Stage 2 — Unit tests<br>(Maven / npm test)
        JK->>SQ: Stage 3 — SAST scan<br>+ code coverage upload
        SQ-->>JK: Quality Gate: PASSED ✅<br>(coverage ≥ 80%, no critical issues)
        JK->>ART: Stage 4 — Build & push Docker image<br>tag: {build-number}-{git-sha:8}
        ART-->>JK: Image URL confirmed + digest
    ```

=== "Approval & Deploy"

    ```mermaid
    sequenceDiagram
        autonumber
        participant JK as "Jenkins"
        participant GATE as "Approval Gate"
        participant GKE as "Genesis GKE"
        participant SLACK as "Slack #platform-releases"

        JK->>GATE: Request production approval<br>(image: myapp-142-a3f21b4c)
        Note over GATE: Human approves OR<br>policy engine auto-approves<br>(non-prod environments)
        GATE-->>JK: ✅ Approved by: sre-lead@enterprise.com
        JK->>GKE: helm upgrade --install myapp ./chart<br>--set image.tag=142-a3f21b4c<br>--wait --timeout 5m
        GKE-->>JK: Rollout complete: 3/3 pods Ready
        JK->>SLACK: ✅ myapp v142 deployed to prod<br>Duration: 4m 32s | Image: ...a3f21b4c
    ```

=== "Failure Paths"

    ```mermaid
    sequenceDiagram
        autonumber
        participant JK as "Jenkins"
        participant SQ as "SonarQube"
        participant GKE as "Genesis GKE"
        participant SLACK as "Slack"
        participant Dev as "👤 Developer"

        Note over JK,SQ: Scenario A — Quality Gate Failure
        JK->>SQ: Scan results submitted
        SQ-->>JK: ❌ FAILED: coverage 61% < 80% threshold<br>3 critical vulnerabilities found
        JK->>Dev: GitHub PR annotation with failure details
        JK->>SLACK: ❌ Build #142 FAILED — QG: coverage too low
        Note over JK,SLACK: Pipeline STOPS. No artifact pushed.

        Note over JK,GKE: Scenario B — Rollout Failure
        JK->>GKE: helm upgrade --install ...
        GKE-->>JK: ❌ Timeout: 1/3 pods Ready<br>CrashLoopBackOff detected
        JK->>GKE: helm rollback myapp (auto)
        GKE-->>JK: Rolled back to revision 141
        JK->>SLACK: ⚠️ Deploy FAILED + rolled back<br>Previous version restored
    ```

---

## 4. SRE Alert Flow — Slack to PagerDuty to Engineer

### What this diagram shows
Any engineer can trigger a **PagerDuty incident** directly from Slack by typing `@pagerduty <team-name> <description>`. A Cloud Function bot handles the entire workflow: authenticating the request, looking up who is currently on-call, creating the incident, emailing the team distribution list, and confirming back in the Slack thread — all within seconds.

**Why this exists:** During a P1 incident, engineers shouldn't need to leave Slack, log into PagerDuty, find the right schedule, and manually create an incident. This removes all friction.

=== "Trigger & Authentication"

    ```mermaid
    sequenceDiagram
        autonumber
        participant ENG as "👤 SRE Engineer"
        participant SLACK as "Slack"
        participant BOT as "Cloud Function Bot<br>(Python / Flask)"

        ENG->>SLACK: @pagerduty platform-sre<br>P1: DB connection pool exhausted
        SLACK->>BOT: POST /slack/events<br>{event_callback, text, channel, ts}
        BOT->>BOT: 1. Check X-Slack-Request-Timestamp<br>   (reject if > 5 min old — replay attack)
        BOT->>BOT: 2. Compute HMAC-SHA256<br>   sig = hmac(SIGNING_SECRET, v0:ts:body)
        BOT->>BOT: 3. compare_digest(computed, X-Slack-Signature)<br>   ✅ Signature valid
        BOT->>BOT: 4. Regex parse:<br>   team = platform-sre<br>   body = P1: DB connection pool exhausted
    ```

=== "PagerDuty Lookup & Page"

    ```mermaid
    sequenceDiagram
        autonumber
        participant BOT as "Cloud Function Bot"
        participant PD as "PagerDuty API v2"
        participant ENG as "📟 On-Call Engineer"

        BOT->>PD: GET /schedules?query=platform-sre<br>Authorization: Token token={PD_API_TOKEN}
        PD-->>BOT: [{id: SCH001, name: Platform SRE Rotation}]
        BOT->>PD: GET /oncalls?schedule_ids[]=SCH001<br>&earliest=true
        PD-->>BOT: [{user: {name: Jane Smith,<br>  email: jane@enterprise.com}}]
        BOT->>PD: POST /incidents<br>{title, service_id, escalation_policy,<br> urgency: high, body: full message}
        PD-->>BOT: {incident: {id: INC-4821,<br>  html_url: pagerduty.com/...}}
        PD->>ENG: 📱 Push notification + SMS page
    ```

=== "Notification & Reply"

    ```mermaid
    sequenceDiagram
        autonumber
        participant BOT as "Cloud Function Bot"
        participant SG as "SendGrid API"
        participant DL as "platform-sre-dl@enterprise.com"
        participant SLACK as "Slack"

        BOT->>SG: POST /v3/mail/send<br>{to: platform-sre-dl@enterprise.com,<br> subject: PagerDuty Incident INC-4821,<br> html: full incident details table}
        SG-->>BOT: 202 Accepted
        SG->>DL: 📧 HTML email delivered to all DL members
        BOT->>SLACK: chat.postMessage (thread reply)<br>"✅ Incident INC-4821 created<br>📟 On-call: Jane Smith<br>🔗 pagerduty.com/incidents/INC-4821"
        Note over SLACK: Reply appears in thread<br>under original @pagerduty message
    ```

---

## 5. Golden Image Baking — GitOps Flow

### What this diagram shows
Every change to a VM base image must go through this pipeline. No one can SSH into a running VM and install packages — **all image changes are GitOps-driven**. The pipeline ensures every image is CIS-hardened, audited, and traceable to a ServiceNow ticket.

**Why immutable images?** If a VM is compromised or drifts from its intended state, you don't fix it — you replace it with a fresh image. This is **infrastructure cattle, not pets**.

=== "Request & Review"

    ```mermaid
    sequenceDiagram
        autonumber
        participant DEV as "👤 Developer"
        participant SNOW as "ServiceNow"
        participant GH as "GitHub PR"
        participant SECOPS as "🔒 SecOps Reviewer"
        participant SRE as "☸️ SRE Reviewer"

        DEV->>SNOW: File RITM ticket:<br>"Add nodejs 20.x to base image<br>Reason: App team requirement"
        SNOW-->>DEV: RITM0042819 approved for implementation
        DEV->>GH: git checkout -b feat/RITM0042819-add-nodejs20
        DEV->>GH: Edit ansible-playbook.yaml<br>(add nodejs to apt_packages list)
        DEV->>GH: Open PR — fill PULL_REQUEST_TEMPLATE.md<br>(ticket link + justification + SecOps checklist)
        GH->>SECOPS: Review request (CODEOWNERS mandatory)
        SECOPS->>GH: ✅ CIS L1 check: no new SUID binaries<br>   CVE scan: clean<br>   UFW: no new external ports
        GH->>SRE: Review request (2 approvals required)
        SRE->>GH: ✅ Approve
    ```

=== "Build & Provision"

    ```mermaid
    sequenceDiagram
        autonumber
        participant GH as "GitHub"
        participant CB as "Cloud Build"
        participant PKR as "Packer"
        participant VM as "GCP Builder VM<br>(temporary, no external IP)"
        participant ANS as "Ansible"

        GH->>CB: PR merge → Cloud Build trigger fires
        CB->>PKR: packer init (download plugins)
        CB->>PKR: packer validate (syntax + API check)
        PKR-->>CB: ✅ Validation passed
        CB->>PKR: packer build<br>(IAP tunnel SSH, no external IP)
        PKR->>VM: Launch n2-standard-4 from debian-12 base
        PKR->>ANS: Invoke ansible-playbook provisioner<br>(over IAP tunnel)
        ANS->>VM: Play 1: CIS L1 hardening<br>(sysctl, auditd, SSH config, AppArmor)
        ANS->>VM: Play 2: UFW firewall rules
        ANS->>VM: Play 3: Dev packages<br>(nodejs, docker, kubectl, helm, terraform)
        ANS->>VM: Play 4: GCP Ops Agent
        ANS->>VM: Play 5: Datadog Agent
        ANS->>VM: Play 6: Pre-snapshot cleanup<br>(bash_history, SSH host keys, apt cache, logs)
        ANS-->>PKR: Provisioning complete ✅
    ```

=== "Image Capture & Notify"

    ```mermaid
    sequenceDiagram
        autonumber
        participant PKR as "Packer"
        participant GCP as "GCP Image Family<br>(enterprise-images project)"
        participant CB as "Cloud Build"
        participant SNOW as "ServiceNow API"
        participant SLACK as "Slack #platform-releases"

        PKR->>GCP: Stop VM + capture disk snapshot
        GCP-->>PKR: Image created:<br>enterprise-debian12-base-143-a3f21b4c
        PKR->>GCP: Set image family:<br>enterprise-debian12-base (latest pointer updated)
        GCP-->>CB: Build step complete
        CB->>SNOW: PATCH /api/now/table/sc_req_item/RITM0042819<br>{state: implemented, image: enterprise-debian12-base-143}
        SNOW-->>CB: 200 OK — ticket updated
        CB->>SLACK: ✅ Golden image build #143 SUCCESS<br>enterprise-debian12-base-143-a3f21b4c<br>Duration: 18m 42s
        CB->>GH: Post PR comment:<br>✅ Image: enterprise-debian12-base-143-a3f21b4c
    ```

---

## Key Design Principles

| Principle | Implementation |
|-----------|---------------|
| **GitOps Single Source of Truth** | All infra declared in Git. Direct resource changes are blocked and alerted on via Cloud Audit Logs. |
| **Immutable Images** | VMs are replaced, never patched in place. Every image is traceable to a git commit and SNOW ticket. |
| **Workload Identity** | Zero static service account keys. All pods use KSA→GSA binding with short-lived tokens. |
| **Least-Privilege IAM** | Every GSA has exactly the roles it needs, nothing more. Reviewed quarterly by SecOps. |
| **VPC Service Controls** | Data exfiltration blocked at the API layer. No data can leave the perimeter without explicit policy. |
| **CIS L1 Baseline** | All OS images and GKE node pools continuously audited. Non-compliant resources trigger alerts. |
| **Mandatory SecOps Review** | Any image recipe change requires a SecOps approval before merge is permitted. |
| **Automated CMDB Updates** | Every build pipeline updates ServiceNow CMDB on success. No manual CMDB entries. |
| **No Secrets in Code** | All secrets live in Secret Manager. GitHub Push Protection blocks accidental commits. |
