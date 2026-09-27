<!-- source: APP_FROM_MODULES.md sha256:827add179a9d63247951d61c4f6c960e767d141dc76e1af6b289fe2433e4f88b -->

# How to build an app from modules

**This document is written for a machine.** It is read by Claude, Codex, or any app that
builds apps out of ready-made nodes. A human does not read it: they say what app
they need, and you do everything else.

Owner: CEO. Version: 1.0, 04 Sep 2026 — first edition, verified by building
one app by this text (§7).

---

## Words that come up constantly below

**Module** is a plugin that has only experts exposed outward and no interface.
An app exists for a human, a module exists for whoever assembles an app.
**Passport registry** is the file `capabilities_declared.json`, assembled from the passports in git;
it holds, for each module, its boundaries, machine requirements, and experts with "what it does".
**Scope** is the set of objects available to a specific agent; every agent has its own.
**Listing** is a product card in the store.
**Gate** is a machine check that must be able to fail.
**Pre-release** is a version of the product in the store that only its author can see.
**Five Forms** is the closed vocabulary of content between apps: list, number, steps,
relations, document (`КОНТРАКТ_ПЯТИ_ФОРМ.md`, code in `tools/формы.py`).

## 0. What is required of you, in one paragraph

You are given a task in human words: who needs the app and what it does. You
break the task down into needs, find a module in the passport registry for each one, honestly
name the gaps, write a screen plan in the five forms, assemble the product's catalog with one
command, make the modules' experts visible to the app's agent, run the app's gate
for its stage, and bring the product to pre-release. The checkers, not this text, are the
specification: `tools/check_app_from_modules.py` knows more than what is written below.

Declare the stage first (§0a `AGENT_BUILD_GUIDE.md`): during the build a module with no passport gives
a named warning, in prod it is a refusal.

---

## 1. What an app built from modules is, and what it is not

An app built from modules is a page-type store product: one window assembled from the five
forms, and an app agent, in whose scope the experts of the chosen modules are visible. The window calls
an expert via `app-agent/run`, the expert runs on the buyer's computer, the response lands
in one of the five forms and is drawn in the window. The app has no code, except for one state
expert, which the builder assembles.

What it is not:

- not a chat: an employee sees a queue, fields and buttons, not a dialogue;
- not a new server: the app has no port and no process, everything live is executed by modules' experts;
- not the owner of the modules: the canon of a module's expert is one and lives in the library, the app
  gets a copy into its own agent's scope, because the store window only sees that scope.

Why it is this way: the interface changes more often than a capability does, and eight products with eight
servers produced almost the entire breakage log of August. An app built from modules repeats the thin mode
of the `new_product.py` framework, only instead of a route table it has a registry.

---

## 2. What is needed before you start

1. **The passport registry has been rebuilt** on this machine and published for devices:

```
python3 tools/build_capability_registry.py --roots-file config_registry_roots.txt \
    -o ~/extella_wizard/registry/capabilities_declared.json --publish
```

2. **The app's agent exists.** The window does not need a model, only the ability to run experts, so
   the agent can be created via the API (platform canon, rule 6). The main agent
   `agent_extella_default` and agents of other products cannot be the target: someone else's live
   object is not to be touched.
3. **The Extella listener is up** on the machine where the test will run: without it a module's expert
   will not execute where the files are, and will answer "no such file".
4. The platform token lives in `~/.extella/api_token.txt` or in the bridge's config.

---

## 3. Break down the task and find the modules

A composite assignment is not searched for as a whole: the search rule requires half the words of the task
or a semantic match, and five needs in a single sentence are not matched by any
module (measured 04 Sep 2026: on a brief with five needs the search returned three capabilities and no
recognition module at all, while on the sub-task about invoices a module came back first). Therefore:

1. Break the task down into needs, one phrase each: "recognize invoices from scans",
   "keep counterparties and deals", "post a document to 1C".
2. For each one, ask the registry: `run_expert wz_capability_find` with `task` set to one
   need. Take only answers with `declared: true` — for those, the boundaries (`limits`) and machine
   requirements (`needs`) are known. An answer with `declared: false` is a capability with no passport: during
   the build it can be taken with the flag `--без-паспорта`, in prod it cannot.
3. Write a need with no module in words into the plan (`missing_ru`, `missing_en`) and into the window's
   "what we don't promise" block. An app that stays silent about a gap is worse than an app with a gap.

A module's boundary decides what the window promises. A recognition module returns text, not the
invoice's fields — that means a "details" screen cannot be assembled without a parsing module, and this is
written into the plan.

---

## 4. The app plan `app.json`

Sample: `python3 tools/окно_из_форм.py --пример`. Rules checked by
`проверить_план`:

- `slug`, `name` and `description` in two languages, `agent_id` of the form `agent_…`, `modules` —
  identifiers from the registry;
- each screen is one of the five forms and exactly one of two: `static` (ready-made content) or
  `action` (a button). For a button: an expert, input fields, a waiting message in two languages, and `map` —
  how the expert's response lands in the form: templates like `{text}` take fields from the response, list
  forms take an array by the `from` key;
- exactly one main action per screen — hence a screen has one button;
- `help` in two languages: steps, what is guaranteed, **what we don't promise** (mandatory), who
  can disclose or roll back. Without a "what we don't promise" block the window is not assembled (§3.20).

A button's expert must belong to a module from `modules`, or to the app itself — the gate
rejects a foreign expert, because there is neither a passport nor provisioning for it.

---

## 5. Build, provision, verify

```
python3 tools/build_app_from_modules.py apps/<slug>            # product catalog from the plan
python3 tools/provision_modules.py apps/<slug>                  # experts made visible to the app's agent
python3 tools/check_app_from_modules.py apps/<slug> --stage build
```

What the build does and why it is not written by hand:

| File | Where it comes from |
|---|---|
| `index.html` | the window from the plan: five forms, a "? How this works" button, a live call, visible waiting |
| `listing.json` | name, description, tags, `expert.run` and `device.run` rights, modules' boundaries |
| `MANIFEST.yaml` | a merge of the modules' manifests, one dependency check |
| `manifest_check.py` | a byte-for-byte copy of the canon |
| `docs/automation_passport.yaml` | the app's passport: agent, modules' experts with "what it does", boundaries, rollback |
| `experts/<slug>_state.py` | state per the schema `extella.automation_state.v1`, the unknown is `null` |
| `icon.png` | the canonical generator `bronze_icon.py` |

Provisioning makes the experts visible to the app's agent and nothing more. Four rules,
each bought with a breakage:

1. an agent's `instructions` are never written: any copy of an agent has the platform's core there, one
   hundred nine thousand characters long, and `agent_forge` used to erase it.
2. A module's expert is copied into the app agent's own scope, even if it is global. The
   store window calls `app-agent/run`, and that only looks for the expert in the agent's scope: for a
   global one it answers `Expert not found` (measured on the VPS test stand on 05 Sep 2026). A copy that
   is already in the scope and matches the canon is not written a second time; a stale one is updated.
3. After writing, the expert is read back from the agent's scope: a "success" from the platform is not
   a fact.
4. The `provisioning.json` report is placed next to the plan; the gate reads it, rather than taking
   the words for granted.
5. After provisioning, the installed copy of the app must be reinstalled
   (`purchase-stream` with an empty body): the deployed agent keeps the set of experts as of the moment of
   installation.

The app's gate calls the existing checkers (passport, permissions, waiting, brand) and adds
only what is specific to an app built from modules: the registry, the plan, provisioning. Its messages are
in two languages; the codes start with `APP_`.

---

## 6. Bringing it to pre-release

An app built from modules is a page-type product with its own agent. The agent is attached to the listing
only at creation: `publish-stream` with the fields `source_id`, `source_type=agent`,
`attach_agent=1`; you cannot add an agent to an already-created listing (measured 25 Aug 2026, response
`403 this app has no deployed agent`).

**The order is mandatory: provisioning first, then the version.** A listing's version carries a
snapshot of the agent's experts at the moment it was created, and on install the platform deploys a
separate app agent (the window's response `agent_id` differs from the source agent) with
that snapshot. An expert copied into the scope after the version was created does not make it into the
snapshot, and the window answers `Expert not found` (measured on the VPS test stand on 05 Sep 2026). This is
fixed only by a new version and reinstalling the copy. A regular rollout of an agent's pages does not
attach it, so an app built from modules has its own tool:

```
python3 tools/deploy_app_from_modules.py apps/<slug>                 # plan, no write
python3 tools/deploy_app_from_modules.py apps/<slug> --выполнить     # pre-release and acceptance by reading back
```

Acceptance reads back: the listing is not published, the version's permissions and agent match
the plan, the experts are read from the agent's scope, the page is served with the `app_token`
substituted in, without the account's token and with a "? How this works" button. The `expert.run` and
`device.run` rights are declared at creation: without the second `targets`, it is stripped out, and
the expert executes in a container where the buyer's files are not.

Buying for yourself is the `--купить-себе` flag (`purchase-stream` with `deploy_mode=existing` and
`target_agent_id`): after it, the listing cannot be deleted, so this is a separate decision.
From there — follow `README.md` "How to bring it to the store": first run in a clean state, a live
scenario, a stop. The "Publish" button is pressed by a human.

---

## 7. Measurement: how many hours for the creator

The quarter's metric is human-hours to deployment. For an app built from modules it is counted for
the creator, not for Extella: record the time from the first line of the plan to a green gate and to
pre-release in the build report (`apps/<slug>/README.md`, the line "Built in"). The first measurement is
04 Sep 2026, the app "Invoice reading" from one module: see `gtm/moduli-den-1.md` in the bridge.

---

## 8. What the standard deliberately does not require

- The app having its own server, port and process: if a need requires a process, that is a
  "service"-class module, and it lives in the module library, not in the app.
- A second content vocabulary: there are five forms, a new one is added by owner's decision.
- An agent with a model: the window only needs to run experts. Need a dialogue — that is a separate
  decision and a separate agent, created by a human in the interface.
- Copies of modules' experts in each app: modules are shared by definition.
