# GCP DevOps Services Cheat Sheet

Google Cloud provides a managed suite of CI/CD and deployment services. This cheat sheet covers the most common implementations and YAML syntax for **Cloud Build**, **Cloud Run**, **Artifact Registry**, and **Secret Manager**.

---

## 1. Cloud Build (`cloudbuild.yaml`)

Cloud Build executes your builds on GCP infrastructure. It natively runs Docker containers as steps.

### Basic Build & Push Pipeline
```yaml
steps:
  # 1. Run unit tests
  - name: 'python:3.10-slim'
    entrypoint: 'bash'
    args: ['-c', 'pip install -r requirements.txt && pytest tests/']
    
  # 2. Build the Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/my-repo/api:$SHORT_SHA', '.']

  # 3. Push the image to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/my-repo/api:$SHORT_SHA']

# Automatically use Artifact Registry
images:
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/my-repo/api:$SHORT_SHA'
```

### Accessing Secrets in Cloud Build
```yaml
steps:
  - name: 'ubuntu'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        echo "My secret token is $$API_TOKEN"
    secretEnv: ['API_TOKEN']

availableSecrets:
  secretManager:
    - versionName: projects/$PROJECT_ID/secrets/my-api-token/versions/latest
      env: 'API_TOKEN'
```

---

## 2. Cloud Run

Serverless container platform. Auto-scales from 0 to N.

### Deploy via CLI
```bash
gcloud run deploy my-service \
  --image us-central1-docker.pkg.dev/my-proj/repo/api:latest \
  --region us-central1 \
  --allow-unauthenticated \
  --cpu 2 --memory 1Gi \
  --set-env-vars="ENV=prod,LOG_LEVEL=info" \
  --set-secrets="DB_PASS=db-password:latest" \
  --min-instances 1
```

### Traffic Splitting (Canary / Blue-Green)
```bash
# Send 10% of traffic to the new revision, 90% to the old
gcloud run services update-traffic my-service \
  --region us-central1 \
  --to-revisions=my-service-00042-new=10,my-service-00041-old=90
```

---

## 3. Artifact Registry

The evolution of Container Registry. Supports Docker, Maven, npm, Python packages, etc.

### Creating a Repository
```bash
gcloud artifacts repositories create docker-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Main Docker registry"
```

### Authentication for Local Docker
```bash
# Configure docker to use GCP credentials
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## 4. Secret Manager

Centralized credential and secret storage.

### Creating and Accessing Secrets
```bash
# Create a secret
gcloud secrets create db-password --replication-policy="automatic"

# Add a value (version)
echo -n "SuperSecret123" | gcloud secrets versions add db-password --data-file=-

# Read a secret value
gcloud secrets versions access latest --secret="db-password"
```

---

## 5. Cloud Deploy (Continuous Delivery)

Manages releases and delivery pipelines to GKE, Cloud Run, and Anthos.

### Delivery Pipeline YAML (`clouddeploy.yaml`)
```yaml
apiVersion: deploy.cloud.google.com/v1
kind: DeliveryPipeline
metadata:
  name: api-pipeline
description: "Deployment pipeline for backend API"
serialPipeline:
  stages:
  - targetId: staging-cluster
    profiles: [staging]
  - targetId: prod-cluster
    profiles: [prod]
```
