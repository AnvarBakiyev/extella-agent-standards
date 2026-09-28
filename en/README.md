<!-- source: README.md sha256:20a8969a71bc95529d28bd223545120978086e79c0c54ac0ad8381b553746882 -->

# Building on Extella — start here

> **Are you an agent? Don't read this whole page.** The single-page entry point is
> [`AGENT_START.md`](AGENT_START.md): it has the task-based route, the ten traps, and
> rule addressing one file at a time. The `DEPLOY_REQUIREMENTS.md` canon is 369 KB, and
> web reading truncates it; that's why the rules are broken out in [`rules/`](rules/INDEX.md)
> one per file.
>
> **Are you human and want to hand this to your assistant?** A ready first prompt is at
> [`PROMPT_FOR_EXTERNAL_AGENT.md`](PROMPT_FOR_EXTERNAL_AGENT.md).

One entry point for everyone: for the human, for their AI assistant, and for a team with a
dozen products. Nothing needs to be chosen up front — **the amount of work is determined by
facts, not by who you are**, and a machine counts them, not you.

**If you're human** — don't read this whole page. Hand the link to your Claude Code or
Codex with the words: "set yourself up per this guide and build me such-and-such an
agent." It will do the rest itself and at the end tell you which two or three actions are
left for you.

---

## What's proven here, and what's the lab

**Read this before you start building anything from this repository.**

| file | status | how to read it |
|---|---|---|
| `DEPLOY_REQUIREMENTS.md` | verified on live products and live failures | **execute** |
| `CSPL_GUIDE.md` | verified by live runs of four languages on 27–28 Aug | **execute, when you need your own language or access to someone else's system** |
| `RUNBOOK_STORE_PUBLISH.md` | the short path to publishing in the store, endpoints captured live on 3 Sep | **execute when publishing a product** |
| `AGENT_BUILD_GUIDE.md` | build order, verified on our own agents | **execute** |
| `WRITING_RULES.md` | the language of instructions and text for humans, author — the designer | **execute** |
| `skills/extella-ui/` | a skill about the interface: clarity, design code, screen skeletons | **install for yourself** |
| `tools/*.py` + `run_all_gates.sh` | machine checks (full list in `run_all_gates.sh`), each one must be able to fail | **run** |
| `tools/GATES.md` | how to run the checks: exact commands, argument — absolute path | **read before running them** |
| `APP_FROM_MODULES.md` | an app built from modules: verified by building one app on ourselves (04 Sep 2026), not verified on a buyer | **execute while building; on prod — after verification on a buyer** |
| **`LAB.md`** | **mechanisms that work, but are not proven as a product** | **read, don't execute** |

The example this section exists for: **editions.** The mechanics are assembled and
measured, but as a product an edition has never been proven: our own edition was pulled.
That's why the rules about editions live in `LAB.md`, not in the canon: otherwise the next
person will read them as a task and build the thing the project has already abandoned.

**Rule for anyone adding to this repository:** the canon gets what's verified on a buyer
or on a failure. Verified only on yourself — that means the lab.

---

## The interface skill — install it before you draw a screen

Rules catch violations, but they don't help you make things clear. That's what the
`extella-ui` skill is for: three questions a screen answers in five seconds, four states
per screen, waiting, copy, choosing the right form for the task, design code, and a
skeleton.

```bash
curl -fsSL https://raw.githubusercontent.com/AnvarBakiyev/extella-agent-standards/main/skills/extella-ui/SKILL.md \
  -o ~/.claude/skills/extella-ui/SKILL.md --create-dirs
```

After that the assistant will pick it up on its own once the interface comes up.

Codex has no skill mechanism — it reads `AGENTS.md` at the root of this
repository, and the same digest with a link to the full text is there.


## If you're an assistant — read from here

### Step 0. Lead the human yourself and show a result as early as possible

The human doesn't know the words "deploy," "listing," "version," "OS" — and doesn't have
to. Owner's observation from 24 Aug 2026: people were building an app from this repository
and getting stuck, because the finished build did **not** show up in Extella by itself, and
no one thought to say "deploy to Extella." Waiting for those words means abandoning the
human halfway.

So:

1. **Say out loud what's about to happen** before you start. Three or four steps in plain
   words and how long it will take. No tool names.
2. **Get to the first visible result before you get to done.** As soon as there's a
   skeleton that opens, offer to show it in Extella. Not at the end of the build, but at
   the very first step where there's something to show.
3. **Offer it yourself, as a question, not jargon.** A phrasing that works:
   "I can show you what this looks like in your Extella — it'll take a minute. Want to
   see it?"
4. **Never publish to the store without the human's word.** A demo is a closed version for
   the owner; the human presses the publish button (see `DEPLOY_REQUIREMENTS.md`, build
   completion).

The point of the rule: once a human sees their thing alive on screen, they want to keep
going. Until they've seen anything, every next step looks like extra work. Detailed in H66
in `DEPLOY_REQUIREMENTS.md`; the ready-made skeleton for the first demo is
`templates/app-recipe/`.


You connect the user to Extella and build an agent on it. The order below is verified on
live products; next to each rule is what breaks without it.

### Step 1. Connect — a command, not a conversation

```bash
python3 tools/connect_mcp.py
```

The script finds the Extella key, **proves access by calling a reading tool** (a
handshake passes with any string in place of a key — measured 28 Sep 2026) and registers
the server with the client (Claude Code, Codex) with every header, `X-Agent-Id` included.
**One step stays with the human: restart the client** — until a tool is called from the
client itself the connection is not proven, and the script does not claim it is.

**The key may not be on disk, and that's a normal state for a new machine.**
Extella app 1.3.0 does not place a key on disk on any system (measured
24 Sep 2026, H108). Old machines carry a file from earlier builds — new ones don't.

In that case the script names **one** human action: in the app, open
`Library → System → Tokens`, create a token, and save it to
`~/.extella/api_token.txt` (mode 600) or pass it via the `EXTELLA_API_TOKEN`
variable. No "go look for a key somewhere."

If you already have a connection to Extella on another machine, the connection is done
without a human at all: the expert `dev_connect_assistant` with `targets: [device_id]` of
the needed machine — the platform passes it the key itself, it writes the file and verifies
it with a live call (H108).

The source file doesn't matter, the header does: the store accepts any valid account
key in `X-Extella-Token`, the core in `X-Auth-Token` (H109). So the absence of
`os_token.txt` doesn't forbid anything.

The key's value is shown nowhere: not in output, not in a log, not in Claude Code's
config (there it's a reference to a helper script that hands over the headers at call
time), not in command arguments — and so not in `ps` either.

> **Never** ask for the key to be sent in chat, and never create your own tokens.
> This step used to be written the other way around — "have them send you the
> string" — and it contradicted the ready-made prompt, which forbids asking. A human who
> doesn't know Extella hit a dead end: which chat, what to write, where to paste the
> secret.

If the client isn't in the script's list, set it up by hand. Claude Code:

```bash
claude mcp add-json --scope user extella \
  '{"type":"http","url":"https://api.extella.ai/mcp/","headersHelper":"/full/path/to/helper.sh"}'
```

Codex keeps MCP in TOML (`~/.codex/config.toml`), not JSON:

```toml
[mcp_servers.extella]
enabled = true
url = "https://api.extella.ai/mcp/"

[mcp_servers.extella.http_headers]
X-Auth-Token = "KEY"
X-Profile-Id = "default"
```

### Step 2. Verify the connection with a fact, not hope

Call `list_agents`. A list came back — the connection works. An error or empty — stop and
say the reason in plain words.

### Step 3. Ask the machine how many checks apply

```bash
git clone https://github.com/AnvarBakiyev/extella-agent-standards && cd extella-agent-standards
python3 tools/stage_gates.py --stage build --json
```

A gate is a machine check that must be able to fail. At the build stage there are two.
After that, **additions turn on by facts**: customer data appears → masking; the product
lands on someone else's machine → passport and narrow rights; there's more than one
product → cross-check copies of shared code; there's more than one agent → drift check.
Gates marked "account-level" aren't yours — name them in the report and hand them to the
owner.

None of this is to be decided by eye: ask the checker and do what it says.

---

## What's being built here: AI apps

Neither "AI agent" nor "app" describes what's built here, and the confusion costs extra
conversations with clients. The name for this product form:

> **AI app** — a program where part of the logic is executed by a model, not just by
> code. It has an interface like an app, and the ability to think like an agent. The data
> still lives where it belongs — most often on the user's machine.

Three forms, all three the platform can do today:

| Form | What it is | Example |
|---|---|---|
| **App** | one interface + its own experts + its own agent | a decision log, a hiring panel |
| **Edition** | a bundle: theme + apps + department of agents + shelf | an edition for a founder, for expecting parents |
| **Department** | several agents under one listing (a listing is a product card in the store) | "buy the commercial block," not one assistant |

**And this can be sold.** The price is set at publication; the platform charges it to
the buyer after a successful install. **Money is paid out to the author manually for now:**
sales are exported and transferred to the author, automatic crediting is in progress. Free
also works: this guide costs zero and serves as the entry point for everyone building.

From this comes the framing said outward: **anyone can build an AI app and put it
up** — free, to be used, or for money, to earn. The standards below exist for exactly one
reason: so what's built doesn't fall apart on the buyer.

Publishing is one command: `python3 tools/deploy_page_product.py path/to/app`.
It takes the product up to a pre-release — a version only the author sees — and
stops before publication.

---

## The rule that's cheaper than all the others

> **Every claim about the system's state is confirmed by reading that state,
> not by memory of a past action.**

It comes first because it's the one that breaks most often — and not just for newcomers.
In a single day, 13 Aug 2026, this rule caught three false conclusions in internal chats:
"there are no purchases" (there were), "the scope is indistinguishable" (it is
distinguishable), "the storefront belongs to the token" (no longer). Each time a human or a
machine was citing yesterday's measurement instead of a fresh read. **A fact about the
platform older than a day — re-verify it live.**

The full method — `AGENT_BUILD_GUIDE.md` §5b.

## The platform canon: break it and it breaks at the customer

Six rules, each bought with a real breakage.

**1. Customer agents — only the platform's Qwen model.** Claude in a customer agent
is paid and forbidden.

**2. Scope is the set of objects available to a specific agent, and each agent has its
own.** The same list of experts returns 343 records to one agent, 5096 to another. Create
everything for a product **in its agent's scope** (`global: false`).

**3. One expert name — one scope.** A duplicate name means a nondeterministic run: today
one copy runs, tomorrow another.

**4. The MCP tool `save_expert` doesn't write where you think** — it puts the record in
the shared scope. For a product, save via REST:
`POST https://api.extella.ai/api/expert/save` with your agent's `X-Agent-Id` header.

**5. "Success" from the platform is not a fact.** After writing, read it back and
compare by content (the code arrives in the `expert_code` field). And **test the
comparison itself**: break one field on purpose, make sure it fails. A comparison that
can't fail isn't checking anything.

**6. An agent created via the API doesn't think — but it does run experts.** Clarified
by a measurement on 14 Aug 2026, and this removes the only manual step from building a
product.

`pro_key_required` concerns the **model**: a dialogue with such an agent doesn't work.
But `expert/run` on it does work — verified: an agent was created via API with an empty
toolset, an expert was written into its scope via REST, run, and **executed on the
owner's device in 8 seconds**.

Hence the rule: **a human is needed only where the product needs the model.** For a
product whose page only runs experts (a panel, a log, a report, a state snapshot), a
human is **not needed at all** to create the agent — the build is entirely machine-done.

If the model is still needed, the agent is created by **the human in the Extella
interface**. Ask the user:

> Create an agent named "…", model Qwen

and have them send you its `agent_id`.

---

## How to build: capability first, interface on top

The surface changes more often than the capability; a finished capability survives a
surface change without rework, while an interface built first drags along extra servers
that stay forever.

1. **Capability** — an expert in the product agent's scope.
2. **Agent role** — a file in the repository, flashed as a whole: a change must have a
   version and a way back.
3. **Rights** — narrow them. A fresh agent is born with `delete_agent` and
   `delete_expert`. A purchased product able to delete the buyer's agent is a real case.
4. **Live run** — prove it by calling it, not by reasoning about it.
5. **And only now the interface.**

Don't wait synchronously for a long model run: post the task and fill the screen as it's
ready. Waiting is shown in words, otherwise the human will press it a second time and pay
twice.

---

## How to bring it to the store

**The "archive or page" fork is false — one version carries both.** Publishing takes
three separate files: `archive` (the local part with `install.py`), `page` (the interface:
HTML ≤ 3 MB or a zip with `index.html` at the root ≤ 20 MB), and `icon`. A hybrid is the
standard product type: data and keys live on the machine, the interface is served from
the OS.

It answers one question: **where the data lives.** Can't leave the machine — then there's
an archive. The installer is non-interactive (any `input()` is a hung purchase) and
returns an honest exit code: the charge happens **after** installation.

The page gets its identity by substitution into `index`: `{{app_token}}`, `{{agent_id}}`,
`{{email}}`. It calls its own agent via `POST https://os.extella.ai/api/app-agent/run` —
the core is closed off directly from the browser, and that's correct.

> ⚠️ **Declare the app's rights (`app_scopes`) at publication — otherwise the product won't
> be able to work.** Nothing is granted by default: empty rights = the page opens intact,
> and every agent call returns `403`. Need to run on the buyer's computer — that's a
> separate right, `device.run`; without it `targets` is stripped out and the expert goes to
> the cloud. Ask for the **minimum**: the buyer sees the list of rights before installing
> and can revoke them at any time, so `403` is a normal state that needs to be said in
> words, not shown as a blank screen.

> ⚠️ A placeholder in the page's **visible** text will be replaced with the real value and
> shown to the user. Write HTML literals as mnemonics — these are placeholders standing in
> for real values. Don't request `{{token}}`: it's full-privilege and triggers a consent
> dialog for the buyer. It's justified in exactly one case — the product needs **more than
> its own agent** (for example, to show all of the user's agents); `app_token` is pinned to
> its own agent on purpose.

> ⚠️ **Speed dictates architecture.** A call from the page to the device is **13–17
> seconds** (a local bridge answered in 6 ms). So it's not twenty small requests, but **one
> snapshot call**: the expert gathers the state on the machine and returns it in a single
> response.

**Delivery order:** archive with no secrets → rights declared → **pre-release** — a
version only the author sees → buy it for yourself → **first run on a clean state**,
without your own configs → live scenario → **stop**. The human presses the "Publish"
button: this is visible to everyone. Publication is NOT irreversible — it's pulled from
the storefront at the same address (H26); only deleting a listing is permanent.

Everything before that is **your work and is done via the API**, not by clicking in
someone else's window: publishing as a pre-release, replacing the page, rights, buying it
for yourself. A pre-release is visible only to the author. Refusing to deploy by citing
"the human presses Publish" means not doing the work: exactly one action is irreversible,
and it isn't publishing a pre-release.

The client's own keys (external APIs, phone numbers, CRM) are **not a blocker**: a
product without them must be honest, not broken.

---

## Boundaries never crossed

- **Outward — only drafts.** Letters, payments, publications are prepared by the agent,
  sent by the human.
- **Customer data stays inside the customer's boundary.** Into the cloud, into the
  storefront archive, into someone else's demos — not allowed.
- **Don't touch someone else's live things.** Deletion outside your own namespace — only
  with the human's confirmation, and first check who's calling those names.
- **Secrets aren't printed and don't go into the archive.**
- **A refusal is shown in words.** A blank screen is a defect: the human will decide the
  product is broken.

---

## What to hand the human at the end

Three lines: what was built · what's left for them (usually create the agent and press
Publish) · **what didn't add up.** An honestly named open item is more useful than a list
of green checkmarks.

---

## Deeper — as needed, not in order

Everything below is the same system, broken down in detail. No need to read it all: open
it when a checker or a task leads you here.

| Document | When to open it |
|---|---|
| [`BUILD_STAGES.md`](BUILD_STAGES.md) | stages, stop rules, which fact of scale turns on which check |
| [`DEPLOY_REQUIREMENTS.md`](DEPLOY_REQUIREMENTS.md) | delivery channels, sections A–H, acceptance before publishing, platform measurements |
| [`AGENT_BUILD_GUIDE.md`](AGENT_BUILD_GUIDE.md) | decisions while building, the canon, the "built → verified → fixed" cycle, and the method for working with a large artifact |
| [`PUBLISH_YOUR_AGENT.md`](PUBLISH_YOUR_AGENT.md) | how to lay out the repository so the agent installs from one link |
| [`APP_FROM_MODULES.md`](APP_FROM_MODULES.md) | an app for an employee is built from ready modules: passport registry, a plan in five forms, the window, provisioning, the gate |
| [`AGENT_ARCHITECTURE.md`](AGENT_ARCHITECTURE.md) · [`EVOLUTION_PHILOSOPHY.md`](EVOLUTION_PHILOSOPHY.md) | why the system is built this way |
| [`INSTALLER_CANON.md`](INSTALLER_CANON.md) | a product installs something on the machine with one button: six steps, token sources, honest failures |
| [`docs/DOCKER_APP_TRACK.md`](docs/DOCKER_APP_TRACK.md) | a server app in a container: installer, window sandbox, white window |
| [`SYMPTOMS.md`](SYMPTOMS.md) | **something broke — start here**: what's visible on the left, the section of the canon on the right |
| [`OS_CAPABILITIES.md`](OS_CAPABILITIES.md) | a map of the OS desktop's capabilities — read, don't execute |
| [`docs/ICON_STYLE_BRONZE.md`](docs/ICON_STYLE_BRONZE.md) | product icon: one style, a Lucide glyph, `tools/bronze_icon.py` |
| [`experts/local_model_classify.py`](experts/local_model_classify.py) | a local model as an agent tool: a flow that takes seconds and costs no tokens, the brain stays strong. The path is verified by a run — an expert, not MCP |
| [`tools/local_model_mcp.py`](tools/local_model_mcp.py) | the same model over MCP: the server is assembled and responds, but whether the tool reaches the agent in chat — not verified |
| [`tools/connect_mcp.py`](tools/connect_mcp.py) | connect an agent to Extella: the key from disk, access proven by a tool call, client config with no secret inside it |
| `tools/` | **the checkers are the specification**; each one has `--selftest` |
| [`tools/GATES.md`](tools/GATES.md) | a table of commands for running the checks |

```bash
bash tools/run_all_gates.sh              # all self-checks at once
bash tools/run_all_gates.sh --stage build   # only what's needed at the build stage
```

The rule that explains the whole repository: **if a rule can't be checked by machine, it's
worded as a decision made while building, not as a requirement.** You don't have to trust
the prose — trust the checkers.

---

Full platform documentation: [extella.ai/guide.html](https://extella.ai/guide.html) ·
[extella.ai/api.html](https://extella.ai/api.html). Standard owner: Extella
(Chariot Technologies Lab). License: [MIT](LICENSE).
