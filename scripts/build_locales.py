#!/usr/bin/env python3
"""Write web/locales/index.json — the language registry the frontend selector uses.

The registry lives in backend/app/languages.py. The static copy lets the selector work
when the frontend is hosted on its own (no API call needed to list languages) and offline.
Run after editing the registry or any web/locales/<code>.json:

    python scripts/build_locales.py            # rewrite index.json
    python scripts/build_locales.py --check    # exit 1 if index.json is stale (used by tests/CI)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import languages  # noqa: E402

LOCALES = ROOT / "web" / "locales"


def build() -> str:
    languages._load_locales.cache_clear()
    items = []
    for lang in languages.REGISTRY:
        ui = languages.ui_status(lang.code, LOCALES)
        items.append({
            "code": lang.code, "tag": lang.tag, "english_name": lang.english_name,
            "native_name": lang.native_name, "script": lang.script, "direction": lang.direction,
            "script_note": lang.script_note,
            "content_language": languages.content_language(lang.code),
            "ui": {"catalogue": ui["catalogue"], "keys": ui["keys"],
                   "essential_complete": ui["catalogue"] and not ui["missing_essential"],
                   "translation_status": ui["translation_status"], "review": ui["review"],
                   "confidence": ui["confidence"]},
        })
    data = {"default_language": "gu", "fallback_language": languages.DEFAULT_CONTENT_LANGUAGE,
            "essential_ui_keys": list(languages.ESSENTIAL_UI_KEYS), "languages": items}
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def main() -> int:
    target = LOCALES / "index.json"
    text = build()
    if "--check" in sys.argv:
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            print("web/locales/index.json is stale: run python scripts/build_locales.py", file=sys.stderr)
            return 1
        print("index.json is up to date")
        return 0
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)} ({len(languages.REGISTRY)} languages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
