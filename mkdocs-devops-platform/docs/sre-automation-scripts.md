# SRE Automation Scripts

Our SRE automation philosophy is built on three core pillars: event-driven architecture, API-first integrations, and strict audit logging. We follow a zero standing privileges model, meaning all automation executes with ephemeral credentials or scoped workload identities. This ensures that every automated action is traceable, reproducible, and secure by design.

!!! info "Deployment Model"
    All scripts run as GCP Cloud Functions (Python 3.11) or as systemd services on GCE VMs, using Workload Identity or environment-injected secrets from Secret Manager. No credentials are hardcoded.

---

## 1. Slack → PagerDuty Bot (Cloud Function)

### Overview
This Flask-based Cloud Function is deployed at the `/slack/events` endpoint to handle the Slack Events API. It performs URL verification challenges and authenticates incoming payloads by verifying the Slack signing secret via HMAC-SHA256. When it detects a message matching the `@pagerduty <team-name>` pattern, it queries the PagerDuty Schedules API v2 to identify the current on-call engineer. It then creates a high-urgency PagerDuty incident, sends a formatted HTML email to the team's distribution list via SendGrid, and replies in the Slack thread with the incident URL and the on-call engineer's name.

### slack_pagerduty_bot.py

#### What does this script do?
1. Receives a webhook payload from Slack Events API when a user mentions `@pagerduty <team-name>`.
2. Validates the Slack request signature to ensure it is authentic.
3. Queries PagerDuty API to find the on-call engineer for the requested team.
4. Creates a high-urgency incident in PagerDuty assigned to that engineer.
5. Sends an email notification to the team's distribution list.
6. Posts a reply back to the Slack thread with the PagerDuty incident link.

#### I/O Summary
| Input | Process | Output |
| --- | --- | --- |
| Slack Event webhook (`POST` with `@pagerduty` mention) | Validate signature → query PD → create incident → email | PagerDuty Incident, Slack reply, Email notification |

#### Key Environment Variables
| Name | Required | Description | Example Value |
| --- | --- | --- | --- |
| `SLACK_SIGNING_SECRET` | Yes | Verifies incoming Slack webhook requests | `8f742231b...` |
| `PAGERDUTY_API_TOKEN` | Yes | Token for creating incidents in PD | `y_Nb...` |
| `PAGERDUTY_SERVICE_ID` | Yes | The ID of the PD service to create incidents under | `P123456` |
| `PAGERDUTY_ESCALATION_POLICY_ID` | Yes | Fallback policy for incidents | `P654321` |
| `SENDGRID_API_KEY` | Yes | Token to send emails via SendGrid | `SG.xyz...` |
| `SLACK_BOT_TOKEN` | Yes | Used to post the reply message back to Slack | `xoxb-...` |

!!! note "Deployment command"
    ```bash
    gcloud functions deploy slack-pagerduty-bot \
      --runtime python311 \
      --trigger-http \
      --entry-point slack_events
    ```

!!! tip "How to test it"
    ```bash
    # Send a mock challenge request to verify the endpoint is up
    curl -X POST https://REGION-PROJECT.cloudfunctions.net/slack-pagerduty-bot \
         -H "Content-Type: application/json" \
         -d '{"type": "url_verification", "challenge": "test1234"}'
    ```

```python
#!/usr/bin/env python3
"""
Slack → PagerDuty Bot — Cloud Function Entry Point
Deployment: gcloud functions deploy slack-pagerduty-bot --runtime python311 \\
             --trigger-http --entry-point slack_events
Required env vars: SLACK_SIGNING_SECRET, PAGERDUTY_API_TOKEN,
                   PAGERDUTY_SERVICE_ID, PAGERDUTY_ESCALATION_POLICY_ID,
                   SENDGRID_API_KEY, SLACK_BOT_TOKEN
"""

import os
import re
import hmac
import hashlib
import time
import logging
import json
from flask import Flask, request, jsonify
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, From, Subject, Content
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Setup JSON structured logging
logger = logging.getLogger("slack-pd-bot")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# Environment Variables
SLACK_SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET', '')
PAGERDUTY_API_TOKEN = os.environ.get('PAGERDUTY_API_TOKEN', '')
PAGERDUTY_SERVICE_ID = os.environ.get('PAGERDUTY_SERVICE_ID', '')
PAGERDUTY_ESCALATION_POLICY_ID = os.environ.get('PAGERDUTY_ESCALATION_POLICY_ID', '')
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN', '')

# Team Distribution Lists
TEAM_TO_DL = {
    'platform-sre': 'platform-sre-dl@enterprise.com',
    'data-engineering': 'data-eng-dl@enterprise.com',
    'backend': 'backend-dl@enterprise.com',
    'frontend': 'frontend-dl@enterprise.com',
    'security': 'secops-dl@enterprise.com',
    'infra': 'infra-dl@enterprise.com'
}

PAGERDUTY_HEADERS = {
    'Authorization': f'Token token={PAGERDUTY_API_TOKEN}',
    'Accept': 'application/vnd.pagerduty+json;version=2',
    'Content-Type': 'application/json'
}

app = Flask(__name__)
slack_client = WebClient(token=SLACK_BOT_TOKEN)

def verify_slack_signature(req) -> bool:
    timestamp = req.headers.get('X-Slack-Request-Timestamp', '')
    signature = req.headers.get('X-Slack-Signature', '')
    if not timestamp or not signature:
        return False
    if abs(time.time() - int(timestamp)) > 300:
        return False
    sig_basestring = f"v0:{timestamp}:{req.get_data(as_text=True)}"
    my_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(my_signature, signature)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(requests.exceptions.RequestException))
def get_pagerduty_schedule_id(team_name: str) -> str:
    url = f"https://api.pagerduty.com/schedules?query={team_name}"
    response = requests.get(url, headers=PAGERDUTY_HEADERS)
    response.raise_for_status()
    schedules = response.json().get('schedules', [])
    if not schedules:
        raise ValueError(f"No schedule found for team: {team_name}")
    return schedules[0]['id']

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(requests.exceptions.RequestException))
def get_pagerduty_oncall(schedule_id: str) -> dict:
    url = f"https://api.pagerduty.com/oncalls?schedule_ids[]={schedule_id}&earliest=true"
    response = requests.get(url, headers=PAGERDUTY_HEADERS)
    response.raise_for_status()
    oncalls = response.json().get('oncalls', [])
    if not oncalls:
        raise ValueError("No one is currently on-call.")
    user = oncalls[0]['user']
    user_details = requests.get(user['self'], headers=PAGERDUTY_HEADERS).json()['user']
    return {'name': user['summary'], 'email': user_details['email'], 'id': user['id']}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(requests.exceptions.RequestException))
def create_pagerduty_incident(title: str, oncall_user_id: str, team_name: str) -> str:
    url = "https://api.pagerduty.com/incidents"
    payload = {
        "incident": {
            "type": "incident",
            "title": title,
            "service": {"id": PAGERDUTY_SERVICE_ID, "type": "service_reference"},
            "urgency": "high",
            "body": {"type": "incident_body", "details": f"Triggered via Slack bot for team {team_name}"},
            "assignments": [{"assignee": {"id": oncall_user_id, "type": "user_reference"}}]
        }
    }
    response = requests.post(url, headers=PAGERDUTY_HEADERS, json=payload)
    response.raise_for_status()
    return response.json()['incident']['html_url']

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(Exception))
def send_dl_email(dl_email: str, incident_url: str, oncall_name: str, oncall_email: str, title: str, team_name: str) -> bool:
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    html_content = f"""
    <h2>New PagerDuty Incident</h2>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><th>Team</th><td>{team_name}</td></tr>
        <tr><th>Title</th><td>{title}</td></tr>
        <tr><th>On-Call</th><td>{oncall_name} ({oncall_email})</td></tr>
        <tr><th>Incident Link</th><td><a href="{incident_url}">View in PagerDuty</a></td></tr>
    </table>
    """
    message = Mail(
        from_email=From('bot@enterprise.com', 'PD Slack Bot'),
        to_emails=To(dl_email),
        subject=Subject(f"[INCIDENT] {title}"),
        html_content=Content("text/html", html_content)
    )
    response = sg.send(message)
    return response.status_code in (200, 202)

def post_slack_reply(channel: str, thread_ts: str, incident_url: str, oncall_name: str, team_name: str) -> None:
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🚨 *Incident Created for {team_name}*\n*On-call Engineer:* {oncall_name}\n<{incident_url}|View Incident in PagerDuty>"
            }
        }
    ]
    slack_client.chat_postMessage(channel=channel, thread_ts=thread_ts, text="Incident created", blocks=blocks)

@app.route('/slack/events', methods=['POST'])
def slack_events():
    if not verify_slack_signature(request):
        logger.warning("Invalid Slack signature")
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.json
    if payload.get("type") == "url_verification":
        return jsonify({"challenge": payload.get("challenge")})

    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        if event.get("type") == "message" and not event.get("bot_id"):
            text = event.get("text", "")
            match = re.search(r'@pagerduty\s+([a-zA-Z0-9-]+)', text)
            if match:
                team_name = match.group(1)
                channel = event.get("channel")
                thread_ts = event.get("ts")
                try:
                    logger.info(f"Processing PD request for team: {team_name}")
                    schedule_id = get_pagerduty_schedule_id(team_name)
                    oncall = get_pagerduty_oncall(schedule_id)
                    title = f"Slack reported incident for {team_name}"
                    incident_url = create_pagerduty_incident(title, oncall['id'], team_name)
                    
                    dl_email = TEAM_TO_DL.get(team_name, 'noc@enterprise.com')
                    send_dl_email(dl_email, incident_url, oncall['name'], oncall['email'], title, team_name)
                    
                    post_slack_reply(channel, thread_ts, incident_url, oncall['name'], team_name)
                    logger.info("Successfully handled PD request")
                except Exception as e:
                    logger.error(f"Error handling PD request: {str(e)}")
                    slack_client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=f"Error creating incident: {str(e)}")

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
```

### requirements_bot.txt

#### What does this script do?
1. Defines Python dependencies required for the Slack-PagerDuty Bot.
2. Ensures reproducible builds across environments.

#### I/O Summary
| Input | Process | Output |
| --- | --- | --- |
| `requirements_bot.txt` | Read during function deployment | Installed Python dependencies |

#### Key Environment Variables
| Name | Required | Description | Example Value |
| --- | --- | --- | --- |
| N/A | No | Handled by Cloud Functions builder | N/A |

!!! note "Deployment command"
    Dependencies are read automatically during the `gcloud functions deploy` command shown above.

!!! tip "How to test it"
    ```bash
    pip install -r requirements_bot.txt
    ```

```text
flask==3.0.3
requests==2.32.3
slack_sdk==3.31.0
sendgrid==6.11.0
tenacity==8.5.0
structlog==24.4.0
functions-framework==3.8.1
```

---

## 2. ServiceNow Webhook → GCP IAM & VM Provisioner (Cloud Function)

### Overview
This Cloud Function acts as a bridge between ServiceNow workflows and GCP resource provisioning. Triggered by outbound REST messages from ServiceNow, it secures the webhook endpoint using HMAC-SHA256 authentication. It supports two primary request types: `iam_grant`, which adds IAM bindings to specific GCP projects based on an approved roles allowlist, and `vm_create`, which provisions Google Compute Engine instances sourced from the enterprise golden image family. Every action is meticulously logged to a BigQuery audit dataset for compliance and historical tracking.

### servicenow_iam_handler.py

#### What does this script do?
1. Validates inbound requests from ServiceNow via HMAC-SHA256 signature.
2. Reads the request type: `iam_grant` or `vm_create`.
3. For IAM grants: verifies requested roles against an allowlist, then adds the policy binding using the GCP Resource Manager API.
4. For VM creations: provisions a GCE instance from the enterprise golden image using the Compute Engine API.
5. Logs every action into a BigQuery audit table.

#### I/O Summary
| Input | Process | Output |
| --- | --- | --- |
| ServiceNow JSON Webhook (`POST`) | Authenticate → Provision Resource → Audit | GCP IAM Policy / GCP VM, BigQuery log entry |

#### Key Environment Variables
| Name | Required | Description | Example Value |
| --- | --- | --- | --- |
| `SERVICENOW_HMAC_SECRET` | Yes | Validates the ServiceNow webhook | `sn_secret_99` |
| `GCP_AUDIT_BQ_TABLE` | Yes | BigQuery dataset/table for audit logs | `enterprise-audit.iam_changes.gcp_grants` |

!!! note "Deployment command"
    ```bash
    gcloud functions deploy servicenow-iam-handler \
      --runtime python311 \
      --trigger-http \
      --entry-point servicenow_webhook
    ```

!!! tip "How to test it"
    ```bash
    # Test IAM grant locally with a mocked request
    curl -X POST https://REGION-PROJECT.cloudfunctions.net/servicenow-iam-handler \
         -H "X-ServiceNow-Signature: <calculated-hmac>" \
         -H "Content-Type: application/json" \
         -d '{"request_type": "iam_grant", "project_id": "test-project", "user_email": "user@enterprise.com", "roles": ["roles/monitoring.viewer"]}'
    ```

```python
#!/usr/bin/env python3
"""
ServiceNow → GCP IAM & VM Provisioner — Cloud Function
Deployment: gcloud functions deploy servicenow-iam-handler --runtime python311 \\
             --trigger-http --entry-point servicenow_webhook
Required env vars: SERVICENOW_HMAC_SECRET, GCP_AUDIT_BQ_TABLE
"""

import os
import hmac
import hashlib
import json
import logging
from datetime import datetime
import functions_framework
from google.cloud import resourcemanager_v3
from google.cloud import compute_v1
from google.cloud import bigquery
from google.iam.v1 import policy_pb2

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("snow-gcp-provisioner")

SERVICENOW_HMAC_SECRET = os.environ.get('SERVICENOW_HMAC_SECRET', '')
AUDIT_TABLE = os.environ.get('GCP_AUDIT_BQ_TABLE', 'enterprise-audit.iam_changes.gcp_grants')
GOLDEN_IMAGE_FAMILY = "projects/enterprise-images/global/images/family/enterprise-debian12-base"

APPROVED_ROLES = frozenset([
    "roles/dataproc.editor",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/compute.instanceAdmin.v1",
    "roles/compute.networkUser",
    "roles/storage.objectViewer",
    "roles/monitoring.viewer"
])

def verify_hmac(request) -> bool:
    signature = request.headers.get('X-ServiceNow-Signature', '')
    if not signature:
        return False
    payload = request.get_data()
    expected_sig = hmac.new(SERVICENOW_HMAC_SECRET.encode('utf-8'), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, signature)

def write_audit_log(action: str, requester: str, project_id: str, details_dict: dict) -> None:
    try:
        client = bigquery.Client()
        row_to_insert = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "requester": requester,
                "project_id": project_id,
                "details": json.dumps(details_dict)
            }
        ]
        errors = client.insert_rows_json(AUDIT_TABLE, row_to_insert)
        if errors:
            logger.error(f"Failed to insert audit log: {errors}")
        else:
            logger.info(f"Audit log inserted for {action}")
    except Exception as e:
        logger.error(f"Audit log exception: {str(e)}")

def handle_iam_grant(payload: dict) -> tuple:
    project_id = payload.get('project_id')
    user_email = payload.get('user_email')
    roles = payload.get('roles', [])
    ticket = payload.get('ticket_number', 'UNKNOWN')

    if not all([project_id, user_email, roles]):
        return {"error": "Missing required fields for iam_grant"}, 400

    invalid_roles = [r for r in roles if r not in APPROVED_ROLES]
    if invalid_roles:
        return {"error": f"Roles not in approved list: {invalid_roles}"}, 403

    try:
        client = resourcemanager_v3.ProjectsClient()
        project_name = f"projects/{project_id}"
        
        policy = client.get_iam_policy(request={"resource": project_name})
        
        member = f"user:{user_email}"
        roles_added = []
        for role in roles:
            binding_exists = False
            for binding in policy.bindings:
                if binding.role == role:
                    binding_exists = True
                    if member not in binding.members:
                        binding.members.append(member)
                        roles_added.append(role)
                    break
            if not binding_exists:
                new_binding = policy_pb2.Binding(role=role, members=[member])
                policy.bindings.append(new_binding)
                roles_added.append(role)
        
        if roles_added:
            client.set_iam_policy(request={"resource": project_name, "policy": policy})
            write_audit_log("IAM_GRANT", payload.get('requester', 'snow'), project_id, {"user": user_email, "roles": roles_added, "ticket": ticket})
        
        return {"status": "success", "roles_added": roles_added}, 200
    except Exception as e:
        logger.error(f"IAM grant failed: {str(e)}")
        return {"error": str(e)}, 500

def handle_vm_create(payload: dict) -> tuple:
    project_id = payload.get('project_id')
    vm_config = payload.get('vm_config', {})
    ticket = payload.get('ticket_number', 'UNKNOWN')
    requester = payload.get('requester', 'snow')

    required = ['name', 'zone', 'machine_type', 'network', 'subnet']
    if not all(k in vm_config for k in required):
        return {"error": "Missing required vm_config fields"}, 400

    try:
        instance_client = compute_v1.InstancesClient()
        
        disk = compute_v1.AttachedDisk()
        disk.initialize_params = compute_v1.AttachedDiskInitializeParams()
        disk.initialize_params.source_image = GOLDEN_IMAGE_FAMILY
        disk.initialize_params.disk_size_gb = vm_config.get('disk_size_gb', 20)
        disk.auto_delete = True
        disk.boot = True

        network_interface = compute_v1.NetworkInterface()
        network_interface.network = f"projects/{project_id}/global/networks/{vm_config['network']}"
        network_interface.subnetwork = f"projects/{project_id}/regions/{vm_config['zone'][:-2]}/subnetworks/{vm_config['subnet']}"

        instance = compute_v1.Instance()
        instance.name = vm_config['name']
        instance.machine_type = f"zones/{vm_config['zone']}/machineTypes/{vm_config['machine_type']}"
        instance.disks = [disk]
        instance.network_interfaces = [network_interface]
        
        labels = vm_config.get('labels', {})
        labels.update({"created_by": requester.replace('@', '_at_'), "created_via": "snow_webhook", "ticket_number": ticket.lower()})
        instance.labels = labels

        if 'tags' in vm_config:
            tags = compute_v1.Tags(items=vm_config['tags'])
            instance.tags = tags

        if 'startup_script' in vm_config:
            items = compute_v1.Items(key="startup-script", value=vm_config['startup_script'])
            instance.metadata = compute_v1.Metadata(items=[items])

        operation = instance_client.insert_unary(
            project=project_id,
            zone=vm_config['zone'],
            instance_resource=instance
        )
        
        write_audit_log("VM_CREATE", requester, project_id, {"vm_name": vm_config['name'], "zone": vm_config['zone'], "ticket": ticket})
        
        return {"status": "success", "operation_name": operation.name}, 202
    except Exception as e:
        logger.error(f"VM creation failed: {str(e)}")
        return {"error": str(e)}, 500

@functions_framework.http
def servicenow_webhook(request):
    if not verify_hmac(request):
        return json.dumps({"error": "Unauthorized"}), 401, {'Content-Type': 'application/json'}

    try:
        payload = request.get_json()
        req_type = payload.get('request_type')
        
        if req_type == 'iam_grant':
            resp, status = handle_iam_grant(payload)
        elif req_type == 'vm_create':
            resp, status = handle_vm_create(payload)
        else:
            resp, status = {"error": "Invalid request_type"}, 400
            
        return json.dumps(resp), status, {'Content-Type': 'application/json'}
    except Exception as e:
        return json.dumps({"error": "Internal Server Error"}), 500, {'Content-Type': 'application/json'}
```

### requirements_snow.txt

#### What does this script do?
1. Defines Python dependencies for the ServiceNow handler function.
2. Ensures all Google Cloud SDKs and functions-framework are available.

#### I/O Summary
| Input | Process | Output |
| --- | --- | --- |
| `requirements_snow.txt` | Deployed along with function | Dependencies installed |

#### Key Environment Variables
| Name | Required | Description | Example Value |
| --- | --- | --- | --- |
| N/A | No | N/A | N/A |

!!! note "Deployment command"
    Read natively by GCP Cloud Functions during deployment.

!!! tip "How to test it"
    ```bash
    pip install -r requirements_snow.txt
    ```

```text
functions-framework==3.8.1
google-cloud-resource-manager==1.12.4
google-cloud-compute==1.19.1
google-cloud-bigquery==3.25.0
cryptography==43.0.1
```

---

## 3. VM Automated Patch Manager

### Overview
The VM Automated Patch Manager is a daemon run weekly via a systemd timer on compute instances. It loads approved package version constraints from a centralized YAML configuration, queries the local `dpkg-query` database, and evaluates version compliance. Non-compliant packages are targeted for targeted upgrades via `apt-get upgrade`. It generates a comprehensive JSON report and sends an HTML summary via email. It safely supports a `--dry-run` flag for testing without applying changes.

### approved_packages.yaml

#### What does this script do?
1. Defines the desired state of critical packages, setting minimum version constraints.
2. The patch manager parses this file and compares it to installed versions.
3. Provides email delivery configurations and local log retention rules.
4. **Note:** Any changes to this file require SecOps review to ensure compliance with enterprise baseline standards.

#### How to add a new package
To enforce a new package version, add it under the correct category with standard comparison syntax:
```yaml
  # New Package Category
  curl: '>=8.0.0'
```

#### I/O Summary
| Input | Process | Output |
| --- | --- | --- |
| Static YAML file | Loaded by Python parser | Configuration dictionary |

#### Key Environment Variables
| Name | Required | Description | Example Value |
| --- | --- | --- | --- |
| N/A | No | Parsed locally from disk | N/A |

!!! note "Deployment command"
    Deployed to VMs during golden image creation or via Chef/Puppet at `/opt/patch-manager/approved_packages.yaml`.

!!! tip "How to test it"
    ```bash
    yamllint approved_packages.yaml
    ```

```yaml
# Enterprise Approved Package Version Constraints
# Managed by: Platform SRE | SecOps Review: SecOps-2024-Q4-0018
# CIS Reference: CIS Debian Linux 12 L1 Benchmark v1.0.0

packages:
  # Core OS & Shell
  bash: '>=5.2.15'
  coreutils: '>=9.1'
  libc6: '>=2.36'
  systemd: '>=252.22'
  
  # Security-Critical
  openssh-server: '>=1:9.2p1'
  openssl: '>=3.0.11'
  gnupg: '>=2.2.40'
  auditd: '>=1:3.0.9'
  libpam-modules: '>=1.5.2'
  
  # Networking
  curl: '>=7.88.1'
  wget: '>=1.21.3'
  iproute2: '>=6.1.0'
  iptables: '>=1.8.9'
  net-tools: '>=2.10'
  
  # System Libraries
  zlib1g: '>=1:1.2.13'
  libssl3: '>=3.0.11'
  libxml2: '>=2.9.14'
  libsqlite3-0: '>=3.40.1'
  
  # Runtime Environments
  python3: '>=3.11.2'
  openjdk-17-jre-headless: '>=17.0.10'
  nodejs: '>=18.19.0'
  
  # Monitoring & Agents
  google-fluentd: '>=1.9.3'
  oslogin: '>=20230907.00'
  
  # Web & Application Servers
  nginx: '>=1.22.1'
  apache2: '>=2.4.57'

email:
  smtp_host: smtp.enterprise.com
  smtp_port: 587
  from_address: patch-manager@enterprise.com
  recipients:
    - ops-alerts@enterprise.com
    - platform-sre-dl@enterprise.com
  use_tls: true

reporting:
  report_dir: /var/log/patch-manager
  retention_days: 90
  log_file: /var/log/patch-manager/patch.log
```

### vm_patch_manager.py

#### What does this script do?
1. Parses the `approved_packages.yaml` constraints.
2. Uses `dpkg-query` to fetch currently installed package versions on the system.
3. Determines compliance by comparing installed versions against constraints.
4. Uses `apt-get` to perform upgrades for non-compliant packages.
5. Saves a JSON result report locally and emails an HTML summary.

#### I/O Summary
| Input | Process | Output |
| --- | --- | --- |
| YAML config, `dpkg-query` stdout | Validate & upgrade non-compliant packages | `apt-get` system changes, JSON log, Email report |

#### Key Environment Variables
| Name | Required | Description | Example Value |
| --- | --- | --- | --- |
| N/A | No | Takes args directly: `--config` and `--dry-run` | N/A |

!!! note "Deployment command"
    Deployed to `/opt/patch-manager/vm_patch_manager.py`.

!!! tip "How to test it"
    ```bash
    python3 vm_patch_manager.py --config approved_packages.yaml --dry-run
    ```

```python
#!/usr/bin/env python3
"""
VM Automated Patch Manager
Usage: python3 vm_patch_manager.py [--dry-run] [--config /path/to/approved_packages.yaml]
"""

import os
import sys
import yaml
import subprocess
import argparse
import json
import smtplib
import socket
import logging
import logging.handlers
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path
from packaging.version import Version, InvalidVersion

def setup_logging(log_file: str, dry_run: bool):
    logger = logging.getLogger("vm-patch-manager")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}')
    
    Path(os.path.dirname(log_file)).mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    try:
        syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
        syslog_formatter = logging.Formatter('vm-patch-manager: %(message)s')
        syslog_handler.setFormatter(syslog_formatter)
        logger.addHandler(syslog_handler)
    except Exception:
        pass
        
    return logger

def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def get_installed_packages() -> dict:
    try:
        output = subprocess.check_output(["dpkg-query", "-W", "-f=${Package} ${Version}\\n"], universal_newlines=True)
        packages = {}
        for line in output.strip().split('\n'):
            if line:
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    packages[parts[0]] = parts[1]
        return packages
    except subprocess.CalledProcessError as e:
        logging.getLogger("vm-patch-manager").error(f"Failed to query packages: {e}")
        return {}

def parse_constraint(constraint_str: str) -> tuple:
    if constraint_str.startswith('>='):
        return '>=', constraint_str[2:].strip()
    elif constraint_str.startswith('>'):
        return '>', constraint_str[1:].strip()
    elif constraint_str.startswith('=='):
        return '==', constraint_str[2:].strip()
    else:
        return '==', constraint_str.strip()

def is_compliant(installed_ver_str: str, operator: str, required_ver_str: str) -> bool:
    try:
        installed = Version(installed_ver_str.split(':')[-1].split('-')[0])
        required = Version(required_ver_str.split(':')[-1].split('-')[0])
        
        if operator == '>=':
            return installed >= required
        elif operator == '>':
            return installed > required
        elif operator == '==':
            return installed == required
        return False
    except InvalidVersion:
        return installed_ver_str == required_ver_str

def check_compliance(installed: dict, approved_packages: dict) -> list:
    results = []
    for pkg, constraint in approved_packages.items():
        if pkg not in installed:
            results.append({"package": pkg, "installed": "Not Installed", "required": constraint, "compliant": False})
            continue
        
        operator, req_ver = parse_constraint(constraint)
        compliant = is_compliant(installed[pkg], operator, req_ver)
        results.append({"package": pkg, "installed": installed[pkg], "required": constraint, "compliant": compliant})
    return results

def run_apt_update(dry_run: bool) -> bool:
    logger = logging.getLogger("vm-patch-manager")
    logger.info("Running apt-get update")
    if dry_run:
        return True
    try:
        subprocess.check_call(["apt-get", "update", "-qq"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        logger.error("Failed to run apt-get update")
        return False

def upgrade_package(pkg_name: str, dry_run: bool) -> dict:
    logger = logging.getLogger("vm-patch-manager")
    result = {"package": pkg_name, "success": False, "before_version": None, "after_version": None, "error": None}
    
    installed = get_installed_packages()
    result["before_version"] = installed.get(pkg_name, "Not Installed")
    
    if dry_run:
        logger.info(f"DRY RUN: Would upgrade {pkg_name}")
        result["success"] = True
        return result
        
    try:
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        process = subprocess.run(["apt-get", "install", "--only-upgrade", "-y", "-qq", pkg_name], 
                               env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if process.returncode == 0:
            result["success"] = True
            new_installed = get_installed_packages()
            result["after_version"] = new_installed.get(pkg_name, "Unknown")
            logger.info(f"Upgraded {pkg_name} from {result['before_version']} to {result['after_version']}")
        else:
            result["error"] = process.stderr.strip()
            logger.error(f"Failed to upgrade {pkg_name}: {result['error']}")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Exception during upgrade of {pkg_name}: {e}")
        
    return result

def generate_html_report(report_data: dict) -> str:
    html = f"""
    <html><body>
    <h2>Patch Manager Report for {report_data['hostname']}</h2>
    <p>Run Time: {report_data['timestamp']}</p>
    <p>Dry Run: {report_data['dry_run']}</p>
    <table border="1" cellpadding="5" cellspacing="0">
    <tr><th>Package</th><th>Required</th><th>Installed</th><th>Compliant</th><th>Upgraded</th></tr>
    """
    
    for item in report_data['compliance']:
        status_color = "green" if item['compliant'] else "red"
        html += f"<tr><td>{item['package']}</td><td>{item['required']}</td><td>{item['installed']}</td>"
        html += f"<td style='color:{status_color}'>{item['compliant']}</td><td>N/A</td></tr>"
        
    for item in report_data.get('upgrades', []):
        success = "Yes" if item['success'] else "No"
        html += f"<tr><td>{item['package']}</td><td>N/A</td><td>{item['after_version']}</td>"
        html += f"<td>N/A</td><td>{success} (was {item['before_version']})</td></tr>"
        
    html += "</table></body></html>"
    return html

def send_email_report(html_content: str, report_data: dict, email_config: dict) -> bool:
    logger = logging.getLogger("vm-patch-manager")
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Patch Report [{report_data['hostname']}] - {'DRY RUN' if report_data['dry_run'] else 'APPLIED'}"
    msg['From'] = email_config['from_address']
    msg['To'] = ", ".join(email_config['recipients'])
    
    msg.attach(MIMEText("Please view HTML version.", 'plain'))
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        server = smtplib.SMTP(email_config['smtp_host'], email_config['smtp_port'])
        if email_config.get('use_tls', True):
            server.starttls()
        server.send_message(msg)
        server.quit()
        logger.info("Sent email report successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def save_json_report(report_data: dict, report_dir: str) -> str:
    Path(report_dir).mkdir(parents=True, exist_ok=True)
    filename = f"patch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(report_dir, filename)
    with open(filepath, 'w') as f:
        json.dump(report_data, f, indent=2)
    return filepath

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help="Do not make actual changes")
    parser.add_argument('--config', required=True, help="Path to YAML config")
    args = parser.parse_args()
    
    config = load_config(args.config)
    logger = setup_logging(config['reporting']['log_file'], args.dry_run)
    logger.info(f"Starting patch manager scan (Dry run: {args.dry_run})")
    
    installed = get_installed_packages()
    compliance = check_compliance(installed, config['packages'])
    
    non_compliant = [c for c in compliance if not c['compliant']]
    
    report_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "hostname": socket.gethostname(),
        "dry_run": args.dry_run,
        "compliance": compliance,
        "upgrades": []
    }
    
    final_success = True
    
    if non_compliant:
        run_apt_update(args.dry_run)
        for nc in non_compliant:
            res = upgrade_package(nc['package'], args.dry_run)
            report_data['upgrades'].append(res)
            if not res['success'] and not args.dry_run:
                final_success = False
                
        # Re-check compliance after upgrades
        new_installed = get_installed_packages()
        report_data['compliance'] = check_compliance(new_installed, config['packages'])
        
    html = generate_html_report(report_data)
    save_json_report(report_data, config['reporting']['report_dir'])
    send_email_report(html, report_data, config['email'])
    
    logger.info("Patch manager completed")
    sys.exit(0 if final_success else 1)

if __name__ == "__main__":
    main()
```

### vm_patch_manager.sh

#### What does this script do?
1. Checks that the current user is root.
2. Rotates logs older than 90 days.
3. Acquires an exclusive file lock to ensure only one instance runs at a time.
4. Activates the Python virtual environment and executes the Python patch manager script.

#### I/O Summary
| Input | Process | Output |
| --- | --- | --- |
| Execution request (from systemd) | Wrap execution, handle locks | Returns script exit code |

#### Key Environment Variables
| Name | Required | Description | Example Value |
| --- | --- | --- | --- |
| N/A | No | Script utilizes hardcoded paths | N/A |

!!! note "Deployment command"
    Ensure script is executable: `chmod +x /opt/patch-manager/vm_patch_manager.sh`

!!! tip "How to test it"
    ```bash
    sudo /opt/patch-manager/vm_patch_manager.sh --dry-run
    ```

```bash
#!/usr/bin/env bash
set -euo pipefail

LOCK_FILE="/var/run/vm-patch-manager.lock"
LOG_DIR="/var/log/patch-manager"
VENV_PATH="/opt/patch-manager/venv"
SCRIPT_PATH="/opt/patch-manager/vm_patch_manager.py"
CONFIG_PATH="/opt/patch-manager/approved_packages.yaml"

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script must be run as root" >&2
        exit 1
    fi
}

rotate_logs() {
    echo "Rotating old logs..."
    find "${LOG_DIR}" -name '*.json' -type f -mtime +90 -delete
}

acquire_lock() {
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        echo "Another instance is already running. Exiting." >&2
        exit 1
    fi
}

main() {
    check_root
    mkdir -p "${LOG_DIR}"
    rotate_logs
    acquire_lock
    
    if [[ ! -f "${VENV_PATH}/bin/activate" ]]; then
        echo "Virtual environment not found at ${VENV_PATH}" >&2
        exit 1
    fi
    
    source "${VENV_PATH}/bin/activate"
    
    set +e
    python3 "${SCRIPT_PATH}" --config "${CONFIG_PATH}" "$@"
    EXIT_CODE=$?
    set -e
    
    if [[ $EXIT_CODE -ne 0 ]]; then
        echo "vm_patch_manager.py exited with error code ${EXIT_CODE}" >&2
        # Example Slack webhook alert could go here:
        # curl -s -X POST -H 'Content-type: application/json' --data '{"text":"🚨 Patch Manager Failed!"}' "$SLACK_WEBHOOK_URL"
    fi
    
    exit $EXIT_CODE
}

main "$@"
```

### vm-patch-manager.service

#### What does this script do?
1. Defines a `oneshot` systemd service, meaning it executes the script and terminates, rather than running continuously as a daemon.
2. Instructs systemd on how to start the wrapper shell script as `root`.
3. Sets up standard logging output to the journal.

#### I/O Summary
| Input | Process | Output |
| --- | --- | --- |
| Systemd timer trigger | Execute defined `ExecStart` command | Script exit code, Journal logs |

#### Key Environment Variables
| Name | Required | Description | Example Value |
| --- | --- | --- | --- |
| N/A | No | Configured natively within the `.service` file | N/A |

!!! note "Deployment command"
    ```bash
    sudo cp vm-patch-manager.service /etc/systemd/system/
    sudo systemctl daemon-reload
    ```

!!! tip "How to test it"
    ```bash
    sudo systemctl start vm-patch-manager.service
    sudo journalctl -u vm-patch-manager.service -f
    ```

```ini
[Unit]
Description=VM Automated Patch Manager Service
After=network.target
Documentation=https://docs.enterprise.com/sre/patch-manager

[Service]
Type=oneshot
ExecStart=/opt/patch-manager/vm_patch_manager.sh
User=root
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vm-patch-manager
TimeoutStartSec=3600

[Install]
WantedBy=multi-user.target
```

### vm-patch-manager.timer

#### What does this script do?
1. Defines the scheduling for the patch manager service.
2. `Persistent=true` guarantees execution if the VM was powered off during the scheduled time window.
3. `RandomizedDelaySec=1800` ensures that fleets of VMs do not hammer package repositories at the exact same time.

#### I/O Summary
| Input | Process | Output |
| --- | --- | --- |
| Real-time clock | Evaluate time schedule constraints | Triggers `vm-patch-manager.service` |

#### Key Environment Variables
| Name | Required | Description | Example Value |
| --- | --- | --- | --- |
| N/A | No | Driven entirely by systemd internal logic | N/A |

!!! note "Deployment command"
    ```bash
    sudo cp vm-patch-manager.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now vm-patch-manager.timer
    ```

!!! tip "How to test it"
    ```bash
    sudo systemctl list-timers | grep vm-patch-manager
    ```

```ini
[Unit]
Description=Weekly VM Patch Manager Execution

[Timer]
OnCalendar=Sun *-*-* 02:00:00
Persistent=true
RandomizedDelaySec=1800

[Install]
WantedBy=timers.target
```
