# Legal verification checklist

**Read this before treating anything NYAYMITRA shows as law.**

Current state of the corpus:

| Item | Count | Status |
|---|---:|---|
| Articles with authoritative text (`text_status = verified_source_text`) | **0** | none loaded |
| Articles with an owner-written explanation only | 9 | `requires_human_verification` |
| Departments / helplines entered | 11 | `requires_human_verification` |
| Triage guides (steps, documents) | 5 | `requires_human_verification` |
| Glossary terms (plain-language only) | 18 | “not the statutory definition” |
| Quarantined legacy rows (never served) | 2,125 | not law, not usable |

The application states this on every answer, and `/meta` reports `verified_text: 0`.

---

## 1. What the project owner must supply

1. **Official Constitution documents** (text or text-layer PDF), placed in `data/raw/`:
   * English — India Code / Legislative Department edition
   * Gujarati — the official Gujarati edition, if Gujarati article text is to be shown
2. **A named reviewer** (advocate, law academic, or legal-aid officer) willing to be recorded as
   `checked_by` for specific articles, departments and guides.
3. **Dated confirmation** for each helpline, portal URL, e-mail and address, with the page it was
   checked against.
4. **A licence/permission note** for any document that is not a Government of India publication,
   recorded in `legal_sources.licence_note`.

Nothing in this repository can substitute for 1–4. No article text, helpline or portal route has
been invented, and none may be filled in from memory.

## 2. How to load the Constitution

```bash
# dry run first — prints duplicates, missing numbers, short bodies, OCR confidence
python scripts/ingest_constitution.py \
    --file data/raw/constitution-of-india-en.pdf \
    --source-key india-code-constitution --language en

# then, with a verified backup
python scripts/ingest_constitution.py \
    --file data/raw/constitution-of-india-en.pdf \
    --source-key india-code-constitution --language en --apply --backup
```

The importer:

* is dry-run by default and refuses `--apply` (exit 3) when the quality gate fails: no articles
  found, low text quality, duplicate numbers, missing titles, suspicious article boundaries, or
  many very short bodies. `--force` overrides it and records the run as
  `completed_with_warnings`;
* never replaces existing non-empty text, and never touches a row a human has verified, even with
  `--replace-existing`. Identical text on a re-run is counted as `unchanged`, not rewritten;
* records the page range, Part and Chapter for every article, so a reviewer can open the same
  pages of the official PDF (`source_pages`, `source_locator`);
* writes only `text_en` / `text_gu` and sets `text_status = verified_source_text`;
* leaves `verification_status = requires_human_verification` — extraction is **not** review;
* reports duplicate article numbers (only the first is kept) instead of overwriting;
* reports missing numbers inside the observed range and **never** synthesises them;
* refuses to overwrite a row a human has already verified;
* reports `low_text_quality` and stops short if the PDF has no usable text layer (scan → OCR is
  the owner's step, not a guess by the tool).

After importing, run `python scripts/constitution_coverage.py` (or `--format both --out
reports/coverage`) for the authoritative count of what is loaded, what has source text, what a
human has signed off, and which article numbers are missing. Missing numbers are **reported, never
filled in**.

## 3. Review protocol (per item)

For each article, the reviewer must:

- [ ] Compare `text_en` character-for-character against the official document (including
      sub-clauses, provisos and amendments).
- [ ] Confirm the article number and part/chapter.
- [ ] Read `citizen_explanation_en` and `citizen_explanation_gu` and confirm the explanation does
      not add rights, deadlines, amounts or outcomes that the article does not contain.
- [ ] Confirm the Gujarati explanation is a faithful rendering (native speaker check).
- [ ] Record their name and the review date in the admin console (or `PATCH
      /admin/articles/{id}/verification`).
- [ ] Re-check on the scheduled cycle (recommended: every 6 months, and after any amendment).

The API refuses `verification_status = verified` unless `checked_by`, `last_checked_at` and
authoritative text are all present (409/400 otherwise; regression-tested).

For departments, the reviewer must confirm each of: name (en/gu), purpose, jurisdiction, helpline,
portal URL, portal label, and set `verified_on` to the date checked.

For triage guides, confirm the steps and required documents against the current procedure, and
that the named department is correct for that category.

## 4. Prohibited in this project

* Inventing or “restoring” missing article text, even partially.
* Presenting a paraphrase as the text of an article.
* Filling a helpline or URL from memory or from a non-official aggregator.
* Marking anything verified without a named human reviewer and a date.
* Using generated text as a court filing, legal notice or advice to a named person.
* Presenting NYAYMITRA output as a legal opinion, a verdict, or a guarantee of any outcome.

## 5. Sign-off record (fill in when used)

| Item | Reviewer | Date checked | Source document / URL | Status |
|---|---|---|---|---|
| Article 14 — text (en) | | | | pending |
| Article 14 — explanation (gu) | | | | pending |
| Article 21 — text (en) | | | | pending |
| Article 32 — explanation (en/gu) | | | | pending |
| Departments (11 entries) | | | | pending |
| Triage guides (5) | | | | pending |
| Glossary (18 terms) | | | | pending |
| Gujarati copy of the UI | | | | pending |

> This table is intentionally empty. Nothing in this repository has been legally verified, and no
> entry may be marked complete without the reviewer's own name and date.

## 6. If a citizen reports an error

1. `/admin` → recent queries / feedback; reproduce the question.
2. If an article, explanation or department is wrong, set `verification_status` to `unverified` or
   `outdated` with a note — the UI immediately stops showing it as verified.
3. If the answer was unsafe (advice, verdict, guarantee), capture the `request_id` and treat it as a
   security-relevant defect; the guard patterns are in `backend/app/ai/guard.py`.
4. Record the correction in the audit trail (the verification endpoint writes it automatically).
