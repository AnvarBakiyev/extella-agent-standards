<!-- source: AGENT_ARCHITECTURE.md sha256:04dfd6318860f473d511eb3353ca63c7dbf250b62a6c4d7bb32f932ff28cb50a -->

# Extella Agent Architecture Principles

Status: REFERENCE, not a norm (as of 28 Jul 2026).

**`AGENT_BUILD_GUIDE.md` is normative.** This document holds the expanded formulations of the principles with all
the caveats — read it when the guide wasn't enough. **On any discrepancy, the guide wins**, not this text:
one rule stated in two places drifts apart silently, and §9 had already drifted within an hour of a field revision.

Version: v0.9.1

Owner: Anvar (all decisions on this document are his alone)

Date: 26 Jul 2026

The "why" frame is `EVOLUTION_PHILOSOPHY.md` (read before this document). Names of the system's parts — `NAMING.md`. This document answers the question "what must be done".

Until formal approval, this document does not supersede `EXTELLA_AI_ONBOARDING.md`, the North Star, or repositories' release protocols. On conflict, the stricter norm currently in force applies. After approval, the document receives a version, an effective date, and an owner for subsequent changes.

## 1. What we are building

An Extella agent is not a chat with a long prompt. It is a managed system of business capabilities that:

- takes on a task via chat, a plugin, an API, a schedule, or an event;
- understands the user's intent;
- applies the organization's rules and knowledge;
- performs verifiable actions through Experts;
- requests confirmation before risky actions;
- leaves evidence of the result;
- can evolve without losing control and can roll back to a previous version.

Short formulation:

> We are not creating just code or a chat, but managed business capabilities that can be applied across different interfaces, verified, evolved as a whole class, and safely reverted to a previous version.

The unit of the product is not "an agent in general" but a specific business capability with known inputs, outputs, constraints, and evidence of execution.

Examples: reconcile two exports, find discrepancies, prepare an advertising campaign, review a contract, post a document in 1C, de-identify a file, calculate margin.

## 2. Agent layers

Below is the reference architecture. Policy, the capability contract, and evidence are always mandatory. The LLM, Concepts, custom CSPL, and Listener are wired in only where the task needs them.

1. **Interface** — chat, a plugin card, a form, a mobile app, an API, or an event.
2. **Agent** — carries the dialogue, clarifies the goal, and explains the result. The current platform profile for client agents is Qwen 3.7. Replacing the model is a separate platform decision and is not done inside a product experiment.
3. **Orchestrator** — builds and executes the plan, selects capabilities, observes limits, and manages state.
4. **Rules** — mandatory constraints, approvals, risk thresholds, and business policies.
5. **Concepts** — managed knowledge, definitions, examples, and organizational context.
6. **Experts** — deterministic or specialized executable capabilities.
7. **CSPL** — the shared way of executing an entire class of Experts; changing the handler can evolve the whole class without rewriting each Expert.
8. **Runtime and Listener** — the execution environment and the controlled bridge to the device, local files, applications, hardware, or a closed perimeter.
9. **Evidence and observability** — the log of decisions, versions, inputs, outputs, checks, cost, and errors.

The model must not stand in for the other layers. It is responsible for the ambiguity of language and for reasoning; deterministic work, permissions, and side effects remain in the managed loop.

## 3. Mandatory principles

Terms:

- **MUST** — a mandatory requirement for production.
- **SHOULD** — the default rule; a deviation requires an explanation.
- **MAY** — a permitted option.

### 3.1. Business capability — the unit of design

Every Agent MUST be decomposed into capabilities. Every capability MUST have:

- a clear business goal;
- an owner;
- a typed input and output;
- preconditions;
- permitted side effects;
- an access and confirmation policy;
- a success criterion;
- evidence of execution;
- a version and a rollback path.

"Can work with 1C" cannot be treated as an architectural contract. "Match a counterparty," "create a document draft," "post a document after confirmation" are separate capabilities.

### 3.2. Deterministic first

If a task can be performed correctly with code, a formula, a schema, a validator, a connector, an SQL/API operation, a specialized model, or a rule, it MUST be performed by a deterministic executable loop without a general-purpose LLM.

The LLM SHOULD be used only for:

- understanding free-form language;
- handling ambiguity;
- choosing among permitted options;
- generating text;
- explaining the result.

This lowers cost, latency, and non-determinism, increases verifiability, and enables local operation.

### 3.3. A prompt is not a security boundary

Permissions, prohibitions, limits, approvals, and isolation MUST be enforced by executable policy, not by a request in the system prompt.

The model MAY propose an action. The policy layer grants permission for the action.

### 3.4. Rules are applied before the action

Rules are applied in two mandatory phases:

1. general Rules and principal/tenant constraints are loaded before planning;
2. action-specific Rules are computed after the exact action request is formed, but before preview, approval, and execution.

On conflict, the formal hierarchy applies: platform safety → tenant security/compliance → business policy → preference. Within one level, an explicit prohibition beats a permission. Changing this hierarchy is a change to the policy engine and is not set by the text of an individual Rule.

The decision MUST retain:

- which rules were found;
- which were actually applied;
- why the action was allowed, rejected, or sent for approval;
- the versions of those rules.

### 3.5. Concepts — managed memory, not a context dump

A Concept MUST have a purpose, a scope, a source, an owner, and a version. A search result over Concepts is treated as data for reasoning, not as an unconditional instruction.

Secrets, tokens, keys, real PII, and reversible pseudonymization tables MUST NOT be stored in Concepts.

### 3.6. Isolation by default

All Experts, Concepts, and Rules MUST be isolated within the agent by default.

`global=true` MAY be used only deliberately, for shared organizational objects. For a global object, the following are mandatory:

- an owner;
- a purpose;
- a version;
- a list of consumers;
- an impact assessment for changes;
- a rollback plan.

Globalness is a boundary of distribution, not a mark of quality or trust.

### 3.7. Denied by default

If a permission, route, schema, or target object is not recognized unambiguously, the action MUST be rejected or moved into a clarification mode.

New tools and integrations must not automatically extend the authority of agents that already exist.

### 3.8. Reading is separate from changing

Capabilities for reading, calculating, preparing a draft, and making an external change MUST be separated.

The recommended sequence:

`read → verify → show the plan/diff → confirm → change → re-verify`

An agent does not get write access merely because it got read access.

### 3.9. An exact preview is shown before the change

Before requesting confirmation, the Agent MUST show a clear representation of:

- what action will be performed;
- on which objects;
- which values will change;
- what external or physical effects will occur;
- what checks and rollback are available.

The preview and the executable action request MUST describe the same action and be linked by a shared hash.

### 3.10. Confirmation applies to the exact action

The user's consent MUST be bound to:

- the authenticated actor and their role;
- the specific action and target;
- the exact objects and parameters;
- the expected effect and scope;
- the hash of the structured action request;
- the version of the capability and policy;
- a nonce/idempotency key;
- an expiration time;
- a single-use flag.

After a material change to the parameters, target, policy, or version, confirmation is requested again. A used or expired confirmation cannot be applied again.

### 3.11. A human is mandatory at high risk

Legally significant operations, payments, mass sending, data deletion, posting of documents, changes to permissions, control of physical devices, and other irreversible actions MUST have an explicit human-in-the-loop.

A deviation is permitted only through a formal risk acceptance with the business owner, security/compliance, a limited scope, a policy gate, limits, canary, monitoring, and a kill switch. Assigning A3/A4 by itself does not remove the human gate.

Absolutely prohibited regardless of the autonomy level:

- the model granting approval to itself;
- executing an action outside the granted principal/tenant permissions;
- bypassing a hardware safety interlock;
- passing a plaintext secret into the LLM;
- silently activating its own production change without an approved Evolution Loop.

### 3.12. Typed capability contract

Every capability MUST publish a contract. Every Expert MUST explicitly declare which capability contract, and which version of it, it implements. A single capability MAY be orchestrational or consist of several Experts.

```yaml
name: capability_name
version: 1.0.0
# input_schema / output_schema сняты 28.07 как мёртвые  # canon-ok: разбор, не требование
side_effects: none | local | external | physical
permissions: []
confirmation: never | conditional | always
timeout_ms: 30000
idempotency: supported | unsupported
evidence_schema: {}
```

Free text MAY be used inside the implementation, but not in place of the contract between layers.

### 3.13. Honest completeness of the result

The agent MUST distinguish:

- the result is complete;
- the result is partial;
- the result is not confirmed;
- the operation may have completed after a timeout;
- there is no result.

It is not permitted to report "done" if only part of the data was verified or the transport returned a timeout. After a timeout/500, the agent MUST re-check the artifact or the state before re-running.

### 3.14. Evidence is part of the result

For a significant operation, an evidence receipt MUST be stored in an append-only or tamper-evident store with provenance, read authorization, encryption at rest, and a retention/deletion policy:

- a run identifier;
- the time;
- the Agent and its version;
- the versions of Rules, Concepts, Experts, and CSPL used;
- a hash of or a reference to the normalized input;
- a structured action plan/decision summary and the steps actually performed, without retaining the model's hidden chain-of-thought;
- confirmations;
- the result of checks;
- side effects;
- errors and retries;
- cost and duration;
- a reference to the output artifact.

Sensitive values in evidence are masked or replaced with authorized references. For low-entropy PII, plain SHA-256 is not enough: a keyed digest/HMAC or a protected reference is used, to rule out brute-forcing the original value.

### 3.15. Observability without leakage

Every production Agent MUST have metrics for:

- the share of successful, partial, and failed runs;
- duration per step;
- LLM cost;
- the number of retries and confirmations;
- quality against the business metric;
- the frequency of manual intervention;
- the versions of the components applied.

Logs MUST NOT contain tokens, keys, or raw sensitive data.

### 3.16. The entire executable bundle is versioned

An Agent version gets an immutable ID and a dependency lock with a cryptographic hash of every element:

- system instructions;
- the provider/model revision and parameters;
- routing;
- Rules and Concepts;
- Experts and CSPL;
- input/output schemas;
- Runtime dependencies;
- the UI contract;
- tests and the set of reference examples.

Changing any of these elements creates a new reproducible bundle. Changing a shared/global dependency automatically creates new dependency-lock versions of all affected bundles, or blocks their execution until compatibility is checked.

### 3.17. Evolving a class through CSPL is verified as a migration

A shared handler MAY evolve the entire class of Experts with a single change. Such a change MUST go through:

1. identifying the affected class;
2. testing all compatible contracts;
3. comparing results before and after;
4. a canary or staged rollout;
5. checking the Experts' invariants;
6. the ability to roll back the handler;
7. evidence of the impact on every instance.

A change cannot be considered safe merely because the Experts' bodies did not change.

### 3.18. An Agent-to-Agent call is just as much a managed contract

A call to another Agent or Expert MUST pass the minimum amount of data and MUST have:

- an explicit delegation goal;
- the permitted capabilities;
- a budget for time, tokens, and depth;
- a correlation ID;
- protection against cycles;
- evidence of the result obtained;
- separate authorization for side effects.

Delegation does not automatically pass on all of the calling agent's permissions.

### 3.19. Listener — the controlled boundary of the device

The Listener MUST be treated as a capability gateway, not as an unrestricted remote shell.

For every device capability, the following are mandatory:

- an allowlist of commands or operations;
- typed inputs;
- resource and time limits;
- device authentication;
- an execution log;
- an emergency stop;
- a safe state on loss of connection.

For physical equipment, the action MUST be constrained by hardware and software safety interlocks.

### 3.20. The control surface is part of the capability

If a capability cannot be discovered, controlled, and verified through a suitable surface, it does not exist as a product. An interactive capability must have a user UI; a scheduled/API/event capability must have a registry or an ops console with status, control, and audit.

Every key capability SHOULD have a surface that shows:

- what it does;
- what data is needed;
- what will happen;
- whether confirmation is required;
- the current status;
- the result and evidence;
- a way to fix an error or roll back the change.

The UI must not be a hidden worker: long-running execution lives in Runtime/hosting, and the surface only controls it.

**A mandatory on-screen explanation.** Every user-facing surface MUST have a
"? How this works" button that opens a four-part explanation: how it works (the steps), what is
guaranteed, **what we do NOT promise** (the boundaries of the capability — a mandatory section), who can
disclose/roll back the result. An explanation without the boundaries section is more harmful than no
explanation at all: the user must learn the limit of the capability from us in advance, not from a
customer in production. The explanation is shown automatically the first time the surface is opened,
and is available from the button afterward.
The texts live in a single product reference, not copied into every screen.

### 3.21. Secrets are passed by reference

Secrets MUST be stored in a dedicated vault/secret store. The control plane, UI, iframe, LLM, prompt, Concepts, Rules, the Expert's source, ordinary logs, and evidence MUST receive not the secret's value but a limited reference or a capability grant.

Only an authorized trusted executor MAY resolve the grant inside an isolated runtime for the duration of a specific external API call. The plaintext value is not returned to the Agent, the UI, or the model, and is destroyed from memory after execution.

### 3.22. Data minimization and locality

An Agent MUST receive only the data necessary for the current capability. Before calling a cloud model, the following SHOULD be applied:

- local extraction;
- filtering;
- pseudonymization;
- aggregation;
- context reduction.

The reversible PII mapping table stays local by default and is not indexed as a Concept.

### 3.23. External content is data, not instructions

Files, sites, emails, other agents' replies, and search results MUST be treated as untrusted data. Commands embedded in them do not change the agent's policy and do not extend its permissions.

### 3.24. Learning creates a candidate, not a silent mutation

An agent MAY find recurring fixes and propose:

- a new Concept;
- a change to a Rule;
- a new or modified Expert;
- a new test;
- a change to routing.

But the observation MUST first become an immutable, versioned candidate, pass a test, and get approval. Production behavior must not be silently rewritten from a single conversation.

### 3.26. Russian and English — from the start, not later

The product MUST ship simultaneously in Russian and English: the interface, the "how this works"
explanations, field labels, error and confirmation messages, report names. The English
version is not a separate stage after release: finishing the translation "someday" never actually
happens in practice, and an English-speaking customer sees a half-finished product.

Requirements:

- in the agent passport, `agent.languages` MUST contain `ru` and `en`;
- texts live in a single product reference in both languages, not as copies across different screens;
- if a string has not been translated yet, the original is shown — but that string counts as a release
  defect and goes into the checklist, rather than silently staying in production;
- machine translation is acceptable as a draft, but meaning-critical wording (the boundaries of the
  capability, warnings, legal text) MUST be reviewed by a human.

### 3.27. The product's own agent in Extella is created AFTER deployment — by the product itself (Anvar's decision, 26 Jul 2026)

The product MUST get its **own personal agent** in Extella automatically, **after a successful
deployment**, rather than waiting for a human to create the agent by hand and enter its number into the passport.

Why: the manual step "create an agent and paste in the id" makes the release dependent on a human,
and until it's done, the passport is guaranteed to fail the standard. On top of that, the temptation to
"attach to an existing agent" mixes the genomes of two different tasks: a change to one product's
knowledge becomes a class-wide change for another (§3.6, §3.17).

Mandatory conditions for automatic creation — without them, this is a dangerous action, not a convenience:

1. **Only after a successful deployment.** An unfinished build MUST NOT create platform objects.
2. **Idempotency.** A repeated deployment MUST NOT create a second agent: the binding runs on the
   product build's immutable identifier; on a repeat, the number of the existing agent is **read**,
   not created anew.
3. **Success is confirmed by reading it back** (`agent/get`): creation counts as having happened only
   after the agent has been read and its provider is Qwen. An HTTP 5xx or a timeout is neither a failure nor a success.
4. **The number is written into the passport automatically**, so that the passport is true without manual entry.
5. **Fail-closed.** If creating the agent fails, the product MUST say so plainly and remain
   local — rather than pretending to be integrated.
6. **Its own agent, not someone else's.** Binding to an existing agent is permitted only as a deliberate
   decision by the owner, with the reason recorded: it makes the genome shared.
7. An **Evolution Receipt** for the creation: what was created, on which account, who initiated it, and how
   to roll it back (delete the created agent).
8. **Own account only.** Creating an agent on a colleague's or a client's account is allowed only with their explicit
   consent; `global` objects are never created automatically.

### 3.25. An error must tell the truth and help recovery

An error MUST contain:

- which step did not complete;
- what may already have changed;
- what has been checked;
- whether a retry is safe;
- what is required from the user or the operator;
- the evidence identifier.

## 4. Autonomy levels

Every capability gets its own level:

| Level | Behavior |
|---|---|
| A0 | Only explains and suggests |
| A1 | Reads and analyzes, no changes |
| A2 | Prepares a draft or a plan; a human confirms the change |
| A3 | Automatically performs pre-approved, low-risk actions within limits |
| A4 | Independently executes a complex loop with continuous monitoring, limiters, and an emergency stop |

The level is assigned to the capability, not to the Agent as a whole. One Agent can have A1 for payments and A3 for building reports.

Moving to the next level happens only after evidence has accumulated, tests have passed, and the risk owner has approved it.

## 5. Lifecycle

### 5.1. Design

1. Fix the business result and the metric.
2. Decompose the process into capabilities.
3. Determine where an LLM is needed and where an Expert/Rule is needed.
4. Describe the data, permissions, risks, and autonomy level.
5. Choose local, cloud, or hybrid execution.
6. Describe evidence and the UI before writing the implementation.

### 5.2. Build

1. Create typed contracts.
2. Implement deterministic Experts.
3. Add Rules and Concepts with a defined scope.
4. Configure orchestration, budget, and timeouts.
5. Wire up the interface and hosting.
6. Add tests, telemetry, and rollback.

### 5.3. Verification

1. Unit tests for Experts.
2. Contract tests for inputs and outputs.
3. Checking policies and isolation.
4. A golden set of real tasks.
5. Negative, adversarial, and timeout scenarios.
6. Checking cost, latency, and completeness.
7. Checking evidence and recovery.

### 5.4. Operation

1. Canary.
2. Monitoring by business metrics.
3. Reviewing errors and manual fixes.
4. Creating a RED test that reproduces the problem on the active version V1.
5. Forming an immutable Candidate V2 with a `candidate_id` and a SHA-256 of the full bundle.
6. A TestRun of the candidate in an isolated environment; GREEN applies only to the candidate's exact SHA.
7. Approval bound to `candidate_id + SHA-256 + scope + actor_id`.
8. Atomically switching the active pointer from V1 to the approved V2.
9. Canary and controlled expansion.
10. Rollback atomically returns the active pointer to V1; the candidate's history and evidence are kept.

A candidate cannot execute in production before activation. Any change after GREEN creates a new SHA, a new TestRun, and a new approval.

This is Extella's Evolution Loop:

`evidence → RED on V1 → immutable Candidate V2 → GREEN of the exact SHA → bound approval → atomic activation → monitoring → pointer rollback`

## 6. Definition of Ready

A capability is ready for development if:

- the business goal and the owner are described;
- the inputs, outputs, and success criterion are known;
- side effects are defined;
- the autonomy level is chosen;
- the applicable Rules and Concepts are listed;
- the scope is defined;
- the data and its handling mode are understood;
- confirmations and rollback are described;
- the evidence receipt is defined;
- there are test examples and expected results.

## 7. Definition of Done

A capability is ready for production if:

- the contract is versioned;
- the happy path and errors are tested;
- permissions are minimal;
- destructive/external actions are confirmed per policy;
- timeouts and retries are handled safely;
- the result is re-checked;
- evidence is generated;
- secrets and PII do not reach prohibited layers;
- there is observability and cost limits;
- there is a suitable user or operational surface;
- there is an operations owner;
- there is a staged rollout and a verified rollback;
- the documentation reflects the actual implementation.

## 8. Anti-patterns

Prohibited or undesirable constructs:

- one giant prompt instead of an architecture;
- "full access to everything" for the sake of convenience;
- creating global objects without an owner;
- an LLM for exact arithmetic and validation when code is available;
- mixing reading and writing in one inseparable tool;
- automatic retrying after a timeout without checking state;
- "successful" when execution is partial;
- silent self-modification of production;
- passing tokens into the UI/iframe or the model;
- storing PII and keys in Concepts;
- Agent-to-Agent calls without a budget, trace, or protection against cycles;
- controlling a device through a general-purpose shell;
- a capability accessible only through a hidden chat command;
- changing a shared CSPL without testing the whole class;
- demonstrating a capability without a working user path.

## 9–11. Moved — these sections no longer live here

Here used to be: the minimal agent passport, the platform's working canon, and the list of what the
platform must provide. All three were removed on 28 Jul 2026, and here's why.

**The passport (§9)** duplicated `templates/agent_passport.yaml` — and drifted from it within an hour. After
the field revision, the document kept requiring ten fields that had been removed (`input_schema`, `output_schema`,
`approval_binding`, `completeness_contract`, `data_fields`, `data_residency`, `evidence_schema`,
`alerts`, `reconciliation`, `owner_on_call`). This is exactly the class of breakage we spend all day
closing off: one rule stated in two places drifts apart silently. **The source of truth is the template in
`templates/`, checked by `tools/check_agent_passport.py`.**

**The working canon (§10)** moved to `AGENT_BUILD_GUIDE.md` §3. There it was also corrected to match
reality: the earlier claim that "`global=true` makes an object visible across agents" was disproved by a live
check on 28 Jul.

**The list to the platform (§11)** is not a standard but an escalation. It lives in
`docs/INCIDENT_KV_SCOPE_SHADOWING.md` in the core-portal repository, where every item has
a reproduction.
