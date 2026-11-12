# SOFTWARE_BILL_OF_MATERIALS.md

NYAYMITRA 2.0 — Software Bill of Materials (SBOM)
====================================================

Generated from installed-package metadata via `scripts/license_audit.py --all`.

## Runtime packages

| # | Package | Version | Licence | Scope |
|---|---------|---------|---------|-------|
| 1 | email-validator | 2.2.0 | Unlicense | runtime |
| 2 | fastapi | 0.162.2 | MIT | runtime |
| 3 | httpx | 0.28.1 | BSD-3-Clause | runtime |
| 4 | pydantic | 2.10.3 | MIT | runtime |
| 5 | pypdf | 7.0.0 | BSD-3-Clause | runtime |
| 6 | python-multipart | 0.0.33 | Apache-2.0 | runtime |
| 7 | starlette | 1.10.0 | BSD-3-Clause | runtime (transitive) |
| 8 | uvicorn | 0.54.0 | BSD-3-Clause | runtime |

## Development packages (transitive, 27 packages)

pytest, pytest-cov and their transitive dependencies (iniconfig, pluggy, packaging,
tomli, etc.). All permissive.

## Totals

* Packages: 60
* Permissive: 60
* Copyleft: 0
* Unknown: 0
* Runtime: 8 (incl. transitive starlette)
* Development: 52

## How to regenerate

```bash
python scripts/license_audit.py --all --json > sbom-$(date +%Y%m%d).json
```

## Limitation

This SBOM reflects the Python environment at generation time. Re-run before each
release to capture dependency changes.
