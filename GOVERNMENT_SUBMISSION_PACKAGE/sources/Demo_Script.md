# NYAYMITRA 2.0 — Demo Script

Three citizen journeys using synthetic demonstration data only. No real personal data is used.

## Prerequisites

```bash
git clone https://github.com/dhundhwana-arch/Nyaymitra-2.0.git
cd Nyaymitra-2.0
git checkout arena/812d6894-nyaymitra-2-0
python3 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements-dev.txt
python scripts/init_db.py
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
Open http://localhost:8000/

---

## Journey 1 — A citizen asks a basic legal information question

1. Open the home page. A red banner notes official article text is not loaded (expected — prototype).
2. Switch language to Gujarati (optional), then back to English.
3. In the assistant, type: "What is equality before the law?" (or Gujarati: "કાયદા સમક્ષ સમાનતા શું છે?")
4. Observe: the answer cites Article 14, is labelled "requires human verification," and ends with a disclaimer that this is information, not legal advice, and to verify with free legal aid (15100).
5. Observe: sources are listed with verification status; no outcome is predicted; no guilt is assigned.

Synthetic data: question "What is equality before the law?" — no personal identifiers.

Expected: Article 14 cited, disclaimer present, "requires human verification" label, no invented citations.

---

## Journey 2 — The system retrieves relevant information and displays sources

1. Type an unrelated query: "zzz qqq" (nonsense).
2. Observe: the system returns "no verified information" and "no matching article or guide is loaded"; it does not guess or invent a citation.
3. Type a department-relevant query: "cyber fraud money stolen from bank account."
4. Observe: the system does not cite an unrelated article (e.g., it does not cite Article 21A); it suggests the NALSA/DLSA/tele-law channels and, where matched, the relevant department and triage steps.
5. Observe the citations panel: each source shows article label, title, and verification status.

Synthetic data: queries "zzz qqq" and "cyber fraud money stolen from bank account" — no personal identifiers.

Expected: no hallucinated citations; honest "not found" for nonsense; relevant department guidance for fraud.

---

## Journey 3 — The system guides the citizen toward the relevant department or human assistance

1. Navigate to the complaint form.
2. Enter synthetic details only (e.g., category "cyber crime", title "Unauthorized bank withdrawal", description without any real names/phones/emails).
3. Observe: a preview appears before anything is saved; the submit button is disabled until the consent checkbox is ticked.
4. Tick consent and submit. Observe: a reference (NYM-XXXXXX) and an access token are shown once; copy them.
5. Use the saved-complaint lookup with the reference and token to retrieve the metadata. A wrong token shows the same generic error (no oracle).
6. Observe the department/glossary pages to find the relevant authority and free legal aid (15100 / nearest DLSA).

Synthetic data: placeholder complaint text only — no real personal information.

Expected: preview before submit; consent-gated submit; reference + token issued once; token-gated lookup; no oracle on wrong token; department/helpline guidance.

---

## Notes for the demonstrator

- All inputs are synthetic; do not enter real personal data during the demo.
- The offline provider is active by default; no external model is called.
- Legal content is not yet verified by a human reviewer; present answers as information, not advice.
- The red "official text not loaded" banner is expected until official Constitution documents are ingested (blocker B-1).

---

Repository: https://github.com/dhundhwana-arch/Nyaymitra-2.0 | commit `068cf9f`
