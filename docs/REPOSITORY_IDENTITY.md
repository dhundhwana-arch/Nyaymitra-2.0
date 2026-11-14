# Repository identity — corrected description (owner action required)

**Created & Developed by Bambhaniya Divyesh Nonghanbhai**

## Current state (verified 2026-11-12)

The GitHub repository description is:

```
Next-Gen Legal AI Justice Access System (Gemini Production Engine)
```

**This description is false in two distinct ways:**

1. **"Gemini Production Engine"** — there is no Gemini engine. The code implements exactly two AI
   providers, `offline` (deterministic, rule-based, source-grounded, used by default) and
   `openai_compatible` (a generic client). Gemini is reachable only as *one optional* value of
   `NYAYMITRA_AI_BASE_URL` — it is a configuration choice, not the system's engine, and no live
   provider credentials exist in this repository.
2. **"Production"** — nothing is deployed. Verified: 0 GitHub deployments, 0 environments, no
   Pages site, 0 releases, 0 tags. The Pages deploy job is manual-only and has never run.

The description also omits what the project actually is (a Gujarati-first, multilingual
access-to-justice and legal-navigation platform) and overstates what the AI does (it is
source-grounded and offline by default; it refuses rather than inventing, and never presents
unverified text as law).

## Corrected description (approved text — apply verbatim)

```
NYAYMITRA 2.0 | Bharat Multilingual Legal Access System
```

This is the exact string approved by the project owner for this field.

## How to apply

The repository metadata API is **not writable from this session** (`gh repo edit` returns
`403 Resource not accessible by integration`). This requires the owner's account.

```bash
gh repo edit dhundhwana-arch/Nyaymitra-2.0 \
  --description "NYAYMITRA 2.0 | Bharat Multilingual Legal Access System"
```

Or in the browser: **Settings → General → Description → Save**.

## Notes on the approved text

* It is *strictly more accurate* than what it replaces: no claim of "production", no claim of a
  specific AI vendor, and no claim of legal authority.
* "Bharat Multilingual" matches the delivered implementation — 23 Indian-language interface
  catalogues with per-language capability status reported separately (`UI_READY`, `UI_PARTIAL`,
  `SAMPLE_CONTENT_AVAILABLE`, `OFFICIAL_TEXT_AVAILABLE`, `HUMAN_VERIFIED`, `ASSISTANT_SUPPORTED`).
* It deliberately does not claim verified legal content. There are **0 authoritative texts and
  0 human-verified statements**; the 9 provisions are owner-authored explanations. Keep it that
  way until B-1 and B-2 close.

## Suggested supporting metadata (optional, same owner action)

| Field | Suggested value |
|---|---|
| Homepage | leave empty until a deployment exists |
| Topics | `access-to-justice`, `legal-tech`, `gujarati`, `multilingual`, `fastapi`, `india`, `constitutional-law` |
| Licence | already MIT (`LICENSE`), no change needed |
