import os
import re
import hmac
import hashlib
import time
from datetime import datetime
from flask import Flask, request, jsonify
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

app = Flask(__name__)
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
PAGERDUTY_API_TOKEN = os.environ.get("PAGERDUTY_API_TOKEN", "")
PAGERDUTY_SERVICE_ID = os.environ.get("PAGERDUTY_SERVICE_ID", "")
PAGERDUTY_ESCALATION_POLICY_ID = os.environ.get("PAGERDUTY_ESCALATION_POLICY_ID", "")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

slack_client = WebClient(token=SLACK_BOT_TOKEN)

TEAM_TO_DL = {
    "platform-sre": "platform-sre-dl@enterprise.com",
    "data-engineering": "data-eng-dl@enterprise.com",
    "backend": "backend-dl@enterprise.com",
    "frontend": "frontend-dl@enterprise.com",
    "security": "secops-dl@enterprise.com"
}

def verify_slack_signature(request):
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False
    sig_basestring = "v0:" + timestamp + ":" + request.get_data(as_text=True)
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    slack_signature = request.headers.get("X-Slack-Signature", "")
    return hmac.compare_digest(my_signature, slack_signature)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(requests.exceptions.RequestException))
def get_pagerduty_oncall(team_name):
    headers = {
        "Authorization": f"Token token={PAGERDUTY_API_TOKEN}",
        "Accept": "application/vnd.pagerduty+json;version=2"
    }
    # Find schedule
    resp = requests.get(f"https://api.pagerduty.com/schedules?query={team_name}", headers=headers)
    resp.raise_for_status()
    schedules = resp.json().get("schedules", [])
    if not schedules:
        return None, None
    schedule_id = schedules[0]["id"]
    
    # Get current on-call
    resp = requests.get(f"https://api.pagerduty.com/oncalls?schedule_ids[]={schedule_id}&earliest=true", headers=headers)
    resp.raise_for_status()
    oncalls = resp.json().get("oncalls", [])
    if not oncalls:
        return None, None
    user = oncalls[0].get("user", {})
    return user.get("id"), user.get("summary")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(requests.exceptions.RequestException))
def create_pagerduty_incident(title, team_name):
    headers = {
        "Authorization": f"Token token={PAGERDUTY_API_TOKEN}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json",
        "From": "bot@enterprise.com"
    }
    payload = {
        "incident": {
            "type": "incident",
            "title": f"[Slack {team_name}] {title}",
            "service": {
                "id": PAGERDUTY_SERVICE_ID,
                "type": "service_reference"
            },
            "escalation_policy": {
                "id": PAGERDUTY_ESCALATION_POLICY_ID,
                "type": "escalation_policy_reference"
            },
            "urgency": "high"
        }
    }
    resp = requests.post("https://api.pagerduty.com/incidents", json=payload, headers=headers)
    resp.raise_for_status()
    incident = resp.json().get("incident", {})
    return incident.get("html_url")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def send_email_alert(dl_email, incident_url, oncall_name, title):
    message = Mail(
        from_email="pagerduty-bot@enterprise.com",
        to_emails=dl_email,
        subject=f"PagerDuty Incident Created: {title}",
        html_content=f"<strong>Incident:</strong> {title}<br/><strong>URL:</strong> <a href='{incident_url}'>{incident_url}</a><br/><strong>On-call:</strong> {oncall_name}"
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    return response.status_code

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    
    if not verify_slack_signature(request):
        logger.error("invalid_slack_signature")
        return jsonify({"error": "invalid signature"}), 403
    
    event = data.get("event", {})
    if event.get("type") == "message" and not event.get("bot_id"):
        text = event.get("text", "")
        match = re.search(r"@pagerduty\s+([a-zA-Z0-9_-]+)(.*)", text, re.IGNORECASE)
        if match:
            team_name = match.group(1).strip()
            msg_body = match.group(2).strip() or "No description provided."
            channel = event.get("channel")
            ts = event.get("ts")
            
            try:
                user_id, oncall_name = get_pagerduty_oncall(team_name)
                if not oncall_name:
                    oncall_name = "Unknown"
                
                incident_url = create_pagerduty_incident(msg_body, team_name)
                
                dl_email = TEAM_TO_DL.get(team_name.lower())
                if dl_email:
                    send_email_alert(dl_email, incident_url, oncall_name, msg_body)
                
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=ts,
                    text=f"Incident created! URL: {incident_url}\nCurrent On-Call: {oncall_name}\nStatus: High Urgency"
                )
                logger.info("incident_created", team=team_name, url=incident_url, oncall=oncall_name)
            except Exception as e:
                logger.error("incident_creation_failed", error=str(e))
                slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=ts,
                    text=f"Failed to create incident: {str(e)}"
                )
                
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
