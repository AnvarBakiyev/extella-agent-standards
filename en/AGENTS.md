<!-- source: AGENTS.md sha256:7714515ed79efa140b78f5edbfcb85d65d07ad201e895ef3c10d7f948dfbdb59 -->

# For the assistant working here

This file is read by Codex and other assistants that have no skill mechanism.
Claude Code has the same thing as a skill, `extella-ui`.

## Single entry point

`README.md` — what to run, what to read without running. Then `DEPLOY_REQUIREMENTS.md`
section H and `BUILD_STAGES.md`.

## If you're building an interface — read this first

`skills/extella-ui/SKILL.md` in full. It has the rules of clarity, the Extella design code, a
screen skeleton and an acceptance checklist. Briefly, so it doesn't get put off for later:

- a screen answers three questions in five seconds: where am I, what's possible, what to do
  first;
- one task per screen, one primary action;
- four states are drawn: empty, in progress, refusal, done;
- waiting is visible before the call, cleared in `finally`;
- a refusal says what to do; "no data" is a legitimate answer;
- palette, fonts and scales are set by the design code, don't invent your own.

## The scope of checks is taken from the machine

```bash
python3 tools/stage_gates.py --stage build --json
```

The checks are themselves the specification. The text next to them explains the reason, but
the source of truth is the run.

## What's not allowed

Outward — only drafts; client data stays within the client's perimeter; no destructive
permissions; don't touch someone else's live system; secrets don't travel in the storefront
archive; a refusal is shown in words.

## Language rule

`WRITING_RULES.md`. Everything a human outside the team will read is written according to it.
Checked by machine: `python3 tools/check_writing_style.py file.md`.
