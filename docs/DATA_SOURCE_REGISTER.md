# Data-Source Register — Constitution of India and translations

**Compiled:** 2026-11-12 (UTC). **Nothing in this register has been downloaded into the project.**
The build environment has no network route to `legislative.gov.in` or `indiacode.nic.in`; the
facts below were read through a web search/reader tool that returns extracted text (at most the
first 30 pages of a PDF) and cannot save files. Therefore every entry has **no checksum, no file
size and no local copy**, and nothing was imported from any of them.

Legend for *Evidence*: **READ** = the document's own first pages were read on the date above;
**LISTED** = named on a page of the publisher's website as returned by web search;
**THIRD-PARTY** = stated by a non-government website only.

## A. Documents whose own pages were read

| Field | English / Hindi diglot edition | Gujarati edition |
|---|---|---|
| URL | https://www.legislative.gov.in/static/uploads/2025/08/b9a933fb88c0a5afba254256bc55a3f0.pdf | https://www.legislative.gov.in/static/uploads/2025/07/316140f5938919bbbce4c22f1bf3d5ff.pdf |
| Publisher | Government of India, Ministry of Law and Justice, Legislative Department | Same — Legislative Department, Official Languages Wing |
| Title (as printed) | भारत का संविधान / THE CONSTITUTION OF INDIA | ભારતનું સંવિધાન / THE CONSTITUTION OF INDIA |
| Language(s) | **Hindi and English in one file ("diglot form")** | Gujarati (English preface) |
| Edition | "sixth pocket size edition … in the diglot form" | "fifth edition of the Constitution of India in the Gujarati language" |
| "As on" date printed | 10th September, 2026 | February, 2026 |
| Amendments incorporated | up to the Constitution (One Hundred and Sixth Amendment) Act, 2023 | up to the Constitution (One Hundred and Sixth Amendment) Act, 2023 |
| Prepared by | Legislative Department (preface signed by the Secretary) | National Translation Mission, CIIL Mysuru, on behalf of the Official Languages Wing |
| Format | PDF | PDF |
| Page count | not established (reader stops at 30 pages) | not established |
| Download date | not downloaded | not downloaded |
| SHA-256 | none | none |
| Kind | Official text (English); official Hindi text | Translation published by the Government of India |
| Licence / reuse | Not stated in the pages read. Not verified. | Not stated in the pages read. Not verified. |
| Evidence | READ (title page, preface, contents to about Article 74) | READ (title page and prefaces, via search extract) |

Two findings that change the import plan:

1. **The "English PDF" is a Hindi–English diglot.** The importer must be given the English text
   only (or the two languages separated first); a whole-file import with `--language en` would
   mix Hindi into the English column. The script-mismatch check added in this milestone reports
   the proportion of each script and blocks such an import. The same file is also the source
   for Hindi.
2. **The Gujarati text extracted by the reader has detached vowel signs** (for example the title
   comes out as `ભારતન ું સુંવિધાન` instead of `ભારતનું સંવિધાન`). Whether this is the PDF's own text
   layer (legacy font encoding) or an artefact of the reader cannot be decided without the file.
   If it is the text layer, text-layer extraction is unusable and the owner's OCR output is the
   right input — as OCR, to be reviewed. The importer now detects this pattern
   (`broken_indic_text_layer`) and refuses to treat such text as official.

## B. Translations named on the Legislative Department's website (files not located)

Pages: `https://lddashboard.legislative.gov.in/constitution-of-india` and
`https://lddashboard.legislative.gov.in/constitution-of-india-in-regional-languages`
(the same content is served at `www.legislative.gov.in/constitution-of-india-in-regional-languages/`,
which needs JavaScript and could not be read directly). Individual file URLs were **not** captured.

| Language | Named on the official pages | Evidence | Remark |
|---|---|---|---|
| English | yes — "Constitution of India - in English" | LISTED + READ | see A |
| Hindi | yes — "Constitution of India - in Hindi" | LISTED + READ (diglot) | see A |
| Gujarati | yes (regional languages list, per third-party copy of the list) | READ | see A |
| Urdu | yes — "Constitution of India - in Urdu" | LISTED | |
| Marathi | yes — "Diglot Edition (English-Marathi)" | LISTED | |
| Tamil | yes — five files | LISTED | split into parts |
| Malayalam | yes | LISTED | |
| Assamese, Bodo, Dogri, Kannada, Kashmiri, Konkani, Maithili, Manipuri, Nepali, Odia, Punjabi, Sanskrit, Santhali, Sindhi, Telugu | yes — rows of the regional-languages table | LISTED | whether each row is the full Constitution or only part of it was not checked |
| Bengali | implied (the table numbers 1–20 with gaps where Bengali, Gujarati, Malayalam, Marathi, Tamil fall alphabetically) | THIRD-PARTY | a third-party page refers to a "2022 Bengali version" |

A Department of Justice / Legislative Department report
(`https://www.doj.gov.in/static/uploads/2025/09/d4ca9ea7a627c0ef71136bfb27114afd.pdf`) states that,
besides Hindi, authoritative texts of the Constitution have been brought out in 15 regional
languages: Assamese, Bengali, Gujarati, Kannada, Malayalam, Marathi, Oriya, Punjabi, Sanskrit,
Tamil, Telugu, Urdu, Sindhi, Nepali and Konkani. The date of that statement was not established.

A third-party website states that for Maithili and Bodo only the Preamble is available. Not verified.

**No language is recorded as "no official translation exists"**: that could not be established
either way. For Bodo, Dogri, Kashmiri, Maithili, Manipuri and Santali the status of a full
official translation is **unknown**.

## C. What is already in the repository

| Item | Kind | Status |
|---|---|---|
| `data/seed/sources.json` (15 entries) | Register of portals and publishers used by the seed content | unchanged |
| `data/seed/constitution_seed.json` | 9 owner-written explanations, Gujarati + English | not official text |
| `data/legacy/…jsonl.gz` | 2,125 fragments of a Santali–English edition | quarantined; never served or imported |
| `data/sources/manifest.json` | Earlier download attempts (all failed) | unchanged |

## D. What the owner needs to do to turn a row above into data

1. Download the file in a normal browser. Record the date. Keep the original file unchanged.
2. `python scripts/inventory_local_data.py <folder> --out inventory.json` (records SHA-256, pages, script mix).
3. Add the source to `data/seed/sources.json` with URL, publisher, edition, date and checksum.
4. Dry-run the import; read the report; apply only when it is clean. See
   `docs/LOCAL_DATA_RECOVERY_AND_IMPORT_PLAN.md`.
