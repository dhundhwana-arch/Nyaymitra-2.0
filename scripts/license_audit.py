#!/usr/bin/env python3
"""Third-party licence inventory for the runtime and development dependencies.

Reads the metadata of the *installed* distributions (no network), so the report describes what
is actually running rather than what a requirements file hopes is running:

    python scripts/license_audit.py                 # human table
    python scripts/license_audit.py --json          # machine readable
    python scripts/license_audit.py --fail-on-copyleft   # CI gate for a permissive-only release

Classification is deliberately conservative: an unknown or missing licence is reported as
**unknown**, never assumed permissive. This feeds `docs/THIRD_PARTY_LICENSE_AUDIT.md` and the
licence section of `docs/IP_INVENTORY.md`.
"""
from __future__ import annotations

import argparse
import json
import sys
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = REPO_ROOT / "backend" / "requirements.txt"

# Licences that permit a proprietary or government-licensed distribution with attribution.
PERMISSIVE_MARKERS = (
    "mit", "bsd", "apache", "isc", "psf", "python software foundation", "mozilla public",
    "unlicense", "cc0", "zlib",
)
# Licences that would require releasing modifications or linking obligations.
COPYLEFT_MARKERS = ("gpl", "agpl", "lgpl", "sspl", "eupl")


def classify(license_text: str | None, classifiers: list[str] | None = None) -> str:
    """Return 'permissive' | 'copyleft' | 'unknown' from whatever metadata is available."""
    haystack = " ".join(filter(None, [license_text or "", *list(classifiers or [])])).lower()
    if not haystack.strip():
        return "unknown"
    # Copyleft is checked first: "LGPL" contains "gpl", and MPL is permissive-ish but flagged
    # separately by the caller through the raw string.
    if any(marker in haystack for marker in COPYLEFT_MARKERS):
        return "copyleft"
    if any(marker in haystack for marker in PERMISSIVE_MARKERS):
        return "permissive"
    return "unknown"


def declared_requirements(path: Path = REQUIREMENTS) -> list[str]:
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = line.split("==")[0].split(">=")[0].split("[")[0].strip()
        if name:
            # Distribution metadata uses underscores, requirements use hyphens.
            names.append(name.lower().replace("_", "-"))
    return names


def _license_of(dist: metadata.Distribution) -> tuple[str | None, list[str]]:
    """Read the licence from whichever metadata convention the package uses.

    Modern packages declare ``License-Expression`` (PEP 639) and no ``License`` field at all;
    reading only ``License`` reported MIT and BSD packages as "unknown", which is exactly the
    kind of false alarm that makes a licence audit useless.
    """
    meta = dist.metadata
    license_text = meta.get("License-Expression") or meta.get("License")
    classifiers = meta.get_all("Classifier") or []
    licence_classifiers = [c for c in classifiers if c.startswith("License ::")]
    if (not license_text or license_text.strip().lower() in {"", "unknown"}) and licence_classifiers:
        license_text = "; ".join(c.split("::")[-1].strip() for c in licence_classifiers)
    return license_text, licence_classifiers


def inventory(include_all: bool = False) -> dict:
    """Inventory declared requirements, or (``include_all``) every installed distribution.

    The declared list is what the project asks for; the transitive closure is what it actually
    ships, and a licence audit that ignores starlette, pydantic-core or anyio would be
    misleading. ``--all`` therefore reports the whole environment and marks dev-only tools.
    """
    wanted = set(declared_requirements())
    if include_all:
        wanted = set()
    packages = []
    for dist in metadata.distributions():
        name = (dist.metadata.get("Name") or "").strip()
        if not name:
            continue
        normalized = name.lower().replace("_", "-")
        if wanted and normalized not in wanted:
            continue
        license_text, classifiers = _license_of(dist)
        packages.append({
            "name": name,
            "version": dist.version,
            "license": license_text or "unknown",
            "license_classifiers": classifiers,
            "classification": classify(license_text, classifiers),
            "homepage": dist.metadata.get("Home-page") or dist.metadata.get("Project-URL"),
        })
    packages.sort(key=lambda item: item["name"].lower())
    dev_tools = {"pytest", "pytest-cov", "pip-audit", "coverage", "iniconfig", "pluggy",
                 "packaging", "tomli", "cachetools", "rich", "cyclonedx-python-lib",
                 "pip-api", "pip-requirements-parser", "requests", "urllib3", "charset-normalizer",
                 "markdown-it-py", "pygments", "mdurl", "boolean.py", "license-expression",
                 "sortedcontainers", "toml", "pyparsing", "msgpack", "platformdirs",
                 "filelock", "virtualenv", "distlib", "pip"}
    for package in packages:
        package["scope"] = "dev" if package["name"].lower().replace("_", "-") in dev_tools else "runtime"
    counts = {"permissive": 0, "copyleft": 0, "unknown": 0}
    for package in packages:
        counts[package["classification"]] += 1
    return {
        "packages": packages,
        "counts": counts,
        "declared_in_requirements": sorted(wanted),
        "missing_from_environment": sorted(
            wanted - {p["name"].lower().replace("_", "-") for p in packages}
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NYAYMITRA third-party licence inventory")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--all", action="store_true", help="include transitive and dev packages")
    parser.add_argument("--fail-on-copyleft", action="store_true")
    parser.add_argument("--fail-on-unknown", action="store_true")
    args = parser.parse_args(argv)

    report = inventory(include_all=args.all)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{'package':<24}{'version':<12}{'class':<12}licence")
        for package in report["packages"]:
            print(f"{package['name']:<24}{package['version']:<12}"
                  f"{package['classification']:<12}{package['license'][:60]}")
        counts = report["counts"]
        print(f"\n{len(report['packages'])} packages: "
              f"{counts['permissive']} permissive, 0-or-more copyleft ({counts['copyleft']}), "
              f"{counts['unknown']} unknown")
        if report["missing_from_environment"]:
            print("declared but not installed: " + ", ".join(report["missing_from_environment"]))

    failed = False
    if args.fail_on_copyleft and report["counts"]["copyleft"]:
        print("error: copyleft dependency present", file=sys.stderr)
        failed = True
    if args.fail_on_unknown and report["counts"]["unknown"]:
        print("error: dependency with an unknown licence", file=sys.stderr)
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
