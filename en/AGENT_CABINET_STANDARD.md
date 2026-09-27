<!-- source: AGENT_CABINET_STANDARD.md sha256:ca74d611d4d8a7a8d82f3229766018bc8b69334531efc401bab4cdcc45011798 -->

# Agent Cabinet Standard (agent cabinet) — part of Extella Evolution

Names of system parts: `NAMING.md`. Cabinet = **Agent Cabinet**, fleet = **Evolution Console**,
proving ground = **Evolution Lab**, change cycle = **Evolution Loop**, agent content = **Agent Genome**.

Owner: CEO · Date: 09 Aug 2026 · Version: 1.2
Reference for comparison: Microsoft Agent 365 (agent management admin center)

## 1. Why

Every agent must have **its own cabinet** — a place where you can see what kind of agent it is, how it
works right now, and how to change it safely. Without a cabinet an agent exists only in the developer's
head: it cannot be handed to another person, shown to a client, or verified.

Rule: **a cabinet is not written by hand for each agent.** It is **assembled from the agent's passport**
(`templates/agent_passport.yaml`) by the generator `tools/build_agent_cabinet.py`. The path is:

```
filled in the passport → the checker passed it → the Agent Cabinet appeared on its own → the agent is visible in Evolution Console
```

Consequence: the passport stops being "paperwork for a checkmark" — it becomes the source of the interface.
Did not fill in the boundaries or the explanation — there is no cabinet, there is no release.

## 2. Two mandatory parts

### 2.1. Agent Passport — "what this is and how it works now"

MUST show the **effective state**, not raw lists of platform objects:

- a stable `agent.platform_agent_id` (link to the live agent, not by name), goal, role, owner,
  work status, last activity;
- the live provider and instructions may land in the draft as `platform_provider` and
  `declared_instructions`; the owner, goal, boundaries, budgets and metrics stay unfilled until
  a human review;
- the active configuration version and its immutable identifier;
- the current sequence of actions (as declared);
- inputs, results, launch points (chat, card, schedule, event, API);
- connected models, integrations, devices, interfaces;
- current knowledge, rules, capabilities — **with the origin of each item**:
  the agent's own / inherited from a group / shared (affects the class), which version is active,
  which stages of work it changes;
- read / prepare / execute rights;
- last runs, errors, costs (**mark as "estimate"**), results.

A separate **"Needs attention"** block (the generator computes it automatically): shared objects whose
change would affect other agents; actions that go outward or touch hardware; actions where a human is
mandatory.

The canonical Shared Gene is declared in the top-level `shared_genes` list of the Agent Passport:
`gene_id` (a stable key), `kind` (`knowledge | rule | expert | handler`), `name`, `version`,
`provenance` with value `global`. The consumer is identified by the agent's stable id. Evolution Console counts
the exact N of consumers **only by `gene_id`**, not by the displayed name. The old `capability.global` remains
visible for migration, but it is not proof of a shared object's identity.

### 2.2. Two views of behaviour — "declared" and "actual"

MUST be side by side and comparable:

- **"How it is supposed to work"** — the declared sequence and logic (from the passport);
- **"How it actually works"** — the routes of the last managed runs: which rules fired,
  which capabilities were called, at which step the agent deviated from the expected path.

This is the main point of the cabinet: **a nice description does not prove actual behaviour.**
A divergence MUST be highlighted, not smoothed over.

### 2.3. Evolution Loop — managed change

A cycle (9 steps, the generator issues it as the cabinet's contract): describe in words → determine what is
changing → choose the scope → create a draft → show impact and dependencies → compare the old and new
version on identical cases → publish → observe → return the exact previous version.

Mandatory constraints:

- from one agent's cabinet, a change begins **only for that agent**;
- when attempting to change a **shared** object, an impact screen MUST appear: *"This mechanism is used
  by N other agents. Create a local version or change the whole class?"* — protection against mass breakage;
- the cabinet uses **the same version log** as Evolution Console. The cabinet is
  a per-agent projection, and NOT a second version mechanism;
- the cabinet is a **mirror, not a second source of truth**: state is read from the platform and the log;
  a divergence is shown honestly ("it is in our registry, it is not on the platform"), not papered over.

### 2.3.1. Creation in Extella from the cabinet (owner's decision of 26 Jul 2026)

The cabinet MUST be able to **create in Extella**, not only show. An agent grows where it is managed:
if adding knowledge or a capability requires leaving for another tool, the cabinet
remains an observation deck, while the agent's genome evolves outside the managed loop.

It MUST be possible to create all four kinds of Agent Genome:

| What we create | What it is for the agent's owner | Platform |
|---|---|---|
| **Knowledge** (Concept) | what the agent must know | `/api/concept/*` |
| **Rule** (Rule) | what the agent is allowed and forbidden to do | `/api/rule/*` |
| **Capability** (Expert) | a verifiable action the agent can perform | `/api/expert/save` |
| **Class handler** (CSPL) | a shared way of executing a whole class of capabilities | `/api/expert/save` |

**Mandatory guarantees** — without them, creation turns into a silent write into someone else's area, and
that is our live failure class, not a hypothesis:

1. **The same Evolution Loop:** draft → verification in Evolution Lab → publication → Evolution Receipt.
   A direct write into production from the cabinet is forbidden.
2. **The default scope is this agent only** (§3.6). A shared object is created only after the impact
   screen, and such creation **finishes in Evolution Console** (§2.4), not in the cabinet.
3. **No duplicate names allowed:** a capability with a name that already exists in another scope is
   rejected — a duplicate produces a non-deterministic run (checked by `wz_expert_janitor`).
4. **Only REST with an explicitly specified scope.** The MCP `save_expert` is forbidden: it silently
   writes into another agent's scope.
5. **Only Qwen** for anything that gets executed.
6. **Success is confirmed by reading back** from the platform (`agent/get`, `experts_db/list`): an HTTP 5xx
   or a timeout is neither a failure nor a success — it is verified by an artifact.
7. **An Evolution Receipt for every creation:** what was created, in which scope, by whom, and how to
   return to the state before the creation.
8. **A new agent is not created in the cabinet:** the cabinet is about one agent, a new one is born in
   Evolution Console or in the Builder (anti-duplication of surfaces, §2.4).

The contract is machine-checkable: the generator `tools/build_agent_cabinet.py` issues an
`evolution.creation` block (kinds, guarantees, default scope, prohibitions), and the self-check verifies it.
The product MUST render exactly this block, not its own list.

## 2.4. Where things live: one mechanism — two views (owner's decision of 26 Jul 2026)

The question "everything in Evolution Console or in Agent Cabinet" is resolved by separating **data** and
**views**:

- **Data and the version log live in ONE place.** One log (draft → test → publish → rollback),
  one projection of state, one risk computation. Two version mechanisms = a guaranteed
  divergence (our recurring failure class: local registry vs. the platform, override vs. rollout).
- **There are two views, and they are about different things:**
  - **Evolution Console** — the top-down view: the whole fleet of agents, risks against the standard,
    cross-links of shared mechanisms, class-wide changes, bulk operations.
  - **Agent Cabinet** — the close-up view: one agent, its effective state with origin,
    "declared vs. actual", its local evolution.

**The rule of change scope** (determines where a change finishes):

| Scope | Begins | Finishes |
|---|---|---|
| this agent only | cabinet | cabinet |
| Shared Gene (class) | Agent Cabinet — catches the attempt and prepares a draft | **Evolution Console** — tests the whole class, before/after comparison, staged rollout, rollback |
| bulk operation | Evolution Console | Evolution Console |

A class-wide change is a migration (§3.17), and it cannot be finished from a single agent's window.

**Anti-duplication (mandatory):**

- Agent Cabinet MUST NOT contain anything that is not in Evolution Console — the cabinet is a projection;
- Evolution Console MUST NOT contain an agent's personal context (its sequence, its
  explanations) — instead there is an "Open Agent Cabinet" button;
- risks are computed **once** (by the standard's checker); the cabinet shows the same numbers filtered,
  not its own computation. The machine contract is `check_report(doc)` /
  `check_agent_passport.py --json`; a consumer uses the stable issue `code`, not parsing the
  Russian text. Two different answers to one question is a defect.

Scale does not change the rule: the more agents there are, the more important the Console is; the more
important a specific agent is, the more important the cabinet is. The surfaces do not compete.

## 3. Honest comparison with Microsoft Agent 365

| Agent 365 capability | What we have now | Comment |
|---|---|---|
| Inventory of the organization's agents | **Have it** (verified live: 15 agents on the account) | within the account; the platform gives no cross-account visibility |
| Agent card: goal, model, configuration | **Have it** — passport + reading the agent from the platform (name, model, provider, instructions, tools) | |
| Effective state: knowledge, rules, capabilities | **Have it** (verified: 155 knowledge items, 73 rules, 916 capabilities) | with origin and active version |
| Activity: sessions, errors, active users | **Partially** — via managed runs and receipts | direct chats with the agent are not visible: there is no native tracing |
| Costs | **Estimate** | not a billing fact; marked with the word "estimate" |
| Export | **Have it** (CSV/JSON from the cabinet's data) | |
| "Agent risks", "orphaned agents" | **Have it, and more meaningfully** — this is the result of our standard's checker | an agent with no owner, no boundaries, no rollback, not on Qwen, with dead links = on the risk list |
| Block / disable an agent | **Locally** (schedules, cards, our own loop) | there is no platform-level block |
| Roles and permissions (Users / Permissions) | **No** | waiting on the platform's role model (escalation A4) |
| Security and compliance, tamper-evident audit | **No** | a log exists, tamper-evident does not |
| End-to-end tracing of "agent called agent" | **Partially** | there is no platform-level tracing |

Rule of presentation: what we do not have MUST be named in the cabinet's interface as a boundary, not
hidden. A cabinet that promises the full picture without having it is the same lie it is meant to guard against.

## 4. Base technology (built by us, lives in this repository)

| File | Role |
|---|---|
| `templates/agent_passport.yaml` | source of truth about the agent; stable platform ID and canonical Shared Genes |
| `tools/check_agent_passport.py` | the single gate + a bilingual structured report with stable issue codes |
| `tools/build_agent_cabinet.py` | **generator of the Agent Cabinet from the Agent Passport**, schema `extella.agent_cabinet.v1.1` |
| `templates/cabinet_widget.js` | XSS-safe render: Agent Passport / actual behaviour / Evolution Loop, RU+EN |
| `templates/help_card.md`, `templates/help_widget.js` | XSS-safe "? How this works" explanation, RU+EN |
| `tools/test_widgets.js` | render/security selftest of the three tabs and the explanation |

The product part (Evolution Console, live data, publishing versions) is implemented
in the product and MUST use these artifacts, not its own copies.

## 5. Readiness criteria for a cabinet

- The cabinet is assembled **by the generator from the passport**, not written by hand.
- The Agent Passport is linked to the live agent via a stable `platform_agent_id`, not via the name.
- Shared Genes have a stable `gene_id`; the exact N of consumers is not counted by names.
- The effective state with origin and the active version are visible.
- "Declared" and "actual" sit side by side, and the divergence is highlighted.
- Changing a shared object is impossible without the impact screen and the choice of "locally / whole class".
- **You can CREATE in Extella from the cabinet** — knowledge, a rule, a capability, and a class handler
  (§2.3.1) — via the same Evolution Loop, by default for this agent only, with a receipt and a rollback.
  Creating a new agent in the cabinet is absent.
- A rollback returns the exact previous version, history and receipts are preserved.
- Boundaries (section 3) are present **in the interface**, not only in the documentation.
- The "? How this works" explanation and the whole interface are **in Russian and English** (§3.26).

## 6. Automation is the main object, agents inside it are components (owner's decision of 26 Jul 2026)

A client buys and installs **an automation** (Agent 1C, Kazakh Lawyer, a travel agency), not
"an Extella agent". That is why the main object of Evolution Console is the automation, and the platform
agents inside it are **hidden technical components**.

The gap this closes: an agent's passport describes ONE agent (`platform_agent_id` — one
string), a composite automation was not described by it.

| Object | File | Checker | Cabinet generator |
|---|---|---|---|
| agent | `templates/agent_passport.yaml` | `tools/check_agent_passport.py` | `tools/build_agent_cabinet.py` (`extella.agent_cabinet.v1.1`) |
| **automation** | `templates/automation_passport.yaml` | `tools/check_automation_passport.py` (self-check 49/49) | `tools/build_automation_cabinet.py` (`extella.automation_cabinet.v1`, self-check 17/17) |
| **the `/api/state` response** | the service itself returns it | `tools/check_state_contract.py` (self-check 13/13) | — |

Mandatory in the automation passport:

1. **a stable `automation_id`** — not a name and not a path; linking by name is forbidden;
2. **the state contract** `service.health` + `service.state` — without it, the Console would be showing
   "the port responds" as "it works";
3. **composition**: platform agents (each with a stable `component_id`, an actual
   `platform_agent_id` or `USER_SELECTED`, and the expected provider `alibaba`), capabilities,
   schedules with an explicit kind (`external_cron | internal | in_service`),
   integrations with PERMISSIONS (see §6.2), knowledge, rules;
4. **boundaries** `limits` and an **explanation** `help_surface` — the same rules as for an agent (§3.20);
5. **two languages** in the name and descriptions (§3.26);
6. **operations**: an on-call owner, a rollback path, a success metric;
7. **`hosting_profile`** (`local | server | client_server`) — where the automation lives. Server-side ones
   have no directory on disk, and without this field the janitor deletes their card as "dead".

Gates that work by machine:

- an agent-component **not on Qwen** → the passport does not pass, the cabinet is not assembled (canon:
  "client agents run only the platform's Qwen");
- **a duplicate agent** in the composition → an error: consumers are counted by id, a duplicate breaks the count;
- **a passport without boundaries** → no cabinet, same as for an agent;
- **an unknown schedule kind** → an error: the Console must know where the tick lives;
- **placement not specified or unknown** → an error (item 7 above).

### 6.0b. State is read by an EXPERT, not by a port (decision of 06 Aug 2026)

The Console runs on someone else's machine. The port `127.0.0.1` there either stays silent, or answers with
someone else's process — the Console must tell both cases apart from "it works". That is why the automation
passport has a preferred source of state — an expert on the device:

| Field of `automation.state_reader` | What it declares |
|---|---|
| `expert` | the name of the dispatcher expert that returns the state |
| `method` | the method inside the dispatcher, if the product has a route table |
| `schema` | the response contract; an unrecognized schema means "state unavailable", not a default |
| `agent_scope` | how to obtain `X-Agent-Id`: `AGENT_FROM_COMPONENT` / `AGENT_USER_SELECTED` / `ACCOUNT_GLOBAL` |
| `agent_scope_ref` | the stable `component_id` from the composition; mandatory for the first two modes, forbidden for `ACCOUNT_GLOBAL` |
| `expert_global` | the exact `global` flag of the Expert; a mandatory boolean, not inferred from the header's scope |
| `execution_device` | the stable id of the target ON WHICH the expert runs |
| `data_device` | the stable id of the target WHERE the data lies (for Baga these are different machines) |
| `evidence` | today the only allowed value is `exact_target` |

Rules checked by machine (`tools/check_automation_passport.py`):

- AT LEAST ONE source of state is mandatory: `state_reader` or `service`;
- the device is a stable target id; `localhost`, `127.0.0.1`, and a port as the value of
  the device are forbidden;
- a product with only `service` gets a warning: the state is read via
  localhost, and a colleague or the client's server does not have that port;
- `evidence` is mandatory, because pinning with a single `target` is SILENTLY ignored
  by the platform: the call goes as a `targets` array, and the response must carry the device id.

**The reference to the agent scope goes through the component, not through an index and not through a
second agent id.** Each element of `components.platform_agents[]` gets a non-empty string `component_id`,
unique within the passport. `agent_scope_ref` refers only to it: reordering the composition does not break
the reference, and `platform_agent_id` continues to live in one place.

Three modes are closed:

- `AGENT_FROM_COMPONENT` refers to a component with an exact `platform_agent_id` of the form `agent_...`;
- `AGENT_USER_SELECTED` refers to a component with `platform_agent_id: USER_SELECTED`. The component
  requires an exact `binding_ref` locator of the form `<path>:<field>`, for example
  `~/extella_baga/agent_binding.json:agent_id`; a path with no field name does not resolve the binding;
- `ACCOUNT_GLOBAL` carries no `agent_scope_ref` and is allowed only with `expert_global: true`.

For the two component-based modes, `expert_global` is orthogonal to the scope: both `false` and `true` are
allowed, because both combinations exist in production. The flag cannot be inferred from `agent_scope`.

The fail-closed transition: the absence of `agent_scope` currently gives a single warning
`AUTOMATION_STATE_SCOPE_REQUIRED`, and the Console shows `STATE_READER_SCOPE_UNAVAILABLE` and does not
pick the first agent. Once the field is declared, wrong values are errors:
`AUTOMATION_STATE_SCOPE_INVALID`, `AUTOMATION_STATE_SCOPE_REF_REQUIRED`,
`AUTOMATION_STATE_SCOPE_REF_UNRESOLVED`, `AUTOMATION_STATE_SCOPE_BINDING_REQUIRED`,
`AUTOMATION_STATE_SCOPE_REF_FORBIDDEN`. The v2 structure is additionally guarded by
`AUTOMATION_AGENT_COMPONENT_ID_REQUIRED`, `AUTOMATION_AGENT_COMPONENT_ID_DUPLICATE`,
`AUTOMATION_STATE_EXPERT_GLOBAL_REQUIRED`, `AUTOMATION_STATE_EXPERT_GLOBAL_INVALID`.
After six products have migrated, the warning `AUTOMATION_STATE_SCOPE_REQUIRED` is upgraded to an error.

### 6.0c. Surface class: what to show in the fleet at all

Not everything installed is a client's automation. The class is declared once in
`surface_classes.yaml` and checked by the gate `tools/check_surface_classes.py`:

| Class | What it is | Does it need an Automation Passport |
|---|---|---|
| `automation` | what the client bought and installed | **yes**, and it must pass the gate |
| `system` | Extella's own platform surface (Builder, Connections, Workspace, Copilot, Studios, Team, the de-identification service) | no — it is part of the tool |
| `installed_app` | a third-party app the user installed via the storefront | no — we are not responsible for it |
| `probe` | our temporary probe | no — it has no place in the client's fleet |

The gate also cross-checks `registry_card_id`: the id of the card on the device can differ from
`automation_id` (Baga is deployed as the card `baga_thin`), and without an explicit link both sides look
like a dead reference.

### 6.0d. The exact shape of `extella.automation_state.v1`

The schema is declared in `automation.state_reader.schema`; the payload itself carries no second
discriminator. All eight top-level fields are mandatory, but their values are not free-form:

| Field | Allowed value |
|---|---|
| `enabled` | only boolean `true` / `false`; the string `"true"` and `null` are not a fact |
| `active_version` | a SemVer 2.0.0 string or `null` |
| `last_run` | an ISO 8601 string, a finite number, an object with a valid `at` or `ts`, or `null` |
| `last_result` | a closed enum `ok` / `failed` / `partial` or `null` |
| `last_error` | `{code, message_ru, message_en}` with three non-empty strings, or `null` |
| `schedules` | an array; each element contains a non-empty `id`, a boolean `active`, and a present `next_run` of type string / finite number / `null` |
| `checked_at` | a valid ISO 8601 string or `null` |
| `bound_to` | an object of the exact shape from §6.1; the object itself is never `null` |

Additional product-specific fields are allowed. They do not replace the canonical fields and do not allow
inferring them by indirect signs. For numeric markers, `bool` does not count as a number, `NaN` and
infinity are forbidden. For `last_run` with both keys present, `at` takes priority: a wrong `at` cannot be
masked by a correct `ts`.

### 6.1. The `bound_to` binding in the `/api/state` response (item A2)

A client who bought an automation must see, not "it works", but **"it works, on such-and-such server,
such-and-such account, such-and-such agent, such-and-such version"**. Otherwise they cannot tell their own
loop from someone else's, and the output loses its meaning. That is why the `/api/state` response must
contain a `bound_to` block:

| Field | What it means |
|---|---|
| `hosting_profile` | an exact enum `local` / `server` / `client_server`, or `null` |
| `host` | a non-empty address at which the service responds, or `null` |
| `platform_profile_id` | a non-empty platform profile under which the automation calls the API, or `null` |
| `account_ref` | **a short irreversible fingerprint of the account** (8–32 lowercase hex), or `null` — NOT a token |
| `agent_ids` | a list of unique stable `agent_...` ids, or `null`; an empty list is an honest fact of no binding |
| `since` | a valid ISO 8601 date of the binding, or `null` |

Four rules that are checked by machine (`tools/check_state_contract.py`):

1. **A field's absence and an honest "unknown" are different things.** The field must be present;
   `null` inside it is a valid response, the field's absence is an error. This is the same rule that
   keeps the Console from passing off a substitute value as a fact.
2. **Secrets have no place in the state.** The state is handed to the client, so `account_ref` is only a
   fingerprint, and any string in the block that looks like a live token fails the check.
3. **`bound_to` reports a fact, not an intent.** If the agent is not bound, the list is empty; a
   divergence from the passport is shown by the Console, not hidden by the service.
4. **The type is not guessed.** A number instead of a string, a string instead of a list, a whitespace
   string, and a case-insensitive substitute like `LOCAL` are contract errors, not values that the
   consumer is expected to fix themselves.

### 6.2. Connector permissions in the passport (item A4)

An enterprise client passes a security review **by the passport, without reading our code**. That is why
each `components.integrations[]` entry declares permissions, not just the fact of writing outward:

| Field | Mandatory | Meaning |
|---|---|---|
| `kind` | yes | which external system |
| `scopes` | yes | exactly what is allowed (`messages.read`, `rows.write`, …) |
| `personal_data` | yes | `none` / `reads` / `stores` — **there is no default** |
| `retention` | if `stores` | how long PII is retained — needed for the data-processing agreement |
| `human_in_loop` | if writing outward | does a human confirm; the answer "no" is allowed, silence is not |
| `secret_ref` | recommended | WHERE the secret lives; the secret itself in the passport = an error |
| `account`, `external_writes` | recommended | whose access is used, and whether it writes outward |

The point of this strictness: "not stated" is not "does not touch". A passport in which a connector's
permissions are not visible hides exactly what the client is reading it for.

The automation cabinet is **assembled by the generator** and contains: the composition (agents marked as
`surface: component` with a link into their Agent Cabinet), the declared state contract with an honest
"state unavailable", an automatically computed attention block (what writes outward, which ticks are
external), and boundaries in two languages. Cabinets of component agents are assembled by the **same**
agent generator — composition, not a second mechanism.

Verified on a live product on 26 Jul 2026: the travel agency passport (`extella_travel_agency`, agent
"Travel agent" on Qwen, two schedules, WhatsApp with an outward write) passes the gate and produces a
cabinet.

## 7. Where registries live (owner's decision of 28 Jul 2026)

The rule from which everything else follows:

> **A registry can only be stored where it can be rebuilt from. If losing the storage
> means losing the data, it is not a registry — it is the only copy.**

The trigger — the incident of 28 Jul: the automations registry read as empty, even though 12 records were
intact. They were sitting in someone else's KV scope, and `global: true` did not reach them: **an agent's
own copy of a key wins over the shared one, silently and with a successful response**. Proven on
`composer:catalog` — the same request returns 25 blocks to one agent, and its own 13 to another. Duplicates
were found in 17 keys out of 121.

That is why registries are split by **who owns the truth**:

| Level | What is there | Where it lives | Role |
|---|---|---|---|
| 1 | what exists at all | **passports in git** | SOURCE OF TRUTH: review, versions, rollback |
| 2 | what is installed here | files on the device + the `/api/state` contract | the fact of this installation |
| 3 | what an agent can find | the assembled registry | DERIVED, rebuilt with one command |

KV keeps a single honest role — **the agent's cache and memory**. The registry is not stored in KV: losing
the cache must be painless.

Assembly of the third level: `tools/build_capability_registry.py` (schema `extella.capability_registry.v1`,
self-check 10/10). It **does not hide problems**: a passport that fails the gate still lands in the registry
with `passport_ok: false` and error codes; one `automation_id` across several passports is a warning;
a capability declared by several automations is marked as a candidate for shared status.

First live run on 28 Jul (canonical repositories): automations declared: **2** — the travel agency
passes, Agent 1C does not; Kazakh Lawyer is absent from the registry, it has no passport. Capabilities
declared: **4**, against 716 experts on the account. This is the honest measure of today's connectedness.
