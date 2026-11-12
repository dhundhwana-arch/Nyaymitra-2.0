# THIRD_PARTY_LICENSE_AUDIT.md

NYAYMITRA 2.0 — Third-party licence audit
==========================================

## Method

Installed-package metadata was read directly (no network) with
`scripts/license_audit.py`. An unknown or missing licence is reported as "unknown"
— never assumed permissive.

## Runtime dependencies (declared in `backend/requirements.txt`)

| Package | Version | Licence (from metadata) | Classification |
|---------|---------|-------------------------|----------------|
| email-validator | 2.2.0 | Unlicense | Permissive |
| fastapi | 0.162.2 | MIT | Permissive |
| httpx | 0.28.1 | BSD-3-Clause | Permissive |
| pydantic | 2.10.3 | MIT | Permissive |
| pypdf | 7.0.0 | BSD-3-Clause | Permissive |
| python-multipart | 0.0.33 | Apache-2.0 | Permissive |
| uvicorn | 0.54.0 | BSD-3-Clause | Permissive |

Full transitive closure (60 packages): 60 permissive, 0 copyleft, 0 unknown.

## Summary

* Copyleft packages: **0** (no GPL / AGPL / LGPL / SSPL).
* Unknown-licence packages: **0**.
* All runtime packages permit proprietary distribution and government licensing with
  attribution.

## Obligations

* MIT / BSD: include copyright notice and licence text in distributions.
* Apache-2.0: include copyright, licence, and a notice of changes (if modified — we have
  not modified these packages).
* Unlicense: public-domain dedication; no attribution obligation.

No redistribution restriction applies to the dependencies themselves. The project's own
code is separately licensed under the repository `LICENSE` (MIT).

## How to re-run

```bash
python scripts/license_audit.py           # declared runtime requirements
python scripts/license_audit.py --all     # full transitive closure incl. dev tools
python scripts/license_audit.py --fail-on-copyleft   # CI gate
```

## Limitation

This audit covers Python package metadata only. It does not cover fonts, icons, images,
datasets, or external service terms (no external services are used at runtime).
