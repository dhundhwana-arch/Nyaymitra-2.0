#!/usr/bin/env python3
"""Audit the interface catalogues in web/locales. Reports; never translates or edits.

    python scripts/audit_locales.py                # table
    python scripts/audit_locales.py --json out.json --markdown docs/LOCALE_QUALITY_AUDIT.md
    python scripts/audit_locales.py --strict       # exit 1 on structural errors (CI)

Checks per language: keys missing (the app shows English for these), keys not in English,
values identical to English (probably untranslated), values in the wrong script, broken
Unicode (replacement characters, unpaired marks, non-NFC, control or bidi-override characters),
placeholder mismatches ({name}), empty values, right-to-left metadata, review label.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app import languages  # noqa: E402

LOCALES = ROOT / "web" / "locales"
PLACEHOLDER = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")
BAD_CONTROL = set("\u202a\u202b\u202d\u202e\u2066\u2067\u2068\ufeff\ufffd")


def unicode_problems(value: str) -> list[str]:
    out = []
    if any(ch in BAD_CONTROL for ch in value):
        out.append("replacement_or_bidi_override_character")
    if any(unicodedata.category(ch) in ("Cc", "Cs", "Co", "Cn") and ch not in "\n\t" for ch in value):
        out.append("control_or_unassigned_character")
    if unicodedata.normalize("NFC", value) != value:
        out.append("not_nfc")
    if re.search(r"(?:^|\s)[\u0300-\u036f]", value) or (value and unicodedata.category(value[0]) in ("Mn", "Mc")):
        out.append("combining_mark_without_base")
    for match in re.finditer(r"\s(\S)", value):
        if unicodedata.category(match.group(1)) in ("Mn", "Mc"):
            out.append("vowel_sign_after_space")
            break
    return out


def audit() -> dict:
    english = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))["strings"]
    report = {"english_keys": len(english), "languages": []}
    index = {e["code"]: e for e in json.loads((LOCALES / "index.json").read_text(encoding="utf-8"))["languages"]}
    for lang in languages.REGISTRY:
        path = LOCALES / f"{lang.code}.json"
        row = {"code": lang.code, "name": lang.english_name, "script": lang.script, "direction": lang.direction,
               "errors": [], "file": path.exists()}
        report["languages"].append(row)
        if not path.exists():
            row["errors"].append("catalogue_file_missing")
            continue
        raw = path.read_bytes()
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            row["errors"].append(f"unreadable: {exc}")
            continue
        meta, strings = data.get("_meta", {}), data.get("strings", {})
        missing = [k for k in english if k not in strings]
        extra = [k for k in strings if k not in english]
        same, wrong_script, broken, placeholders, empty = [], [], {}, [], []
        for key, value in strings.items():
            if not isinstance(value, str) or not value.strip():
                empty.append(key)
                continue
            problems = unicode_problems(value)
            if problems:
                broken[key] = problems
            if key in english:
                if sorted(PLACEHOLDER.findall(value)) != sorted(PLACEHOLDER.findall(english[key])):
                    placeholders.append(key)
                if lang.code != "en" and value == english[key] and re.search(r"[A-Za-z]{4}", value):
                    same.append(key)
            if lang.code != "en":
                counts = languages.script_counts(value)
                letters = sum(counts.values())
                if letters >= 4 and counts.get(lang.script, 0) / letters < 0.4 and value != english.get(key):
                    wrong_script.append(key)
        essential_missing = [k for k in languages.ESSENTIAL_UI_KEYS if k not in strings]
        row.update({
            "translated_keys": len(strings) - len(extra), "missing_keys": len(missing),
            "coverage_percent": round(100 * (len(english) - len(missing)) / len(english), 1),
            "falls_back_to_english_for": len(missing), "essential_missing": essential_missing,
            "unknown_keys": extra, "identical_to_english": same, "mostly_other_script": wrong_script,
            "broken_unicode": broken, "placeholder_mismatch": placeholders, "empty_values": empty,
            "meta_dir": index.get(lang.code, {}).get("direction"), "meta_status": meta.get("translation_status"),
            "meta_reviewed": meta.get("review") not in (None, "", "none"), "confidence": meta.get("confidence"),
        })
        if lang.code not in index:
            row["errors"].append("not_listed_in_index_json")
        elif index[lang.code].get("direction") != lang.direction:
            row["errors"].append("direction_mismatch_between_index_and_registry")
        if (lang.script == "Arab") != (lang.direction == "rtl"):
            row["errors"].append("script_direction_inconsistent")
        if meta.get("translation_status") not in ("PROJECT_AUTHORED", "MACHINE_TRANSLATED", "HUMAN_REVIEWED"):
            row["errors"].append("translation_status_missing")
        if broken:
            row["errors"].append("broken_unicode")
        if placeholders:
            row["errors"].append("placeholder_mismatch")
        if empty:
            row["errors"].append("empty_values")
        if extra:
            row["errors"].append("unknown_keys")
        if meta.get("translation_status") == "MACHINE_TRANSLATED" and row["meta_reviewed"]:
            row["errors"].append("machine_translated_marked_reviewed")
    report["totals"] = {"languages": len(report["languages"]),
                        "with_errors": sum(1 for r in report["languages"] if r["errors"]),
                        "complete": sum(1 for r in report["languages"] if r.get("missing_keys") == 0),
                        "unreviewed": sum(1 for r in report["languages"] if r.get("meta_status") == "MACHINE_TRANSLATED")}
    return report


def markdown(report: dict) -> str:
    lines = ["# Locale quality audit", "",
             "Generated by `python scripts/audit_locales.py --markdown docs/LOCALE_QUALITY_AUDIT.md`. Do not edit by hand.",
             "", f"English catalogue: **{report['english_keys']}** strings. A key that a language lacks is shown in "
             "English by the app (`t()` falls back per key); nothing is invented.", "",
             "| Code | Language | Dir | Status in file | Reviewed | Strings | Coverage | Shown in English | Same as English | Other script | Unicode | Errors |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in report["languages"]:
        if "missing_keys" not in r:
            lines.append(f"| {r['code']} | {r['name']} | {r['direction']} | — | — | — | — | — | — | — | — | {'; '.join(r['errors'])} |")
            continue
        lines.append(f"| {r['code']} | {r['name']} | {r['meta_dir']} | {r['meta_status']} | "
                     f"{'yes' if r['meta_reviewed'] else 'no'} | {r['translated_keys']} | {r['coverage_percent']}% | "
                     f"{r['missing_keys']} | {len(r['identical_to_english'])} | {len(r['mostly_other_script'])} | "
                     f"{len(r['broken_unicode'])} | {'; '.join(r['errors']) or 'none'} |")
    t = report["totals"]
    lines += ["", f"Languages: {t['languages']} · complete: {t['complete']} · machine-translated and unreviewed: "
              f"{t['unreviewed']} · with structural errors: {t['with_errors']}", "",
              "What this audit cannot tell: whether a translation is *correct*. Only a native speaker can."]
    detail = [r for r in report["languages"] if r.get("identical_to_english") or r.get("mostly_other_script") or r.get("broken_unicode")]
    if detail:
        lines += ["", "## Details"]
        for r in detail:
            lines.append(f"\n### {r['code']} — {r['name']}")
            for label, key in (("Identical to English", "identical_to_english"), ("Mostly another script", "mostly_other_script")):
                if r[key]:
                    lines.append(f"* {label}: " + ", ".join(f"`{k}`" for k in r[key]))
            for k, v in r["broken_unicode"].items():
                lines.append(f"* Unicode: `{k}` — {', '.join(v)}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json"); parser.add_argument("--markdown"); parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = audit()
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    text = markdown(report)
    if args.markdown:
        Path(args.markdown).write_text(text, encoding="utf-8")
    print(text)
    return 1 if args.strict and report["totals"]["with_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
