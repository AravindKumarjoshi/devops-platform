# Architecture Diagrams

Welcome to the Enterprise GCP DevOps & SRE Platform architecture documentation. This platform embodies a strong GitOps culture, ensuring that all infrastructure and platform changes are version-controlled, auditable, and peer-reviewed. The diagrams below map out the critical systems within our environment, illustrating how the centralized shared VPC, CI/CD pipelines, SRE alert flows, and golden image pipelines are orchestrated to deliver a secure, scalable, and resilient platform.

---

## 1. GCP Centralized Shared VPC — Platform Overview

Our GCP infrastructure leverages a Centralized Shared VPC model to maintain strict network isolation and centralized security controls. The Shared VPC Host Project provides the core networking infrastructure, including the shared-vpc network, Cloud NAT, Cloud Router, and Interconnect/VPN back to our on-premises data centers. Service projects are attached to this host, allowing the GKE Platform, Data Platform, and App Platform to consume the shared network while remaining logically isolated. Additionally, VPC Service Controls establish a security perimeter around these projects to prevent data exfiltration, and Private Google Access ensures secure communication with Google APIs.

```mermaid
graph TD
    subgraph On-Premises
        SNOW[ServiceNow]
        GHE[GitHub Enterprise]
    end

    subgraph Cross-Cutting Services
        KMS[Cloud KMS]
        IAM[IAM & Workload Identity]
    end

    subgraph VPC-SC Perimeter
        subgraph SharedVPC_Host_Project
            SVPC[shared-vpc network]
            NAT[Cloud NAT]
            CR[Cloud Router]
            VPN[Interconnect/VPN]
        end

        subgraph GKE-Platform-Project
            GKE[GKE Cluster]
            AR[Artifact Registry]
            CB[Cloud Build]
            subgraph GKE_Namespaces
                JNS[jenkins-prod]
                APPNS[app namespaces]
            end
            GKE --> GKE_Namespaces
        end

        subgraph Data-Platform-Project
            DP[Dataproc]
            BQ[BigQuery]
            GCS[Cloud Storage]
        end

        subgraph App-Platform-Project
            CRUN[Cloud Run]
            CF_SNOW[Cloud Function - SNOW Webhook]
            CF_SLACK[Cloud Function - Slack PD Bot]
        end
    end

    SVPC --> GKE-Platform-Project
    SVPC --> Data-Platform-Project
    SVPC --> App-Platform-Project
    
    CR --> NAT
    CR --> VPN
    VPN <--> On-Premises
    
    SNOW --> |API Calls| API_GW[API Gateway]
    API_GW --> |Trigger| CF_SNOW
    
    GHE --> |Webhooks| CB
    CB --> |Push Images| AR
    
    KMS -.-> |Key Mgmt| GKE-Platform-Project
    KMS -.-> |Key Mgmt| Data-Platform-Project
    KMS -.-> |Key Mgmt| App-Platform-Project
    
    IAM -.-> |AuthZ & GSA bindings| GKE-Platform-Project
    IAM -.-> |AuthZ & GSA bindings| Data-Platform-Project
    IAM -.-> |AuthZ & GSA bindings| App-Platform-Project
```

---

## 2. Jenkins on GKE — Controller & Dynamic Agent Architecture

Our CI/CD workhorse is Jenkins running securely on Google Kubernetes Engine. Configuration is managed strictly via Jenkins Configuration as Code (JCasC), minimizing drift and manual UI changes. The setup relies on the Kubernetes Cloud plugin to dynamically provision ephemeral build agents tailored to specific tasks, minimizing resource usage and attack surface. Agents authenticate to Google services, such as Artifact Registry, seamlessly and securely via Workload Identity without needing static service account keys, while the Jenkins Controller relies on a resilient regional SSD PersistentVolumeClaim (PVC) for configuration and job history persistence.

```mermaid
graph TD
    DEV[Developer Browser]
    GHE[GitHub Enterprise]
    SONAR[SonarQube External]
    GCP_AR[Artifact Registry]
    WI[Workload Identity Binding]

    subgraph GKE Cluster
        subgraph ingress-nginx namespace
            ING[Ingress Resource]
            ILB[Internal GCP HTTPS LB]
        end

        subgraph jenkins-prod namespace
            JC[Jenkins Controller Pod\nJCasC mounted]
            PVC[(PVC jenkins-home 100Gi SSD)]
            JUI[Jenkins UI Service\nClusterIP 8080]
            JJNLP[Jenkins JNLP Service\nClusterIP 50000]
            JC --- PVC
        end

        subgraph jenkins-agents namespace
            KAN[Kaniko Agent Pod]
            MAV[Maven Agent Pod]
            NOD[NodeJS Agent Pod]
            SON[SonarScanner Agent Pod]
            TF[Terraform Agent Pod]
        end
    end

    DEV --> ILB
    ILB --> ING
    ING --> JUI
    JUI --> JC

    JC --> |Spawns Pods| KAN
    JC --> |Spawns Pods| MAV
    JC --> |Spawns Pods| NOD
    JC --> |Spawns Pods| SON
    JC --> |Spawns Pods| TF

    JJNLP <--> |Agent Communication| KAN
    JJNLP <--> |Agent Communication| MAV
    JJNLP <--> |Agent Communication| NOD
    JJNLP <--> |Agent Communication| SON
    JJNLP <--> |Agent Communication| TF

    KAN --> |Push| GCP_AR
    MAV -.-> |WI Auth| WI
    NOD -.-> |WI Auth| WI

    WI -.-> GCP_AR
    SON --> |Scan| SONAR
```

---

## 3. CI/CD Pipeline — Git to Genesis Platform (GKE)

The core deployment pipeline enforces a strict progression from version control to the production Genesis GKE platform. It guarantees that all code is validated, scanned, and formally approved before taking effect. Upon a Git push, Jenkins orchestrates linting, unit tests, and a rigorous SonarQube SAST and coverage analysis. Failure at the quality gate blocks the pipeline and alerts the developer; success triggers the creation and storage of an immutable artifact in Artifactory. Following manual or policy-engine approval, Jenkins initiates a Helm-based deployment to the Genesis cluster, equipped with automated rollback in case the new release fails to stabilize.

```mermaid
sequenceDiagram
    participant Developer
    participant GitHub_Enterprise
    participant Jenkins
    participant SonarQube
    participant Artifactory
    participant ApprovalGate
    participant GenesisGKE
    participant Slack

    Developer->>GitHub_Enterprise: git push / PR open
    GitHub_Enterprise->>Jenkins: Webhook trigger (push event)
    Jenkins->>Jenkins: Checkout, Dockerfile lint, Unit Tests
    Jenkins->>SonarQube: SAST scan + coverage analysis
    SonarQube-->>Jenkins: Quality Gate result (pass/fail)
    
    alt Quality Gate FAILED
        Jenkins->>Slack: Notify failure
        Jenkins->>Developer: Annotate PR with failures
    else Quality Gate PASSED
        Jenkins->>Artifactory: Push artifact/Docker image (tagged with build number + git SHA)
        Artifactory-->>Jenkins: Artifact URL confirmed
        Jenkins->>ApprovalGate: Request manual approval (Prod deploy)
        ApprovalGate-->>Jenkins: Approved (human or policy engine)
        Jenkins->>GenesisGKE: helm upgrade --install (with image tag)
        GenesisGKE-->>Jenkins: Rollout status
        
        alt Rollout FAILED
            Jenkins->>GenesisGKE: helm rollback
            Jenkins->>Slack: Alert rollback
        else Rollout SUCCESS
            Jenkins->>Slack: Deploy success notification with image tag + duration
        end
    end
```

---

## 4. SRE Alert Flow — Slack to PagerDuty to Engineer

In high-pressure situations, manual incident escalation is prone to delays. Our custom Slack bot streamlines the process by integrating directly with the PagerDuty API v2. When an engineer triggers an alert via Slack, a Cloud Function verifies the payload security and parses the request. It then dynamically looks up the current on-call engineer using PagerDuty's schedule and on-call endpoints before creating a high-urgency incident. Simultaneously, a formal notification is broadcasted to the SRE distribution list via SendGrid, and the engineer in Slack receives a thread reply confirming the incident assignment.

```mermaid
sequenceDiagram
    participant SRE_Engineer
    participant Slack
    participant CloudFunction_Bot
    participant PagerDuty_API
    participant SendGrid
    participant OnCall_Engineer

    SRE_Engineer->>Slack: @pagerduty platform-sre P1: DB connection pool exhausted
    Slack->>CloudFunction_Bot: Events API POST (event_callback)
    CloudFunction_Bot->>CloudFunction_Bot: Verify Slack signing secret (HMAC-SHA256)
    CloudFunction_Bot->>CloudFunction_Bot: Regex parse team=platform-sre, message body
    CloudFunction_Bot->>PagerDuty_API: GET /schedules?query=platform-sre
    PagerDuty_API-->>CloudFunction_Bot: Schedule ID list
    CloudFunction_Bot->>PagerDuty_API: GET /oncalls?schedule_ids[]=SCH001&earliest=true
    PagerDuty_API-->>CloudFunction_Bot: on_call: Jane Smith (jane@enterprise.com)
    CloudFunction_Bot->>PagerDuty_API: POST /incidents {title, service_id, urgency:high}
    PagerDuty_API-->>CloudFunction_Bot: Incident URL INC-4821
    PagerDuty_API->>OnCall_Engineer: Page / push notification
    CloudFunction_Bot->>SendGrid: Send HTML email to platform-sre-dl@enterprise.com
    SendGrid-->>CloudFunction_Bot: 202 Accepted
    CloudFunction_Bot->>Slack: Reply in thread: Incident INC-4821 created. On-call: Jane Smith.
```

---

## 5. Golden Image Baking — GitOps Flow

To ensure all compute instances comply with enterprise security standards, we employ an automated GitOps workflow for building Golden Images. The process is fully auditable, originating from a ServiceNow ticket and progressing through mandatory peer and SecOps reviews on GitHub. Cloud Build coordinates the execution of Packer and Ansible, which harden the base image according to CIS Level 1 benchmarks, configure firewalls, install necessary toolchains (like Node.js, Docker, Kubernetes tools), and embed monitoring agents. The resulting immutable image serves as the single source of truth for VM deployments, and the provisioning system automatically updates CMDB records upon success.

```mermaid
sequenceDiagram
    participant Developer
    participant ServiceNow
    participant GitHub_PR
    participant SecOps_Reviewer
    participant SRE_Reviewer
    participant CloudBuild
    participant Packer
    participant Ansible
    participant GCP_Images

    Developer->>ServiceNow: Create RITM/CHG ticket (package addition request)
    ServiceNow-->>Developer: Ticket RITM0042819 approved for PR
    Developer->>GitHub_PR: git checkout -b feat/RITM0042819-add-nodejs20 && git push
    Developer->>GitHub_PR: Open PR (fill PULL_REQUEST_TEMPLATE.md)
    GitHub_PR->>SecOps_Reviewer: Review request (mandatory)
    SecOps_Reviewer->>GitHub_PR: Review: CIS L1 checklist verified, CVE scan clean ✓
    GitHub_PR->>SRE_Reviewer: Review request (2 SRE approvals required)
    SRE_Reviewer->>GitHub_PR: Approve ✓
    GitHub_PR->>CloudBuild: PR merged → Cloud Build trigger fires
    CloudBuild->>Packer: packer init && packer validate
    Packer-->>CloudBuild: Validation OK
    CloudBuild->>Packer: packer build (GCP builder, IAP tunnel, no external IP)
    Packer->>Ansible: Invoke ansible-playbook provisioner
    
    Ansible->>Ansible: Play 1: CIS L1 hardening (sysctl, auditd, SSH, AppArmor)
    Ansible->>Ansible: Play 2: UFW firewall rules
    Ansible->>Ansible: Play 3: Install packages (nodejs20, docker, kubectl, helm)
    Ansible->>Ansible: Play 4: GCP Ops Agent
    Ansible->>Ansible: Play 5: Datadog Agent
    Ansible->>Ansible: Play 6: Pre-snapshot cleanup (bash_history, SSH host keys, logs)
    
    Ansible-->>Packer: Provisioning complete
    Packer->>GCP_Images: Capture image → enterprise-debian12-base-{build}-{sha}
    GCP_Images-->>CloudBuild: Image family updated
    CloudBuild->>ServiceNow: REST API: Update RITM0042819 → Implemented
    CloudBuild->>GitHub_PR: Post success comment with image name
```

---

## Key Design Principles

The architecture illustrated above is governed by a set of core engineering principles designed to meet enterprise compliance and availability requirements:

*   **GitOps Single Source of Truth:** All infrastructure and platform configurations are declared in version control. Direct manual changes to resources are prohibited.
*   **Immutable Images:** Virtual machines and containers are deployed from immutable golden images that pass rigorous security checks during the build phase.
*   **Workload Identity:** Services authenticate dynamically using Google Cloud Workload Identity. No static, long-lived service account keys are stored or transmitted.
*   **Least-Privilege IAM:** Access to resources and APIs is strictly limited by fine-grained Identity and Access Management policies, enforcing minimum necessary permissions.
*   **VPC Service Controls:** Cloud resources are encapsulated within a secure perimeter, preventing unauthorized data access or exfiltration.
*   **CIS L1 Baseline Mandatory:** All OS images and Kubernetes clusters are continuously audited against the Center for Internet Security Level 1 benchmarks.
*   **Peer and SecOps Review Required:** Changes to critical infrastructure code require multiple layers of automated checks and manual approvals from relevant domain experts.
*   **Automated CMDB Updates:** Infrastructure state changes and deployment events automatically synchronize with the central Configuration Management Database (ServiceNow) for audit and tracking.
