import os
import hmac
import hashlib
import json
import uuid
from datetime import datetime
import functions_framework
from google.cloud import resourcemanager_v3, compute_v1, bigquery
from cryptography.hazmat.primitives import hashes

SERVICENOW_SECRET = os.environ.get("SERVICENOW_SECRET", "").encode()
BQ_DATASET = "enterprise-audit.iam_changes"
BQ_TABLE = f"{BQ_DATASET}.gcp_grants"

APPROVED_ROLES = {
    "roles/dataproc.editor",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/compute.instanceAdmin.v1",
    "roles/compute.networkUser"
}

def verify_signature(request):
    signature = request.headers.get("X-ServiceNow-Signature")
    if not signature:
        return False
    payload = request.get_data()
    expected = hmac.new(SERVICENOW_SECRET, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def audit_log(action, requester, target, details):
    client = bigquery.Client()
    rows = [{
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "requester": requester,
        "target": target,
        "details": json.dumps(details)
    }]
    client.insert_rows_json(BQ_TABLE, rows)

def handle_iam_grant(payload):
    project_id = payload.get("gcp_project_id")
    principal = payload.get("principal")
    roles = payload.get("roles", [])
    requester = payload.get("requester_email")
    
    if not all(r in APPROVED_ROLES for r in roles):
        return {"error": "One or more roles not in approved list"}, 403
        
    client = resourcemanager_v3.ProjectsClient()
    project_name = f"projects/{project_id}"
    
    policy = client.get_iam_policy(request={"resource": project_name})
    
    for role in roles:
        binding_exists = False
        for binding in policy.bindings:
            if binding.role == role:
                binding.members.append(f"user:{principal}")
                binding_exists = True
                break
        if not binding_exists:
            policy.bindings.add(role=role, members=[f"user:{principal}"])
            
    client.set_iam_policy(request={"resource": project_name, "policy": policy})
    
    audit_log("iam_grant", requester, project_id, {"principal": principal, "roles": roles})
    return {"status": "success", "message": f"Granted roles {roles} to {principal}"}, 200

def handle_vm_create(payload):
    project_id = payload.get("gcp_project_id")
    requester = payload.get("requester_email")
    config = payload.get("vm_config", {})
    
    name = config.get("name")
    zone = config.get("zone")
    ticket_number = config.get("ticket_number", "UNKNOWN")
    
    instance_client = compute_v1.InstancesClient()
    
    labels = config.get("labels", {})
    labels.update({
        "created_by": requester.replace("@", "_at_").replace(".", "_"),
        "created_via": "servicenow",
        "ticket_number": ticket_number
    })
    
    instance = compute_v1.Instance()
    instance.name = name
    instance.machine_type = f"zones/{zone}/machineTypes/{config.get('machine_type', 'e2-medium')}"
    
    disk = compute_v1.AttachedDisk()
    disk.initialize_params = compute_v1.AttachedDiskInitializeParams()
    disk.initialize_params.source_image = "projects/enterprise-images/global/images/family/enterprise-rhel9-base"
    disk.initialize_params.disk_size_gb = int(config.get("disk_size_gb", 20))
    disk.auto_delete = True
    disk.boot = True
    instance.disks = [disk]
    
    network_interface = compute_v1.NetworkInterface()
    network_interface.network = f"projects/{project_id}/global/networks/{config.get('network', 'default')}"
    if config.get("subnet"):
        network_interface.subnetwork = f"projects/{project_id}/regions/{zone[:-2]}/subnetworks/{config.get('subnet')}"
    instance.network_interfaces = [network_interface]
    
    instance.labels = labels
    
    if config.get("service_account"):
        sa = compute_v1.ServiceAccount()
        sa.email = config.get("service_account")
        sa.scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        instance.service_accounts = [sa]
        
    tags = compute_v1.Tags()
    tags.items = config.get("tags", [])
    instance.tags = tags
    
    metadata = compute_v1.Metadata()
    if config.get("startup_script"):
        metadata.items = [
            compute_v1.Items(key="startup-script", value=config.get("startup_script"))
        ]
    instance.metadata = metadata

    op = instance_client.insert(project=project_id, zone=zone, instance_instance_resource=instance)
    op.result() # Wait for completion
    
    audit_log("vm_create", requester, project_id, {"instance": name, "zone": zone})
    return {"status": "success", "resource_url": f"https://console.cloud.google.com/compute/instancesDetail/zones/{zone}/instances/{name}?project={project_id}"}, 200

@functions_framework.http
def servicenow_webhook(request):
    if not verify_signature(request):
        return {"error": "Invalid signature"}, 401
        
    try:
        payload = request.get_json()
        req_type = payload.get("request_type")
        
        if req_type == "iam_grant":
            res, code = handle_iam_grant(payload)
            return res, code
        elif req_type == "vm_create":
            res, code = handle_vm_create(payload)
            return res, code
        else:
            return {"error": "Unknown request_type"}, 400
    except Exception as e:
        return {"error": str(e)}, 500
