<!-- source: PROMPT_UPDATE_AGENT.md sha256:b966c24b672fe672dfac55cff03b046fdf3730b3c3ae8dbe88ac8dfa44bbf85c -->

# Prompt "update the product to the standards" — handout version

The canonical text to hand out to builder chats. **Version 3, 12 Aug 2026 (evening)** —
after the platform rolled out app rights, and the live OS schema changed between two
checks within a single day. Hand this out from here, not from memory: fixes go into this
file.

Version 2 (that same morning) is stale in one place: it didn't know about `app_scopes`,
without which a storefront product publishes whole and silently doesn't work.

---

**Re-read the Extella standards — they were updated today, 12 Aug 2026, and some of the
previous conclusions are overturned. Then check your product against them.**

Repository: **github.com/AnvarBakiyev/extella-agent-standards** — clone it or update it,
the local copy is behind. Read in this order:

- `README.md` — the single entry point: connecting, the canon, the build order, the path
  to the store;
- `DEPLOY_REQUIREMENTS.md`, **the whole section H** — that's where everything new is;
- `BUILD_STAGES.md` — stages, stop rules, how a builder chat should behave.

**Rule zero: work only inside your own product's namespace.** The account is shared;
never touch colleagues' experts, rules or agents. Deleting anything outside your own
namespace happens only after a human confirms it, and even then: grep the repositories
for consumers beforehand, smoke-test afterward.

## What changed today — check every point against your product

1. **App rights (`app_scopes`) — a new required publishing step (H12).** Empty rights
   mean the app **cannot reach the agent's API at all**. The page will open whole, and
   every call will return `403`. Declare the minimum; if you need to run on the buyer's
   computer, that's a separate right, **`device.run`** — without it `targets` is
   stripped and the expert runs in the cloud instead. Rights **can be revoked at any
   time**, so `403` is a normal state: say in words "right revoked, enable it here,"
   don't show a blank screen.
2. **Hybrid is a standard product type (H10).** One version carries `archive`, `page`
   and `icon` as three fields. The "archive or page" fork is a false one: the data and
   keys can live on the machine while the interface is served from the OS. The type is
   determined by **where the data lives**.
3. **A page reaches the device (H5-bis).** Measured: `app-agent/run` executed an expert
   on the user's machine, in 13.6 and 17.3 seconds. **If you stopped work on the
   conclusion that "the sandbox can't reach the device" — that conclusion is
   overturned.**
4. **Speed dictates the architecture.** 13–17 seconds per call versus 6 milliseconds
   for a local bridge. That means **one snapshot call** instead of many small ones: the
   expert gathers device state and returns it in a single response. Porting the
   interface "as is" will produce an unusable interface.
5. **`{{token}}` is fully capable and expensive, not forbidden (H11).** It triggers a
   consent dialog for the buyer and gives power over the whole account. It's justified
   exactly when the product needs **more than its own agent** (for example, showing all
   of the user's agents): `app_token` is deliberately pinned to its own agent, it can't
   be used to manage the fleet.
6. **Purchases are readable, but not from the page (H11).** `my-purchases` works live,
   but it only knows the account token. The source for "what the user has" is core
   objects through the rights `expert.read` / `kv.read` / `rules.read`.
7. **A fact about the platform older than a day — re-verify it live.** The OS schema
   changed between two checks within a single day. Don't cite yesterday's note as a
   reason to stop.

## Order of work

1. **Determine the product type** by where the data lives, and don't rule out a hybrid.
2. **Declare the stage and the facts**, get the scope from the machine:
   `python3 tools/stage_gates.py --stage build --json`. Gates marked "account-level"
   aren't yours: name them in the report and hand them to the integrator.
   If you don't declare a stage, it's treated as `prod`.
3. **Change behavior, not produce documents.** Don't write contracts and manifests "just
   in case"; whatever is missing goes into the report as a line.
4. **Work in the working copy, push the branch right away, not at the end.** Not in a
   temp clone: work that only lives in `/private/tmp` disappears with the folder — a
   day of work on Console was nearly lost that way already.
5. **Your own agent:** check what it thinks it is (`agent/run`, `agent_id` in the body);
   role by a file in the repo → flashed as a whole → a rollback path; **narrow the
   tools** — a fresh agent is born with `sys__all__` and `delete_*`. Creating an agent
   in the live interface is a human action — ask the owner.
6. **Write experts over REST** (`POST /api/expert/save` + `X-Agent-Id`), not through the
   MCP `save_expert`. After writing, read it back and compare by content (field
   `expert_code`, not `code` — an asymmetry between fields, H5-quater). **Check the
   cross-check itself:** break one field on purpose and make sure it fails.
7. **A timeout does not mean failure.** Deferred runs return a `task_id`; fetch the
   result through `/api/tasks/check`, the client timeout is 60–90 seconds. "HTTP didn't
   come back, so it broke" has already cost us days.
8. **Canonical shared modules** (`platform_client`, the selection screen) are not edited
   in place — a fix goes into the canon, copies sync from it. Access to the core from a
   device is taken as in the canon: `~/.extella/api_token.txt`, fallback
   `~/extella_wizard/app/config.json`.
9. **Carry it through to a pre-release yourself — don't stop at a zip.** Rights declared
   → publish as a pre-release (`published=0`, visible only to the author) → buy it for
   yourself → install → **first run from a clean state** → the scenario live. Stop right
   before `Publish` — a human clicks that button. Client keys (Tourvisor, WhatsApp, CRM)
   are not a blocker: the product must be honest without them. Attach `listing_id`,
   `version_id`, and what the first run showed.

**Stop rules (a violation is a defect at any stage):** external writes only as drafts;
client data stays inside the client's perimeter; no destructive rights, and `app_scopes`
kept minimal; don't touch anyone else's live things; secrets don't go into the archive;
a refusal is visible in words.

**Report — three parts: "closed / not mine / not closed, honestly,"** plus
`OWNER_TASKS.md` with exact steps for a human, if any are needed. An honestly named
unclosed item is more useful than green checkmarks.
