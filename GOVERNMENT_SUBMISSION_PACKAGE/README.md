# NYAYMITRA 2.0 — Government Submission Package

**AI-Powered Inclusive Justice Access & Navigation System**
Functional software prototype / Proof of Concept — subject to independent evaluation.

## Repository

- **URL:** https://github.com/dhundhwana-arch/Nyaymitra-2.0
- **Branch:** `arena/812d6894-nyaymitra-2-0`
- **Audited source snapshot:** `cc56d0e` (tests and validation executed here); **Final package commit:** `947698e`
- **Pull request:** #1 — https://github.com/dhundhwana-arch/Nyaymitra-2.0/pull/1 (open, draft, mergeable — owner approval required to merge)
- **CI:** push run `42599240604` green on commit `8b1e652` (current HEAD); prior push run `42598098956` green on commit `947698e` (package commit); source snapshot `cc56d0e` verified via push run `42595255121`

## Contents

| File | Description |
|------|-------------|
| `sources/Executive_Summary.md` | Editable source — government-facing overview |
| `sources/NYAYMITRA_2.0_Project_Report.md` | Editable source — full project report |
| `sources/Technical_Architecture_Report.md` | Editable source — architecture |
| `sources/Prototype_Progress_Report.md` | Editable source — progress & evidence |
| `sources/Legal_Privacy_Safety_Report.md` | Editable source — legal/privacy/safety |
| `sources/Development_Roadmap.md` | Editable source — 1-month + post-support roadmap |
| `sources/Risk_Register.md` | Editable source — risks & mitigations |
| `sources/Government_Pitch_Deck.md` | Editable source — 8–10 slide deck |
| `sources/Demo_Script.md` | Editable source — 3 citizen journeys |
| `sources/Submission_Checklist.md` | Editable source — SSIP/Startup Srujan fields |
| `EVIDENCE_MATRIX.md` | Traceability: claim → evidence → location → status → limitation |
| `*.pdf` | Rendered PDFs of each source document |

## Positioning

NYAYMITRA 2.0 is presented as a **functional software prototype / Proof of Concept**, subject to independent evaluation. It is intended to assist citizens in understanding legal information, locating relevant government departments, identifying official sources, and finding human assistance.

It is **NOT intended to replace** courts, lawyers, police, government authorities, or qualified legal professionals.

## Verified evidence (source snapshot `cc56d0e`; final package commit `947698e`)

| Check | Result |
|-------|--------|
| Automated test suite (`pytest`) | 226 passed, 0 failed |
| Coverage (`--cov=backend/app`) | 92% — 2,545 statements, 202 missed |
| Dependency audit (`pip-audit`) | No known vulnerabilities found |
| Database integrity (`scripts/check_db.py`) | OK — integrity ok, 4 migrations applied, 0 missing indexes |
| Frontend syntax (`node --check`) | Pass |
| App startup (`uvicorn`) | `/api/v1/ready` = 200, offline provider |
| Real AI model (`verify_ai_provider.py`) | Exit 3 — no model runtime available (BLOCKED) |
| Human legal review | 0 articles verified — reviewer packet ready (BLOCKED) |

See `EVIDENCE_MATRIX.md` for full traceability.

## How to reproduce

```bash
git clone https://github.com/dhundhwana-arch/Nyaymitra-2.0.git
cd Nyaymitra-2.0
git checkout arena/812d6894-nyaymitra-2-0
python3 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements-dev.txt
python scripts/init_db.py              # migrate + seed
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
python -m pytest -q --cov=backend/app  # 226 passed, 92% coverage
```

## Approvals required before submission

1. Repository owner: review and merge PR #1 (no force push, no merge by this agent).
2. Named human legal reviewer: sign off legal content (9 articles, 11 departments, 5 triage guides).
3. Real-device / screen-reader testing.
4. Real AI model verification against `scripts/verify_ai_provider.py`.

No API keys, credentials, or personal data are included in this package.
