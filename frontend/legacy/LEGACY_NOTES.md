# Legacy frontend (superseded, kept for reference)

These files are the original NYAYMITRA 2.0 prototype. They are **no longer served** by the
application — the working UI lives in `/web` and is served by the FastAPI backend at `/`.

| File | Origin | Why it is here rather than deleted |
|---|---|---|
| `index.html` | `frontend/index.html` (`main` @ `53df9ea`) | 127 KB hand-built design prototype. Its palette, Gujarati copy and layout informed `/web`. Kept as a design reference and as evidence for the audit. |
| `app_core.js` | `frontend/app_core.js` | Never loaded by `index.html` (dead code). Contained a third copy of the triage knowledge and a 6-article gu/hi/en library. Kept because the Gujarati article paraphrases were reused (with provenance) in `data/seed/constitution_seed.json`. |
| `build_library_js.py` | `frontend/build_library_js.py` | Generator with hard-coded Termux paths; replaced by `scripts/ingest_constitution.py`. Kept as evidence of the (broken) data pipeline. |

## Removed files and their evidence

| Removed | Reason | Where the content lives now |
|---|---|---|
| `frontend/index_v2.html` | Byte-identical duplicate of `index.html` (md5 `95b0c137047691502d26a0d363219198`) | `frontend/legacy/index.html` |
| `frontend/library_fix.js` (4.8 MB) | Generated, never referenced by any HTML, contained the 2 125 junk records | `data/legacy/constitution_articles_legacy_2026-11-07.jsonl.gz` |
| `frontend/interactive_library.js` (96 KB) | Generated, never referenced, contained 470 **identical** `"Article N/A"` placeholder records with no legal content | Nothing of value to preserve; sample kept in `docs/REPOSITORY_AUDIT.md` §6.2 |
| `backend/database.py` | Code/schema mismatch made every read fail (`no such column: title_gu`); contained a fabricated `remedy_gu` seed | Git history + `docs/REPOSITORY_AUDIT.md` §5.2 |

The prototype's known defects (broken Constitution tab markup at lines 659–675, `speakText(text)`
ReferenceError, template-literal `ReferenceError` in the generated scripts) are documented in
`docs/REPOSITORY_AUDIT.md` §5 and are **not** fixed here: this file is an archive, not a build
target.
