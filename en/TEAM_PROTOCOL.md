<!-- source: TEAM_PROTOCOL.md sha256:eb09014b584f6502b4ad25fe46587e85c99f876a414a9ec1f5f0b97a30d240a4 -->

# Extella multi-agent team protocol (approved by the owner on 24 Jul 2026)

Read by EVERY session (Claude, Codex, any AI developer) before starting work.
Alongside this file: `EXTELLA_AI_ONBOARDING.md` (the platform canon) and `docs/WORKBOARD.md`
(the live board).

## Roles and zones

| Role | Who | Zone | What's NOT allowed |
|---|---|---|---|
| **Integrator (hub)** | the Claude session "core-portal" | main of every repo, releases, PINs for colleagues, install-all, VPS, canons/memory, coordination, escalations to the platform | — |
| **Wizard Engine (R&D)** | Claude sessions engine/* | ui/wz_build, wz_agentic, wz_process, perf, codegen convergence | pushing to main, pins, installers, VPS |
| **Production hardening** | Codex | branches codex/*, QA regressions scripts/check_*, acceptance | pushing to main, publishing releases |
| **Toolbar and cards** | the Claude session "Toolbar 2" | toolbar.js, the card registry/sync/tombstones, plugin products, register_app_cards | pins and install-all (prepares scripts, the integrator wires them in) |
| **Satellite features** | the remaining Claude sessions | their own feature in their OWN worktree | the shared clone, other people's files |

## Ironclad rules

1. **One valve to the outside.** main, a signed release, pinning a SHA in install-all, anything on
   the VPS — only the integrator moves these. Handing off work = a branch + a report
   (symptom/cause/files/gates/rollback).
2. **Dev sessions work ONLY in a git worktree/branch** (`.claude/worktrees/...` or a branch off a
   fresh origin/main). No one but the integrator edits in the shared clone. Anything uncommitted
   in the shared clone = an incident.
3. **Announce your work.** Before starting a task — a line in `docs/WORKBOARD.md` (task · session
   · branch · status). Finished/handed off — update the line. The integrator clears the board.
4. **The file rule (No.8).** One file — one owner editing it at a time. Before editing: `git
   fetch` + a look at WORKBOARD; a collision → the second one waits for the first one's commit.
5. **Gates are mandatory** before handing off: `preflight_ui.sh` ("ALL CLEAR"), `smoke_e2e.py`
   (all green), and for the engine — the live `live_wizard_agentic_e2e.py` green TWICE IN A ROW.
6. **The platform canon** (EXTELLA_AI_ONBOARDING.md, the repo's CLAUDE.md): client agents are Qwen
   only; never print secrets; the platform sends "not found" as an HTTP 500 — that's "empty," not
   a lost connection; 5xx/timeout ≠ failure (retry); a mute refusal = a defect — the reason must
   arrive in words.
7. **Private code is not published on GitHub** — it's distributed as a zip from
   files.82-115-42-21.sslip.io (a secret scan is mandatory).
8. **Colleagues are not testers.** We reproduce things on the test account
   (~/.extella_test_token) and with artifacts; we ping a colleague with at most one final update
   command.
9. **Codex coordination** — through handoff files in the repo (docs/CODEX_*.md): repro, cause,
   direction, acceptance criterion. Between Claude sessions — cross-session messages with a
   mandatory reply-report.
10. **Deploying the toolbar override — ONLY from origin/main.** The file
    `~/Library/Application Support/extella-desktop/toolbar.js` is placed exclusively through
    pack/RAW/install-all (= origin/main). Deploying directly from a side clone or worktree is
    FORBIDDEN: on 24 Jul a designer's side build (a branch cut before 23 Jul, without the main
    fixes) overwrote the working override directly at ~22:22 → the storefront printed raw JSON. If
    you have your own toolbar clone — rebuild and deploy ONLY from a fresh origin/main, once your
    own work has already been merged into it. Diagnosis when "the storefront broke": FIRST thing,
    `grep -c hasSnapshot;grep -c onlyKnown` on the deployed toolbar.js vs the pack — a version
    mismatch is more likely than a code regression.
11. **The toolbar's release artifact is built ONLY from a clean clone of origin/main**, never from
    a local worktree with assets. On 25 Jul the integrator built the Studio from a Codex worktree
    with an OLD `profit-growth.html` → the artifact diverged from the canon (extra unescaped
    `</script>` — a storefront incident class). The right way: a fresh `git clone`/`git checkout
    origin/main` in a clean directory → `node toolbar/build.js --release-artifacts` → cross-check
    the sentinels + `grep -c '^</script>'`=0 → deploy. Dev sessions' local worktrees are forbidden
    as a build source.
12. **Want to change the protocol itself** — through the integrator, and with the owner's word.


## What to send to the shared channel, versus handle yourself

**The rule appeared on 17 Aug 2026** after a message where **one new fact** came wrapped in ten
lines of process: "saving to memory," "waiting for reconnection," "checking now." The fact was
valuable — the token isn't present in the expert's environment on every machine. Everything else
was a report of steps that the reader didn't need.

**The bar is simple: send the result, not the step.**

| send | don't send |
|---|---|
| a **defect** that reproduces: what you did, what you expected, what happened, on which machine | intermediate debugging steps |
| a **best practice**: what worked and is worth writing down for others | "saving," "waiting," "checking now" |
| a **fork**: two paths, where the choice changes the product | a request to confirm the obvious |
| a **refutation of the canon**: a rule that didn't work — this is the most valuable thing | retelling something the canon already has |

**Check the canon first.** `DEPLOY_REQUIREMENTS.md` — everything we've measured about the
platform; `LAB.md` — what we tried and why we closed it. Half the questions there are already
answered by a measurement, not an opinion.

**An hour of searching on your own first.** Didn't work out — write, but lead with what you've
already checked and what you've ruled out: that turns your message from a question into half a
solution.

**And the reverse rule for us.** A recipe verified on one machine cannot be handed out as
universal. That's exactly how I let a colleague down that same day: the mechanism for reading the
secret worked for the owner and didn't work for her, and the reply gave no hint of that
difference.
