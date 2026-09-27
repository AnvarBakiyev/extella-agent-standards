<!-- source: START_HERE.md sha256:f94831cdd4226a37a055c6c885b8cce35af787c5658cff143a51dfdb3eaa4c06 -->

# One entry point — README

There is no longer a separate "where to start": the single entry point to the standard is
**[README.md](README.md)**. Decided 12 Aug 2026 — two entry points (one for a human, one for
scale) forced the reader to classify themselves first, and that confused people.

Below is the former text, kept for the sake of existing links.

---

# START_HERE — where to start

**Repository:** extella-agent-standards · **Company:** Extella (Chariot Technologies Lab) · **Owner:** Anvar (CEO)

## 1. Who reads this repository

**A machine, not a human.** Extella agents are built by Claude, Codex, and the apps that build
them. A human does not read these documents or fill anything in from them: they say what they
need, and the builder does the rest — including the agent's passport.

## 1a. Stage first, then everything else

The scope of checks is set by the **build stage**: `build` — a short mandatory set plus
add-ons by facts (client data, someone else's machine), `prod` — the full set. Ask the machine
and act on its answer:

```
python3 tools/stage_gates.py --stage build --json
```

No stage declared — it counts as `prod`. Stop rules apply at every stage.
The old names `demo`/`pilot` are synonyms for `build`.
Stage document: `BUILD_STAGES.md`, machine source: `stages.yaml`.

## 2. The single entry point

**`AGENT_BUILD_GUIDE.md`** — read it in full, that is enough to build an agent.
188 lines: what an Extella agent is, the nine decisions to make while building, the platform
canon, what to release together with the agent, and how to check yourself.

Everything else in the repository is **reference material loaded as needed**, not read
straight through. The list, with the "when needed" condition, is in §7 of the guide.

The specification is not the text but the **checkers in `tools/`**: each one has `--json`
with stable codes and `--selftest`. A rule that cannot be checked by machine is stated in the
guide as a build-time decision, not as a requirement.

## 3. The former reading order (for a human, if they still read it)


Read in exactly this order:

0. **EVOLUTION_PHILOSOPHY.md** — the frame: **why** the system is built this way. A short
   document, but without it the rules below look like bureaucracy. Main thesis: an agent's
   value is not created at the moment it's created, but over the course of its life, which is
   why our product is managed behavior change.
1. **AGENT_ARCHITECTURE.md** — the main standard: what an Extella agent is and the 25 mandatory
   principles. Until you've read it — you don't sit down to build an agent.
2. **EXTELLA_AI_ONBOARDING.md** — how the platform is built and its known traps (where people
   before you have already tripped).
3. **NAMING.md** — what the parts of the system are called (Extella Evolution, Agent Passport,
   Agent Genome, Evolution Console / Lab / Loop). Write and speak using these words — don't
   invent your own.
4. **BRAND_FOR_AGENTS.md** — the brand in an agent's interface: which words are forbidden,
   which colors are allowed, how the interface speaks. Checked by machine:
   `python3 tools/check_brand_copy.py <files>`.
5. **TEAM_PROTOCOL.md** — rules for working together as a team: who is responsible for what and
   how not to get in each other's way.

## 3. Before starting work

Fill in the checklist **checklists/DoR.md** — "are you ready to start".
If even one item doesn't check out — close it first and only then start.

## 4. Before release

Before the agent reaches the client:

1. Go through the checklist **checklists/DoD.md** — "is the agent ready to work for the client".
2. Fill in the agent's passport following the template **templates/agent_passport.yaml**.
3. Run the checker:

```
python3 tools/check_agent_passport.py my_agent.yaml
```

It will say whether the agent is ready or not, and list exactly what's missing.
Until the checker says "ready" — the agent does not go to the client.
For the Evolution Console and automation, use the same calculation in JSON, don't rewrite the
rules:

```
python3 tools/check_agent_passport.py my_agent.yaml --json
```

Every issue contains a stable `code`, `severity`, `path`, `message_ru`, `message_en`.

## 4b. Two rules that get forgotten most often

1. **On-screen explanation.** Every capability must have a "? How this works" button with the
   blocks: how it works · what is guaranteed · **what we do NOT promise** · who can disclose or
   roll it back. Use the ready-made ones: `templates/help_card.md` (what to write) and
   `templates/help_widget.js` (ready-made window code).
2. **Russian and English at once.** The interface, explanations, and error messages are made in
   both languages in one release. "We'll translate it later" doesn't count as done.

The passport checker will not let a release through if `limits` (boundaries), `help_surface`
(where the explanation is) and `languages: ["ru", "en"]` are not filled in.

## 4c. Agent Cabinet — appears by itself from the Agent Passport

Every agent must have an Agent Cabinet: the Agent Passport (what's declared), actual behavior,
and the Evolution Loop (change via draft → test → publish → rollback).
**You don't need to write it by hand** — it's assembled from the Agent Passport:

```
python3 tools/build_agent_cabinet.py my_agent.yaml --markdown
```

If you're building an **automation** (something the client installs as a whole: Agent 1C, a
lawyer, a travel agency), not a single agent — the passport is different:

```
python3 tools/check_automation_passport.py my_automation.yaml
python3 tools/build_automation_cabinet.py my_automation.yaml --markdown
```

Template — `templates/automation_passport.yaml`. Platform agents inside an automation are
described as **components**, not as separate objects (§6 of the cabinet standard).

The cabinet standard and an honest comparison with Microsoft Agent 365 (what we can do, what we
can't yet) — `AGENT_CABINET_STANDARD.md`. Interface render — `templates/cabinet_widget.js`.
Haven't filled in the boundaries and the explanation — the cabinet won't assemble: it's the same
gate as at release. `agent.platform_agent_id` links the passport to the live agent. Canonical
Shared Genes are declared with stable `gene_id`; consumers are not counted by display name.

## 5. Repository rules

- Documents can only be changed through a change Anvar approves. No one writes directly to the
  main branch.
- Every document has a version and a date; both are updated on any change.
- All questions go to Anvar.

---

Version 1.1 · 26 Jul 2026 · Document owner: Anvar
