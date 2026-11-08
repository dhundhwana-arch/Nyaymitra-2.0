# Handover — where the work is, how to prove it, what is not done

This document exists so that someone who has never seen this repository can, in about ten
minutes, answer four questions: *is this the code that was tested?*, *where is the backup?*,
*does it work without me?*, and *what is still missing?*

---

## 1. Where the work is

| Item | Value |
|---|---|
| Working tree | `/home/user/Nyaymitra-2.0` |
| Repository | `dhundhwana-arch/Nyaymitra-2.0` (public) |
| Branch | `arena/812d6894-nyaymitra-2-0` |
| Remote tracking | `origin/arena/812d6894-nyaymitra-2-0` — local and remote are identical at the last handover commit |
| Pull request | #1 — open, **draft**, mergeable; **not merged** (owner approval required) |
| Databases | `data/nyaymitra.db` (runtime), test databases live in pytest temp dirs |
| Uploaded documents | `storage/documents/` (runtime; not in git) |

The branch is the feature branch. This session is pinned to it, so no additional branch was
created — creating one would have moved the work away from the pull request that reviews it.

## 2. Preservation and integrity

Two artefacts, deliberately separate:

| Artefact | Path | Contains | Why separate |
|---|---|---|---|
| Code archive | `backups/nyaymitra-2.0-code-<commit>.tar.gz` | the tracked files of the handover commit (no caches, no database, no uploads) | a code handover must not carry personal data |
| Manifest | `backups/nyaymitra-2.0-code-<commit>.manifest.json` | SHA-256 + size for every tracked file | lets anyone prove the copy is intact |
| Database backup | `backups/nyaymitra-<timestamp>.db` | the runtime database via `scripts/backup_db.py` (VACUUM INTO + integrity check) | contains synthetic test complaints only; access-controlled separately |

The manifest covers **120 tracked files**. Symlinks and gitlinks are excluded by
design — they have no content of their own — and the checker prints how many it skipped, so the
exclusion is visible rather than silent.

Verify a copy with three commands:

```bash
# 1. does the tree match the manifest?
python scripts/verify_changeset.py --verify backups/nyaymitra-2.0-code-<commit>.manifest.json

# 2. can the archive be extracted, and does every extracted file match?
python scripts/verify_changeset.py --verify-archive backups/nyaymitra-2.0-code-<commit>.tar.gz \
                                   --manifest backups/nyaymitra-2.0-code-<commit>.manifest.json

# 3. is the database backup readable?
python scripts/backup_db.py --list
```

Exit codes: `0` identical, `1` mismatch (missing / extra / modified file), `2` the check itself
could not run. A mismatch is never reported as a pass.

## 3. Test evidence

```bash
python -m pytest                                   # 186 passed, 1 warning in ~23 s
python -m pytest --cov=backend/app                 # 2306 statements, 189 missed, 92 %
node --check web/app.js web/admin.js scripts/smoke_web.mjs
```

| Suite | Tests |
|---|---:|
| backend (12 original modules) | 168 |
| `test_handover_tooling.py` (changeset checker + provider probe) | 18 |
| **Total** | **186** |

The frontend smoke test needs jsdom, which is not vendored:
`npm install --no-save jsdom && node scripts/smoke_web.mjs http://127.0.0.1:8000`. It is a jsdom
simulation, not a browser — see `KNOWN_LIMITATIONS.md` #24.

CI (`.github/workflows/ci.yml`): pytest 3.11, pytest 3.12, dependency audit (`pip-audit`), and
frontend checks. The run IDs for this commit are recorded in `TESTING_REPORT.md` §2.

## 4. Real-model status: **not verified here**

`scripts/verify_ai_provider.py` is a live probe: it sends a real question through
`ai.rag.answer_question`, so retrieval, triage-guide injection, answer validation and citations
are all exercised together, and it refuses to invent a result.

In this environment it exits **3 (unavailable)**. Two attempts, both honest:

```
$ python scripts/verify_ai_provider.py
  provider preference : auto · base URL : (unset) · API key : (unset)
  → "A live model was not verifiable in this environment." (exit 3)

$ NYAYMITRA_AI_PROVIDER=openai_compatible \
  NYAYMITRA_AI_BASE_URL=http://127.0.0.1:11434/v1 \
  NYAYMITRA_AI_MODEL=llama3.2:3b NYAYMITRA_AI_API_KEY=ollama \
  python scripts/verify_ai_provider.py --json
  {"status": "unavailable", "reason": "could not reach http://127.0.0.1:11434/v1/models (ConnectError)"}  (exit 3)
```

No Ollama binary, no local model server, and this sandbox's outbound network only reaches the
package indices, so model weights cannot be downloaded here. The exact requirement — install
Ollama, pull `llama3.2:3b`, export four variables, re-run the probe — is printed by the script
itself and is repeated in `DEPLOYMENT_GUIDE.md` §4.1.

The provider wiring is covered by **stub-server tests** (`test_handover_tooling.py`): a local
HTTP server speaking the chat-completions protocol proves the client parses a real response,
that the prompt contains the retrieved sources, that citations survive validation, and that a
hallucinated article is rejected and falls back to the offline text. **That is wiring, not a
model.** No claim of "real model verified" appears anywhere in these documents.

## 5. Repository separation (NYAYMITRA vs DIVU-AGI)

* `DIVU-AGI` is a separate public repository. It is **not** referenced by this codebase, and no
  file, database, credential or deployment configuration is shared with it.
* Nothing from this session touched another repository. `grep -rin "divu"` over the whole tree
  returns nothing.
* The only cross-project trace is historical and inert: the archived prototype UI at
  `frontend/legacy/app_core.js` still contains a "Ask JARVIS" button, and `REPOSITORY_AUDIT.md`
  records what was salvaged from `JARVIS-AI-Justice-Access` (nothing — it was a strict subset).
  `frontend/legacy/` is not mounted by the application and is never served.
* Databases and credentials are local: `data/*.db` and `storage/` are git-ignored; tokens come
  from `NYAYMITRA_*` environment variables and are never committed.

## 6. Defects found and fixed during this handover pass

| Finding | Impact | Fix |
|---|---|---|
| `guard.ARTICLE_REF` used `re.IGNORECASE` on the whole pattern, so `[A-Z]?` matched a lowercase letter: **"Article 14 is relevant" parsed as article "14I"** | A *correct* answer from a real model would have been discarded as an uncited reference and silently replaced by the offline text. Found only because the stub model produced a natural sentence | Only the word "article" is case-insensitive now; regression tests added |
| Gujarati digits (`કલમ ૧૪`) never matched ASCII article labels | A correct Gujarati answer would have been rejected | Native digits are normalised to ASCII before comparison; the allowed set is unchanged |
| A **symlink `node_modules` was committed**, pointing at `/tmp/webcheck/node_modules` (an absolute path from this sandbox) | Dangling for everyone else; leaked a local path into the repository | Removed from tracking, `node_modules` added to `.gitignore`; jsdom is installed with `npm install --no-save jsdom` |

## 7. What the owner still has to do

1. **Approve the merge.** Nothing is merged; PR #1 stays a draft until you say otherwise.
2. **Run the probe against a real model** (`scripts/verify_ai_provider.py`) once Ollama or a
   hosted endpoint is available, and keep the output — that is the only thing that turns "wiring
   tested" into "model tested".
3. **Supply the official Constitution documents** (blocker B-1) and then ingest them; the
   coverage report will keep saying *0 with authoritative text* until that happens.
4. **Appoint a reviewer** (blocker B-2) and **test on a real phone** (blocker B-3).

The full list, with the evidence that would close each item, is in `REMAINING_BLOCKERS.md`.
