# NYAYMITRA 2.0 — Multilingual Implementation Report

**Date:** 2026-11-12 (UTC) · **Branch:** `arena/08f8f3c5-nyaymitra-2-0` · Nothing was deployed.

Created & Developed by Bambhaniya Divyesh Nonghanbhai

## 1. What exists now, in one paragraph

The app can be used in 23 languages (the 22 languages of the Eighth Schedule and English) through
one language selector. The **interface** is complete in Gujarati and English, has the essential
navigation labels in 17 further languages, and a few labels in 4. The **legal content** is exactly
what it was: 9 owner-written explanations in Gujarati and English, **0 articles of official text in
any language**, nothing human-verified. For every other language the app shows the English content
and says so. No Constitution text was machine-translated. The live matrix is in
[`LANGUAGE_AVAILABILITY_MATRIX.md`](LANGUAGE_AVAILABILITY_MATRIX.md) and at `GET /api/v1/languages`.

## 2. Four states that are never mixed

| State | Where it lives | Who can set it |
|---|---|---|
| Interface translation | `web/locales/<code>.json` → `_meta.translation_status` (`PROJECT_AUTHORED` / `MACHINE_TRANSLATED`) | developer |
| Kind of legal text | `article_texts.content_status`: `OFFICIAL_SOURCE`, `OCR_REVIEW_REQUIRED`, `MACHINE_TRANSLATED`, `HUMAN_REVIEWED`, `VERIFIED`; the API reports `UNAVAILABLE` when there is no row | importer sets only the first three, from the declared extraction method |
| Human verification | `verification_status` (`requires_human_verification` on every import) | a person; the importer never writes `verified` |
| Owner explanation | `constitution_articles.citizen_explanation_*` | owner; never stored in `article_texts` |

## 3. Architecture

```
backend/app/languages.py      registry (code, BCP 47 tag, ISO 639-3, native/English name, ISO 15924 script,
                              direction), script detection, digit + NFC normalisation, availability
web/locales/index.json        static copy of the registry for the selector (scripts/build_locales.py)
web/locales/<code>.json       one interface catalogue per language; missing keys fall back to English
web/app.js                    t(key) → selected catalogue → English; sets <html lang dir data-script>
backend/app/middleware.py     LanguageFallbackMiddleware: ?language=<any registry code> is served in the
                              content language and labelled with Content-Language / X-Language-Fallback
article_texts (migration 005) one row per (article, language) with its own provenance
```

* **Codes.** ISO 639-1 where one exists, otherwise ISO 639-3 (`brx`, `doi`, `kok`, `mai`, `mni`, `sat`).
  Scripts: `ks-Arab` and `sd-Arab` (right-to-left), `mni-Beng`, `sat-Olck`, `pa-Guru`, Devanagari for
  `brx`, `doi`, `kok`, `mai`. The alternatives (Kashmiri/Sindhi in Devanagari, Manipuri in Meetei Mayek,
  Konkani in Roman) are noted in the registry and not implemented.
* **Right to left.** Urdu, Sindhi and Kashmiri set `dir="rtl"`; the stylesheet uses logical properties;
  stored content, links and phone numbers keep their own direction.
* **Fonts.** No web fonts are downloaded (no CDN, offline-safe). Each script names the Noto family and
  the fonts shipped by Android, Windows, macOS and Linux. Ol Chiki and Nastaliq depend on the device
  having a suitable font.
* **Unicode.** Text is stored exactly as supplied. Comparison and search use NFC with digits of every
  script unified to ASCII; ZWJ/ZWNJ are kept. The search tokeniser previously cut Indic words at the
  first vowel sign outside Gujarati and Devanagari; it now covers all target scripts.
* **Language detection** is by script. Scripts used by one target language give a confident answer.
  Devanagari (8 languages), Bengali script (3) and Perso-Arabic (3) cannot be separated from a short
  question without a statistical model: the selected language decides, otherwise the result is the most
  widely used language of that script with `confidence: "low"` and the alternatives listed. Assamese,
  Sindhi and Kashmiri are recognised by letters unique to them.

## 4. Database change (migration 005)

`backend/migrations/005_article_texts.sql` adds one table, `article_texts`, and two indexes. Nothing
existing is altered. Columns: `article_id`, `language`, `title`, `body`, `part_title`, `chapter_title`,
`source_id`, `source_locator`, `source_pages`, `edition`, `extraction_method`, `content_status`,
`verification_status`, `content_sha256`, `created_at`, `updated_at`; unique on (`article_id`, `language`).

* Applied automatically at start-up, like the earlier migrations. Reversal: `005_article_texts.down.sql`
  (drops the table; texts in languages other than Gujarati/English would be lost — back up first).
* `text_en` / `text_gu` stay (the search index and existing endpoints read them). The importer writes
  both places for those two languages. Article number, Part and Chapter stay on the article row, so
  numbering and structure are shared by all languages.
* The one source/page slot on the article row now follows English; Gujarati fills it only when no
  English text exists. Each language's own pages and source are in `article_texts`.

## 5. Import pipeline changes

`scripts/ingest_constitution.py --language <code> --extraction-method text_layer|ocr|manual_entry|structured_import [--edition …]`

| Earlier gap (see the import plan) | Now |
|---|---|
| Gujarati-digit headings created separate articles | digits of any script are unified for the number; the body is untouched |
| `243ZA`, `239AA` not recognised | two-letter suffixes parsed |
| A second language overwrote the first one's page reference and Part title | fixed; per-language provenance |
| OCR text labelled as source text | `--extraction-method ocr` → `OCR_REVIEW_REQUIRED`; the method must be declared to apply a text file |
| Only English `PART`/`CHAPTER` headings | headings in the scripts of the target languages; digit Part numbers mapped to Roman |
| Part headings between articles were never picked up (every article got the first Part) and the heading was left inside the previous article | fixed |
| No checksum | SHA-256 of the file printed and of each text stored |
| — | new gate: `broken_indic_text_layer` (detached vowel signs) and `script_mismatch` (for example Santali or Hindi text offered as Gujarati/English) |
| — | a source not registered as `official` cannot be stored as `OFFICIAL_SOURCE` |

Still open: no CSV / structured-JSON importer (the column layout of the owner's files is unknown);
contents pages must be excluded by the operator; a lettered Part written in another script is not
mapped to `IVA`/`IXA`.

## 6. API changes (41 operations; 4 new)

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/languages` | Registry + availability for all 23 languages, computed from the database |
| `GET /api/v1/languages/{code}` | One language |
| `POST /api/v1/languages/detect` | `{text, hint?}` → script, language, confidence, candidates |
| `GET /api/v1/constitution/articles/{no}/text?lang=<code>` | The article in exactly that language, or `content_status: "UNAVAILABLE"`, plus the owner explanation labelled as not official |

Changed, backwards compatible:

* Any `GET …?language=<registry code>` is accepted. For a language without content the response is in
  English with headers `Content-Language: en`, `X-Requested-Language`, `X-Language-Fallback: true`.
  Unknown codes are still rejected (422).
* `POST /api/v1/ai/explain` accepts every registry code in `language`. New response fields:
  `requested_language`, `detected_language`, `language_fallback`, `language_notice`.
* `GET /api/v1/library`: `content_language` accepts any registry code; items carry `content_language`,
  `language_fallback`, `content_status`; the response lists `matched_terms`.
* `GET /api/v1/constitution/articles/{no}`: new `language_texts` (status of each language, no bodies).
* `GET /api/v1/meta`: `capabilities.interface_languages`.

## 7. Frontend changes

* One labelled `<select>` with 23 languages (native name and English name) replaces the two buttons.
  The choice is remembered on the device.
* All interface text moved out of `app.js` into `web/locales/`; nothing is fetched from a third party.
* A notice appears whenever the interface is machine-translated, only partly translated, or the
  content is shown in another language.
* Article page: per-language status badges; a clear message when the article has no text in the
  selected language. Legal Library: matched words highlighted, status label on each result.
* Assistant: fallback notice with the detected script. About page: the availability table.
* Service worker cache name bumped (`nyaymitra-v3`) so installed copies pick up the new shell.
* Still hard-coded in Gujarati/English inside `app.js`: badge names, category names and warning
  texts. In other languages they appear in English.

## 8. Assistant

* A question may be written in any of the 23 languages. Article references are recognised with digits
  of any script and with the usual word for "article" in each script (for example `अनुच्छेद २१`,
  `অনুচ্ছেদ ১৪`, `آرٹیکل ۳۲`, `உறுப்பு 21A`).
* Retrieval is unchanged: answers are built only from stored records; an article that is not stored is
  reported as not available; citations carry the article label, verification status and source.
* Answers are written in Gujarati or English only. In any other language the answer is in English,
  marked `language_fallback`, and nothing is machine-translated.
* **Limit:** a free-text question in another language (no article number) is matched only through
  the guides' keyword lists (which include some Hindi words) and words it shares with the stored
  Gujarati/English content. Anything else gets the "no information" answer rather than a guess.
  The offline rule-based mode still works with no API key; no paid dependency was added.

## 9. Tests (all run locally on 2026-11-12)

| Suite | Result |
|---|---|
| `python -m pytest` (backend) | **389 passed** (262 before; 127 new in `backend/tests/test_multilingual.py`) |
| `python -m pytest tests` (source-quality tool) | 15 passed |
| `scripts/e2e_activation.mjs`, one site | **43 / 43** |
| `scripts/e2e_activation.mjs`, frontend and backend on different origins | **43 / 43**, 0 CORS-blocked calls |
| `scripts/smoke_web.mjs` | all citizen journeys passed (admin console skipped: no token set) |

What the new tests cover: registry contents and codes; digits of 13 scripts; detection for all 23
languages; tokenising every script; every catalogue's metadata and script; text in each of the 21
other languages stored and read back unchanged and re-imported idempotently; OCR never labelled
official or verified; second language not overwriting the first; suffixes and Indic headings; broken
text layer and wrong script blocked; unknown language / method / non-official source refused; fallback
headers; unavailable text not translated; assistant in every language; migration 005 reversible.

**These are simulated-browser tests (jsdom).** They check the DOM (`lang`, `dir`, labels, notices), not
pixels. Not tested: glyph rendering and font availability on real devices, visual right-to-left
layout, the service worker, speech input/output in the new languages, the deployed websites.

Two existing tests were changed, both deliberately: the language-toggle test now checks the selector,
and the two CLI apply tests pass the new mandatory `--extraction-method`. No test was removed.

The end-to-end run needs a higher read limit than the default 120 requests/minute because it loads
every language within a minute: start the server with `NYAYMITRA_RATE_LIMIT_READ=5000` for that run only.

## 10. Security and performance findings

* Language codes are validated against the registry on every endpoint; search highlighting escapes
  HTML before inserting `<mark>`; no inline styles or third-party assets were added (CSP unchanged).
* Catalogue files are static and exempt from the rate limiter (as `/assets/` already was); API limits
  are unchanged. No secret, token or personal data was added to the repository.
* Local timings (9 articles): `/languages` 5 ms, 17.7 kB; library search 8 ms; a catalogue ~1 kB.
* **Will not scale as is:** the library loads every item on each request. Fine for today's 43 items;
  with ~470 articles in several languages it needs SQL-side filtering or a cache.
* Full-text search (FTS) indexes only the Gujarati/English columns; other languages are matched by
  substring.
* Responses are not compressed by the app; rely on the hosting proxy or add compression.
* There is no admin action yet to mark an `article_texts` row reviewed or verified.

## 11. Deployment notes (not deployed)

* Backend: no new settings. Migration 005 runs at start-up — **take a database backup first**.
* The Docker image already copies `web/`, so catalogues are included. A separately hosted frontend
  must publish `web/locales/` with the rest of `web/`.
* After editing the registry or a catalogue: `python scripts/build_locales.py` and commit `index.json`.
* Verify after deployment: `node scripts/e2e_activation.mjs https://<frontend> [https://<backend>]`.

## 12. Known limitations and remaining work

1. No official Constitution text in any language (owner's files not supplied; see the import plan).
2. Interface text in 21 languages is machine-generated and unreviewed; Bodo, Manipuri, Santali and
   Dogri are partial; Kashmiri, Sindhi and Konkani are low-confidence. Native-speaker review is needed.
3. Only ~12 of 157 interface strings exist outside Gujarati and English: forms, buttons and messages
   are in English there.
4. Departments, guides and glossary exist in Gujarati and English only.
5. Real-device rendering is untested.
6. Items listed in sections 5, 7, 8 and 10.
