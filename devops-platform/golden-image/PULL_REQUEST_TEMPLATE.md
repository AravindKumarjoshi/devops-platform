# PR Title Format: [JIRA-1234] Brief description of changes

## Ticket Linkage
- **Jira/ServiceNow ID:** [Enter Ticket ID Here]
- **Link:** [Link to Ticket]

## Change Type (Check all that apply)
- [ ] CIS hardening update
- [ ] Package addition
- [ ] Package removal
- [ ] Package version update
- [ ] Ops agent config
- [ ] Firewall rule
- [ ] Other

## Justification and Business Case
[Provide a clear justification for why this change is necessary and the business value it brings.]

## SecOps Approval Checklist
- [ ] CIS benchmark reference checked and adhered to
- [ ] CVE scan completed and reviewed
- [ ] Security review requested

## Testing Evidence
- [ ] Packer validate passed
- [ ] Ansible lint passed
- [ ] Test VM spun up from candidate image
- [ ] Application/Validation tests passed

## Rollback Plan
[Describe the steps to revert this change if issues occur in production. E.g., re-run pipeline on previous commit.]

## Affected Image Families
- [ ] enterprise-rhel9-base
- [ ] enterprise-debian12-base
- [ ] Other: 

## Review Requirements
- [ ] SecOps Approval
- [ ] Platform SRE 1 Approval
- [ ] Platform SRE 2 Approval

## Post-Merge Checklist
- [ ] Verify Cloud Build pipeline completes successfully
- [ ] Confirm new images are available in GCP console
- [ ] Verify ServiceNow CMDB update
