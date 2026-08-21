#!/usr/bin/env python3
import os
import yaml
import subprocess
import argparse
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from packaging.version import parse as parse_version
import socket
import logging

LOG_FILE = "/var/log/patch-manager/patch.log"
REPORT_DIR = "/var/log/patch-manager"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "approved_packages.yaml")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("vm_patch_manager")

def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def get_installed_packages():
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${Package} ${Version}\n"],
        stdout=subprocess.PIPE,
        text=True,
        check=True
    )
    packages = {}
    for line in result.stdout.strip().split('\n'):
        if line:
            parts = line.split()
            if len(parts) == 2:
                packages[parts[0]] = parts[1]
    return packages

def check_compliance(installed, approved):
    out_of_compliance = []
    for pkg, constraint in approved.items():
        if pkg in installed:
            installed_ver = installed[pkg]
            # Strip out debian revision for basic comparison if needed, or use full
            # format from constraint is like '>=1.24.0'
            op = constraint[:2]
            req_ver = constraint[2:]
            
            v_inst = parse_version(installed_ver.split('-')[0])
            v_req = parse_version(req_ver)
            
            if op == '>=':
                if v_inst < v_req:
                    out_of_compliance.append((pkg, installed_ver, req_ver))
    return out_of_compliance

def apt_update():
    logger.info("Running apt-get update")
    subprocess.run(["apt-get", "update"], check=True, stdout=subprocess.DEVNULL)

def upgrade_package(pkg, dry_run=False):
    if dry_run:
        logger.info(f"[DRY-RUN] Would upgrade {pkg}")
        return True
    
    logger.info(f"Upgrading {pkg}")
    res = subprocess.run(
        ["apt-get", "install", "--only-upgrade", "-y", pkg],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if res.returncode == 0:
        return True
    else:
        logger.error(f"Failed to upgrade {pkg}: {res.stderr.decode()}")
        return False

def send_report_email(report_data):
    sender = "patch-manager@enterprise.com"
    recipient = "ops-alerts@enterprise.com"
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Patch Report - {report_data['hostname']} - {report_data['compliance_percentage']}% Compliant"
    msg['From'] = sender
    msg['To'] = recipient

    html = f"""
    <html>
      <head></head>
      <body>
        <h2>Patch Management Report</h2>
        <p><b>Hostname:</b> {report_data['hostname']}</p>
        <p><b>Timestamp:</b> {report_data['timestamp']}</p>
        <p><b>Compliance:</b> {report_data['compliance_percentage']}%</p>
        <ul>
            <li>Checked: {report_data['packages_checked']}</li>
            <li>Upgraded: {report_data['packages_upgraded']}</li>
            <li>Failed: {report_data['packages_failed']}</li>
        </ul>
      </body>
    </html>
    """
    
    part = MIMEText(html, 'html')
    msg.attach(part)
    
    try:
        s = smtplib.SMTP('localhost')
        s.sendmail(sender, [recipient], msg.as_string())
        s.quit()
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

def main():
    parser = argparse.ArgumentParser(description="VM Patch Manager")
    parser.add_argument("--dry-run", action="store_true", help="Do not actually upgrade packages")
    args = parser.parse_args()
    
    approved = load_config(CONFIG_FILE)
    installed = get_installed_packages()
    
    out_of_compliance = check_compliance(installed, approved)
    
    report = {
        "hostname": socket.gethostname(),
        "timestamp": datetime.utcnow().isoformat(),
        "packages_checked": len(approved),
        "packages_upgraded": 0,
        "packages_failed": 0,
        "compliance_percentage": 100.0,
        "dry_run": args.dry_run
    }
    
    if out_of_compliance:
        if not args.dry_run:
            apt_update()
            
        for pkg, inst_ver, req_ver in out_of_compliance:
            success = upgrade_package(pkg, args.dry_run)
            if success:
                report["packages_upgraded"] += 1
            else:
                report["packages_failed"] += 1
                
        # Re-check compliance
        if not args.dry_run:
            installed_after = get_installed_packages()
            final_out_of_compliance = check_compliance(installed_after, approved)
            compliant_count = len(approved) - len(final_out_of_compliance)
            report["compliance_percentage"] = round((compliant_count / len(approved)) * 100, 2)
        else:
            report["compliance_percentage"] = round(((len(approved) - len(out_of_compliance) + report["packages_upgraded"]) / len(approved)) * 100, 2)
            
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_file = os.path.join(REPORT_DIR, f"report-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
        
    logger.info(f"Report saved to {report_file}")
    send_report_email(report)

if __name__ == "__main__":
    main()
