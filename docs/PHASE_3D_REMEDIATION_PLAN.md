# Phase 3D — Remediation Plan (proposal only)

**Nothing in this document has been executed.** Every step needs the owner's decision first.
Evidence for each point is in `docs/PHASE_3D_DATABASE_AUDIT.md`.

## Principles carried through every step

- No existing row is deleted, edited, re-labelled or promoted to verified.
- Fragments are never auto-converted into articles.
- `backend/justice_access.db` is kept byte-identical (sha256 `da5ff06f…7a53c`) until archived.
- Official text enters only through a dry-run-first, gate-checked import, as `requires_human_verification`.
- No merge to `main`, no deployment, as part of this plan.

## Decision 1 — which line of work is canonical (blocks everything else)

| Option | What it means | Assessment |
|---|---|---|
| **A. Continue on the rebuild** (`arena/812d6894-…`, or `feature/hackindia-deployment` if its 5 deployment commits are wanted) and port the useful parts of Phase 3C onto it | One schema, one pipeline, legacy data already quarantined there | **Recommended** |
| B. Continue on this branch | Keeps Phase 3C as is, but abandons 31 commits of rebuild and re-does the quarantine | Not recommended |
| C. Keep both | Two schemas and two pipelines for the same job | Not recommended |

Practical note for option A: an Arena session works on the branch it was created with, which is
cut from `main`. To have a future session start on top of the rebuild, either PR #1 is merged into
`main` by the owner (the owner's decision — not done here), or the previous session is resumed.

## Decision 2 — the legacy 2,125 rows

Proposed: **quarantine, do not repair.**

1. Treat `constitution_articles` in `justice_access.db` as evidence of a legacy import, not a corpus.
2. Under option A this is already done on the rebuild branch (`data/legacy/…jsonl.gz` +
   `legacy_import_chunks`, admin-only). Verify the archive against the audit figures
   (2,125 rows; 1,732 chunks / 393 article-labelled; 1,905 Ol Chiki-dominant) before relying on it.
3. Stop serving it: the prototype frontend file `frontend/library_fix.js` (14,928 lines) embeds
   extracted library data and should be checked for the same Santali content before any public use.
4. Never display `remedy_en`: it is importer boilerplate, not sourced text.
5. If Santali support is wanted later, re-ingest the official Santali PDF as its own language
   with its own provenance; do not salvage these fragments.

## Decision 3 — one schema for official text

Proposed under option A: keep the rebuild's `constitution_articles` (migrations 001/003),
`legal_sources` and `ingest_runs`; **retire `official_constitution_articles`** from Phase 3C
rather than carry two designs. Port these Phase 3C behaviours, which the earlier pipeline lacks:

| Port | Why |
|---|---|
| SHA-256 recorded per source file and stored with each run | earlier pipeline has no checksum |
| Text-layer quality checks for Gujarati (legacy-font, PUA, missing text layer) | guards against non-Unicode Gujarati PDFs |
| Cross-language numbering report with no automatic suffix mapping | required by Phase 3C task 11 |
| Human-signed exceptions file for omitted/repealed numbers | avoids silently accepting gaps |
| Raw, un-normalised text preservation tests | Gujarati Unicode safety |

Open design point to settle before porting: the rebuild stores English and Gujarati in one row.
Pairing a Gujarati article to an English one is itself a judgement for suffixed articles, so the
import should stage each language separately and only pair after human confirmation.

Also to fix on whichever branch survives: the Phase 3C dry-run key `existing_seed_rows_untouched`
should be renamed (it counts legacy rows, not seed summaries), and `docs/PHASE_3C_STATUS.md`
should say the Santali finding pre-dates Phase 3C.

## Decision 4 — getting the real PDFs in

The sandbox cannot reach `legislative.gov.in` or `indiacode.nic.in`. Options:

| Option | Trade-off |
|---|---|
| Owner runs acquisition + dry-run locally and commits only the manifest and reports | PDFs stay out of Git; parser tuning needs a round-trip per change |
| Owner attaches the PDFs to the session / a private location the sandbox can read | fastest for tuning; needs a "register local file" step that records checksum, who supplied it and when |
| Commit the PDFs (or Git LFS) | simplest transport; large binaries in a public repo; Government of India works need attribution — owner to confirm reuse terms |

Whichever is chosen, add a `register` command: accept a manually supplied file, compute SHA-256
and page count, record `supplied_by`, `supplied_at` and the claimed URL, and mark it
`provenance: manually_supplied` (distinct from a verified download). Today a manual file is refused.

Before any import, a person confirms from the title pages: edition date, "amendments up to"
statement, and that the Gujarati file has a real Unicode text layer.

## Proposed order (after decisions)

1. Owner confirms Decisions 1–4.
2. Verify the legacy archive against this audit; no changes to the data.
3. Port Phase 3C checks onto the canonical branch; single schema; tests green on that branch.
4. Register or download the two PDFs; record checksums.
5. Inspect extraction quality on the real files; tune the parser; dry-run only.
6. Human review of coverage, duplicates, missing numbers and cross-language differences.
7. Gate-checked import, all rows `requires_human_verification`.
8. Only then consider Phase 4.

## Not proposed

Deleting the legacy rows; rewriting `main`; merging or closing PR #1; marking anything verified;
deriving Gujarati text by translating English.
