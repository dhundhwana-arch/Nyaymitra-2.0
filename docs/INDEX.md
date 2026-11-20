# Documentation Index

**NYAYMITRA 2.0 — map of every document in this repository**

**Created & Developed by Bambhaniya Divyesh Nonghanbhai**

**At commit:** `342103eca3e209e10bd705a2ac5c48225c9afe13`

---

## Start here

Read in this order. Each answers a different question.

| Order | Document | Answers |
|---|---|---|
| 1 | [`../README.md`](../README.md) | What is this project and how do I run it? |
| 2 | [`../PROJECT_FINAL_STATUS.md`](../PROJECT_FINAL_STATUS.md) | What state is it actually in, right now? |
| 3 | [`../MASTER_PROJECT_CONTEXT.md`](../MASTER_PROJECT_CONTEXT.md) | Full technical and historical context (12 sections) |
| 4 | [`../COMPLETED_WORK_INVENTORY.md`](../COMPLETED_WORK_INVENTORY.md) | What is built, with evidence per item |
| 5 | [`../GEMINI_HANDOVER.md`](../GEMINI_HANDOVER.md) | How to continue without rebuilding anything |
| 6 | [`FEATURE_STATUS.md`](FEATURE_STATUS.md) | Per-feature status with the test that proves it |

---

## Architecture and design

| Document | Contents |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System layers, request flow, safety pipeline |
| [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) | 22 tables, 30 indexes, invariants |
| [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) | 41 operations under `/api/v1` |
| [`MULTILINGUAL_IMPLEMENTATION_REPORT.md`](MULTILINGUAL_IMPLEMENTATION_REPORT.md) | 23-language registry, RTL, status model |
| [`LANGUAGE_AVAILABILITY_MATRIX.md`](LANGUAGE_AVAILABILITY_MATRIX.md) | Per-language completeness |
| [`LOCALE_QUALITY_AUDIT.md`](LOCALE_QUALITY_AUDIT.md) | Translation quality findings |
| [`INTEGRATION_PLAN.md`](INTEGRATION_PLAN.md) | How the rebuild branches were merged |

## Data and legal corpus

| Document | Contents |
|---|---|
| [`DATA_SOURCE_REGISTER.md`](DATA_SOURCE_REGISTER.md) | 15 registered legal sources |
| [`LEGAL_VERIFICATION_CHECKLIST.md`](LEGAL_VERIFICATION_CHECKLIST.md) | What a human reviewer must check |
| [`LOCAL_DATA_RECOVERY_AND_IMPORT_PLAN.md`](LOCAL_DATA_RECOVERY_AND_IMPORT_PLAN.md) | Recovering the owner's local corpus |
| [`PHASE4_DATA_IMPORT_REPORT.md`](PHASE4_DATA_IMPORT_REPORT.md) | Importer results |
| [`PHASE4A_DATA_RECOVERY_GUIDE.md`](PHASE4A_DATA_RECOVERY_GUIDE.md) | Read-only inventory tool usage |
| [`PHASE_3B_ACQUISITION_REPORT.md`](PHASE_3B_ACQUISITION_REPORT.md) | Source acquisition attempt |
| [`PHASE_3C_REPORT.md`](PHASE_3C_REPORT.md) · [`PHASE_3C_STATUS.md`](PHASE_3C_STATUS.md) | Acquisition outcome |
| [`PHASE_3D_DATABASE_AUDIT.md`](PHASE_3D_DATABASE_AUDIT.md) · [`PHASE_3D_REMEDIATION_PLAN.md`](PHASE_3D_REMEDIATION_PLAN.md) | Legacy corpus audit and remediation |
| [`NYAYMITRA_DATA_ACTIVATION_REPORT.md`](NYAYMITRA_DATA_ACTIVATION_REPORT.md) | Data activation work |

## Testing and quality

| Document | Contents |
|---|---|
| [`TESTING_REPORT.md`](TESTING_REPORT.md) | 475 tests, 92 % coverage |
| [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) | Every known limitation, numbered |
| [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md) | Security posture |
| [`security/THREAT_MODEL.md`](security/THREAT_MODEL.md) | Threat model |
| [`security/INCIDENT_RESPONSE.md`](security/INCIDENT_RESPONSE.md) | Incident process |
| [`security/BACKUP_AND_RECOVERY.md`](security/BACKUP_AND_RECOVERY.md) | Backup and restore |

## Release and deployment

| Document | Contents |
|---|---|
| [`RELEASE_READINESS_CHECKLIST.md`](RELEASE_READINESS_CHECKLIST.md) | 3-stage release gate (A/B/C) |
| [`REMAINING_BLOCKERS.md`](REMAINING_BLOCKERS.md) | What still blocks release |
| [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) | Deployment procedure |
| [`REPOSITORY_AND_PRODUCTION_READINESS.md`](REPOSITORY_AND_PRODUCTION_READINESS.md) | Repo vs production state |
| [`REPOSITORY_IDENTITY.md`](REPOSITORY_IDENTITY.md) | Approved repo description and naming |
| [`../DEPLOY_MANUAL.md`](../DEPLOY_MANUAL.md) | Step-by-step manual deploy |

## Legal, privacy and IP

| Document | Contents |
|---|---|
| [`legal/LEGAL_COMPLIANCE_MATRIX.md`](legal/LEGAL_COMPLIANCE_MATRIX.md) | Applicable Indian law mapped to controls |
| [`legal/LEGAL_RISK_REGISTER.md`](legal/LEGAL_RISK_REGISTER.md) | Legal risk register |
| [`legal/DATA_FLOW_MAP.md`](legal/DATA_FLOW_MAP.md) | Where personal data goes |
| [`legal/DATA_RETENTION_POLICY.md`](legal/DATA_RETENTION_POLICY.md) | Retention rules |
| [`legal/CONSENT_AND_NOTICE_REVIEW.md`](legal/CONSENT_AND_NOTICE_REVIEW.md) | Consent and notice |
| [`legal/HUMAN_LEGAL_REVIEW_CHECKLIST.md`](legal/HUMAN_LEGAL_REVIEW_CHECKLIST.md) | Reviewer checklist |
| [`ip/IP_INVENTORY.md`](ip/IP_INVENTORY.md) | Intellectual property inventory |
| [`ip/THIRD_PARTY_LICENSE_AUDIT.md`](ip/THIRD_PARTY_LICENSE_AUDIT.md) | Dependency licences incl. AGPL note |
| [`ip/SOFTWARE_BILL_OF_MATERIALS.md`](ip/SOFTWARE_BILL_OF_MATERIALS.md) | SBOM |
| [`ip/OWNERSHIP_AND_CONTRIBUTION_REVIEW.md`](ip/OWNERSHIP_AND_CONTRIBUTION_REVIEW.md) | Ownership review |
| [`ip/GOVERNMENT_LICENSING_READINESS.md`](ip/GOVERNMENT_LICENSING_READINESS.md) | Licensing readiness |

## Audit and history

| Document | Contents |
|---|---|
| [`audits/HACKINDIA_READINESS_AND_PROJECT_STATUS.md`](audits/HACKINDIA_READINESS_AND_PROJECT_STATUS.md) | HackIndia readiness audit (redacted) |
| [`REPOSITORY_AUDIT.md`](REPOSITORY_AUDIT.md) | Repository audit |
| [`CANONICAL_BUILD_AND_BRANCH_RECONCILIATION.md`](CANONICAL_BUILD_AND_BRANCH_RECONCILIATION.md) | How canonical was chosen |
| [`../CONVERSATION_CONSOLIDATION_REPORT.md`](../CONVERSATION_CONSOLIDATION_REPORT.md) | Two-conversation consolidation audit |
| [`NYAYMITRA_FRONTEND_BACKEND_CONNECTION_REPORT.md`](NYAYMITRA_FRONTEND_BACKEND_CONNECTION_REPORT.md) | Frontend/backend wiring |
| [`HANDOVER.md`](HANDOVER.md) | Earlier handover note (superseded by `GEMINI_HANDOVER.md`) |
| [`FINAL_COMPLETION_REPORT.md`](FINAL_COMPLETION_REPORT.md) | Earlier completion report (**historical**) |

---

## ⚠ Historical documents — numbers are stale

These describe an **earlier snapshot** (226 tests, commit `8b1e652`, PR #1). Treat their figures as historical, not current.

* [`../FINAL_PROJECT_COMPLETION_REPORT.md`](../FINAL_PROJECT_COMPLETION_REPORT.md)
* [`../FINAL_VERIFICATION_REPORT.md`](../FINAL_VERIFICATION_REPORT.md)
* [`../HACKINDIA_SUBMISSION.md`](../HACKINDIA_SUBMISSION.md)
* [`../GOVERNMENT_SUBMISSION_PACKAGE/README.md`](../GOVERNMENT_SUBMISSION_PACKAGE/README.md)
* [`PHASE_3C_STATUS.md`](PHASE_3C_STATUS.md)

**Current authority:** [`../PROJECT_FINAL_STATUS.md`](../PROJECT_FINAL_STATUS.md) and [`../MASTER_PROJECT_CONTEXT.md`](../MASTER_PROJECT_CONTEXT.md).

---

**Created & Developed by Bambhaniya Divyesh Nonghanbhai**
