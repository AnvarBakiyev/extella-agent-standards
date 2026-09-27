<!-- source: BUILD_STAGES.md sha256:d77dca70e57c8f369aa8a384a78f0154df3e398ec4d62bd913ad2fa0521f849e -->

# Build stages: build → prod

This document answers one question: **how many checks apply right now.**
It outranks the scope of requirements set by the other documents: if a guide requires
a passport, but the build is running without someone else's machine — no passport is needed.

The machine-readable source is `stages.yaml`; query it like this:

```
python3 tools/stage_gates.py --stage build --json
```

Stages must not be recited from memory: the checker determines scope, not the text.

---

## There are two stages (the owner's decision, 12 Aug 2026)

The first edition had three stages — demo, pilot, prod. Discussion with the owner showed
that the demo/pilot boundary was artificial: the client already hands over their data for
the demo, and that's a normal sales scenario, not a violation. The real jumps in the cost of
error are not labels — they are **facts**.

| | **Build** (`build`) | **Prod** (`prod`) |
|---|---|---|
| What's happening | from the first line of code to a working thing at the client's | the product goes out to any buyer |
| Cost of error | awkwardness, fixable on the spot | mass-scale and financial: the money is already charged before a bad install shows up |
| Baseline gates | **2** | 21 |
| Time frame | hours–days | weeks |

The old names `demo` and `pilot` are synonyms for `build`: handoffs and preflight written
before the merge keep working.

### The build stage: baseline gates (2) + additions triggered by facts

The baseline is what the demo itself would fail without:

* `check_code_canon` — the platform canon in code: scopes, `X-Agent-Id`, duplicate names.
  Break it, and the product starts up non-deterministically — and that happens right in
  front of the client.
* `check_ui_api_contract` — the interface and the server agree on the same thing. A mismatch
  looks like dead buttons — the most expensive defect in a demo.

From there, additions are triggered by **facts, not by a label**. A fact gets checked; a
label is an opinion.

| Fact | What gets added | Why |
|---|---|---|
| **Client data has shown up** | `check_masking_policy`; tasks are pinned to a device (`targets` as an array) | we once had candidate résumés get sorted through on someone else's Mac |
| **The product landed on someone else's machine** | passport, `check_agent_tools`, the state contract, wrapper-canon and first-screen copies; an honest installer exit code | you can't fix someone else's machine by hand once it breaks |

Deliberately **not required during build**: the manifest, card classes, the registry, the
cabinet, the brand and design gates, the single source of truth, the findings log, drift,
observability, cost limits, an operations owner, failure-path tests.

### Prod: the full set

The product is sold to anyone. An error multiplies, and the buyer is charged after
installation — "it installed crooked" means money. The full set applies — the exact number
is given by `python3 tools/stage_gates.py --stage prod`, and it is not written down here: on
25 Sep 2026 this said "21 gates" while the actual count was 25. Including the
`DEPLOY_REQUIREMENTS.md` sections that apply to the product type, and the release preflight.

**Manual acceptance item for the interface (Ella's rule against the AI look):** fonts are
ours (Nunito / Source Serif 4 / JetBrains Mono, plus
`button,input,select,textarea{font-family:inherit}`), checked in the inspector on a heading,
a button and a field. The product picks its own palette and character; what stays shared is
the fonts and the composition. The full rule is `NO_AI_LOOK.md`.

---

## The second multiplier: product type

A page-type product (interface via the `page` field, runs in a sandbox on the Extella web)
has no archive, no installer, no local service — entire sections of the requirements don't
apply to it, regardless of stage. A device-type product (archive + installer, runs on the
machine) applies all of them.

**Amendment, 12 Aug 2026 (evening): this isn't a choice between two.** One listing version
carries `archive`, `page` and `icon` as three separate fields, so **hybrid is a standard
type**: data and keys on the machine, the interface from the OS, and between them an expert
call that runs on the device. The type determines **where the data lives**, not which
delivery channel to pick.

The applicability table is in `DEPLOY_REQUIREMENTS.md`, "Product type decides scope" and
section H (H10 — hybrid, H12 — app rights).

**Order of reasoning: type first (what applies at all), then stage and facts (how much of
what applies is needed right now).**

---

## The agent lives one life — there's no freeze

the owner's decision, 12 Aug 2026: there is no such thing as a "demo agent" and a "prod agent"
as two different creatures. An agent is born during build and grows up into prod without
changing identity. The old rule "prod agents are frozen" is repealed and replaced with:

> **You can always change your own agent — but with a trace and a way back.** The
> instructions live as a file in the repository and get flashed in whole; every change has a
> version and the option to roll back. What's forbidden isn't change — it's change that
> leaves no trace.

Separately, and just as strictly as before: **don't touch what belongs to someone else and
is live** — agents, experts and data that other people use (colleagues, other products,
other clients) don't get changed during a build. Need an object — create your own, in your
own scope.

---

## Stop rules: apply at every stage

Fast doesn't mean "anything goes." These six rules are cheap, and breaking exactly them is
what makes a fast build dangerous. Edited 12 Aug 2026:

1. **External writes are drafts only.** The agent prepares letters, payments, publications;
   a human sends them.
2. **Client data stays inside the client's boundary.** During a demo and during build, it's
   fine: the client hands it over themselves. It must not be carried out of that boundary:
   into the platform's cloud, into the storefront archive (it ships to any buyer), into
   global scopes, into a demo for another client. Leaving the machine is allowed only with
   masking.
3. **No destructive rights, and request the minimum.** No `delete_*` on a client agent
   without a written reason: the platform copies the source's tools, and we've already had a
   product ship that could delete the buyer's agent. Since 12 Aug 2026 this rule has a second
   half, visible to the client: a storefront product declares **app rights** (`app_scopes`),
   and the buyer reads them before purchase. Asking for `*.write` "just in case" isn't a small
   thing — it's a reason not to buy. And the flip side: rights **can be revoked at any
   moment**, so a denied right is a normal product state, not an outage (see rule 6).
4. **Don't touch what belongs to someone else and is live.** Your own agent evolves with a
   trace and a rollback; other people's objects don't get changed at all.
5. **Secrets don't travel.** The archive ships to the buyer whole; the page bundle's assets
   are public.
6. **A refusal is visible in words.** A blank screen is a defect at any stage.

Breaking a stop rule isn't "a stage left unfinished" — it's a defect: it gets rolled back at
any stage.

---

## Rights over platform objects: your own namespace is free rein

the owner's decision, 12 Aug 2026, born of irritation at "permit writing an expert, permit
deleting one": an expert is a disposable entity — created fast, reused, deleted without
regret.

* **Inside your own namespace** (experts, rules, concepts, KV of your own scope) — create,
  change and delete **without asking a human**.
* **Outside your own namespace** — deletion needs confirmation, always. Not out of
  politeness: half the records in the account have no `id`, and there are duplicate names —
  deleting "someone else's, by name" once wiped out the wrong copy.

---

## Finishing a build: the chat carries it to pre-release, a human decides on going public

**Edited 13 Aug 2026. The previous paragraph is repealed — it cost a colleague their
deploy.**

There used to be a norm here: "the output of a build is a finished file plus instructions
on what to click; a human uploads it." The basis was "publishing through the API is where
chats stumble." That's out of date: on 12–13 Aug, chats published Recruiter, Guide and
Predictive Sales through the API, and the stumbling stopped. But the wording stayed and
acted as a ban: a chat refused to deploy and offered to **walk the owner through the form
click by click**, field by field.

The rule in force:

> **The chat carries a new listing to pre-release itself, over the API** — `publish-stream`,
> rights, buying a copy for itself, a first run on a clean state. A pre-release with
> `published=0` is visible only to its author: nothing in it is irreversible.
>
> **There are two public actions:** `POST /api/listing/{lid}/publish {"published": true}` for
> a new listing, and `add-version-stream` for one that's already published.
>
> **Publishing is reversible (verified 16 Aug 2026):** the same address with
> `{"published": false}` takes the product off the storefront; the tool is
> `tools/set_published.py`. The line here isn't about irreversibility, it's about being
> public: the action is visible to everyone, so it's the owner's call. The only permanent
> action is `DELETE /api/listing/{id}` — it tears down the listing and all its versions. Both
> are done by a human, or by the chat after the human's own, separate, explicit decision.
> `edit-version` changes a version that's already public and follows the same line.
>
> **Amendment, 14 Aug 2026 (H20):** for a product that's already published, there is no
> separate publishing step for a version — `published` belongs to the listing, and **every
> version added becomes visible to everyone immediately**. Check before adding: read the
> listing's `published` value. A one there means it needs the owner's go-ahead: the new
> version will go public immediately.

Why exactly this way: for us, deploy is **code**, not a set of manual actions (§5b
`AGENT_BUILD_GUIDE`). What gets done by hand moves at hand speed. Walking a human through a
form isn't caution — it's pushing the work onto the owner.

A file at the named location is still needed — but as the **result**, not as the delivery
method.

---

## Rules of conduct for the builder chat (calibrated on live sessions, 12 Aug 2026)

Every rule was paid for by a specific session — this isn't theory.

1. **An update is a change in behavior, not the production of documents.** Don't start new
   contract files, "just-in-case" manifests, or release wrapper code; a gap that would
   require a new artifact is a line in the report to the owner.
   (Console session: a whole shift went into a PRODUCT_CONTRACT for a component that didn't
   need one.)
2. **Work happens in the working copy; the result is a branch in origin.** A temporary clone
   with a local commit equals lost work: /tmp gets reaped.
3. **Chats don't drive the live Extella interface.** Creating an agent in the UI is a human
   action; clicking around in the owner's open app is off-limits even with good intentions.

   > ⚠️ **This rule is about CLICKS, not about deploy. Amendment 13 Aug 2026.** It has already
   > been misread twice as "a chat can't publish at all" — and a colleague was left without a
   > deploy while the chat offered to walk her through the form by hand. Read it like this:
   >
   > * **a new listing as a pre-release is ordinary chat work and is done over the API**. A
   >   pre-release with `published=0` is visible only to the author, nothing irreversible
   >   happens, no permission is needed;
   > * **`add-version-stream` on an already-published listing is a public action**: a live,
   >   anonymous re-check on 14 Aug 2026 saw the new version immediately. It needs a separate,
   >   explicit choice from the owner before the call, the same as before Publish;
   > * **there are two public actions** — Publish of a new listing, and add-version of an
   >   already-published one. Both are done by a human, or by the chat after the human's own,
   >   separate, explicit decision;
   > * **walking a human through a form by clicking isn't deploy — it's an imitation of
   >   deploy.** For us, deploy is code: what gets done by hand moves at hand speed (§5b
   >   AGENT_BUILD_GUIDE).
   >
   > A chat refusing to deploy by citing this item is a misreading of the standard, not
   > caution.
4. **Canonical shared modules** (`platform_client`, the agent-picker screen) get changed in
   the canon and then spread to copies by sync. Patching your own copy in place is a
   divergence that will surface when the platform fails.
5. **Deletion in a shared scope, even one the owner approved, needs two checks:** consumers
   BEFORE (grep across repositories and cards for who calls these names) and a smoke test of
   consumers AFTER. "One record, no duplicates" does not equal "nobody's using it."
6. **A verification check must be able to fail.** A re-check that's always green masks
   discrepancies — test it on a live object (break one field on purpose and make sure it
   catches it). A real case: the check was reading the field `code`, while the platform
   returns `expert_code` — the "check" wasn't checking anything.
7. **Report format is three parts: "closed / not mine / not closed, honestly."**
   Account-level gates (drift, the agent registry, other people's cards) aren't yours: name
   them and hand them to the integrator. The list of actions only a human can take goes in a
   separate file, OWNER_TASKS.md, with exact steps.
8. **An agent is born over-privileged.** A freshly created agent gets dozens of tools
   including `sys__all__` and `delete_agent` — narrowing its rights down to the minimum is a
   mandatory first step after creation, not an option (three real cases).

## Build order: agent first, interface on top (decision, 12 Aug 2026)

The rule came out of the 1C Agent session and was adopted by the owner as canon — it
noticeably speeds up the work and removes a whole class of dead ends.

**Build the capability through the agent and its experts; bolt the interface on top once the
capability already works.** Not the other way around.

Why this is faster, not just "more correct":

* **The capability can be verified without an interface.** A live call to the agent proves it
  works right away; proving the same thing through an interface means building the interface
  first.
* **The surface changes more often than the capability.** While the platform keeps refining
  windows, pages and bridges, a working capability survives any change of surface without a
  rewrite. The 1C session showed the cost of the reverse order: a chat nearly rewrote a
  working interface to fit a surface that couldn't call experts.
* **Fewer fragile components.** An interface built before the capability drags in relay
  servers and bridges "just to call it somehow" — and they stay forever.

In practice:

1. **Capability**: an expert (or a class handler) plus the agent role as a file in the
   repository.
2. **A live run through the agent** — proof that the thing works.
3. **Only now, the surface**: a thin panel, a card, a page — matching the delivery type
   (`DEPLOY_REQUIREMENTS.md`).
4. Keep the old surface, if there was one, **as a fallback**, until the new one is proven by a
   live scenario — don't switch it off ahead of time.

A dispatcher on top of the experts is welcome: the agent passes the operation's name
(`system.health`), and the dispatcher itself queues it on the device and returns the result.
One agent — one dispatcher expert — one point on the device: that way the surface changes
without touching the capability.

---

## Scope grows with scale, not with who you are (decision, 12 Aug 2026)

The standard doesn't split into "for us" and "for outside developers." A client can have
more agents and products than we do — and then they need MORE checks, not fewer. Splitting
by user type is wrong; the split has to be by a checkable fact of scale.

**The core is for everyone.** The platform canon, the stop rules, acceptance before
publishing, the "capability first" order, honest verification, narrow rights. This applies
to anyone handing a product to a buyer: the platform's physics and the cost of error are the
same for everyone.

**Scale wrapper — triggered by fact.** Some gates compare products **against each other**:
wrapper-canon copies, first-screen copies, manifest copies, the card-class registry, drift
across all agents, the capability registry, the cabinet. In the singular, these aren't
"simpler" — they're **meaningless**: copies have nothing to diverge from, a registry has
nothing to collect.

| Fact of scale | What kicks in |
|---|---|
| More than one product | canon-copy verification, first-screen copies, manifests |
| More than one agent on the account | passport drift, the agent registry |
| A team has formed (several authors) | a single source of truth for rules, a findings log, a team protocol |
| The product goes out to many | everything above, plus the release chain |

It's the same principle as with stages: **a fact gets checked, a label is an opinion.**

---

## Delivery channel: the toolbar is going away, the OS remains (decision, 12 Aug 2026)

The canonical distribution channel is the **Extella OS store**. The toolbar and its plugins
are a **sunsetting** channel: products living as plugin cards are still supported, but new
ones aren't built that way, and the standard no longer relies on them.

Practical consequences, already built into the checkers:

* the product's interface is declared by **the product itself** (`ui:` in the passport —
  file and port), not by a plugin card; the card remains an optional, fallback source;
* the card catalog is set by `EXTELLA_CARDS_DIR`, and its absence is not a check failure;
* an "embedded component" as a delivery channel means "inside another product"; today that's
  the toolbar, and the category disappears along with it. **Anything living inside the
  toolbar must get a plan to move to the storefront** — otherwise it will be left with no
  delivery channel at all.

**Inventory, 12 Aug 2026** — what lives inside the toolbar today and where it's moving:

| What | What it actually is | Where to |
|---|---|---|
| `evolution-console.html`, 516 KB | the **product** "Agent Management" | a page-type storefront product: fits within the 3 MB limit |
| `profit-growth.json` | the **manifest of the same product**, under a historical name (`name: Evolution Console`, `ui.htmlFile: evolution-console.html`) | moves together with it; renaming requires edits to `registry.js`, `router.js`, and a test |
| `profit-growth.html`, 234 KB | **not wired to anything**: no manifest references it. By its headers, a prototype of a managed rule-change flow | owner's call: finish it or delete it |

The product holds onto the host through just a handful of messaging channels: swapping the
transport for `POST /api/app-agent/run` with `{{app_token}}` doesn't touch either the screens
or the scenarios.

> **How to read this inventory.** The first version of this table (12 Aug) counted two
> products here — because it counted FILES instead of reading manifests. In our case, the
> file name doesn't match the product name in three cases out of three. Same rule as with
> deleting records: **count entities, not text.**

---

## A gate has no right to depend on someone else's folder (14 Aug 2026)

Found during a live run: the gate `store_product_expert` fails with a traceback, because it
looks for a file at an **absolute path outside the repository** — in the working copy of
whoever wrote it. It's green for the author, red for everyone else, and the reason isn't
readable: instead of an explanation, you get a stack trace.

> **Rule: a gate operates from the repository root and nothing else.** If an external source
> is needed, it either lives in the repository, or the gate honestly says "no source, nothing
> to check" in one line, instead of crashing.

A check that's green only on one machine is worse than no check at all: it creates false
confidence for the author and noise for everyone else.

## Debts of the standards themselves (owner: the integrator)

* ~~`check_ui_api_contract` doesn't handle host-injected pages~~ — **closed 14 Aug 2026**.
  The gate learned to read the page's contract with the host: which actions it sends and
  which of them the adapter serves. On the live Console it immediately found the cause of a
  day-long loop — **the page calls 14 actions, the adapter serves 2**. Along with that, the
  gate got a real self-check: the old one was being skipped and exiting zero, meaning it
  could never fail.
* ~~Palette split~~ — **closed 14 Aug 2026 by measurement**. The mismatch turned out to be
  exactly **eight colors**: `141414 1E1E1E C9C3B8 D7E0DC EFECE2 F5F3EC FAF9F5 FFFFFF` were in
  the design rule and missing from the gate's palette, so an app built **correctly** would
  fail on them. The tokens were added to `check_brand_copy` as an explicit `APP_UI` block
  naming the source: the brandbook describes marketing surfaces, `DESIGN_RULE_FOR_APPS.md`
  describes program interfaces, and it takes precedence for those (as of 4 Sep 2026 —
  `DESIGN_CODE.md` at the root of this repository; the previous file sits in `archive/` as
  history).
* ~~App rights live in a decision, not in a gate~~ — **closed 14 Aug 2026**:
  `tools/check_app_scopes.py` derives the required set from the page's code and checks it
  against what's declared. It catches both sides: a shortfall (403 for the buyer) and an
  excess (the buyer sees it before purchase).
* **The platform changes faster than the records about it.** On 12 Aug 2026, the live OS
  scheme changed between two checks within the same day. Rule for everyone: a fact about the
  platform older than a day gets re-verified live, not quoted.

---

## What this changes for the builder chat

As its first action, the chat states the stage and the facts, and takes the scope from the
checker. Not stated — counts as `prod`: silence buys no slack.

Wording to open with: "stage build, no client data, no third-party machine — gates
`check_code_canon` and `check_ui_api_contract`, stop rules observed."
One line, and the argument about scope is over before it starts.
