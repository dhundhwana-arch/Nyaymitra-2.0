"""Phase 3C command line.

    python -m ingestion.pipeline acquire     # download PDFs, update manifest
    python -m ingestion.pipeline run         # extract + reports + DRY-RUN import (default)
    python -m ingestion.pipeline run --apply # import, only if every gate passes
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ingest
from .acquire import acquire_all, verify_checksums
from .extract import extract_articles
from .pdfio import ExtractionError, page_texts
from .quality import compare_numbering, coverage_report, text_quality
from .sources import (DB_PATH, EXCEPTIONS_PATH, MANIFEST_PATH, REPORT_DIR, ROOT, load_manifest,
                      now_utc, write_json)


def _load_exceptions(path: Path) -> dict:
    """Human-signed exceptions, e.g. repealed article numbers that legitimately have no heading."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("reviewed_by") or not data.get("reviewed_at"):
        raise ValueError(f"{path.name} must carry reviewed_by and reviewed_at (human sign-off)")
    return data


def build_gates(checks: dict, quality: dict, coverage: dict, errors: dict, exceptions: dict) -> dict:
    gates = {}
    for sid in checks:
        lang = sid.rsplit("-", 1)[-1]
        ok_missing = set(exceptions.get("accepted_missing_base_numbers", {}).get(lang, []))
        ok_dupes = set(exceptions.get("accepted_duplicate_labels", {}).get(lang, []))
        gates[f"{sid}:checksum"] = {"passed": checks[sid]["ok"], "detail": checks[sid]["reason"]}
        if sid in errors:
            gates[f"{sid}:extraction"] = {"passed": False, "detail": errors[sid]}
            continue
        if sid not in quality:
            gates[f"{sid}:extraction"] = {"passed": False, "detail": "not extracted (source not acquired)"}
            continue
        q, c = quality[sid], coverage[sid]
        gates[f"{sid}:text_quality"] = {"passed": q["passed"], "detail": q["failures"]}
        missing = [n for n in c["missing_base_numbers"] if n not in ok_missing]
        gates[f"{sid}:coverage"] = {"passed": not missing and c["candidates_extracted"] > 0,
                                    "detail": {"unexplained_missing_base_numbers": missing}}
        dupes = [d["label_raw"] for d in c["duplicates"] if d["label_raw"] not in ok_dupes]
        gates[f"{sid}:duplicates"] = {"passed": not dupes, "detail": {"unexplained_duplicates": dupes}}
        gates[f"{sid}:order"] = {"passed": not c["out_of_order"], "detail": c["out_of_order"]}
    return gates


def run(apply: bool = False, root: Path = ROOT, manifest_path: Path = MANIFEST_PATH,
        report_dir: Path = REPORT_DIR, db_path: Path = DB_PATH,
        exceptions_path: Path = EXCEPTIONS_PATH) -> dict:
    manifest = load_manifest(manifest_path)
    checks = verify_checksums(manifest, root)
    quality, coverage, extracted, errors, batches = {}, {}, {}, {}, {}
    for sid, entry in manifest.get("sources", {}).items():
        if not checks[sid]["ok"]:
            continue  # never extract from a file whose provenance is not established
        lang = entry["language"]
        try:
            pages = page_texts(root / entry["local_path"])
        except ExtractionError as exc:
            errors[sid] = str(exc)
            continue
        res = extract_articles(pages, lang)
        quality[sid] = text_quality(pages, lang)
        coverage[sid] = coverage_report(res["articles"], lang)
        coverage[sid]["rejected_heading_candidates"] = len(res["rejected"])
        extracted[sid] = res
        batches[sid] = (entry["sha256"], res["articles"])
        write_json(report_dir / f"articles-{lang}.json", {
            "source_id": sid, "source_sha256": entry["sha256"],
            "verification_status": "requires_human_verification",
            "articles": [a.to_dict() for a in res["articles"]], "rejected_candidates": res["rejected"]})

    by_lang = {manifest["sources"][s]["language"]: extracted[s]["articles"] for s in extracted}
    comparison = (compare_numbering(by_lang["en"], by_lang["gu"]) if {"en", "gu"} <= set(by_lang)
                  else {"status": "not_run", "reason": "both languages must be extracted first"})
    gates = build_gates(checks, quality, coverage, errors, _load_exceptions(exceptions_path))
    all_passed = bool(gates) and all(g["passed"] for g in gates.values())

    dry = ingest.plan(db_path, batches)
    if apply and all_passed:
        import_result = ingest.apply(db_path, batches, gates)
    elif apply:
        import_result = {"mode": "apply", "status": "REFUSED", "rows_written": 0,
                         "reason": "quality gates failed", "dry_run": dry}
    else:
        import_result = dry

    report = {"generated_at": now_utc(), "checksums": checks, "extraction_errors": errors,
              "text_quality": quality, "coverage": coverage, "numbering_comparison": comparison,
              "gates": gates, "all_gates_passed": all_passed, "import": import_result}
    write_json(report_dir / "phase3c-report.json", report)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("acquire")
    r = sub.add_parser("run")
    r.add_argument("--apply", action="store_true", help="write to the database (only if all gates pass)")
    args = ap.parse_args(argv)
    if args.cmd == "acquire":
        m = acquire_all()
        for sid, e in m["sources"].items():
            print(f"{sid}: {e['last_attempt_status']}" + (f" - {e['last_attempt_error']}" if e["last_attempt_error"] else
                  f" sha256={e['sha256']} pages={e['page_count']}"))
        return 0 if all(e["last_attempt_status"] == "ok" for e in m["sources"].values()) else 1
    rep = run(apply=args.apply)
    for name, g in rep["gates"].items():
        print(("PASS " if g["passed"] else "FAIL ") + name + ("" if g["passed"] else f"  {g['detail']}"))
    print("import:", json.dumps(rep["import"], ensure_ascii=False))
    return 0 if rep["all_gates_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
