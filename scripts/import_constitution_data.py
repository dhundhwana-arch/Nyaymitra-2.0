#!/usr/bin/env python3
"""Inspect, validate and import article-wise Constitution data (CSV, JSON, JSONL, TXT, PDF, folder).

    # 1. What is in the file? (reads the file only; no database needed)
    python scripts/import_constitution_data.py inspect FILE [--language gu]

    # 2. Dry run: full data-quality report, nothing written
    python scripts/import_constitution_data.py check FILE --language gu --source-key KEY \
        --extraction-method ocr [--mapping mapping.json] [--expected numbers.txt] \
        [--report out.json] [--markdown out.md]

    # 3. Import (takes a verified backup first, one transaction, journaled)
    python scripts/import_constitution_data.py apply FILE --language gu --source-key KEY --extraction-method ocr

    # 4. Undo one import run
    python scripts/import_constitution_data.py rollback RUN_ID
    python scripts/import_constitution_data.py runs                      # list import runs

    # Hindi–English diglot PDF: keep only the English text, by page layout
    python scripts/import_constitution_data.py check FILE.pdf --language en --diglot --source-key KEY

Exit codes: 0 ok · 2 usage/file error · 3 quality gate failed · 4 a mapping file is required.
Imported text is always stored as requires_human_verification; OCR as OCR_REVIEW_REQUIRED.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import languages  # noqa: E402
from backend.app.config import load_settings  # noqa: E402
from backend.app.db import backup_database, get_db, init_database, transaction  # noqa: E402
from backend.app.services import diglot, ingest  # noqa: E402
from backend.app.services import structured_import as si  # noqa: E402


def _dump(data, path: str | None) -> None:
    if path:
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"written: {path}")


def _load(args) -> tuple[si.Loaded, dict | None, dict | None]:
    path = Path(args.file)
    si.refuse_quarantined(path)
    mapping_file = json.loads(Path(args.mapping).read_text(encoding="utf-8")) if getattr(args, "mapping", None) else None
    diglot_report = None
    if getattr(args, "diglot", False):
        if path.suffix.lower() != ".pdf":
            raise SystemExit("--diglot needs a PDF file")
        wanted = languages.get(args.language).script
        other = args.other_script
        pages, diglot_report = diglot.extract_pdf(path, wanted, other)
        texts = [p.text for p in pages]
        diglot_report["numbering_cross_check"] = diglot.compare_numbering(texts, [p.other_text for p in pages])
        loaded = si.Loaded("document", si._document_rows(texts), list(si._DOC_COLUMNS),
                           f"pdf (layout-separated, kept {wanted})", [], len(texts), "pdf")
    else:
        loaded = si.read_records(path, records_path=(mapping_file or {}).get("records_path"))
    return loaded, mapping_file, diglot_report


def cmd_inspect(args) -> int:
    try:
        loaded, mapping_file, diglot_report = _load(args)
    except si.MappingRequired as exc:
        print(json.dumps(exc.report, indent=2, ensure_ascii=False))
        return 4
    mapping = si.infer_mapping(loaded, args.language, mapping_file, args.accept_inferred)
    out = {"file": args.file, "sha256": si.sha256_of(Path(args.file)), "mapping": mapping}
    if diglot_report:
        out["diglot"] = diglot_report
    print(json.dumps({k: v for k, v in out.items() if k != "diglot"} | (
        {"diglot": {k: v for k, v in diglot_report.items() if k != "per_page"}} if diglot_report else {}),
        indent=2, ensure_ascii=False))
    _dump(out, args.report)
    if mapping["status"] != "ok":
        print("\nMAPPING REQUIRED — copy 'mapping_template' into a file, fix it, and pass --mapping FILE.", file=sys.stderr)
        return 4
    return 0


def _prepare(args, conn):
    loaded, mapping_file, diglot_report = _load(args)
    mapping = si.infer_mapping(loaded, args.language, mapping_file, args.accept_inferred)
    if mapping["status"] != "ok":
        raise si.MappingRequired(mapping)
    method = args.extraction_method
    if method is None and loaded.format.startswith("pdf"):
        method = "text_layer"
    records, skipped = si.build_records(loaded, mapping, args.language, method, normalize=args.normalize_ocr)
    expected = None
    if args.expected:
        expected = [line.strip() for line in Path(args.expected).read_text(encoding="utf-8").splitlines() if line.strip()]
    report = si.quality_report(path=Path(args.file), loaded=loaded, mapping=mapping, records=records, skipped=skipped,
                               language=args.language, extraction_method=method, source_key=args.source_key,
                               expected=expected, existing=si.existing_texts(conn, args.language))
    if diglot_report:
        report["diglot"] = diglot_report
        for reason in diglot_report["blocking_reasons"]:
            report["blocking_reasons"].append(reason)
        report["ready_to_apply"] = not report["blocking_reasons"]
    if method is None:
        report["blocking_reasons"].append("extraction_method_not_declared")
        report["ready_to_apply"] = False
    return loaded, records, report, method


def cmd_check(args, apply: bool = False) -> int:
    settings = load_settings()
    if apply:
        init_database(settings)
    elif not settings.db_path.exists():      # a dry run never creates or changes the real database
        settings = dataclasses.replace(settings, db_path=Path(tempfile.mkdtemp()) / "check.db")
        init_database(settings)
    try:
        with get_db(settings.db_path) as conn:
            loaded, records, report, method = _prepare(args, conn)
            source = conn.execute("SELECT source_type FROM legal_sources WHERE source_key = ?", (args.source_key,)).fetchone()
            if source is None:
                report["blocking_reasons"].append("unknown_source_key")
            elif method and ingest.content_status_for(method) == "OFFICIAL_SOURCE" and source["source_type"] != "official":
                report["blocking_reasons"].append("source_not_registered_as_official")
            report["ready_to_apply"] = not report["blocking_reasons"]
    except si.MappingRequired as exc:
        print(json.dumps(exc.report, indent=2, ensure_ascii=False))
        print("\nMAPPING REQUIRED — nothing was imported.", file=sys.stderr)
        return 4
    print(si.render_markdown(report))
    _dump(report, args.report)
    if args.markdown:
        Path(args.markdown).write_text(si.render_markdown(report), encoding="utf-8")
    if not apply:
        print("DRY RUN — nothing was written.")
        return 0 if report["ready_to_apply"] else 3
    if not report["ready_to_apply"]:
        print("Refusing to import: " + ", ".join(report["blocking_reasons"]), file=sys.stderr)
        return 3
    backup = backup_database(settings.backup_dir, settings.db_path)
    print(f"Backup taken and verified: {backup}")
    with get_db(settings.db_path) as conn:
        result = si.apply(conn, records, report, language=args.language, source_key=args.source_key,
                          source_file=Path(args.file).name, extraction_method=method, edition=args.edition,
                          replace_existing=args.replace_existing, backup_path=str(backup))
    print(json.dumps(result, indent=2))
    print(f"Undo with: python scripts/import_constitution_data.py rollback {result['run_id']}")
    return 0


def cmd_rollback(args) -> int:
    settings = load_settings()
    backup = backup_database(settings.backup_dir, settings.db_path)
    print(f"Backup of the current state: {backup}")
    with get_db(settings.db_path) as conn:
        with transaction(conn):
            result = ingest.rollback_run(conn, args.run_id, force=args.force)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not result["conflicts"] else 3


def cmd_runs(_args) -> int:
    settings = load_settings()
    with get_db(settings.db_path) as conn:
        for r in conn.execute("SELECT id, started_at, source_key, source_file, articles_found, articles_written, status"
                              " FROM ingest_runs ORDER BY id"):
            print(f"{r['id']:>4}  {r['started_at']}  {r['status']:<24} written={r['articles_written']:<4} "
                  f"found={r['articles_found']:<4} {r['source_key']}  {r['source_file']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, need_language: bool):
        p.add_argument("file")
        p.add_argument("--language", required=need_language, choices=sorted(languages.CODES))
        p.add_argument("--mapping", help="JSON file: {field: column, 'constants': {field: value}, 'records_path': 'a.b'}")
        p.add_argument("--accept-inferred", action="store_true",
                       help="accept columns identified from their content when the header is not recognisable")
        p.add_argument("--diglot", action="store_true", help="two-language PDF: keep only --language, by page layout")
        p.add_argument("--other-script", default="Deva", help="ISO 15924 script of the language to leave out (default Deva)")
        p.add_argument("--report", help="write the JSON report here")

    p = sub.add_parser("inspect"); common(p, False); p.set_defaults(func=cmd_inspect)
    for name in ("check", "apply"):
        p = sub.add_parser(name); common(p, True)
        p.add_argument("--source-key", required=True)
        p.add_argument("--extraction-method", choices=list(si.IMPORT_METHODS))
        p.add_argument("--edition")
        p.add_argument("--expected", help="text file with the article numbers the publication contains, one per line")
        p.add_argument("--normalize-ocr", action="store_true",
                       help="also store a separate cleaned copy of OCR text (the original is kept unchanged)")
        p.add_argument("--replace-existing", action="store_true")
        p.add_argument("--markdown", help="write the Markdown report here")
        p.set_defaults(func=(lambda a, n=name: cmd_check(a, apply=(n == "apply"))))
    p = sub.add_parser("rollback"); p.add_argument("run_id", type=int); p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_rollback)
    p = sub.add_parser("runs"); p.set_defaults(func=cmd_runs)
    args = parser.parse_args()
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
