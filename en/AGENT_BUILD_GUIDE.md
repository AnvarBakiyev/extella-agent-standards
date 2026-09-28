<!-- source: AGENT_BUILD_GUIDE.md sha256:11bd9f42c0399f80bfefdcef11ce6d27c10a8433e65634532bcac95e50c31027 -->

# How to build an Extella agent

**This document is written for a machine.** It is read by Claude, Codex or any app that
builds agents. A human does not read it and fills nothing in from it: they say what they need,
and you do everything else.

Owner: CEO. Version: 3.0, 12 Aug 2026 — two stages instead of three, add-ons by facts, agent freeze lifted (§0a).

---

## Words that come up constantly below

**Scope** is the set of objects available to a specific agent; every agent has its own.
**Listing** is a product card in the store.
**Gate** is a machine check that must be able to fail.

## 0. What is required of you, in one paragraph

You are given a task in human words. You **declare a stage** (§0a), build the agent and
run exactly the checkers that this stage requires. The checkers, not this text,
are the specification: if a rule cannot be checked by a machine, it is phrased below as a
build-time decision, not as a requirement.

---

## 0a. The stage decides the scope. This is the first action, not a formality

**Not all of this document applies all the time.** There are two stages (owner's decision of 12 Aug 2026 —
the former demo and pilot are merged: the client gives their data already for the demo, and that is fine):

| Stage | What happens | Gates |
|---|---|---|
| `build` | from the first line to a working thing at the client | **2** + add-ons by facts |
| `prod` | the product is handed out to any buyer | 21 |

Add-ons during the build are switched on **by facts, not by a label**: client data appeared →
masking and pinning tasks to a device; the product landed on someone else's machine → passport,
permissions, state contract, copies of the canon. Ask the machine for the scope:

```
python3 tools/stage_gates.py --stage build --json
```

**No stage declared — it counts as `prod`:** silence buys no leniency. The old names `demo`
and `pilot` are accepted as synonyms for `build`.

**Stop rules apply at every stage** — external writes only as a draft; client
data only inside the client's perimeter (taking it out to the cloud/archives/third-party surfaces is forbidden);
no destructive permissions; do not touch someone else's live objects (your own agent evolves with a trail and
a rollback — there is no freeze); secrets do not travel; a refusal is visible in words. Violating them is a defect,
not "an unfinished stage". Details: `BUILD_STAGES.md`.

Finishing the build: **the chat prepares the artifact, the human uploads it** through the OS publication form
(a ready file + a three-line instruction). Permissions on platform objects: your own namespace —
free, including deletion; deletion outside your own — with confirmation.

---

## 0b. Why all of this is arranged exactly this way

One idea from which the rest follows: **an agent's value is created not at the moment of creation, but
over its lifetime.** Assembling a working demonstration is easy; what is hard is changing the behaviour of a
live agent without breaking it and without losing the ability to go back. That is why Extella's product is
not an agent constructor but **managed change of behaviour**.

Hence three consequences that explain almost all the rules below:

**Declared is not equal to actual.** A pretty description does not prove behaviour. That is why the
passport declares, the state shows the fact, and the divergence between them must be visible, not
smoothed over.

**Change matters more than creation.** That is why everything has a version, a rollback path and a boundary
of propagation: a shared object changes the behaviour of everyone who uses it.

**Silence costs more than an error.** A loud error costs a minute. An operation that answered "success" that
did not happen costs weeks — we learn the truth from artifacts several days later. Almost every
expensive incident we have had was exactly like that.

In full — `EVOLUTION_PHILOSOPHY.md`, but for building this is enough.

---

## 1. What an Extella agent is

Not a chat with a long prompt, but a managed **business capability**: its inputs, outputs,
boundaries and evidence of execution are known. The unit of the product is not "an agent in general" but a specific
capability: reconcile two exports, check a contract, anonymise a file, read data from 1C.

The layers you assemble: interface → agent (dialogue) → orchestrator (plan and limits) →
rules → knowledge → experts (deterministic execution) → CSPL (a shared class handler) →
listener (device boundary) → evidence.

The model is responsible for the ambiguity of language. Permissions, side effects and exact computations are
not its job.

---

## 2. Nine decisions you make while building

No gate checks them — they determine WHAT you build. The machine checks the rest.

**2.1. Deterministic first.** If there is code — take code. LLM for arithmetic and validation
is forbidden. A capability that can be written as a function must not be a prompt.

**2.2. A prompt is not a security boundary.** If an action must not be allowed, it cannot be disallowed
by an instruction — only by the absence of a tool or by a check in code.

**2.3. Reading is separated from changing.** One tool does not do both: otherwise you cannot
grant read-only permission.

**2.4. Isolation by default.** Everything is created in this agent's area. A shared object is a separate
deliberate decision, and it changes the behaviour of everyone who uses it.

**2.5. A human is mandatory at high risk.** External writes, money, the irreversible — a draft and
confirmation, not an autonomous action.

**2.6. An error tells the truth.** HTTP 500 and a timeout are neither failure nor success: verify by an artifact.
"Success" on partial execution is a defect, not optimism.

**2.7. A mute refusal is worse than a loud error.** If something did not get done — say so in the answer. Our
most expensive class of breakage is exactly this: the operation answers "success" that did not happen.

**2.8. A fallback is an honest refusal, not a substitution.** Did not find something mandatory (an agent, a key,
a device) — refuse and say what is missing. A quiet substitution works for you and breaks for the client.

**2.9. Search before you create.** Before writing a new capability, ask
`wz_capability_find` with the task in words. If something similar exists — take it or adapt it.

---

## 2a. What to close the task with: a decision table

This section used to say HOW to build safely, and not a word about WITH WHAT. The result is visible
as a number: the account's 290 capabilities have **4 class handlers**, while 257 capabilities
live in families of 4 or more. The same thing is written again and again.

| What is in front of you | What to close it with |
|---|---|
| the agent must **know** something | **knowledge** (Concept) |
| something is **forbidden** or requires confirmation | **rule** (Rule) |
| a one-off deterministic action | **expert** |
| the **third similar** action in a row | **class handler** (CSPL) |
| the task is already closed by a ready agent or automation | **a call to another agent** — that is also a capability |
| the needed tool already exists in the world | **CLI** or **MCP**, not your own code |

**A hint about the third similar one.** Writing a third similar expert — stop and think about a
class handler: it lets you change the behaviour of the whole family at once, instead of editing N files.
Our most obvious example is 96 capabilities with the prefix `cap_`, which repeat one
pattern 17 times: "install a CLI, declare the commands, run". This is not a ban on writing an expert: it is a reason to
weigh it. Premature abstraction is harmful too.

**What NOT to close it with.** A prompt — for what can be computed by code. A new expert — for what already
exists in the registry: first ask `wz_capability_find` with the task in words.

## 2b. Where to run the work and what to build the surface with — recommendations

**These are recommendations, not gates.** The checkers do not check them, you may deviate — but name the
reason in the report. The section appeared on 13 Aug 2026 from the owner's question: "we tied an expert
to every button, is there any sense in that". There is no sense, and here is the price.

### The latency ladder (measured on live products)

| Where it runs | How long the human waits |
|---|---|
| in the page itself (JS) | **0 ms** |
| the product's local server on the machine | 6 ms |
| the core directly | ~810 ms |
| a KV read | 1.7–2.9 s |
| **an expert from the page to the device** | **13–17 s** |

Between the first and the last row — thousands of times. A button with an expert behind it is a button
after which the human stares at the screen for fifteen seconds.

> **An expert is not a button, it is work.** It is called when you need the model, the user's
> machine or their private data. Show, filter, sort, validate a
> form, compute a sum, page through — the page does that in zero milliseconds.

The historical reason we have it otherwise: in the toolbar the page could only send messages
to the host, so an expert hung on every button. The page has long been able to do more — **half
of the former experts need not be carried over at all.**

### What to run where

| Task | Where | Why |
|---|---|---|
| draw, sort, validate input | **in the page** | zero latency, zero permissions, zero refusals |
| read account state: agents, rules, KV | **`/api/ext/core`** (permission `api.full`) | one network call instead of launching an expert |
| text, parsing, a decision — the model is needed | **`agent.run` / `expert.run`** | this is precisely the model's work |
| local files, 1C, keys, a service | **an expert on the device** (`device.run`) | the data does not leave the machine |
| someone else's API (CRM, Tourvisor, a bank) | **`/api/ext/fetch`** | no local server, no open CORS |
| many small calls per second | **the local part** (archive) | 6 ms versus 13 seconds — otherwise the interface is dead |

**The technique that solves the most:** not twenty small calls, but **one snapshot call**.
The expert gathers the state on the device and returns it in one answer; after that the page works
with what is already in hand. Fifteen seconds once on opening instead of fifteen per click.

### What to build the surface with

| Technology | Fits | Caveat |
|---|---|---|
| **HTML + JS in one file** | yes, up to 3 MB | fastest to build and edit; our guide is like that |
| **React / Vue / Svelte** | yes, zip up to 20 MB | only a built bundle. There is no server-side rendering (Next.js SSR) |
| **exe, dmg, binary** | yes, via an archive up to 100 MB | installed by `install.py`, the interface on top as a page |
| **CLI** | yes | a binary on the device plus a wrapper expert so the agent can call it |
| **OS browser extension** | yes, `.js` up to 512 KB | adapt someone else's site for the client without changing anything in their system |
| **Profile (several agents)** | yes, as one listing | we sell a department, not an employee |

**What you cannot do, so as not to design the impossible:** the page does not work in the background (the
window is closed — nothing is computed); the product cannot knock on the user's door by itself; there is nowhere
to store secrets in the page — a key is either entered or lives in the local part.

### How to choose, in one line

**The data decides the product type. The call frequency decides the surface. The model decides whether an
expert is needed at all.**

---

## 3. Platform canon: break it and prod breaks

This is not style, these are properties of Extella verified by fact as of 28 Jul 2026.

**Platform Qwen only.** Client agents run on `alibaba` / qwen-3.7. Claude is
paid and forbidden. The passport gate checks this.

**Scope decides everything, `global: true` does not save you.** Every agent has its own set of available objects: the list of experts
returns 343 records to one agent and 5096 to another. The travel agency's agent does not see a single one of its own
experts — it calls them and they work, but they are not in the list. **An agent's own copy of a key beats
the shared one even with an explicit `global: true`.** Hence the rule: the writer and the reader of a shared key must
work under the same agent.

**The registry lives where it can be rebuilt from.** If losing the storage means losing the data, it is
not a registry but the only copy. The source of truth is the passports in git; KV is only a cache.

**Secrets by reference.** The passport, the state and the logs record WHERE a secret lies, never the
secret itself. The state is handed to the client.

**An expert your code calls must be in the installer.** Otherwise it works for you, and for the
client it is silently absent.

**Russian and English from the start.** The interface, explanations and error texts — in two languages from the very
beginning, in ALL apps. Translating later does not count. Checked by a machine: `check_translation`
(canon H95) does not pass a section without English, and a fingerprint of the Russian next to the translation catches
a lagging or drifting translation. A single-language app does not pass acceptance.

---

## 3a. Calling an expert from a page: platform traps

The "panel through the toolbar bridge" channel is closed: the toolbar was removed on 12 Aug 2026,
the channel was struck from the rulebook on 23 Sep 2026 (`DEPLOY_REQUIREMENTS.md`, "Delivery
channels"). An OS page calls experts through `{{app_token}}` and `app-agent/run` — rule H106; a
serverless scaffold with a route table and a dispatcher comes from `tools/new_product.py --page`.
Below is only what the rulebook does not cover and what catches everyone (measured 04 Aug 2026):

- **An expert run ≈ 10 seconds** of overhead (an empty probe — 8 s).
  Assemble the first screen with ONE method, not four calls.
- **An asynchronous run (`wait: false`) is bounced by an instant "Worker hung".**
  Call synchronously; follow up on a deferred task only if the platform itself
  returned a `task_id`.
- **Pinning — only `targets` as an array.** A single `target` the platform
  accepts silently and ignores: the work goes to someone else's device looking like success.
- **Your own timeouts in the request body break the run** — that is the client's concern, not the server's.
- **The expert must know the root of THE copy of the product where the data lies.** A machine
  can have several clones; a search through the list once picked the developer's clone with
  an empty database, and the product honestly answered "no table" — it looked like a page
  breakage.
- **Verify on a test stand, not in the app.** A page in an iframe with a call stub
  and a `window.onerror` catcher catches what live looks like "loading forever":
  the page script is an IIFE, one error kills it entirely.

---

## 4. What you must ship together with the agent

### 4.1. The passport — and you fill it in yourself

`templates/agent_passport.yaml` for one agent, `templates/automation_passport.yaml` for
an automation of several. **The human writes in nothing**, because you already have everything:

| Field | Where you take it from |
|---|---|
| `business_goal`, `what` | from the human's original request — in THEIR words |
| `limits` | what you deliberately did NOT do |
| `needs` / `integrations` | what you connected and which permissions you requested |
| `experts`, `rules`, `concepts` | what you created |
| `rollback` | how to return the state to what it was before your build |
| `hosting_profile` | where you placed it |
| `kind` + `ref` | what executes the capability: `expert`, `agent`, `automation`, `cli`, `mcp`, `cspl`, `skill` |

The `what` field matters more than it seems: **the capability is found by it.** Write in the client's words, not
with a function name. "Finds clients with a birthday and prepares a greeting" — yes; "scans the database
by the birthday field" — no.


**A call to another agent is a full-fledged capability.** If the task "check a contract" is already
closed by a ready agent, declare `kind: agent` and `ref: agent_...`, rather than writing an expert anew.
One condition: when delegating to an agent a nesting limit is mandatory
(`budgets.max_delegation_depth`) — otherwise a cycle of agents is not bounded by anything. This is the only
place where a budget remained mandatory, and there it is not a ceremony.

Do not fill in the `optional` section in the templates. It exists for the requirement of a specific client;
invented values make the passport worse — it starts lying plausibly.

### 4.2. The state contract, if this is a service

`/api/health` and `/api/state`. The state must have a `bound_to` block: where it lives, which
account and agent it is bound to. An absent field and an honest `null` are different things: the field must be there.
The exact response schema is `extella.automation_state.v1`: `enabled` only boolean;
`active_version` — SemVer or `null`; `last_run` — ISO/number/object with `at|ts` or `null`;
`last_result` — only `ok|failed|partial|null`; `last_error` — three string fields or `null`;
each schedule contains `id`, a boolean `active` and a present `next_run`.

If the state is read by an Expert, the passport declares **two separate axes**: how to obtain
`X-Agent-Id` (`state_reader.agent_scope`) and with which flag the Expert is saved
(`state_reader.expert_global`). Do not derive one from the other: a global Expert can be read under
the header of a specific agent. For the two component modes both flag values are allowed;
`ACCOUNT_GLOBAL` requires `expert_global: true`. The reference `agent_scope_ref` points to a stable unique
`components.platform_agents[].component_id`, not to an index and not to a copy of `platform_agent_id`.
For `USER_SELECTED` the binding is an exact locator `<path>:<field>`; a path without a field is not read.
If exactly one id did not resolve — an honest `STATE_READER_SCOPE_UNAVAILABLE`; do not pick the first agent.

### 4.2b. Data protection, if personal data passes through the agent

The masking policy lives **in the agent's cabinet**, not in the Evolution Console: it is bound to
the exact `platform_agent_id`, and one agent can be part of several automations. A second
editor would give a second source of truth.

The rule that matters most here: **a toggle is not protection.** Protection may be shown as enabled
only on confirmation from the local engine — PRE and POST — not by a saved
switch. No confirmation — an honest "unknown", not a look of well-being.

The form and the write gates are produced by the cabinet generator in the `masking_policy` block; the config check is
`tools/check_masking_policy.py`. While there are no platform roles, write "roles are on the way", and
keep moving the key between devices switched off.

### 4.2c. Agent control: the screen renders the contract, not its own list

Changing the behaviour of a live agent goes by one path: **draft → what it will affect → run on
test cases → publish → launch → rollback.** The contract of this path is produced by the cabinet
generator in the `agent_control` block, and the surface must render exactly it.

Why so strict: a screen's own list of operations will inevitably drift from the engine, and
the first thing to fall off will be the publication condition — a "Publish" button without checks will appear. **Publishing
is unavailable until the impact is shown and the run is passed**, and the way back is visible on the screen, not
hidden in a submenu.

The version log is shared with the cabinet. A second log is a guaranteed divergence.

### 4.2c-2. Client agent permissions: the reference cut-down set

A client product agent does its work through ITS OWN experts. It does not need to manage
the account, and permissions must be cut down to that:

| Reference (the "1C Agent" set, verified on a live product) |
|---|
| `rules_list`, `concept_search`, `run_expert`, `check_task`, `get_default_target`, `health_check` |

A product with its own memory gets `kv_get / kv_set / kv_search / kv_list`
and `list_experts / get_expert` added. Anything beyond that — a one-line justification in the agent's passport.

**The main thing is not the length of the list but a blanket allowance.** `sys__all__sys_mcp_extella` is
not a tool but the entire platform MCP server in one line. Verified
live on 05 Aug 2026: "Kazakh Lawyer" had 16 harmless checkboxes in the list, `list_agents`
was NOT among them — and it still called `list_agents_mcp_extella` and returned the exact
ids of the account's agents. So checkboxes next to a blanket allowance restrict
nothing: the client's agent effectively holds both `delete_agent` and `delete_profile`.

Hence the rule: **a client agent must not have `sys__all__` / `sys__server__`**
— otherwise a neat list of permissions is a report for us, not protection for the client.
Check: `tools/check_agent_tools.py` (reads the live account, does not occupy a device).

### 4.2d. The dependency manifest: `MANIFEST.yaml` in the product root

Everything the product expects from the machine is named in ONE file and checked by the installer before
the first action. A dependency not named in advance is checked at the moment it fails at a
colleague's — "no module", "port busy", "no connection with the internet alive" — and costs a day of
blind correspondence (on 03 Aug it cost exactly a day).

```yaml
checks:
  - kind: python
    min_version: "3.10"
    fix_ru: "поставь Python 3.10+"
  - kind: module
    name: "docx"
    level: warn            # without it only the Word export does not work
    fix_ru: "pip3 install python-docx"
```

Kinds: `python` (version), `module` (does it import), `file` / `dir` (does it exist), `port`
(is it FREE), `command` (is it in PATH). `level: warn` — warn and continue;
by default a refusal stops the install.

Three rules, each bought with someone else's pain:
- **Write `fix_ru` as an action**, not a diagnosis: "pip3 install pymupdf", not "no fitz".
- **Set `warn` where the dependency has a fallback path** (the token is read from three
  places; keyring is replaced by file storage). A false install refusal is worse than a hole.
- **Read the manifest with the canonical module** `templates/manifest_check.py`, a copy lies in
  the product root. Its own parser in every product = one stops the install where
  another quietly continues it.

The gate `tools/check_manifest_copies.py` (in the pack's preflight and in `run_all_gates.sh`) watches
three things: the manifest exists, the module matches the canon, the installer **calls** it —
a file next to the installer that nobody runs is the most expensive kind of green checkmark.

### 4.3. Boundaries and an explanation on screen

`limits` — at least one honest line "what this does NOT do". `help_surface` — where the human
will read "how this works". Without them release is forbidden by a gate.

### 4.4. What the window must look like

If your work has an interface, it is part of Extella, not a separate product. Insert the paragraph below
into the generation rules in full: it is self-contained, the storefront repository is not needed for it.

> The interface is part of Extella, not a separate product. Use only these tokens:
> fonts **Nunito** (the whole interface: text, buttons, tabs, fields), **Source Serif 4**
> (headings), **JetBrains Mono** (only section labels and machine text);
> light theme — background #FAF9F5, surfaces #FFFFFF/#F5F3EC, text #0A0A0A, accent #C57E33,
> petrol #2F6B66, borders #D7E0DC; dark — background #0A0A0A, surfaces #141414/#181818,
> text #F5F3EE, accent #D4944A, borders rgba(243,238,229,.09).
> Font sizes only 11 / 13 / 15 / 20 / 26, nothing smaller than 11px; weights 400 / 500 / 600.
> Spacing is a multiple of four: 4 · 8 · 12 · 16 · 24 · 32 · 48, there are no values outside the scale.
> Radii: cards and panels 12, small controls 8, action buttons are pills (999),
> round icon buttons 50%. There are no other radii.
> The mandatory rule `button,input,select,textarea{font-family:inherit}` — without it
> the browser sets buttons in Arial.
> Bronze is only for action, and there is exactly one main action on a screen; petrol is only for the system.
> 1px borders instead of shadows, no gradients, no emoji, no all-caps,
> no full stops in headings, no logo of your own and no theme or language switcher of your own.
> Headings are set in the serif Source Serif 4 without negative letter-spacing — a bold
> sans-serif in a heading is forbidden.
> Take the theme and language from the host messages `etb_theme` and `etb_init` (light = the attribute
> `data-lm` on `<html>`). Texts address the user informally, a button promises exactly what it does,
> every error says what to do next.

The author of the rule is Extella's design owner. **The source of truth since 31 Jul 2026 is `DESIGN_CODE.md`; since 04 Sep 2026 it lies in the root of
this repository (the toolbar repository is closed, tag `toolbar-final-2026-08`).** It is the only one and cancels the former rules: Source Sans 3, radii of 4–6px and
mono all-caps labels are no longer canon. The former documents (`archive/DESIGN_RULE_FOR_APPS.md`,
`archive/UX_CANON.md`) remain as history and are not referenced. `DESIGN_CODE.md` is how
the platform looks; `NO_AI_LOOK.md` is how an app must not look. Both are in the root of
this repository; a ready prompt insert is the section "Prompt insert" in `NO_AI_LOOK.md`.

**Deviation from the canon — only by the design owner's written decision**, not by the taste of whoever is building.
If the needed decision is not in `DESIGN_CODE.md`, there is no decision: first the rule as a pull request into
this file, then the code.

The paragraph above is a copy. Divergence from the source is caught by `tools/check_design_rule.py`: a rule
that lives in two places drifts apart — this is a recurring class of accidents.

How mandatory this is: a colour outside the palette is a defect, not a trifle. On 29 Jul I myself put into a
system card a blue `#3D6FA8` that is not in Extella's palette at all, and noticed it only
when the rule arrived as text.

---

### 4.4b. The card on the storefront: icon, description, tags are part of the product

The owner's decision of 14 Aug 2026: **"icons, description and tags are mandatory, otherwise there will be a mess
later".** The reason is measurable — of our ten listings **four went out without an icon, three without a
description**.

What any product that gets into the store must have:

| | |
|---|---|
| **icon** | 512×512, square, from Extella's palette. Made with the command: `python3 tools/make_icon.py <знак> <путь>` |
| **description** | from 80 characters, answers "what it does and who needs it". Not a repeat of the name |
| **tags** | 2–6 of them, lowercase, hyphenated; one is the product type: `приложение`, `издание`, `агент`, `демо`, `инструмент` (for a product with an English name — English ones: `app`, `edition`, `agent`, `demo`, `tool`; the tag language follows the language of the name) |
| **name** | up to 40 characters, **without a version** ("Доска v2.1" lies within a week) and without service words |

Checked by `tools/check_listing_meta.py`; the deployer calls it **before** the rollout —
an unready card stops the rollout just like a red passport does.

**Why this is not a matter of taste.** The icon is the only thing by which a human finds their window
among twelve. The description is the only thing by which they decide whether to install. Tags are the only thing
by which the store will assemble shelves. With five products the mess is invisible, with fifty it is
irreparable: every card will have to be fixed by hand and after the fact.

**Why a tool and not a requirement.** While the icon was "separate work in an editor",
it was not drawn a single time out of four. A requirement without a tool is not a rule but a
wish that would be more honest not to write down.

---

## 4.5. The shortest path to the product is an SLA, not a wish

The owner's decision of 29 Jul 2026. The rule is mandatory, it has no gate and cannot have one:
"the shortest path" is not measured by a machine, it is held by discipline.

**Sort work by its effect on the product, not by order of arrival.** First what the product
cannot reach people without; then improvements; then hygiene. Permission discrepancies,
an outdated canon, duplicates — record them as facts and carry on, but do not stop the release over them.

**Decide the reversible yourself and say in one line what you decided.** Go to the owner only with the
irreversible, the external or what changes prod behaviour. Every extra question costs a round of
correspondence and does not bring the product closer; the owner's time is the scarcest resource of the loop.

**Batch the questions.** If you do need the owner — collect all of them for the shift into one list,
rather than bringing them one at a time.

**Speed does not justify silence.** What was not done and why — in plain text. Quietly
cut scope is not speed but a debt nobody knows about. This is part of the same SLA.

## 4.7. The product checks itself

**Owner's decision of 19 Aug 2026.** Products are made quickly, and a human checks them —
and that is the most expensive link. We do not stand behind the buyer's shoulder, and there is nobody
to check every product by hand after every edit. So the product itself must
do the checking.

**Requirement: the product has one command that answers "ready" or "not ready
and here is exactly what".**

```bash
python3 app/main.py --selftest
```

Four conditions without which a self-check is useless:

1. **The list of what is checked is taken from the interface, not written by hand.** A measurement
   on 30 Jul 2026 on the Recruiter: the author wrote the list of methods himself, the check was green
   on 26 methods, while the interface called 45. A missing method does not fail — it gives
   an empty screen without a word about an error.
2. **The self-check must be able to fail.** Checked by a machine: the gate makes a
   copy of the product, removes one method that the interface calls, and requires red.
3. **A report in words.** The exit code is for the machine; the human needs "not ready: the interface
   calls methods that do not exist — X, Y".
4. **The same command is available to the buyer** as a "Check installation" button. Then the client
   sends the result, not "it doesn't open for me". What must be checked is PRECISELY
   the installed build: a measurement on 12 Aug 2026 — the installed panel had not a single
   product library, the report did not assemble, yet it looked like "it works".

A sample that passes the gate:

```python
def самопроверка():
    разметка = pathlib.Path("app/panel.html").read_text()
    нужные = set(re.findall(r"api\('([^']+)'\)", разметка))   # the list FROM the interface
    нет = sorted(и for и in нужные if not hasattr(service, и))
    if нет:
        print("НЕ ГОТОВ: интерфейс зовёт методы, которых нет:", ", ".join(нет))
        return 1
    print("ГОТОВ: все методы интерфейса на месте, проверено", len(нужные))
    return 0
```

**The protocol for the store.** The same gate prints the report in the form the
storefront accepts — schema `extella.selfcheck/v1`:

```bash
python3 tools/check_self_check.py --протокол --версия=1.2.0 \
        --артефакт=путь/к/архиву.zip путь/к/продукту
```

The main thing in the protocol is not the word "ready" but `negative_control`: which method was removed and
whether the self-check went red. A green line without a negative control is worth nothing,
and the store marks such a version as "not proven".

`artifact.sha256` is computed over the same file that goes to the store — otherwise one could attach
a green report from an old build to a fresh build. The store recomputes the fingerprint
on intake and rejects a mismatch.

The path on the author's machine does not get into the protocol: the command is printed relative, because
the home directory is a person's name, and the buyer sees the protocol.

**Checked by a machine:** `tools/check_self_check.py`. It finds the entry point, runs it
on the intact product, then on a spoiled copy, and compares. The gate looks not for the quality of the
product but for the honesty of its self-check.

**What this does not close:** live calls to third-party services without keys, and what
the eye sees. You cannot take a screenshot in the OS sandbox, so acceptance by eye remains.

**Measurement on 19 Aug 2026:** the Recruiter passes — its self-check reads the list from
`app.html` and catches a missing method. The Composio connectors product has no self-check
at all.

## 4.4c. Waiting is visible: a button that stays silent is a defect

**Owner's decision of 18 Aug 2026.** A click launches an expert. The core answers in 1.7
seconds, an expert in 13, a call from the page to the device in 13–17. All this time
the human looks at an unchanged screen. They do not read the logs and cannot know that
work is going on: they click a second time, then a third, then decide the product is broken.

A second click is not only nerves. It goes to the platform and does the work twice:
a second email, a second parse, a second charge.

**Rule: for any action that goes beyond the page, the state is visible
immediately, repetition is blocked, and the end is named in words.**

| response time | what the human must see |
|---|---|
| under 1 second | nothing special is needed |
| 1–10 seconds | the button is disabled and marked as waiting, in the same frame |
| longer than 10 seconds | plus words saying what exactly is happening: "The agent is reading the database…" |
| the end | a result or a refusal in words; the button returns to work |

Four mandatory conditions:

1. **The state switches on BEFORE the call**, not after the answer. Switched on after — that is
   nothing: the human has already clicked a second time.
2. **Repetition is blocked** while the action is running. The button is disabled, not just
   recoloured.
3. **There is a `finally`.** Without it the very first error will leave the button disabled forever,
   and the product will die silently — worse than if it had crashed loudly.
4. **A spinner without a caption is forbidden after ten seconds.** Nameless spinning
   is indistinguishable from a hang, and the human will reload the window anyway.

A ready helper, so that this is not rewritten in every app anew:

```js
// The one place where waiting lives. The button is disabled before the call and always
// returns to work — both after success and after refusal.
async function сОжиданием(кнопка, подпись, действие) {
  const было = кнопка.textContent;
  кнопка.disabled = true;
  кнопка.textContent = подпись;             // "Saving…", "The agent is reading the database…"
  try {
    return await действие();
  } finally {
    кнопка.disabled = false;
    кнопка.textContent = было;
  }
}
```

**Checked by a machine:** `tools/check_waiting_state.py`. It reads the functions that
go to the platform and requires all four conditions. It does not touch the shared request
transport: it has no screen; the state is shown by whoever has the button. A background
task that nobody waits for is exempted by the line `// ожидание: фоновая задача`
above the function.

**Measurement on our own product on 18 Aug 2026:** the Recruiter panel — 54 mute actions,
including saving the API key. The very place where a human most often clicks
twice.

## 4.5c. Cyrillic lives in texts, Latin in identifiers

We write code in Russian, and this is a deliberate choice: comments, messages, function
names in Python — the team reads them faster. But there are four places where Cyrillic
breaks SILENTLY, and in a single day, 20 Aug 2026, five runs crashed against these places:

| place | what happens |
|---|---|
| bash variable names | the shell does not substitute the value; the heredoc breaks, the file comes out EMPTY, and the commit declares it exists |
| URL paths | the browser percent-encodes, the server compares with the unencoded — they never match; a 404 goes into the window |
| platform identifiers | the agent's name is cut: "Рекрутёр" turned into an empty one (D3) |
| bash string literals with `$` | "$Р" is read as a substitution — the icon landed in a folder literally named `$Р` |

Rule: **texts and comments — in Russian; bash variables, URL paths,
platform identifiers and everything a machine reads without decoding —
in Latin.** Cyrillic Python names work and stay.

This is not style but a class of silent breakages: none of the four places answers
with an error — they simply do the wrong thing.

## 4.6b. Check what the human sees, not the links of the chain

**An expensive lesson of 15–16 Aug 2026.** I reported to the owner: "window ✓ program ✓ service ✓".
Every checkmark was true: HTTP 200, files on disk, the service up. The owner opened
the windows and saw an English error in one, a blank sheet in the second and a useless dashboard in
the third. **The report was true about every link and false about the whole.**

Rule: **acceptance is what the human sees on the screen, and the result of their scenario.**

| what was checked | what should have been |
|---|---|
| the page is served, 200 | the page OPENED and has content on it |
| the app's files are on disk | the app drew its interface |
| the service is up | the scenario passed in full: drew → closed → opened → still there |
| the expert returned `готово: true` | from the window you can do what it exists for |

Three consequences, each cost hours:

* **`load` on a frame does not mean "loaded".** With a dead server the browser shows
  its own error page inside and reports success;
* **silence is not "probably everything is fine".** If a probe did not answer, that is a refusal. Our
  first probe was silent because it was not running, and the window believed everything was fine;
* **compare what is served with what is live.** `curl` showed our edit, the browser held an old
  copy from the cache — an hour went into looking for the cause in the wrong place.

A quick technique: **reproduce the hostile environment on your side.** The OS window gives the app
a foreign page without storage — a local frame with
`sandbox="allow-scripts"` gives exactly the same. One file of ten lines, and the behaviour is visible in a minute,
not after the owner's complaint.

## 4.6. Found a systemic error — you must record it

A rule and a GATE at the same time (`tools/check_findings_log.py`).

While building an agent you almost always find other people's defects: an outdated canon, diverged
copies, permissions wider than declared, a gate that lies. Walking past silently means leaving
it to the next one, and they will spend the same hours again. In one day, 29 Jul, the following were found this way: a canon
that called an agent with 45 tools "a model of cut-down permissions"; a mandatory privacy
test that lived in scratchpad and was lost; two tests that pinned down a violation of the canon
instead of the canon.

**Format.** Next to the build lies `evidence/findings.yaml` — a list of findings, each with
the fields `what`, `where`, `impact`, `severity` (`blocker` | `major` | `minor`).

**An empty list is valid and mandatory.** That is precisely the point of the gate: no file means
nobody looked; a file with `findings: []` means someone looked and found nothing. Zero and "we do not
know" are different things, and the product must distinguish them.

## 5. The cycle: built → checked → fixed

```
python3 tools/check_agent_passport.py мой_агент.yaml          # agent passport
python3 tools/check_automation_passport.py мой_паспорт.yaml   # automation passport
python3 tools/check_state_contract.py http://127.0.0.1:PORT/api/state
python3 tools/check_brand_copy.py <файлы интерфейса>
python3 tools/check_code_canon.py <каталоги с кодом>       # canon in the code, not in the passport
python3 tools/check_masking_policy.py политика.json        # data protection, if personal data passes through the agent
```

Each has `--json` (stable `code`, `severity`, `path`, messages in two languages) and
`--selftest`. Read `code`, do not parse the text.

Did not pass — fix it and run again. This is your cycle, there is no human in it.

---

## 5a. Rewrote something that already worked — compare with the old, not with the expectation

The owner's rule of 30 Jul 2026, written down after we got burned by it twice in one evening.

When you move, merge or rewrite a working piece — an installer,
an expert, a wrapper — "the new one started" proves NOTHING. There is only one proof:
**the behaviour of the new matched the behaviour of the old**. Compare the result, not the feeling:
the same file, the same card, the same launch, the same saved data.

A live case. Five plugin installers were merged into one. The new one installed, the cards were written,
everything looked right. A line-by-line comparison with the old ones showed two defects that no
launch check had seen:

- each plugin had **its own cleanup policy** (one keeps `.venv`, another `.state`,
  a third `data`, two do not clean at all). A common policy would have wiped the client's state;
- each had **its own launch command**. A common command would not have brought up two plugins out of five.

Neither defect would have shown up in a sandbox: the folder is empty, the ports are taken by working copies.
Therefore: **first write down what the old one does, then check what the new one does.** A divergence
is explained in words or fixed — but it does not remain unexplained.

The second consequence of the same evening: **code that arrives over the network is checked for
integrity.** If your agent or its installer downloads something, what is downloaded must
have a declared checksum, and on a mismatch the install must stop.
Silently installing "almost the same" code is worse than not installing at all: it will break later and not at
your place.

---

## 5b. The method of working with a large artifact (from the build for the telecom operator, 13 Aug 2026)

Sent by the telecom operator's platform builder chat as a distillation of **how the work was actually done**
on a 16 MB artifact. Below is only what was not in the standards; the rest is mapped
in a table to already existing rules, so that two phrasings of the same thing do not appear (as
once happened with the palette).

**The principle above everything — it comes first not for the sake of beauty:**

> **Every statement about the state of the system must be confirmed by reading that
> state, not by memory of a past action.**

The author says this rule solved half the mysteries of the build: "someone else's desktop",
a phantom version, an "unchanged" median. Verified on this side too: in one day it
caught three of my own false conclusions — "there are no purchases" (there were), "scope is indistinguishable"
(distinguishable), "the storefront belongs to the token" (no longer). Each time the cause was a reference to
yesterday's measurement instead of a new read.


### §5c. Reusability of experts: layered reuse (measured 20 Aug 2026)

A device skill is reused in three layers, and only the thinnest one needs to be copied:

1. **The device tool** — the implementation of the skill (example: `tools/на_доску.py` + a dictionary of five
   shapes). One per device, zero changes when a new consumer is connected.
2. **The wrapper expert** — ~20 lines of "take the parameters → call the tool". Expert scopes
   are isolated per-agent — that is hygiene, not an obstacle: each agent gets ITS OWN copy
   of the wrapper with ITS OWN default source (the label `ext_<источник>_` keeps agents from overwriting
   each other's drawings).
3. **A rule for the agent** — when to call the expert and with which parameters. From the UX it looks like
   a native capability of the agent: "put … on the board" — and the artifact appears in the app.

**Measurement.** On 20 Aug 2026 the board tool (written for Evolution Console · Lab) was connected in one go
to four agents: CSO · the telecom operator (`cso_board_push`), the main chat
(`board_push`), Recruiter (`rec_board_push`), 1C Agent (`onec_board_push`). Changes in
the tool — 0 lines; the wrapper — 20 lines per agent; drawings from four sources live on
one board without conflicts. The formula: **N apps + M agents, not N×M integrations.**

Two mandatory details from the same measurement: (a) the wrapper needs a `def` — the expert/save validator
will not pass a nohup-style one without def; (b) the skill lives on a specific device — in the agent's rule
pin `targets=["<device_id>"]`, otherwise default routing will send the launch to the VPS,
where the tool is absent ("Target unavailable" then speaks of target_id — what goes into `targets`
is precisely the device_id).

### An edit = a migration script, not editing a file

The artifact is not edited by hand. Every change is a separate script in git with a number, a date,
**the customer's decision in the docstring** and replacement anchors. The file can be lost or rebuilt —
the migration log restores it from any state.

Why this is not bureaucracy: an edit by hand leaves no answer to the question "why is it 81 here
and not 78". In a month the client will ask this question.

### An anchor is unique — or a refusal

A text replacement is performed **only when there is exactly one occurrence**. "18 occurrences" means
stop and rework the anchor, not "I'll replace the first".

> A silent replacement in the wrong place is worse than a crashed script: the script is visible at once, while a wrong
> replacement shows up a week later at the client.

A ready implementation: **`templates/safe_edit.py`** — backup, uniqueness check, replacement,
verification after writing, rollback on failure. It deliberately does not accept regular expressions: a regex
hides the ambiguity that caused the rule to appear. The self-check has been tested for
failure.

### After every edit — an invariants gate

The artifact has a machine integrity check, and it is run **after every edit**:
tag balance, navigation order, integrity of internal links, validity of embedded
JSON. An edit without a green gate does not count as done.

An example from the telecom-demo build: the storefront gate — div balance, tab order equal to navigation,
881 "figure → dialogue" links with none broken.

### The build is deterministic and reproducible

Generators run from a fixed seed and give byte-for-byte identical output.
A published artifact can be restored with one command from git, and the check is a rebuild and a
comparison of hashes with the published one. Without this, "it built differently for me" can be neither
confirmed nor refuted.

**Determinism of content is not yet determinism of the artifact.** The author of the rule
checked it at our request and found a divergence in his own work: 94 files matched file by file, while the
zip archives of two runs diverged (`5ddfce19…` versus `e7e69ce3…`). Containers carry
timestamps. After the timestamp was fixed to a constant, two independent runs gave one hash:

```
845e4033ade7b96ebb2ca57a7f46e0a9c6fe4b565fac7e4ad1cd028b566fa10d  демо аналитики обращений, прогон 3
845e4033ade7b96ebb2ca57a7f46e0a9c6fe4b565fac7e4ad1cd028b566fa10d  демо аналитики обращений, прогон 4
d05b627f2e6fab1de332f7f79f961cd27d20f87497f1bf5c87320485555eb150  телеком-бандл, прогон 1
d05b627f2e6fab1de332f7f79f961cd27d20f87497f1bf5c87320485555eb150  телеком-бандл, прогон 2
```

**A clarification of the mechanics — measured on our side on 13 Aug 2026, because the phrasing
"zipfile writes the current time" leads the wrong way.** Python takes the timestamp **from the source file**,
not from the clock, so not every build breaks:

| How we write | Two runs | Why |
|---|---|---|
| `z.write(файл, имя)` with unchanged sources | **match** | the timestamp is taken from the file's `mtime` |
| `z.writestr("имя", данные)` | **diverge** | a new entry's timestamp = now |
| `z.write()` over a **re-created** file | **diverge** | the generator updated `mtime` |
| `ZipInfo(date_time=константа)` | **match** always | the timestamp depends neither on the clock nor on the files |

The practical conclusion: our own archive builder for the Recruiter turned out to be reproducible
(`ee911fae…` twice) — but **by lucky accident**, because it packs unchanged files
from disk. Add generation of even one file to it — and reproducibility will vanish
silently. That is why the timestamp is fixed in advance, not after things have diverged.

A ready implementation: **`templates/det_zip.py`** — a fixed timestamp, fixed permissions,
sorted write order, refusal on an incomplete build.

**And a separate finding about the checks themselves, from the same pass.** The first version of the
`det_zip` self-check proved "two runs gave one hash" — and **passed even with the timestamp fixing
removed**: for a `ZipInfo` without a date the default is also a constant (the year 1980). A repeatability check
does not check the fixing.

The cure is to check **the property, not the consequence**: re-read the archive and make sure that every
entry's timestamp equals the given one, and its permissions equal the given ones. After that both deliberate breakages fail:
removed the timestamp — "timestamp (1980,1,1), not (2026,1,1)"; removed the permissions — "permissions 0o600".

A second detail from the same place: the control check "a naive build diverges" was flaky, because
**DOS time in zip is a multiple of two seconds**, while the pause was 1.1 s. Two builds landed on the same
timestamp, and the check sometimes "proved" the opposite.

### The rest is already in the standards — do not rewrite it

| Rule of the method | Where it lives | Do not set up a second time |
|---|---|---|
| "Done" = "checked that it is done" | the principle above + "a reconciliation can fail" (`DEPLOY_REQUIREMENTS`, H5-quater) | ✅ |
| Diagnosis before action | §5a "compare with the old, not with the expectation" | ✅ |
| Customer data — inside the customer's perimeter | stop rule 2 (`BUILD_STAGES`) + gate `check_masking_policy` | ✅ |
| Reversibility always | stop rule 4 + versions instead of overwriting (H8, H10) | ✅ |
| a platform refusal — straight into the canon | §4.6 and gate `check_findings_log` | ✅ |
| Acceptance by facts, a report without smoothing | the report "closed / not mine / honestly not closed" (`PROMPT_UPDATE_AGENT`) | ✅ |

### Why in the end this is about speed, not neatness

The telecom operator's builder chat — the fastest of ours at deploying — answered the question "what is the secret" like this,
and the answer deserves a place in the method:

> **The one who deploys fast is not the one who deploys fast, but the one who, between "changed" and "deployed",
> has not a single manual step, not a single unrecorded piece of knowledge and not a single risk
> unchecked by automation.**

Broken down into five components, each a direct consequence of the rules above:

1. **A rollout is code, not actions.** There is no step "go into the interface and click": build,
   publication, reinstall — scripts. What is done by hand goes at the speed of hands.
2. **One reference, three surfaces.** Not three products, but one reference folder from which
   the derivatives are produced by pipelines. Slow teams make one edit three times.
3. **Refusals are paid for once.** Every pitfall is recorded in the canon **on the day of the failure** — that is why
   the calls are right the first time. Speed today is the discipline of recording yesterday.
4. **Gates instead of manual checking.** Not a hundred pages by eye, but seconds of machine checks.
   Confidence from automation is exactly time.
5. **Absence of fear.** A backup, versions instead of overwriting, a one-step rollback, a reproducible
   build. When you cannot break something irreversibly, "let's re-check everything once more just
   in case" falls away — and that is exactly where teams lose hours.

**The first assembly of the pipeline costs a day. Each subsequent rollout — minutes.** Teams that
"do it quickly by hand" win the first day and lose all the others.

### The cycle of one iteration

```
reconnaissance (what is actually there)
  → a migration script with unique anchors
  → the invariants gate
  → a live check of the result (render / click / request against prod)
  → the leak gate, if the surface is public
  → a commit with a trail
  → acceptance by checklist + an honest report
```

---

## 6. Anti-patterns — your work will be turned back for these

- one giant prompt instead of an architecture;
- "full access to everything" for the sake of convenience;
- an LLM where there is code;
- "success" on partial execution;
- quiet self-modification of a production system;
- a token in the interface, in an iframe or in the model;
- personal data and keys in knowledge (Concepts);
- a capability available only from a hidden chat command;
- a demonstration of a possibility without a working user path;
- a change to a shared handler without a run of the whole class;
- a second route map next to the one that already exists in the product;
- "fixed" by the code, without proving that the app shows precisely this file;
- **a check that does real work**: a run with an "empty body" is not safe
  everywhere — a route that sends outward or creates entities will do it even from
  an empty body. Such routes are verified only on REFUSALS (a foreign Origin, a wrong
  identifier), and the successful path on a test perimeter. On 04 Aug my own probe
  sent two messages to Telegram and created five agents on a live account;
- **comparing two versions without checking that both are alive**: twice in a day a "match"
  meant that both servers had not come up or a foreign process was answering on the port.
  Before comparing — make sure the port is free and that it is precisely your code answering.

---

## 7. References — read them only if you need them

This guide is self-contained. Below is what is loaded as needed, not always:

| File | When it is needed |
|---|---|
| `AGENT_CABINET_STANDARD.md` | you are making an automation of several agents or a cabinet |
| `EXTELLA_AI_ONBOARDING.md` | you need details of how the platform works and its traps |
| `BRAND_FOR_AGENTS.md` | you are writing interface texts |
| `NAMING.md` | you are unsure what to call a part of the system |
| `EVOLUTION_PHILOSOPHY.md` | you need to make a decision that is not described here |
| `AGENT_ARCHITECTURE.md` | you need the full phrasing of a principle with all its caveats |
| `CHANGELOG.md` | you need to understand why a rule is exactly the way it is |

---

## 8. What the standard deliberately does not require

So that you do not invent things. On 28 Jul 2026, 30 fields out of 66 were removed from the passports: eight had never been read by anyone
ever, the rest became optional.

The standard **does not require**: execution budgets (the runtime does not apply them), an on-call person and a success metric
(the agent is built by a machine — assigning a human on its behalf is an invention), input and output schemas,
data classification, an evidence schema, a retention policy.

The criterion by which a field stays in the passport: **the product reads it OR a gate stands on it
that has already caught a live breakage.** Everything else is a waste of your context and a reason to write
an untruth.
