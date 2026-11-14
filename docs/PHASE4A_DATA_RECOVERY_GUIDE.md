# Phase 4A — recovering the existing Constitution data from Termux

Date: 2026-11-14 · Branch: `arena/08f8f3c5-nyaymitra-2-0`

**Status: nothing has been recovered yet.** The English and Gujarati datasets exist only on the owner's
tablet. This guide and the tool were tested on synthetic folders. No file from the tablet has been seen,
no checksum is known, and nothing has been imported (`apply` was not run).

Created & Developed by Bambhaniya Divyesh Nonghanbhai

## 1. What exists in the repository (audited)

| Item | Path | State |
|---|---|---|
| Inventory + package tool | `scripts/inventory_local_data.py` | Existed; had defects (below); now version 2.1, tested |
| Importer | `scripts/import_constitution_data.py` | `inspect`, `check`, `apply`, `rollback`, `runs` — reviewed, see §6 |
| Phase 4 report | `docs/PHASE4_DATA_IMPORT_REPORT.md` | formats, rejection reasons, report format |
| Templates | `data/templates/articles_template.csv`, `articles_template.json`, `mapping_template.json` | optional; your files need not match them |
| Source manifest | `data/sources/manifest.json` | two official PDFs listed, **neither acquired** (`acquired: false`, no checksum) |
| Source register | `data/seed/sources.json`, `docs/DATA_SOURCE_REGISTER.md` | one Constitution source key today: `india-code-constitution` |

Defects found in the old inventory script and fixed:

1. No readable (Markdown) report — added `--markdown`.
2. It measured gaps against a fixed 1–395 range — removed; gaps are now between the lowest and highest number found, with a note that gaps are not proof of missing data.
3. In shared storage it listed any file with `index`, `mapping`, `article`, `gujarati`… in its name, which could expose unrelated personal files — shared storage is now searched by strong names only (§3).
4. It could crash on an unreadable folder; it did not look at `.log` files; SQLite was opened read-only but not immutable — all fixed.
5. No transfer package, no manifest, no proof that originals were unchanged — added.

### Importer input formats and syntax (unchanged from Phase 4)

`.csv` `.tsv` `.json` `.jsonl` `.ndjson`, a folder of `.txt`/`.md` (one article per file), whole-document `.txt`/`.md` with page markers, `.pdf` with text layer, diglot `.pdf` with `--diglot`.

```
python scripts/import_constitution_data.py inspect FILE [--language gu|en] [--mapping map.json]
python scripts/import_constitution_data.py check   FILE --language gu --source-key KEY --extraction-method ocr|text_layer|manual_entry
                                                   [--mapping map.json] [--accept-inferred] [--normalize-ocr]
                                                   [--expected numbers.txt] [--report r.json] [--markdown r.md]
python scripts/import_constitution_data.py apply   (same options)      ← NOT to be run in this phase
python scripts/import_constitution_data.py rollback RUN_ID
```

## 2. What the tool does and does not do

* Opens your files **for reading only**. It never modifies, renames, moves or deletes them, never runs OCR, never uploads anything.
* Writes only the output files you name (`--out`, `--markdown`, `--package`).
* After the run it re-checks size and modification time of every file it read (plus SHA-256 when packaging) and prints `originals unchanged: yes`.
* Needs only Python — no packages. (PDF page counts appear only if `pypdf` happens to be installed; not required.)

## 3. Privacy rules built into the tool

| Place | What is listed |
|---|---|
| Project folders you name (e.g. `~/NYAYMITRA-AI`) | data files whose path contains: constitution, samvidhan, bandharan, gujarati, article, ocr, master, index, mapping, nyaymitra, બંધારણ, સંવિધાન |
| `--search` folders (shared storage, Download) | **only** files whose path contains: constitution, samvidhan, sanvidhan, bandharan, nyaymitra, બંધારણ, સંવિધાન |
| Everything else | not opened, not hashed, not named — only counted |

Never entered: `Android`, `DCIM`, `Pictures`, `Movies`, `Music`, `node_modules`, `.git`, virtual environments.
Never copied into a package (listed with path, size and checksum, each with its reason — on screen as `NOT COPIED:` lines and in `INVENTORY.md`):

* files that look like credentials (key files, or text containing something shaped like an API key or password);
* files whose name suggests data about people: complaint, grievance, citizen, user(s), feedback, chat, conversation, session, contact, aadhaar, personal, private — their content is not inspected either;
* SQLite databases (they may hold complaints) unless `--include-databases`;
* `.zip` / `.gz` archives (contents cannot be checked) unless `--include-archives`;
* files larger than `--max-file-mb`.

The inventory holds file facts (path, size, checksum, column names, row counts, share of Gujarati/Latin letters, duplicate and gap counts). It does not contain article text.

**Limits:** these rules work on file names and on the first 2 MB of text files. A personal file with an innocent name inside the project folder, or a secret further than 2 MB into a file, would not be caught. Read `INVENTORY.md` and the `tar -tzf` listing before sending anything.

## 4. Termux procedure — copy and paste

Replace `~/NYAYMITRA-AI` with your real project folder if it differs (step B finds it).

**A. Prepare (one time)**

```bash
pkg install -y python curl nano
termux-setup-storage
curl -fsSL -o ~/inventory_local_data.py https://raw.githubusercontent.com/dhundhwana-arch/Nyaymitra-2.0/arena/08f8f3c5-nyaymitra-2-0/scripts/inventory_local_data.py
python ~/inventory_local_data.py --help | head -5
grep -m1 TOOL_VERSION ~/inventory_local_data.py        # must show 2.1
```

If the download fails: `pkg install -y git && git clone -b arena/08f8f3c5-nyaymitra-2-0 https://github.com/dhundhwana-arch/Nyaymitra-2.0.git ~/Nyaymitra-2.0 && cp ~/Nyaymitra-2.0/scripts/inventory_local_data.py ~/`

**B. Find the project folder and the known file (read-only)**

```bash
find ~ -maxdepth 3 -type d \( -iname '*nyaymitra*' -o -iname '*constitution*' -o -iname '*samvidhan*' \) 2>/dev/null
find ~ ~/storage/shared/ -name 'constitution_gujarati_master_index.csv' -not -path '*/Android/*' 2>/dev/null
```

**C. Inventory only (nothing copied yet)**

```bash
python ~/inventory_local_data.py ~/NYAYMITRA-AI --search ~/storage/shared \
  --out ~/nyaymitra-inventory.json --markdown ~/nyaymitra-inventory.md
cat ~/nyaymitra-inventory.md
```

Read the report. If an expected file is missing, add its folder as another project folder, e.g.
`python ~/inventory_local_data.py ~/NYAYMITRA-AI ~/other-folder --search ~/storage/shared …`.
Use `--all` only for a folder that holds nothing but project data.

**D. Build the transfer package (copies; originals stay where they are)**

```bash
python ~/inventory_local_data.py ~/NYAYMITRA-AI --search ~/storage/shared \
  --package ~/nyaymitra-transfer --max-file-mb 25
cat ~/nyaymitra-transfer/INVENTORY.md
```

Files above 25 MB (probably the PDFs) are listed with their checksum but not copied. To include the Gujarati PDF, use a new folder name and a higher limit: `--package ~/nyaymitra-transfer-2 --max-file-mb 200`.

**E. Fill in the source facts**

```bash
nano ~/nyaymitra-transfer/SOURCE_INFO.md
```

Then rebuild the archive so it contains your answers (the data files are not touched):

```bash
cd ~ && tar -czf nyaymitra-transfer.tar.gz nyaymitra-transfer && sha256sum nyaymitra-transfer.tar.gz | tee nyaymitra-transfer.tar.gz.sha256
```

`SOURCE_INFO.md` is your notes file: it is deliberately not in the checksum manifest, so editing it does not break verification. Every data file is in the manifest. If `nyaymitra-transfer.tar.gz` already exists the tool never overwrites it; the `tar` command above replaces only that archive, which is a copy.

**F. Check the package**

```bash
python ~/inventory_local_data.py --verify-package ~/nyaymitra-transfer
tar -tzf ~/nyaymitra-transfer.tar.gz | head -50
```

**G. Put the archive where the browser can reach it**

```bash
cp ~/nyaymitra-transfer.tar.gz ~/nyaymitra-transfer.tar.gz.sha256 ~/storage/shared/Download/
```

## 5. The transfer package

```
nyaymitra-transfer/
  MANIFEST.sha256        SHA-256 of every file in the package (sha256sum -c format)
  inventory.json         machine-readable inventory: original path, relative path, size, checksum, facts, guesses
  INVENTORY.md           the same, readable
  SOURCE_INFO.md         questions only you can answer (edition, how the files were made, …)
  gujarati/<folder>/<original relative path>
  english/<folder>/<original relative path>
  unclassified/<folder>/<original relative path>
nyaymitra-transfer.tar.gz  +  nyaymitra-transfer.tar.gz.sha256
```

Original file names and relative paths are kept. Each file carries `language_guess`, `kind_guess` (source_pdf, ocr_output, article_data, index_or_mapping, log, …) and `derivation_guess` (`ocr_derived`, `pdf_text_derived`, `original_document`, `unknown`) **with the reason for the guess**. These come from names and letters only; your answers in `SOURCE_INFO.md` override them.

### Sending it

Nothing is uploaded by the tool. Choose one:

1. **Arena chat (this session):** in the browser, use the attach button and pick `Download/nyaymitra-transfer.tar.gz`; paste the line from `nyaymitra-transfer.tar.gz.sha256` into the message. The size limit for attachments here is not known to me — if the upload is refused, send without PDFs (default 25 MB limit) or use option 2.
2. **GitHub draft release** (the repository is public; a *draft* release is visible only to people with write access, but treat it as less private than a chat attachment):
   ```bash
   pkg install -y gh && gh auth login
   gh release create data-transfer-1 ~/nyaymitra-transfer.tar.gz ~/nyaymitra-transfer.tar.gz.sha256 \
     --repo dhundhwana-arch/Nyaymitra-2.0 --draft --title "Owner data transfer" --notes "Constitution data package"
   ```
3. **ChatGPT:** attach the same `.tar.gz` (or, if archives are refused, `INVENTORY.md`, `inventory.json` and the individual CSV/JSON files). Files given to ChatGPT do not reach this repository; they would still need to come here by 1 or 2 before any import.

If nothing else works, send only `~/nyaymitra-inventory.json` and `~/nyaymitra-inventory.md` first: they are small and tell me the formats.

### What happens on receipt (before any import)

`sha256sum -c` on the archive → `--verify-package` → compare with `inventory.json` → `inspect` and `check` on each file against a temporary database → report to you. `apply` only after you approve the report.

## 6. Importer review (isolated temporary databases only)

| Check | Result | Evidence |
|---|---|---|
| `inspect` / `check` on CSV, TSV, JSON, JSONL, folder, TXT | pass | `test_phase4_import.py` |
| Index file without article text (like a master index) stops with MAPPING REQUIRED, exit 4 | pass | `test_index_without_text_stops_with_mapping_report` |
| Unrecognisable headers stop instead of guessing | pass | `test_unrecognisable_headers_give_mapping_report_not_a_guess` |
| Gujarati text stored byte-for-byte (conjuncts, ZWJ/ZWNJ, digits, quotes) | pass | `test_gujarati_text_survives_byte_for_byte` |
| Gujarati letter suffix (`૨૧ક`) rejected, not converted; inventory reports the letter as written | pass | `test_check_is_a_true_dry_run_and_reports_accurately`, inventory test |
| Duplicate / gap / rejection counts exact on a known file | pass | same test |
| OCR → `OCR_REVIEW_REQUIRED` + `requires_human_verification`; "verified" in the file ignored | pass | same test; `test_file_cannot_declare_itself_verified` |
| `check` changes neither the source file nor the database, takes no backup | pass | same test (full-table digest before/after) |
| Existing summaries untouched | pass | `test_summaries_are_never_overwritten` |
| Rollback, rollback conflict | pass | `test_rollback_*`, `test_cli_dry_run_apply_rollback` (temporary DB) |

Known gaps in the importer for the files you describe (cannot be closed without seeing them):

* A **master index** (article → pages) plus **page-wise OCR text** is two files; the importer handles one article-wise file at a time. If your data is in that shape, a join step is needed and I must see the columns first.
* Gujarati letter suffixes need the letter→suffix mapping confirmed from the edition.
* The right `--source-key` for your editions does not exist yet; the editions must be registered first (from `SOURCE_INFO.md`).

## 7. Test results (2026-11-14, local)

| Suite | Result |
|---|---|
| `pytest` backend | **460 passed** (17 in `backend/tests/test_data_recovery.py`) |
| `pytest tests` | 15 passed |

Proof that originals are not modified (`test_data_recovery.py`, synthetic "tablet" with a project folder and shared storage):

* a snapshot of every file (bytes, size, modification time, permissions, and the list of names) is identical before and after inventory and after packaging;
* no `-wal`/`-shm`/journal file appears next to a SQLite database;
* read-only files in a read-only folder are inventoried without error;
* a package inside the project folder is refused; an existing package is never overwritten; the tool's own output is not re-inventoried;
* unrelated personal files in shared storage appear in neither report; secrets and the database are in neither the package folder nor the archive;
* the manifest verifies; after unpacking elsewhere it verifies; a changed file is reported as MISMATCH.

The shared development database `data/nyaymitra.db` had the same checksum before and after the full test run. All tests use temporary databases.

Not tested: a real Android/Termux device, real shared-storage permissions, your real files, very large folders (speed), attaching to a chat.

### Final readiness audit (2026-11-14, tool 2.1)

Defects found in 2.0 and fixed:

| Defect | Fix |
|---|---|
| A file such as `complaints_export.csv` inside the project folder was copied into the package | personal-data names are listed only, never inspected or copied |
| `.zip`/`.gz` files were copied although their contents cannot be checked | not copied unless `--include-archives` |
| Editing `SOURCE_INFO.md` made `--verify-package` fail | notes file is not checksummed; verification passes after editing |
| An existing `NAME.tar.gz` was silently overwritten | the tool refuses and changes nothing |
| A copy differing from its original was recorded but the tool still exited 0 | exit code 1 and an error telling you not to send the package |
| Files left out were only counted on screen | each is printed as `NOT COPIED: path (size) — reason` |
| The guide used `nano` without installing it | added to the install line |

Each fix has a test in `backend/tests/test_data_recovery.py`.

## 8. Still needed from the owner

1. Output of step C (`nyaymitra-inventory.md` / `.json`) — or the whole package from step D.
2. The package: Gujarati OCR output, `constitution_gujarati_master_index.csv`, article mapping data, OCR logs, English Parts/Articles data.
3. `SOURCE_INFO.md` answers: title page, edition/"as on" date, publisher, download address, page count of each PDF; whether the English PDF is the Hindi–English diglot; how each dataset was made (OCR / PDF text / typed); OCR program and settings; Gujarati letter suffixes seen; anything already proof-read.
4. The Gujarati PDF itself (or at least its checksum and page count, which the inventory records) if page references are to be checked.
5. The script that produced the English Parts/Articles split and the Gujarati index, if it still exists (explains the columns).
6. Approval before any `apply`.

## 9. Blocked until then

* Any statement about how many English or Gujarati articles exist, their quality, or completeness.
* Registering the editions as sources; choosing `--source-key`.
* Deciding whether a join step (index + page text) is needed.
* `check` reports on real data; import; display of official text in the app.
