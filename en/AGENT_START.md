<!-- source: AGENT_START.md sha256:d1330566eac1996cb747e00eca5b2ac9579f12f630608971ad4c60491330ea36 -->

# Agent start: one page, then by address

You're connecting a person to Extella and building on it. This page is the entry point. It's
small on purpose: everything else is taken **one file at a time**, not all at once.

## Reading rule (this is what tripped up the first external agents)

**Take raw links, not GitHub pages.** Measurement 25 Sep 2026: the repository page is 497 KB of
styling, the raw README is 31 KB. The rule corpus `DEPLOY_REQUIREMENTS.md` is 369 KB: reading
it over the web truncates it, and the agent never reaches the rules. That's why the rules are
laid out one per file — each one reads in full:

    https://raw.githubusercontent.com/AnvarBakiyev/extella-agent-standards/main/en/rules/H106.md

Index of all rules: `rules/INDEX.md` — it has the number, topic, and link.

**`extella.ai/api.html` is not the source of truth.** It's public reference material, and it's
incomplete: working paths (calling an expert from a page, publishing, pinning to a machine)
aren't described there. The reference's silence proves nothing. The source is this repository.

## Task-based route

| Task | Read (in order) |
|---|---|
| Connect to Extella on this machine | `rules/H108.md`, `rules/H110.md`, then `tools/connect_mcp.py` |
| Build an agent and its capabilities | `rules/H5.md`, then `AGENT_BUILD_GUIDE.md` — it's large, take it section by section |
| A page-type app in an OS window | `rules/H106.md`, `rules/H107.md`, `rules/H54.md`, `rules/H17.md` |
| Publish to the store | `RUNBOOK_STORE_PUBLISH.md`, `rules/H109.md`, `rules/H20.md` |
| Installer and delivery to a device | `INSTALLER_CANON.md`, `rules/H98.md`, `rules/H103.md` |
| Interface, copy, brand | `WRITING_RULES.md`, `BRAND_FOR_AGENTS.md`, `DESIGN_CODE.md` |
| Product bilinguality (RU+EN) | `rules/H95.md`, `rules/H111.md` |
| **Something's not working** | `SYMPTOMS.md` — entry by symptom: what you see on screen → where to look |
| What's proven vs. what's the lab | `README.md`, the status section; `LAB.md` — read, don't execute |

## Ten traps everyone gets stuck on

1. **One key, different headers.** For the store (`os.extella.ai`) — `X-Extella-Token`; for the
   core (`api.extella.ai`) — `X-Auth-Token`. No special file is needed: any valid account key
   works. → `rules/H109.md`
2. **The key doesn't appear by itself on a new machine.** The app doesn't put it on disk. The
   person creates the key in `Library → System → Tokens`, or the `dev_connect_assistant` expert
   makes the connection. → `rules/H108.md`
3. **An OS window doesn't listen for `etb_*` and doesn't report the device.** The page calls
   `POST os.extella.ai/api/app-agent/run` with `{{app_token}}`. → `rules/H106.md`
4. **The dispatcher expert names the device**, and from then on every call is pinned with
   `targets: [device_id]`. There's nothing to pin an agent run to. → `rules/H107.md`
5. **App permissions are granted separately.** `403` means "not allowed," fixed in the app's
   card, not in the code.
6. **A deferred run is not an error.** The platform defers work at around the 51st second:
   "running" ≠ a result — state is read with a separate, lightweight expert. → `rules/H54.md`
7. **Channel limits:** request body up to 64 KB, keep the response under 200 KB, up to 30 calls
   per minute. Files are read by an expert on the device, not by the browser.
8. **The response arrives wrapped twice**, and a Python dict is not JSON. → `rules/H17.md`
9. **`invalid decimal literal (<container>, line 1)`** is not a syntax issue: the code didn't
   decrypt on the device, the key didn't match. → `rules/H104.md`
10. **An agent created via the API answers `pro_key_required` until the provider and model
    are configured in the Extella interface.** This is NOT "an API agent doesn't talk": per a
    training participant's report of 28 Sep 2026, after Qwen was configured in the interface
    that same agent answered. Our own probe has not confirmed it yet — so what is stated here
    is a condition, not a ban. Experts work either way. → `rules/H107.md`

## First actions

```
python3 tools/connect_mcp.py          # connection; if there's no key, it names one action
python3 tools/stage_gates.py --stage build --json   # how many checks this work needs
```

On Windows, `python3` may be called `py -3`. If the instruction didn't work — that's a fact for
us: send the exact output, and we'll fix the canon.

## What proves you've read it

Before you build, name **the rule numbers for your task, and one line on each**, from the table
above. That's cheaper than four days of correspondence: the first external agents declared "the
platform can't do this" exactly where the rule had already been written and measured.

## How to argue with the canon

If a measurement contradicts a rule, bring the platform's exact response: which call, which
headers, which code. The canon is corrected by measurements, and half the rules here came about
exactly that way. Hypotheses without a measurement don't make it into the canon.
