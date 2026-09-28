<!-- source: EXTELLA_AI_ONBOARDING.md sha256:0d93052e76bf392c1660d84b746ede7b39aa182edfc28ad89155ec88ea25a544 -->

# Extella — onboarding for an AI agent (Codex / Claude / any LLM assistant)

This document is the condensed experience of several weeks of real building on Extella
(Adoption Wizard, toolbar, the Travel Agency / Competitor Intel / Legal packs). Read it in full
BEFORE your first action. Everything here is something we've already been burned by. This
document is internal — do NOT publish it.

---

## 1. What Extella is (in 60 seconds)

Extella is a platform for corporate AI agents: cloud (api.extella.ai) + desktop app (Extella
Desktop, Electron) + a **listener** on the client's devices (a daemon that runs code locally).
Key entities:

| Entity | What it is | Where it lives |
|---|---|---|
| **Agent** | An LLM with instructions and tools (Qwen 3.7 or Claude model) | cloud |
| **Expert** | A named function in "fython" (a Python dialect), run by the cloud or on a device via the listener | cloud; runs wherever you tell it to |
| **Concept** | A unit of knowledge with an embedding (semantic search) | cloud |
| **Rule** | A behavioral rule for the agent | cloud |
| **KV** | A key-value store (`/api/kv/*`) — configs, catalogs, schedules, queues | cloud |
| **Target** | A device with a listener (UUID); an expert can be directed to a specific target | devices |
| **Profile** | The account's workspace (usually `default`) | cloud |

## 2. THE IRON CANON (violation = broken prod or client money)

1. **All client agents are the platform Qwen 3.7.** `agent_extella_default` is Claude Sonnet,
   and it's PAID: don't use it as the "default" and don't run loops on it. BYOK/gpt-4o are
   forbidden in client scenarios.
2. **An agent created via the API is born Pro-BYOK and answers `pro_key_required` on run —
   until the model is configured in the Extella interface.** The reliable path is unchanged:
   a person in the UI "copies" the base Qwen agent (2 clicks) and hands you the id. But
   "agents cannot be created via the API" is wrong: per a training participant's report of
   28 Sep 2026, once Qwen was configured in the interface the API-created agent did answer.
   We have not confirmed this with our own probe; treat it as a condition, not a ban, and
   read `pro_key_required` as "the model is not configured", not as "this is not allowed".
3. **Scoping: `global: true` is not universal advice but a case-by-case decision.** For a NEW
   application its objects live in its own scope; they are made shared only under a justified
   contract — otherwise another agent gets your names and you get theirs. Where sharing really
   is needed, `global: true` goes both on save and on call. The same expert_name in two scopes
   = a nondeterministic run (which of the two executes is a lottery). Remember: `global: true`
   is global WITHIN THE ACCOUNT and does not save you from shadow copies — every agent has its
   own world, and an agent's own copy of a key beats the shared one. Duplicate check: the
   `wz_expert_janitor` expert.
4. **Prod agents are frozen.** Process changes go only through the Builder agent, with the
   decision recorded in a session (`~/extella_wizard/sessions/`). Letters/outbound sends are
   drafts only — a person sends them.
5. **Files = the source of truth.** Agent instructions and expert code canonically live as
   files in git (`adoption_wizard/*_instructions.md`, `experts/*.py`). Order: edit the file →
   flash the platform as a whole → commit. No edits "only on the platform."
6. **Never hardcode or print secrets.** The Extella token comes from
   `~/extella_wizard/app/config.json` (or from the owner). Never into logs, chats, or commits
   (scrub before pushing). Keep in mind: the listener itself prints the token to debug logs (a
   known bug) — don't publish logs.

## 3. REST API — cheat sheet and traps

Base: `https://api.extella.ai`. Headers: `X-Auth-Token`, `X-Profile-Id: default`, `X-Agent-Id`
(for running an agent).

- Paths are **singular**: `/api/agent/run`, `/api/expert/run`, `/api/expert/save`,
  `/api/kv/get|set|search`; tasks are plural: `/api/tasks/check`.
- **Exception**: the expert list is `/api/experts_db/list`.
- **[Updated 23 Jul, live] `/api/agent/get` RETURNS `instructions` and `tools`** (verified:
  14.8K characters of instructions, 47 tools) — an agent can now be read: backup, audit, drift
  detection. Files in git remain the source of truth, but verification by reading is now
  possible.
- **[Updated 23 Jul] `agents/list`** — the team was fixing it; on our account we previously saw
  it empty — check it on your own token before using it, fallback is the id in the config.
- MCP endpoint: `https://api.extella.ai/mcp/` (**streamable-http**; the old SSE `/sse/` is
  legacy). If the MCP bridge glitches on save_expert — the fallback to REST
  `/api/expert/save` always works.

### Asynchronous tasks
**[Updated 23 Jul, live]** A long `expert/run` goes into deferred and **returns `task_id` right
in the response** (the `task_id` field + `result: "deferred, use task_id as reference"`); poll
`/api/tasks/check` (plural!). Statuses during execution are now **honest `running`** (the old
`time:<timestamp>` heartbeats are gone — verified by three polls of a live task). Keep in mind:
a client timeout < ~50s won't let you wait out a deferred response — wait at least 60–90s.

### Transient errors
**HTTP 500 / timeout ≠ failure.** The operation often actually goes through. Rule: verify by
artifacts (did the expert get created, did the KV get written) and retry idempotently. Errors
are often opaque (`empty output`, 500 with no details) — diagnose by traces, not by the error
text.

## 4. Agents via the API — survival rules

**[LIVE CHECK 23 Jul — three old workarounds removed, the tech team fixed it in prod:]**
1. **Multi-tool WORKS: 2+ tools per turn, arguments do NOT get merged together** (verified: two
   run_expert calls with different params in one turn — each got its own). The "one tool per
   turn" rule from the agent instructions can be dropped (gradually, with a test run).
2. **`recursion_limit` is accepted as a parameter** in the `agent/run` body (verified at 80; a
   full run of >50 steps hasn't been tested yet — check it on the first long task).
3. **`previous_response_id` works** (dialogue memory: a word from turn 1 was reproduced in turn
   2 by rid). Self-contained messages remain good practice for resilience to dropped
   connections, but it's no longer a mandatory workaround.
4. **`background: true` in agent/run is IGNORED** (echoes back `background: false`) — there's
   still no honest async on agent turns; for long agent work, still split it up/poll artifacts.
5. **Keyless conversations**: the platform used not to store them (`store:false`); after the
   `previous_response_id` fix, memory via `store:true` + rid works — but the transcript file
   (`sessions/<sid>_chat.json`) remains a reliable fallback.
6. **The fine-tune output ceiling is ~22K characters.** Large JSON plans get truncated. Request
   `max_output_tokens: 16000`+, split the output, validate the JSON, and re-request the tail.
7. A large inline expert result may not make it through ("Task completed but upload result
   failed") — write the result to a file (`output_path`) and return a compact summary.

### Live status of platform fixes (verified in prod 23 Jul, owner's account)
| What | Status |
|---|---|
| agent/get → instructions+tools | ✅ works |
| Multi-tool per turn (EXT-1) | ✅ works |
| previous_response_id (EXT-3) | ✅ works |
| task_id on deferred + `running` statuses (EXT-N5/#156) | ✅ works |
| get_expert → global:true (EXT-N13) | ✅ works |
| Agent sees global experts (EXT-N2) | ✅ works |
| Extella MCP wrappers (EXT-N7) | ✅ work (search_targets/search_kv live) |
| Cyrillic in export/chats (EXT-7) | ✅ fixed (needs the `by`+`id` fields in the body) |
| Device heartbeat: `available` in targets (#157, "staging") | ✅ already visible in prod via search_targets |
| recursion_limit as a parameter (EXT-2) | ✅ accepted; a run of >50 steps not verified |
| Device routing from an agent (EXT-N3) | ⏸ not proven: the listener was offline at test time — check when Running |
| Honest async agent/run (EXT-9) | ❌ background:true is ignored |

## 5. Experts — how to write them correctly

### Regular (fython) experts
```python
$extens("include.py")
include("import requests", ["extella-pip install requests"])

def my_expert(param: str = "", api_token: str = "") -> dict:
    """Description — the first line of the docstring goes into the catalog."""
    ...
    return {"ok": True}
```
- **Dependencies ONLY through `include("import X", ["extella-pip install X"])`.** A bare
  `try/except ImportError` dies on a clean client environment.
- Saving: `/api/expert/save` with `global: true`; after saving — **verify**: download the
  expert back (`get_expert`) and compare byte-for-byte, then run acceptance on a real input.
  The platform sometimes "swallows" a save silently.
- **VISIBILITY TRAP (23 Jul, live run):** a global expert is NOT visible for execution to every
  channel of the account. REST-save with `X-Agent-Id: A` → REST-run works, but the MCP client
  and the agent runtime answer "Expert not found"; save via the MCP bridge → visible to the MCP
  client, but NOT to the agent runtime; and only a save with `X-Agent-Id: <id of the calling
  agent>` makes the expert visible to THAT agent's tools (verified on `connector_execute` +
  `agent_XwZBKvd8dD70jKvW4WrZm`). Rule: save the expert an agent needs to call under that
  agent's header, and verify with acceptance via `run_agent`, not just REST.
- **The platform drops falsy parameters** (False, "", 0 may not get through). Guard dangerous
  actions with a positive flag: execute only on an explicit `apply=true`, dry-run by default.
- A global expert runs on a **random available device** if no target is specified. Anything
  that depends on the local environment (tesseract, files, brew) should either be pinned to a
  target or moved into a local service.

### nohup experts (background processes on a device)
- **Raw Python**: WITHOUT `$extens`/`include`/`def`/`return` at the top.
- `{{placeholder}}` values are substituted ONLY for explicitly passed parameters; kwargs
  defaults are NOT substituted → fallbacks are mandatory in the code: `if not X or
  X.startswith("{{"): X = <default>`.
- Secrets — fall back to `~/extella_wizard/app/config.json`, otherwise an honest fail (not a
  silent one).
- Don't do a long build/save of other experts from inside a device expert — the saves may not
  stick. Build from an external client (a bridge/script on the host).

### Listener (the daemon on a device)
- Talks to `https://disnet.extella.ai/` (NOT api!). The `extella-listener` package from
  GitLab-PyPI, Python 3.12.
- **New device**: run `run_expert install_nohup_handler` + `register_cspl_shell` once,
  otherwise any nohup/shell expert fails with `'str' object is not callable`. This is a
  mandatory onboarding step for every device/VPS.
- The listener is headless: it has no GUI libraries (pyobjc and the like). Anything that
  touches the screen/GUI is a separate helper in a GUI session.

## 6. The Extella Desktop toolbar (v6) and plugins

### Structure
- The toolbar is built into the app: `app.asar → packages/extella-toolbar-suite/toolbar/build/toolbar.js`
  (~3 MB, readable JS, 15K+ lines). The loader first looks for an **override** at
  `~/Library/Application Support/extella-desktop/toolbar.js` — if the file exists, it loads that
  one. No file — the built-in one loads. This is the local-development mechanism.
- Sources (modular build): `~/extella_tools/extella-library-lite-main/toolbar/` →
  `src/core/*`, `src/panels/*`, `public/plugins_manager.html` (the storefront) → build with
  `node build.js` → `build/toolbar.js`.
- **Development cycle: edit src → `node build.js` → copy build/toolbar.js into the override →
  full restart of Extella (Cmd+Q).** Never edit the build file by hand. Every change = a git
  commit (we've already lost the source of truth once — don't repeat it).
- UI = a floating pill: Chat | Library | Plugins. Modules `ETB.*` (auth, api, registry, plugins,
  marketplace…). Injection into a BrowserView with `contextIsolation:true`, **NO Node/require at
  runtime** — file operations only through local bridge servers or experts.
- The storefront opens in a **blob-iframe with no session cookies** — the parent passes the
  token (this is already fixed in api.js/auth.js: 401 → refresh → retry). Keep this in mind for
  new iframe features.

### Plugins (how to add your app to the toolbar)
- Registry: `~/extella-plugins/_registry/<id>.json`. The working format is mode `repo_ui` +
  `ui.local_server`: `{port, mainFile, healthPath}`; the URL is built as
  `http://localhost:<port>/<mainFile>`.
- Autostart convention: the global expert `_etb_srv_<plugin_id>` — the toolbar calls it to
  bring up the plugin's local server if it's asleep.
- Local servers die on reboot — for persistent ones we use launchd
  (`~/Library/LaunchAgents/ai.extella.*.plist`, live examples: wizard-bridge on port 8765,
  ta-bridge on 8766).
- **Don't patch toolbar v6 for the sake of a plugin** — a plugin is added ONLY as a card in the
  registry. Editing toolbar.js is a separate decision for the owner to make.
- Install validator: take the port from the app's docker-compose/config; **never check :5000 or
  :7000** — on macOS those are AirPlay (returns 403 → an infinite loop); 2xx/3xx = alive; cap at
  ~30 polls.

### ⚠ KV is scoped by X-Agent-Id (23 Jul, we almost lost the catalog)
`kv/get`/`kv/set` with different `X-Agent-Id` values see DIFFERENT values for the same key (even
with `global: true`). The canonical scope for storefront catalogs is the `agent_extella_default`
header (historical; it's only a scope key, Claude isn't run). A write with the "wrong" agent
header goes into a shadow twin: first read the key with several headers and find where the real
value lives (by updated_at/size), then write to that same place; before overwriting a catalog,
assert a minimum size on what you read. The same scoping class applies to EXPERTS (see §5).

### Storefront catalogs in KV
`_mkt_installed` (what the user has installed), `_mkt_automations` (process cards),
`_mkt_mcp`/`_mkt_mcp_2`/`_mkt_mcp_3` (the MCP server catalog; **KV is sharded** — cut large
catalogs into several keys), `composer:catalog`. Allowlist of external MCP:
`~/.extella_mcp/allowlist.json`.

## 7. Scheduler, hosting, inbound

- Schedules: KV keys `sched:*` (+ `sched:__index__`). The ticker is the `wz_scheduler_tick`
  expert, and it needs to be run by cron on an always-on device. It does NOT tick on its own:
  for us that's a VPS, with cron every 15 min. Verify the ticker is actually enabled before
  promising "runs 24/7."
- Inbound messages: polling (Telegram getUpdates, etc.), no webhooks. `wz_scheduler_tick` has a
  `reply_expert` branch: if `inbound:<sid>` has a reply_expert set, the tick calls it with
  {message_text, chat_id, client} and replies with its reply field.
- Client secrets — vault: ciphertext `sec:<client>:<connector>` in KV, decrypted with a LOCAL
  `vault.key` on the hosting device. The key never leaves the device.
- A bot on the owner's PERSONAL number/account — always set the filter "reply only to numbers
  from the client database" (we had an incident where the bot replied to personal contacts).

## 7.5. Workspace: self-growing capabilities (P2) — GATE CANON

The `wz_workspace` engine (repo `copilot/`, plugin on port 34767) can **grow itself new
capabilities out of its own dead ends**: a task gets stuck → `cap_design` (Qwen writes code for
a new expert `wscap_<slug>`) → a passport card goes to a person → `cap_apply` on the word "I
authorize it" → registration → dispatch by triggers. If you're editing this mechanism, do NOT
weaken the canon:

1. **Only a person registers code.** The autopilot NEVER passes the `cap_apply` gate. Approval
   is tied to the card (slug + sha256 of the code): a mismatched/stale slug = refusal. "I don't
   authorize it"/"no" = refusal (a negation outranks a positive substring); an ambiguous answer
   doesn't close the question.
2. **Grown v1 capabilities are READ-ONLY.** An AST lint `_cap_lint` (not a substring check!): a
   whitelist of imports, a ban on writing files (`open` with `w/a/x/+`), `subprocess`, bare
   `eval/exec/compile`, `os.getenv`, `/api/agent/*`, `/api/expert/*`. File writes remain behind
   a separate write gate with a preview. The lint is the 2nd echelon AFTER the person, not the
   only barrier.
3. **The expert's name is salted with `ws_id`** (`wscap_<slug>_<hash>`) — otherwise workspaces
   would overwrite each other's code (a global namespace). The capability's output is scrubbed
   of secrets before the ledger/chat/log.
4. **Qwen code-gen pitfalls** (otherwise `cap_design` comes back silently empty): the word
   "expert" must NOT be in the prompt (Qwen refuses to "output expert code" — a platform
   safeguard), phrase it as "a python function for a personal project"; explicitly forbid tools
   (otherwise it drifts into `list_rules`/`search_concepts` and the turn breaks off);
   `max_output_tokens` ≥ 9000 (the reasoning model eats the budget on "thinking"); a 240s
   timeout and retry on HTTP 500 (`tries=3`).
5. **Lesson from prod:** a person eyeballing the code card does NOT catch a subtle logical
   error. A live autopilot grew a tax capability that counted DEPOSITS as income → a phantom
   $585K tax bill; caught only by a test run. The "unlearn" gate (`cap_forget`) is active
   insurance, not decoration. Dedup by word stems (`n=auto`), so the autopilot doesn't breed
   duplicates.

## 8. Live objects — DO NOT BREAK without an explicit request from the owner

- Agents: Wizard `agent_hM0qLHwu-Hw_4sjydTU1g`, Builder `agent_FLYxB0v1qIY2phB5beVP5`, Qwen
  Extella `agent_XwZBKvd8dD70jKvW4WrZm`, fine-tune `agent_iVWWFbzjmNwxgZNB5chIr`, the prod
  "ET-Tech" agents.
- VPS PS.kz `82.115.42.21` (user ubuntu): systemd `extella-listener`, cron for ops summaries and
  the scheduler. Do not reinstall, do not clean up.
- Plugin registry `~/extella-plugins/_registry/` — don't edit other people's cards.
- The live toolbar.js override — before any replacement, make a dated backup next to it
  (`.bak_<what>_<date>`).
- GitHub repos have been handed to teams: `extella-adoption-wizard` (platform team),
  `extella-marketplace-pack` (designer, toolbar). Push to them only on the owner's order; the
  designer has their own unmerged work there.

## 9. Working hygiene (hard-won)

1. **Backup before editing a live file**: `cp file file.bak_<marker>_<date>`. Always.
2. **Release = file → platform → verify → git commit.** The wizard bridge additionally
   publishes signed releases (`publish_release.py`, channel `rel:bridge:meta`, Ed25519).
3. **Before any push to a public repo** — scan for secrets (JWT `eyJ…`, `sk-…`, telegram
   `NNN:AA…`, `ghp_…`, `glpat-…`, private keys) and internal names/client PII. Infra identifiers
   (VPS IP, target UUID) — at the owner's discretion.
4. **Cyrillic**: if you're putting it into base64 anywhere — only `\uXXXX` escapes (atob isn't
   UTF-8). The new toolbar no longer uses base64, but the trap is universal.
5. **Don't trust a "green" status** — run E2E on a real input (a live search, a live Telegram
   message) before saying "it works."
6. Keep demo data and real client data separate; reload the demo database before every demo.
7. The concept embedding worker periodically stalls (new concepts don't get found by search) —
   there's a `wz_embedding_canary`; if you suspect this, run it instead of debugging your own
   code.

## 10. Where to look for details (on the owner's machine)

- `adoption_wizard/README_ADOPTION_WIZARD.md` — the wizard's main doc; `AGENT_SPEC.md` — the
  agent spec (the source of truth for checkboxes/freezing); `DEPLOYMENT_HOSTING.md` — hosting.
- `adoption_wizard/BUGS_FOR_TIMUR.md` and `~/Downloads/extella_bugs_to_fix.md` — full lists of
  known platform bugs with reproduction steps.
- `POST_HANDOFF_AUDIT_2026-07-10.md`, `TOOLBAR_CHANGES_POST_HANDOFF.md` — the current state of
  the repositories and the toolbar merge plan.
- GitHub: `AnvarBakiyev/extella-adoption-wizard` (wizard, v1.1.0 is current),
  `extella-marketplace-pack`, `extella-travel-agency-pack`, `extella-competitor-intel-pack` —
  live examples of correctly assembled packs (experts + install.py + a registry card).

**The main principle:** the platform is rough around the edges in places — it forgives whoever
verifies artifacts, splits up the work, and keeps the source of truth in files. Don't trust a
single API response, whether it says success or failure.
