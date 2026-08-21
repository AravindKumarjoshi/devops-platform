# Interview Questions & Answers

This document serves as a comprehensive collection of interview questions and answers, neatly categorized for clarity. 
Topics covered: Terraform, GCP, GCP DevOps, Shell Scripting, Kubernetes (K8s), Docker, DevOps, Architecture, Networking, etc.

---

## Topic: Terraform

### 1. Basics & Core Concepts

**Q: What is Terraform?**
**A:** Terraform is an open-source Infrastructure as Code (IaC) tool by HashiCorp that allows users to define and provision infrastructure using a declarative configuration language.

**Q: What is Infrastructure as Code (IaC)?**
**A:** IaC is the practice of managing and provisioning computing infrastructure through machine-readable configuration files, rather than physical hardware configuration or interactive configuration tools.

**Q: What are the key features of Terraform?**
**A:** Key features include: Execution plans, Resource graphs, Change automation, and Support for multiple providers.

**Q: What is a Terraform provider and how do you manage multiple providers?**
**A:** A provider is a plugin that allows Terraform to interact with APIs of external services (e.g., AWS, GCP, Azure). You can manage multiple providers in a single configuration by defining multiple provider blocks with lias arguments and specifying the provider = <alias> in resource definitions.

**Q: How do you upgrade provider versions and what is .terraform.lock.hcl?**
**A:** You upgrade provider versions by modifying the version in the configuration and running 	erraform init -upgrade. The .terraform.lock.hcl file records the exact provider versions used, ensuring consistent installs across different machines or CI/CD pipelines.

**Q: What is Terraform Cloud and Sentinel?**
**A:** **Terraform Cloud** is a SaaS platform by HashiCorp for managing Terraform runs, remote state, and team collaboration. **Sentinel** is a policy-as-code framework integrated into Terraform Cloud/Enterprise for enforcing governance and security policies on configurations before they are applied.

---

### 2. State Management & Backends

**Q: What is a Terraform state file and why is it important?**
**A:** The state file (	erraform.tfstate) tracks the infrastructure resources managed by Terraform, mapping real-world resources to your configuration. It is crucial because it gives Terraform a single source of truth to detect changes, plan updates accurately, and manage dependencies.

**Q: What is a backend in Terraform and how do you manage remote state?**
**A:** A backend defines where Terraform's state is stored (e.g., local, AWS S3, GCS, Azure Blob). Remote state is managed by configuring a ackend block. This allows teams to share state securely and prevents local state drift.

**Q: How do you collaborate on Terraform state with a team?**
**A:** Use remote state backends with **State Locking** enabled (e.g., S3 + DynamoDB, or GCS). Avoid manual state edits, enforce version control, and use CI/CD pipelines or Terraform Cloud for execution. 
*Follow-up: How do you handle remote state locking issues?* 
For DynamoDB/AWS, you can use 	erraform force-unlock <LOCK_ID> to remove a stale lock caused by a terminated process. Always ensure CI/CD jobs terminate cleanly.

**Q: How do you secure your Terraform state file?**
**A:** 
- Use encrypted remote backends (e.g., S3 with KMS).
- Limit access via IAM or RBAC.
- Never commit state files to source control (add to .gitignore).
- Use sensitive = true on output blocks to mask sensitive data in console output.

**Q: Your Terraform state file got corrupted or deleted accidentally. How would you recover it?**
**A:** 
- **Remote:** Use storage versioning (e.g., S3 Object Versioning) to restore a previous state file.
- **Local:** Use the 	erraform.tfstate.backup file.
- **No Backup:** Write matching .tf code and re-import resources using 	erraform import.

**Q: You committed .tfstate to Git by mistake. What do you do?**
**A:** Remove it from tracking using git rm --cached terraform.tfstate and commit. Add state files to .gitignore. Crucially, rotate any exposed credentials or secrets that were in the state file, and scan history with tools like 	ruffleHog or git-secrets.

**Q: What is the 	erraform state command used for?**
**A:** It is used for advanced manual state operations, such as listing resources (list), showing details (show), moving (mv), or removing (
m) items from the state without affecting real infrastructure.

---

### 3. Workspaces & Environments

**Q: How do you handle multi-environment (dev, staging, prod) deployments in Terraform?**
**A:** 
- **Method 1 (Separate Directories):** Use separate directories with distinct backend configs and variables (e.g., dev.tfvars, prod.tfvars).
- **Method 2 (Workspaces):** Use Terraform workspaces to manage multiple state files within a single configuration.

**Q: When should you use workspaces vs separate backends?**
**A:** 
- **Workspaces:** Best for low-complexity environments with identical configurations (e.g., transient testing environments).
- **Separate Backends (Directories):** Best for strict isolation, better auditability, and higher security between environments like Staging and Production.

---

### 4. Modules & Reusability

**Q: What are Terraform modules and how do you reuse code?**
**A:** Modules are self-contained containers for multiple resources used together. You reuse code by calling these modules (local paths or remote Git/Registry sources) across multiple projects, promoting DRY (Don't Repeat Yourself) principles.

**Q: How do you reuse a module across multiple teams and handle versioning?**
**A:** Store reusable modules in a versioned Git repo or Terraform Registry. Reference them using source URLs with version tags (e.g., source = "git::https://...ref=v1.0.0"). Enforce semantic versioning.

**Q: How do you safely upgrade a shared module without breaking infrastructure?**
**A:** Pin module versions. Test upgrades in lower environments first. Run 	erraform plan to carefully review changes. Apply incrementally and monitor impact.

**Q: What are best practices for Terraform module development?**
**A:** Keep modules small and focused, use input/output variables effectively, document usage (e.g., via 	erraform-docs), and strictly version control them.

---

### 5. Variables, Outputs & Secrets

**Q: How do you define variables and output variables?**
**A:** Variables are defined in ariable blocks to parameterize configurations. Outputs are defined in output blocks to extract and display resource attributes after deployment.

**Q: How do you handle sensitive data and secrets in Terraform?**
**A:** 
- Use secret managers (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault).
- **Never** hardcode secrets in .tf or .tfvars files.
- Pass secrets via environment variables (TF_VAR_my_secret).
- Use the sensitive = true flag on variables and outputs to mask them in logs.

---

### 6. HCL Logic, Lifecycle & Resources

**Q: Explain the use of count and or_each in Terraform.**
**A:** Both create multiple instances of a resource. 
- count uses an integer index (best for identical resources).
- or_each iterates over a map or set of strings (best when resources need distinct identifiers, preventing recreation if list order changes).

**Q: What are dynamic blocks?**
**A:** Dynamic blocks allow you to programmatically construct repeatable nested blocks (like ingress rules in a security group) inside a resource using expressions based on variables or lists.

**Q: How do you manage dependencies between resources?**
**A:** Terraform automatically builds a dependency graph based on resource references. For hidden dependencies, you explicitly use the depends_on meta-argument.

**Q: What is the purpose of the lifecycle block?**
**A:** It customizes resource management behavior. Key arguments include:
- create_before_destroy: Creates the replacement before destroying the old one (useful for zero-downtime rolling updates).
- prevent_destroy: Protects critical resources from accidental deletion.
- ignore_changes: Ignores out-of-band updates to specific attributes.

---

### 7. Commands & Provisioners

**Q: What do init, plan, pply, and destroy do?**
**A:** 
- init: Prepares the working directory, downloads providers, sets up backend.
- plan: Compares state to real infra and shows proposed actions.
- pply: Executes the plan to reach desired state. (-auto-approve skips the interactive prompt).
- destroy: Tears down all resources managed by the configuration.

**Q: What do alidate, mt, and graph do?**
**A:** alidate checks syntax and internal consistency. mt rewrites code to canonical formatting. graph generates a visual dependency tree.

**Q: What is the difference between local-exec, 
emote-exec, and 
ull_resource?**
**A:** 
- local-exec runs commands on the machine executing Terraform.
- 
emote-exec runs commands on the target resource (via SSH/WinRM).
- 
ull_resource manages no real infrastructure but acts as a placeholder to run provisioners.
*Best Practice:* Avoid provisioners unless absolutely necessary. Rely on configuration management tools (Ansible, Chef) or cloud-native init scripts (cloud-init) instead. Scripts must be idempotent.

---

### 8. Troubleshooting & Advanced Operations

**Q: How do you handle resource drift?**
**A:** Run 	erraform plan to identify the drift, and 	erraform apply to overwrite manual changes and reconcile back to code. Alternatively, update the .tf code to match the new reality. Tools like driftctl provide visibility into unmanaged resources.

**Q: How do you import existing infrastructure into Terraform?**
**A:** Use 	erraform import <resource_type>.<name> <cloud_id>. This maps the real resource to the state file. You must then manually write the matching .tf code so subsequent plans are clean.

**Q: What is 	erraform taint vs 	erraform destroy?**
**A:** 	aint (or 	erraform apply -replace in newer versions) marks a single resource as degraded so it will be deleted and recreated on the next apply. destroy completely removes resources. untaint reverses a taint.

**Q: A bad 	erraform apply caused downtime. How do you roll back?**
**A:** Terraform has no native "rollback" button. 
- Revert the bad commit in Git and run 	erraform apply again.
- Restore a previous state file version (if safe).
- *Best Practice:* Use CI/CD testing, plan reviews, and deployment patterns like Blue-Green or Canary to prevent downtime.

**Q: Can you implement blue-green deployments in Terraform?**
**A:** Yes. Deploy two parallel environments (blue and green). Update a load balancer resource (or DNS) in Terraform to switch traffic to the new environment. Once validated, destroy the old environment.

**Q: What is a resource target and how is it used?**
**A:** 	erraform apply -target=<resource> applies changes *only* to a specific resource and its dependencies. It's useful for targeted fixes or breaking dependency cycles, but should be used cautiously as it skips evaluating the full state.

**Q: How do you optimize Terraform performance in large infrastructures?**
**A:** 
- Split monolithic projects into smaller, decoupled modules/states.
- Use depends_on sparingly.
- Avoid overly complex or_each or deep nesting.
- Enable provider caching (plugin_cache_dir).

**Q: How do you integrate Terraform into a CI/CD pipeline?**
**A:** Standard pipeline: mt -> init -> alidate -> plan -> (Manual Approval or automated policy checks via Sentinel) -> pply. Remote state and secure vault integration are mandatory for CI/CD.

---

## Topic: Google Cloud Platform (GCP) & GCP DevOps

### 1. Core GCP Concepts & Resource Management

**Q: What is the GCP resource hierarchy and how do you manage permissions at different levels?**
**A:** The hierarchy is: Organization -> Folders -> Projects -> Resources. IAM permissions are inherited top-down. Managing permissions at higher levels (Folders/Org) ensures consistency, while Project-level permissions allow isolation.

**Q: What is the difference between a project number and a project ID?**
**A:** 
- **Project ID:** A unique, user-defined string used across GCP services (mandatory for most API calls).
- **Project Number:** An automatically generated unique integer assigned by Google.

**Q: What are Service Accounts and how do they differ from user accounts?**
**A:** A Service Account is a special account used by an application or a compute workload (like a VM or Cloud Run) to interact with GCP APIs securely, rather than a human user. 
*Follow-up: How do you secure them?* Use Workload Identity Federation instead of downloading static JSON keys, enforce the principle of least privilege using custom IAM roles, and rotate keys if static ones must be used.

---

### 2. Compute & Serverless Architecture

**Q: What is the difference between Compute Engine, App Engine, Cloud Run, and Cloud Functions?**
**A:** 
- **Compute Engine (IaaS):** Full control over VMs, manual scaling and OS management.
- **App Engine (PaaS):** Managed platform for web apps, auto-scales but restricted to specific runtimes.
- **Cloud Run (Serverless Containers):** Auto-scales stateless containers to zero, handling any runtime.
- **Cloud Functions (FaaS):** Event-driven serverless code execution (e.g., triggered by Pub/Sub or Cloud Storage uploads), great for lightweight glue logic.

**Q: When should you use Cloud Run vs. Google Kubernetes Engine (GKE)?**
**A:** Use **Cloud Run** for stateless microservices and APIs that need rapid auto-scaling (including scale-to-zero) with zero infrastructure management. Use **GKE** when you have complex, stateful workloads, require custom networking (like service mesh), or need precise control over the orchestration environment.

---

### 3. Google Kubernetes Engine (GKE) & Containerization

**Q: How do you scale a GKE cluster to handle unpredictable traffic?**
**A:** Use the **Horizontal Pod Autoscaler (HPA)** to scale the number of pods based on CPU/Memory or custom metrics, and the **Cluster Autoscaler** to dynamically add/remove worker nodes when pods cannot be scheduled due to resource constraints.

**Q: Why does a GKE pod fail with "CrashLoopBackOff" and how do you fix it?**
**A:** It means the container starts but immediately crashes. Use kubectl logs <pod-name> to view application errors, and kubectl describe pod <pod-name> to check for issues like missing environment variables, OOMKilled (Out of Memory), or failing readiness/liveness probes.

**Q: How do you implement zero-downtime deployments in GKE?**
**A:** Use Kubernetes **Rolling Updates** by configuring maxSurge and maxUnavailable in the Deployment YAML. Alternatively, use a Blue/Green deployment strategy by manipulating service selectors, or Canary releases via a service mesh like Istio/Anthos.

---

### 4. CI/CD & Infrastructure Automation

**Q: How does Google Cloud Build work and how do you handle sensitive data within it?**
**A:** Cloud Build executes CI/CD pipelines defined in cloudbuild.yaml. For sensitive data, **never** hardcode secrets. Store them in **Google Secret Manager** and reference them in the pipeline using the secretEnv field. Ensure the Cloud Build service account has the Secret Manager Secret Accessor role.

**Q: What steps troubleshoot a failing Cloud Build pipeline?**
**A:** 
1. Check Cloud Build logs in the GCP Console for the specific failing step.
2. Verify YAML syntax and step timeouts.
3. Check if the Cloud Build Service Account lacks necessary IAM roles (e.g., permission denied on Artifact Registry).
4. Verify VPC connectivity if using private worker pools.

**Q: How do you integrate Terraform with Cloud Build?**
**A:** Use the official Terraform builder image in your cloudbuild.yaml steps to run 	erraform init, 	erraform plan, and 	erraform apply. Store the Terraform state file remotely in an encrypted **Cloud Storage** bucket with versioning enabled.

---

### 5. Networking

**Q: What is a Shared VPC and when should you use it?**
**A:** A Shared VPC allows an organization to connect resources from multiple projects into a common VPC network. This centralizes network administration (firewalls, subnets, routing) in a "Host Project," while developers manage their own resources in "Service Projects."

**Q: What is Cloud NAT and Private Google Access?**
**A:** 
- **Cloud NAT:** Allows VMs without public IPs to access the internet for updates/patches securely.
- **Private Google Access:** Allows VMs on a private subnet to reach Google APIs (like Cloud Storage or BigQuery) using internal IP addresses instead of traversing the public internet.

**Q: How do you securely connect an on-premises network to GCP?**
**A:** 
- **Cloud VPN:** Uses IPsec over the public internet (max 3 Gbps per tunnel).
- **Cloud Interconnect:** A dedicated, physical enterprise-grade connection bypassing the public internet for high throughput and low latency.

**Q: What is Cloud Armor?**
**A:** A network security service that provides DDoS protection and Web Application Firewall (WAF) capabilities at the edge, integrated directly with the Global HTTP(S) Load Balancer.

---

### 6. Security, DevSecOps & Compliance

**Q: What is VPC Service Controls?**
**A:** It allows you to define a security perimeter around Google Cloud resources (like BigQuery or Cloud Storage) to mitigate data exfiltration risks. Even if an attacker steals valid IAM credentials, they cannot access the data from outside the defined network perimeter.

**Q: How do you implement DevSecOps (Shift-Left Security) in GCP?**
**A:** 
1. Run SAST/DAST tools (e.g., Trivy, SonarQube) as steps in Cloud Build.
2. Use **Artifact Registry** vulnerability scanning for Docker images.
3. Enforce **Binary Authorization** in GKE to ensure only signed, verified images can be deployed.
4. Implement Policy-as-Code using Sentinel (Terraform) or Anthos Config Management.

**Q: What is Cloud Data Loss Prevention (DLP)?**
**A:** A service that scans, discovers, and automatically masks or redacts sensitive data (like PII, credit cards, or health records) in text, images, or GCP storage systems to ensure compliance (GDPR/HIPAA).

---

### 7. Observability & Monitoring

**Q: What is the difference between Cloud Monitoring, Cloud Logging, and Cloud Trace?**
**A:** 
- **Cloud Monitoring:** Collects metrics (CPU, Memory, Latency), creates dashboards, and triggers alerts.
- **Cloud Logging:** Centralized log management and retention. You can create log-based metrics from specific log patterns.
- **Cloud Trace:** A distributed tracing system that tracks latency across microservices to identify performance bottlenecks.

**Q: How do you handle a scenario where logs are missing for a specific service?**
**A:** 
1. Ensure the Ops Agent (or fluentbit in GKE) is properly installed and running.
2. Check if the Compute/GKE service account has the 
oles/logging.logWriter role.
3. Check Cloud Logging router sinks to ensure exclusion filters aren't accidentally dropping the logs.

---

### 8. Storage & Databases

**Q: What is the difference between Cloud SQL, Cloud Spanner, and Bigtable?**
**A:** 
- **Cloud SQL:** Fully managed MySQL, PostgreSQL, or SQL Server. Great for standard relational workloads up to ~30TB. Regional.
- **Cloud Spanner:** Globally distributed, horizontally scalable relational database with strong consistency and SQL support. Built for massive scale and high availability.
- **Cloud Bigtable:** A NoSQL wide-column store optimized for high-throughput, low-latency reads/writes (e.g., IoT data, time-series, ad-tech).

**Q: How do you optimize BigQuery queries for performance and cost?**
**A:** 
1. Avoid SELECT *. Only select required columns (it's a columnar database).
2. Partition tables by date/timestamp to restrict the amount of data scanned.
3. Cluster tables based on frequently filtered columns.
4. Use materialized views for complex, frequently run aggregations.

---

### 9. Advanced Architecture & Troubleshooting

**Q: How do you design for Disaster Recovery (DR) in GCP?**
**A:** 
- Deploy stateless applications across multiple regions using a Global HTTP(S) Load Balancer.
- Replicate data using Multi-Region Cloud Storage buckets and cross-region read replicas for Cloud SQL.
- Use Infrastructure as Code (Terraform) to quickly recreate the environment in a secondary region if the primary region goes down completely.

**Q: You notice a sudden spike in your GCP billing. How do you troubleshoot and optimize costs?**
**A:** 
1. Check the **Billing Reports** and group by Project/Service to identify the culprit.
2. Ensure you are using **Committed Use Discounts (CUDs)** or **Sustained Use Discounts (SUDs)** for stable workloads.
3. Use Preemptible VMs (or Spot VMs) for fault-tolerant batch processing.
4. Implement Lifecycle Policies on Cloud Storage to move older data to Coldline/Archive classes.
5. Right-size VMs based on Cloud Monitoring recommendations.


---

## Topic: Terraform (Advanced & Scenario-Based)

### 1. Operations & Troubleshooting

**Q: What is the 	erraform taint command and what replaced it?**
**A:** 	erraform taint and untaint were deprecated in Terraform 0.15 and removed in 1.0. They were used to mark a resource for forced recreation. The modern replacement is to use the -replace flag during apply: 	erraform apply -replace="aws_instance.web". This forces recreation in a single step without permanently modifying the state file beforehand.

**Q: How do you handle Drift Detection in Terraform?**
**A:** Drift occurs when manual changes are made in the cloud console, causing the real-world infrastructure to diverge from the state file. 
1. Run 	erraform plan to detect the drift.
2. Either revert the manual changes in the console to match Terraform, OR update the Terraform configuration to reflect the new desired state.
3. Run 	erraform apply to realign the state.

**Q: How do you import existing, manually created infrastructure into Terraform?**
**A:** Use the 	erraform import command, or (in Terraform 1.5+) use the import block. You can also use 	erraform plan -generate-config-out=generated.tf (Terraform 1.6+) to automatically draft the corresponding HCL configuration for the imported resources, vastly reducing the manual reconciliation work required.

**Q: What is the external data block in Terraform?**
**A:** The external data source allows an external program or script (like Python or Bash) to act as a data source. It runs the script, which outputs JSON, and exposes that arbitrary data for use elsewhere in the Terraform configuration.

**Q: How do you recover from a failed 	erraform apply?**
**A:** Because Terraform is declarative, you can usually fix the configuration error and re-run pply. If the infrastructure is in a broken state, you should revert your code via your Version Control System (VCS) to the last known good commit and run 	erraform apply again. If the state file itself is corrupted, use Terraform Enterprise/Cloud's State Rollback feature to revert to the previous state version.

---

### 2. Architecture & Extensibility

**Q: What is Terragrunt and what problem does it solve?**
**A:** Terragrunt is a lightweight wrapper for Terraform that provides extra tools to keep configurations DRY (Don't Repeat Yourself). It is especially useful for managing remote state consistently, working with multiple Terraform modules, and managing deployments across multiple cloud accounts or environments without copying/pasting backend blocks.

**Q: What are Terraform provisioners and why are they discouraged?**
**A:** Provisioners (like local-exec and 
emote-exec) execute scripts on a local or remote machine as part of resource creation or destruction (e.g., bootstrapping software). They are discouraged because they break Terraform's declarative nature and idempotency. It is better to use configuration management tools like Ansible, or cloud-native solutions like cloud-init or golden AMIs (via Packer).

**Q: When would you need to write a custom Terraform Provider and how is it done?**
**A:** You write a custom provider when you need to manage in-house APIs, niche services, or proprietary technology not natively supported by Terraform. Providers are written in **Go** using the Terraform Plugin SDK. You must implement the API authentication and the CRUD (Create, Read, Update, Delete) lifecycle operations for your resources.

**Q: Briefly explain the core architecture and execution flow of Terraform.**
**A:** 
1. **CLI:** Parses commands and arguments.
2. **Configuration Loader & State Manager:** Loads the HCL files and pulls the current state.
3. **Graph Builder:** Evaluates the configuration to build a dependency graph (Resource Graph) of all resources.
4. **Graph Walk:** Terraform walks the graph, parallelizing operations for non-dependent resources (Execution).

**Q: What are Sentinel policies and what are their enforcement levels?**
**A:** Sentinel is a policy-as-code framework used in Terraform Cloud/Enterprise to enforce governance (e.g., restricting instance sizes, enforcing tags). 
The enforcement levels are:
- **Advisory:** Logs a warning but allows the run to proceed.
- **Soft Mandatory:** Blocks the run, but can be overridden by an administrator.
- **Hard Mandatory:** Completely blocks the run with no override permitted unless the policy is removed.

---

### 3. Deployments & CI/CD

**Q: How do you implement zero-downtime deployments or rolling updates using Terraform?**
**A:** Terraform can manage immutable infrastructure to achieve this. You can use features like create_before_destroy = true inside the lifecycle block to ensure a new instance is spun up before the old one is terminated. For complex rolling updates, use count or or_each combined with health checks, or manage Blue/Green deployments by toggling DNS/Load Balancer targets.

**Q: What is the best practice for integrating Terraform into a CI/CD pipeline?**
**A:** 
1. Separate plan and pply phases.
2. Run 	erraform fmt and 	erraform validate on every commit.
3. Run 	erraform plan on Pull Requests (PRs) and output the plan diff directly to the PR comments for review.
4. Run 	erraform apply only after the PR is merged into the main branch, preferably with a manual approval gate for production environments.


---

## Topic: Kubernetes (K8s) & Google Kubernetes Engine (GKE)

### 1. Core Architecture & Concepts

**Q: Explain the Kubernetes Architecture.**
**A:** Kubernetes follows a master-worker architecture. 
- **Control Plane (Master):** Contains the API Server (frontend), Scheduler (pod placement), Controller Manager (maintains desired state), and ETCD (key-value store for cluster state).
- **Worker Nodes:** Contain the Kubelet (node agent ensuring containers run), Container Runtime (Docker/containerd), and Kube-proxy (network routing).

**Q: What are Init Containers?**
**A:** Init containers run and complete *before* the main application containers start in a pod. They are used for initialization tasks like setting up config files, running database migrations, or waiting for external services to become available.

**Q: What is the difference between a ReplicaSet and a Deployment?**
**A:** 
- **ReplicaSet:** Ensures a specific number of pod replicas are running at any given time.
- **Deployment:** A higher-level abstraction that manages ReplicaSets. Deployments provide advanced features like rolling updates, rollbacks, and pausing/resuming updates, making them the standard way to deploy applications.

**Q: What are the different types of Services in Kubernetes?**
**A:** 
1. **ClusterIP:** (Default) Exposes the service on an internal IP, reachable only within the cluster.
2. **NodePort:** Exposes the service on a static port on each Node's IP, allowing external access.
3. **LoadBalancer:** Provisions a cloud provider's external load balancer (e.g., GCP Cloud Load Balancing) to route traffic to the NodePort/ClusterIP.
4. **ExternalName:** Maps the service to a DNS name.
5. **Headless Service:** (ClusterIP: None) Allows direct DNS resolution to Pod IPs (used often with StatefulSets).

### 2. Advanced Scheduling & Troubleshooting

**Q: What is the difference between Taints/Tolerations and Node Affinity?**
**A:** 
- **Taints & Tolerations:** Taints *repel* pods. If a node is tainted, no pod can schedule on it unless the pod has a matching toleration.
- **Node Affinity:** *Attracts* pods to specific nodes based on node labels (either strictly required or preferred).
*Scenario:* To dedicate nodes solely to ML workloads, you taint the GPU nodes so standard pods are repelled, and use Node Affinity on the ML pods so they are specifically drawn to the GPU nodes.

**Q: A pod is in CrashLoopBackOff. How do you debug it?**
**A:** 
1. View application logs: kubectl logs <pod-name> (or kubectl logs <pod-name> --previous for the crashed instance).
2. Check events and state: kubectl describe pod <pod-name>.
3. Check for OOMKilled (Out of Memory) or failing liveness/readiness probes.
4. Run an interactive shell for testing: kubectl exec -it <pod-name> -- /bin/sh.

**Q: How do you implement zero-downtime deployments in GKE?**
**A:** Define a Deployment with a 
ollingUpdate strategy (maxUnavailable: 0 and maxSurge: 1). Configure proper 
eadinessProbes so traffic isn't routed to the new pod until it's ready, and use preStop lifecycle hooks to gracefully drain existing connections before the old pod terminates.

**Q: How do you connect kubectl to a GKE cluster?**
**A:** Run: gcloud container clusters get-credentials <cluster-name> --region <region>. This fetches the kubeconfig and uses your GCP IAM credentials for authentication.

---

## Topic: Docker & Containerization

**Q: What is a multi-stage Dockerfile and why is it useful?**
**A:** A multi-stage build uses multiple FROM statements in a single Dockerfile. It allows you to use a heavy base image with all build tools (like Node, Maven, or Go) to compile the application, and then copy *only* the compiled artifacts into a tiny, secure runtime image (like Alpine or Distroless). This drastically reduces the final image size and attack surface.

**Q: How would you containerize a Node.js or React application?**
**A:**
`dockerfile
# Example Multi-stage React Build
FROM node:18 AS build
WORKDIR /app
COPY . .
RUN npm install && npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
`

---

## Topic: CI/CD & Jenkins

**Q: Explain the Master-Slave architecture in Jenkins.**
**A:** 
- **Master (Controller):** Central server that schedules jobs, manages configurations, and oversees the environment. It should not execute heavy builds itself.
- **Slave (Agent):** Worker machines dispatched by the master to execute the actual build/test/deploy tasks. This distributes the workload and allows builds on different OS environments.

**Q: What is the difference between Declarative and Scripted Pipelines?**
**A:** 
- **Declarative:** Uses a strict, YAML-like Groovy block structure (pipeline { stages { ... } }). It focuses on readability, predefined structure, and built-in error handling.
- **Scripted:** Uses standard Groovy code (
ode { ... }). It is highly flexible and allows for complex, custom logic, but is harder to read and maintain.

**Q: How do you securely handle Secrets or Access Tokens in Jenkins?**
**A:** Store tokens in the Jenkins Credentials Manager. Inject them into pipelines using the withCredentials block, which masks the secrets in the console output. (e.g., withCredentials([string(credentialsId: 'gitlab-token', variable: 'TOKEN')]) { ... }).

---

## Topic: Site Reliability Engineering (SRE) & Observability

### 1. The Core Pillars

**Q: What is the difference between Monitoring and Observability?**
**A:** **Monitoring** tracks known failure modes and tells you *when* a system is failing (e.g., "CPU is at 95%"). **Observability** provides the tooling to ask arbitrary questions to understand *why* the system is failing, which is crucial for debugging unknown distributed system issues.

**Q: What are the Four Golden Signals of Observability?**
**A:** 
1. **Latency:** The time it takes to service a request (measured in percentiles like p95/p99, not averages).
2. **Traffic:** The demand placed on the system (e.g., HTTP requests per second).
3. **Errors:** The rate of requests that fail (e.g., HTTP 5xx errors).
4. **Saturation:** How "full" a system resource is (e.g., CPU, Memory, Disk I/O).

**Q: Explain Metrics, Traces, and Logs.**
**A:** 
- **Metrics:** Numeric values aggregated over time (e.g., CPU=75%). Highly efficient for dashboards and alerts.
- **Traces:** Tracks a single user request's journey across multiple distributed microservices. Crucial for finding bottlenecks (e.g., "The DB query in the Payment service took 2s").
- **Logs:** Immutable, timestamped records of discrete events. Crucial for finding the exact error message or stack trace.

### 2. SRE Practices on GCP

**Q: How do you calculate Error Budgets and SLOs?**
**A:** A Service Level Objective (SLO) defines target reliability (e.g., 99.9% availability over 30 days). The **Error Budget** is the allowable downtime (e.g., 43.2 minutes). If an outage lasts 60 minutes, you have consumed >100% of your error budget. When the budget is depleted, feature releases should be halted to focus purely on reliability fixes.

**Q: What is the best strategy for handling incident management?**
**A:** Implement a structured incident management process: assign clear roles (Incident Commander, Ops, Comms), establish dedicated communication channels, and conduct blameless Post-Incident Reviews (Post-Mortems) to find root causes and prevent recurrence.

---

## Topic: General GCP DevOps Scenarios

**Q: You have 75+ GCP projects. What is the most scalable way to monitor them?**
**A:** Set up a **Monitoring Metrics Scope** in a central GCP project and add all other projects as monitored projects. This provides consolidated observability without duplicating dashboards.

**Q: How do you enforce least privilege for Terraform deployments in GCP?**
**A:** Create a dedicated GCP Service Account with the required permissions to provision infrastructure. Configure **Workload Identity Federation** (or use CI/CD pipeline impersonation) so developers cannot manually deploy resources from their personal accounts. Store the Terraform state securely in a GCS bucket.

**Q: How do you securely connect to a GCE VM in a private subnet?**
**A:** Use **Identity-Aware Proxy (IAP) for TCP forwarding**. This allows secure SSH access to private VMs without requiring external IP addresses, bastion hosts, or VPNs, while enforcing IAM and context-aware access policies.

**Q: What is the GCP equivalent of AWS Security Groups and NACLs?**
**A:** GCP relies on **VPC Firewall Rules** (which are stateful and applied to instances via network tags or service accounts) and **Hierarchical Firewall Policies** (which apply to entire folders or organizations).

**Q: How do you manage multi-environment configurations securely in GCP?**
**A:** Store environment-agnostic code in version control. Store sensitive configurations (DB passwords, API keys) in **Google Secret Manager**. Fetch these secrets dynamically during deployment (via Cloud Build) or at runtime (via GKE volume mounts or Cloud Run environment variables).

---

## Topic: Linux Basics & Scripting

**Q: How do you check CPU usage and troubleshoot performance on Linux?**
**A:** Use 	op or htop to see real-time CPU/Memory usage and identify rogue processes. Use mpstat for multi-core analysis, or journalctl to view system logs for service failures.

**Q: How would you find the last 5 users who logged into a Linux machine?**
**A:** Run the command: last -n 5.


---

## Topic: Advanced Observability & OpenTelemetry (OTel)

**Q: What is OpenTelemetry (OTel) and what role does the OTel Collector play?**
**A:** OpenTelemetry is an open-source, vendor-neutral framework for generating, processing, and exporting telemetry data (Metrics, Traces, Logs). 
The **OTel Collector** acts as the central telemetry pipeline. It consists of:
- **Receivers:** How data gets in (e.g., OTLP, Prometheus format).
- **Processors:** How data is transformed (e.g., batching, adding metadata, filtering).
- **Exporters:** Where data is sent (e.g., Prometheus, Jaeger, OpenSearch, Datadog).

**Q: How does distributed tracing work in Jaeger and what are Span Kinds?**
**A:** Distributed tracing tracks a request as it moves through multiple microservices. The entire journey is a **Trace** (identified by a unique Trace ID), and each individual operation within it is a **Span** (identified by a Span ID).
Common **Span Kinds** include:
- SERVER: The service receives an incoming request.
- CLIENT: The service makes an outgoing call to a dependency (e.g., an external API or DB).
- INTERNAL: Internal processing within the service itself.

**Q: How do you correlate Logs with Traces?**
**A:** By injecting the Trace ID and Span ID into the log payload. When an error log is generated (e.g., stored in OpenSearch), you can query that specific Trace ID in your logging backend to see the exact distributed trace in Jaeger, providing instant context on *why* the error occurred.

**Q: Write a PromQL query to find the request rate and the p95 latency of a service.**
**A:**
- **Request Rate (per second over 5 mins):** 
  sum by(service_name)(rate(traces_span_metrics_calls_total[5m]))
- **p95 Latency:** 
  histogram_quantile(0.95, sum by(le, service_name)(rate(traces_span_metrics_duration_milliseconds_bucket[5m])))

**Q: What is the difference between Grafana and Prometheus/Jaeger?**
**A:** Prometheus is a time-series database (storage engine) for metrics, and Jaeger is a storage backend for traces. **Grafana** is simply the visualization and dashboarding layer that sits on top of these data sources to query and display them in a unified UI.

---

## Topic: GCP Core Services & Architecture Scenarios

**Q: What are the lifecycle states of a Google Compute Engine (GCE) instance?**
**A:** PROVISIONING -> STAGING -> RUNNING -> STOPPING -> TERMINATED. (You can also have SUSPENDED if the VM is paused).

**Q: How does VPC Network Peering work in GCP?**
**A:** VPC Network Peering connects two VPC networks so that resources in each network can communicate with each other using internal IP addresses. It works across different GCP projects and even different GCP organizations without routing traffic over the public internet.

**Q: Explain the GCP Shared Responsibility Model.**
**A:** Google manages the security **OF** the cloud (physical data centers, hardware, hypervisors, and core network infrastructure). The customer manages security **IN** the cloud (configuring IAM policies, firewall rules, encrypting data, and securing application code).

**Q: How do you protect data from being accidentally deleted or overwritten in Cloud Storage (GCS)?**
**A:** 
- Enable **Object Versioning** to keep historical versions of objects when they are overwritten or deleted.
- Use **Retention Policies (Object Lock)** to specify a minimum duration that objects must be retained before they can be deleted.

**Q: Write a basic Terraform snippet to provision a Compute Engine instance and a Cloud Storage bucket.**
**A:**
`hcl
resource "google_storage_bucket" "my_bucket" {
  name          = "my-unique-bucket-name"
  location      = "US"
  force_destroy = true
}

resource "google_compute_instance" "my_vm" {
  name         = "my-web-server"
  machine_type = "e2-medium"
  zone         = "us-central1-a"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network = "default"
    access_config {
      # Allocates a public IP
    }
  }
}
`

**Q: How do you build a serverless REST API in GCP?**
**A:** You can deploy your application logic using **Cloud Functions** or **Cloud Run** (for containerized apps), and sit it behind **API Gateway** to handle authentication, rate limiting, and routing.


---

## Topic: Kubernetes (Advanced & Production Scenarios)

### 1. Deep Architecture & Operations

**Q: Walk me through exactly what happens when you run kubectl apply -f deployment.yaml.**
**A:** 
1. The request hits the **kube-apiserver**.
2. The API server authenticates, authorizes, and validates the YAML, then stores the desired state in **etcd**.
3. The **Controller Manager** detects the new desired state and creates a ReplicaSet.
4. The **Scheduler** notices new pods with no assigned node and assigns them to nodes based on resources and constraints.
5. The **Kubelet** on the assigned worker node receives the instruction, pulls the image via the container runtime, and starts the container.

**Q: What is the difference between a Deployment, StatefulSet, and DaemonSet?**
**A:** 
- **Deployment:** For stateless applications (e.g., web servers). Pods are interchangeable.
- **StatefulSet:** For stateful applications (e.g., databases, Kafka). It provides stable, unique network identifiers and persistent storage per pod, even across rescheduling.
- **DaemonSet:** Ensures exactly one copy of a pod runs on every eligible node in the cluster (e.g., logging agents, monitoring daemons like Fluent-bit).

**Q: Job vs. CronJob?**
**A:** 
- **Job:** Runs a task to completion exactly once (e.g., database migration).
- **CronJob:** Runs a Job on a time-based schedule (e.g., nightly backups).

### 2. Networking, Security & Storage

**Q: How does traffic reach a pod from the internet in production?**
**A:** 
Internet -> Cloud Load Balancer -> Ingress Controller (handles routing rules/SSL) -> Service (internal load balancing) -> Pod.

**Q: What is a NetworkPolicy and why use it?**
**A:** By default, all pods in a Kubernetes cluster can talk to each other. A NetworkPolicy applies zero-trust security by defining firewall rules at the pod level, restricting which pods can communicate with which other pods (Ingress/Egress).

**Q: Are Kubernetes secrets actually secure? How do you manage them in production?**
**A:** By default, Kubernetes secrets are just base64-encoded, *not* encrypted. In production on GCP, you should:
1. Enable Application-Layer Secrets Encryption (encrypting the etcd layer with Cloud KMS).
2. Use **Google Secret Manager** combined with the External Secrets Operator or CSI drivers to inject secrets dynamically at runtime, avoiding storing them in Git or raw k8s manifests.

**Q: How do you prevent users from running privileged containers?**
**A:** Use **Pod Security Admission** (enforcing restricted profiles) or policy engines like **OPA Gatekeeper / Kyverno** to block pod creations that request privileged access, host network, or root user access.

### 3. Resource Management

**Q: What is the difference between Requests and Limits?**
**A:** 
- **Requests:** The guaranteed amount of CPU/Memory reserved for a container on a node.
- **Limits:** The absolute maximum amount a container can use. If a container exceeds its memory limit, it will be OOMKilled (Out Of Memory), even if the physical node still has plenty of RAM available.

**Q: GKE Standard (Node Pools) vs. GKE Autopilot?**
**A:** 
- **Standard:** You manage the underlying Compute Engine VMs (Node Pools), OS upgrades, and capacity. Better for specialized hardware (GPUs) or custom configurations.
- **Autopilot:** Google manages the entire cluster infrastructure. You just deploy pods and pay per pod resource request. It is a fully managed, hands-off experience.

**Q: What is Workload Identity in GKE?**
**A:** Workload Identity is the secure way for GKE pods to authenticate to GCP services (like Cloud Storage or Cloud SQL). It links a Kubernetes Service Account (KSA) directly to a Google Service Account (GSA), removing the need to export and mount static JSON service account keys into containers.

### 4. GitOps & Troubleshooting (Scenario)

**Q: What is Helm and what is ArgoCD (GitOps)?**
**A:** 
- **Helm:** A package manager for K8s that templates YAML files, making it easy to deploy different values for different environments (alues-dev.yaml, alues-prod.yaml).
- **ArgoCD:** A GitOps tool that continuously monitors your Git repository (the single source of truth) and automatically syncs those configurations to your live cluster, detecting drift and enabling rapid rollbacks.

**Q: Scenario: A critical deployment just failed in production. Walk me through your steps.**
**A:** 
1. **Don't panic and read the logs:** Check the CI/CD pipeline (Cloud Build/Jenkins) to see exactly which stage failed (Build, Test, or Deploy).
2. **Rollback immediately to restore service:** kubectl rollout undo deployment/my-app. Do not "fix forward" while production is down.
3. **Verify the failure:** Check kubectl describe deployment my-app or kubectl get events. Verify if a ConfigMap or Secret was updated recently.
4. **Reproduce & Fix:** Once the service is restored to the previous stable state, reproduce the bug in staging, fix it, and redeploy a new, properly tagged version (e.g., 2.1-fixed). *Never use the latest tag in production because it makes rollbacks impossible.*


---

## Topic: Containerization Deep Dive (Docker)

**Q: Explain Docker architecture and its main components.**
**A:** Docker uses a client-server architecture:
- **Docker Client:** The CLI interface (docker).
- **Docker Daemon (dockerd):** The background service that builds, runs, and manages containers, networks, and volumes.
- **Docker Registry:** Stores Docker images (e.g., Docker Hub, Artifact Registry).

**Q: What is the difference between CMD and ENTRYPOINT in a Dockerfile?**
**A:** 
- ENTRYPOINT defines the main executable that will always run when the container starts.
- CMD provides default arguments to that executable. CMD can be easily overridden from the command line, whereas overriding ENTRYPOINT requires a specific flag.
*Best practice:* Use ENTRYPOINT for the main command and CMD for default flags.

**Q: Explain Docker layers and the layer caching mechanism.**
**A:** Images are built in layers; each Dockerfile instruction (like RUN, COPY) creates a new layer. Docker caches these layers to speed up builds. If a layer changes (e.g., a source code file changes), all subsequent layers are invalidated and must be rebuilt. 
*Optimization:* Always copy package.json or 
equirements.txt and install dependencies *before* copying the rest of the source code, maximizing cache usage.

**Q: What is the difference between COPY and ADD?**
**A:** Both copy files into the image, but ADD can also extract .tar archives automatically and download files from remote URLs. Use COPY unless you specifically need ADD's extraction features.

**Q: What is the difference between docker stop and docker kill?**
**A:** 
- docker stop sends a SIGTERM signal, allowing the application to gracefully shut down (with a 10-second timeout by default) before sending SIGKILL.
- docker kill immediately sends a SIGKILL signal, forcefully terminating the process.

**Q: Explain Docker Namespaces and Cgroups.**
**A:** Docker relies on Linux kernel features:
- **Namespaces:** Provide process-level isolation (e.g., PID, NET, IPC, MNT). A container believes it has its own OS environment.
- **Cgroups (Control Groups):** Limit and account for resource usage (CPU, Memory, Disk I/O). They prevent a single container from exhausting the host's resources.

**Q: What are the different Docker Networking modes?**
**A:** 
- **Bridge (default):** Private internal network for containers on the same host.
- **Host:** Removes network isolation; the container uses the host's network stack directly.
- **None:** Completely disables networking.
- **Overlay:** Enables communication between containers across multiple Docker hosts (used in Swarm).
- **Macvlan:** Assigns a MAC address to the container, making it appear as a physical device on the network.

---

## Topic: Kubernetes Networking & Advanced Concepts

**Q: What is the role of a Container Network Interface (CNI) in Kubernetes?**
**A:** CNI is a standard that defines how network plugins should configure network interfaces for Linux containers. In Kubernetes, the CNI plugin (e.g., Calico, Cilium, Flannel) is responsible for assigning IP addresses to Pods and implementing NetworkPolicies for security.

**Q: Explain the difference between a Pod network and a Service network.**
**A:** 
- **Pod Network:** The CIDR range used to assign IPs directly to Pods. Every Pod gets a unique IP in this range, and they can route to each other across nodes.
- **Service Network:** A separate CIDR range used to assign virtual IPs (ClusterIPs) to Services. These IPs do not belong to any physical interface; they are handled by kube-proxy rules (iptables/IPVS) to load balance traffic to the backend Pod IPs.

**Q: What is kube-proxy and what does it do?**
**A:** kube-proxy runs on every node in the cluster. It watches the API server for changes to Services and Endpoints, and translates these into OS-level network rules (like iptables or IPVS). This ensures that traffic sent to a Service's ClusterIP is load-balanced to the correct backend Pods.

**Q: How does Service Discovery work in Kubernetes and what is the role of DNS?**
**A:** Kubernetes runs a cluster DNS server (usually CoreDNS). When a Service is created, CoreDNS automatically generates a DNS record for it. Pods are configured to query this DNS server first.
*Format:* <service-name>.<namespace>.svc.cluster.local. This allows applications to communicate simply by using the service name instead of hardcoded IPs.

**Q: What is the difference between an Ingress and an Ingress Controller?**
**A:** 
- **Ingress:** A Kubernetes API object (YAML) that defines routing rules (e.g., route /api to service A, /web to service B).
- **Ingress Controller:** The actual software (e.g., NGINX, Traefik, HAProxy) that runs in the cluster, reads those rules, and configures its underlying proxy to route the traffic. The Ingress object does nothing without a Controller running.

**Q: How do you secure communication between Pods and Nodes?**
**A:** 
1. Use **NetworkPolicies** to restrict ingress/egress traffic between pods.
2. Implement a **Service Mesh** (like Istio or Linkerd) to enforce automatic mutual TLS (mTLS) encryption for all pod-to-pod traffic.
3. Ensure the underlying CNI plugin supports encryption (e.g., Calico with WireGuard).

