# Extella Evolution Naming Architecture

Owner: the owner · Date: 26 Jul 2026 · Version: 1.0
Mandatory for use across all products, interfaces, documents and code.
The reasoning behind these names lives in `EVOLUTION_PHILOSOPHY.md`.

## 1. Product and positioning

**Extella Evolution** is a platform for managing the state and development of AI agents.
Category: **Agent Evolution Platform**.

Tagline (RU): "Build the agent once. Grow its knowledge, rules and capabilities throughout
its whole life."
Tagline (EN): "The evolution layer for AI agents."

The difference from the market, in one line: **Microsoft Agent 365 manages a fleet of
agents. Extella Evolution manages how those agents change and develop.** We are not
claiming inventory and observability — we are claiming controlled behavior change.

Deliberately NOT used: "Agent 365" (imitates Microsoft), "AgentOS", "Agent Fabric",
"Agent Control Plane" — taken, or turned into generic market terms.

## 2. Glossary of terms

| Term | What it is | Where it lives in code/product |
|---|---|---|
| **Extella Evolution** | the whole product | top level |
| **Agent Passport** | a **declaration** about the agent: owner, purpose, active version, boundaries, success metric, languages, permissions | `templates/agent_passport.yaml`, gate `tools/check_agent_passport.py` |
| **Agent Genome** | the agent's **mutable content**: knowledge, rules, capabilities, shared handlers, access, integrations — with provenance and versions | computed: `passport.genome` in `tools/build_agent_cabinet.py` |
| **Shared Gene** | a shared (inherited) genome element used by several agents | `provenance: global`; the basis of the impact screen "used by N more agents" |
| **Agent Cabinet** | a view of **one** agent: passport, genome, actual behavior, its evolution | `templates/cabinet_widget.js` |
| **Evolution Console** | a view of the **whole fleet**: agents, risks, the shared-gene map, class-wide changes, bulk operations | product (formerly the "Agent Control Center") |
| **Evolution Lab** | a safe testing ground: behavior before and after a change, without invoking live agents and without external writes | product |
| **Evolution Loop** | the cycle that turns a change into a working one | `AGENT_ARCHITECTURE.md` §5.4 |
| **Evolution Receipt** | the receipt for a cycle step: what, who, when, with which versions and what result | version log |

```
Extella Evolution
├── Agent Passport   — what is declared about the agent
├── Agent Genome     — what determines its behavior (incl. Shared Genes)
├── Agent Cabinet    — where you view and change ONE agent
├── Evolution Console — where you manage the FLEET and class-wide changes
├── Evolution Lab    — where a change is verified before publication
└── Evolution Loop   — how a change becomes working (Evolution Receipts)
```

## 3. Two clarifications without which the terms get confused

### 3.1. Passport ≠ Genome (different purpose)

- **The passport declares** — it is a commitment document: who the owner is, why the agent
  exists, which version is active, what the agent does NOT do (boundaries), how to tell
  it's working well. A person fills it in; a gate checks it.
- **The genome determines** — it is the actual content of behavior: knowledge, rules,
  capabilities, handlers, access. It is computed from the platform and the log, not
  written by hand.
- **Actual behavior proves it** — the routes of real runs and receipts.

Formula: **the passport declares · the genome determines · actual behavior proves.**
A gap between these three levels is not a minor detail — it is the main object of control
(§3.20, §2.2 of the cabinet standard).

### 3.2. Console ≠ Cabinet (different views, one mechanism)

The phrasing "a console where you manage a single agent or the whole system" is ambiguous
and leads to two admin panels. We separate them per the decision in §2.4 of the cabinet
standard:

- **Evolution Console** — the fleet, risks, the shared-gene map, class-wide changes, bulk
  operations;
- **Agent Cabinet** — one agent; a shared-gene change starts here but finishes in the
  Console.

The data and the version log are **the same one**. Cabinet is a Console projection for one
agent, not a second mechanism.

## 4. Rules of use

1. **Product names are not translated**: Extella Evolution, Agent Genome, Agent Passport,
   Evolution Console / Lab / Loop, Shared Gene, Agent Cabinet — written this way in any
   interface language.
2. **Descriptions and captions are bilingual** (§3.26). Russian glosses for the names:
   Agent Passport — "agent's passport"; Agent Genome — "agent's genome: knowledge, rules,
   capabilities"; Evolution Console — "console for managing the agent fleet"; Agent
   Cabinet — "agent's cabinet"; Evolution Lab — "testing ground for verifying changes";
   Evolution Loop — "cycle of controlled change"; Shared Gene — "shared (inherited) genome
   element".
3. **On first mention in a customer-facing document**, give the gloss: "Agent Genome (the
   agent's genome — its knowledge, rules and capabilities)." The word "genome" without a
   gloss triggers biotech associations in an enterprise conversation.
4. **Do not multiply terms.** Nine is the limit. A new term is introduced only by changing
   this file, with the owner's approval.
5. Old working names are considered deprecated: "Agent Control Center" → Evolution
   Console; "Proving Ground" → Evolution Lab; "Capability Studio" remains a separate demo
   catalog, not part of Evolution.

## 5. What needs to be checked before external use (not done)

- trademark search across software/SaaS classes in target jurisdictions (RU, KZ, US, EU);
- domain and social-handle availability;
- check "Agent Genome" and "Evolution Console" separately — as phrases they are stronger
  than either word alone; "Evolution" by itself is too generic to protect.

Until checked, the names are used as internal/product names, not as a registered
trademark.
