# Extella Agent Standards

How we build, ship and operate AI agents on the [Extella](https://os.extella.ai) platform.

**These are working standards, not a style guide.** Almost every rule here was bought with a
real incident: a product that could delete the buyer's agent, a task that ran on a colleague's
laptop with someone else's data, a verification step that could never fail and therefore
verified nothing. Where a rule exists, the incident behind it is written down next to it.

The corpus is in Russian — that is our working language. This page tells you what is here and
how to start; the documents themselves you can read with any translator, and the machine-readable
parts (gates, stage definitions) are language-independent.

## Who this is for

- **Machines.** Claude, Codex, or any application that builds agents. The main guide is written
  to be executed, not admired.
- **People shipping products on Extella** — as a reference for what breaks and why.
- **Anyone curious** how a small team keeps a fleet of AI agents from quietly lying about
  its own state.

## The two questions that decide everything

Before writing a line, two questions determine how much work applies:

**1. How is it delivered?** Store page (`page` field, runs sandboxed on Extella's web) ·
store archive (installer, runs on the user's machine) · embedded component (ships inside
another product, no storefront of its own). Different channels, different requirements.

**2. Where is it in life?** `build` — from first line to a working thing at the customer:
**2 gates**. `prod` — sold to any buyer, a mistake is now mass-scale and monetary: **21 gates**.

Extras are switched on by **facts, not labels**: customer data appears → masking; the product
lands on someone else's machine → passport, narrowed rights, state contract.

Ask the machine rather than reading prose:

```bash
python3 tools/stage_gates.py --stage build --json
```

## Six stop-rules that apply at every stage

Fast does not mean anything goes. These are cheap to obey, and violating them is what makes
fast work dangerous:

1. **Outbound writes are drafts.** Emails, payments, publications are prepared by the agent
   and sent by a human.
2. **Customer data stays in the customer's perimeter.** Fine on a demo — the customer gave it.
   Never into the platform cloud, a storefront archive, global scopes, or another customer's demo.
3. **No destructive rights.** No `delete_*` on a customer-facing agent without a written reason.
   A purchased product once shipped able to delete the buyer's other agents.
4. **Don't touch what's alive and not yours.** Your own agent evolves — with a trace and a way
   back. Other people's objects don't change at all.
5. **Secrets don't travel.** The archive reaches the buyer whole; bundle assets are public.
6. **Failure is visible in words.** A blank screen is a defect at any stage.

## Where to start

**One entry point: [README.md](README.md)** (Russian) — it is written for an assistant to
execute and links everything else. There is no separate "getting started" file.

| File | What it answers |
|---|---|
| `AGENT_BUILD_GUIDE.md` | how to build one — read it whole |
| `BUILD_STAGES.md` | stages, stop-rules, how a building chat should behave |
| `DEPLOY_REQUIREMENTS.md` | delivery channels, sections A–H, acceptance before publishing |
| `PROMPT_UPDATE_AGENT.md` | the prompt we hand to building chats |
| `tools/` | the gates — **the actual specification** |

**The gates are the spec, not the prose.** If a rule can't be checked by a machine, it is
written as a decision to make, not a requirement to satisfy. Every gate has `--selftest`;
`bash tools/run_all_gates.sh` runs them all.

## What is deliberately not here

**Passports of our live products.** They would expose the composition of our account. The
repository ships one anonymised example, `passports/EXAMPLE_agent.yaml`; point the gates at
your own with `EXTELLA_PASSPORTS_DIR`. A gate that finds no passports says so loudly rather
than passing quietly — a check that cannot fail is worse than no check.

**Customer names and data.** None appear anywhere in this repository, by rule.

## Status

Living document, revised as the platform moves — sometimes several times a day. Dates in the
text are real: they tell you how old a claim is. Measurements are labelled as measurements, and
where we were wrong, the correction stays in place instead of the original quietly disappearing.

Owner: Extella (Chariot Technologies Lab).
