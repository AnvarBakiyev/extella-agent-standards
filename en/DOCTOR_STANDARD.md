<!-- source: DOCTOR_STANDARD.md sha256:cf83f61875dfe9657a8ef840a2a517e8660470aeda72be7e82c430e14e4c5109 -->

# Environment doctor — a self-check standard for apps (proposal)

**Source**: practice from the "Recruiter" product (Chariot Technologies Lab), September 2026.
Over a month of support we collected 11 families of installation and runtime errors on
someone else's device: an old Python, libraries that failed to install, a foreign OS, a busy
port, several versions at once, permissions and cloud folders, network and clock skew, scopes
that were never granted, a sleeping device listener, encodings, an update on top of old data.
The buyer sees every one of them as "nothing works."

## Rule

The app must check its own environment **itself** and report trouble **in words inside the
product** — not to a console nobody opens. Three moments:

1. **Install** — the installer fixes on its own whatever it can without admin rights (find a
   working Python on the device and restart itself with it; install libraries into its own
   environment and re-read them; bring up the panel and check that it is the one on the port).
   What can't be fixed — one precise command for the buyer's OS. Slow checks (network,
   executor) don't hold up the person: the product runs them.
2. **Every launch** — a quick check (<0.5 s, local only). Trouble → a banner with one action.
3. **Moment of refusal** — a platform refusal carries a "Check and fix" button: a full check
   (network, the executor device via an actual expert call) and an answer of "what to click."
   Plus a "Copy environment report" button — versions, check results, the tail of the install
   log; no secrets or client data; it never sends itself anywhere.

## Ready-made core

`tools/extella_doctor.py` — universal, with no tie to any specific product: the app describes
what to check with a passport dictionary (`min_python`, `modules`, `data_dir`, `min_free_mb`,
`panel_port`, `platform`, `max_clock_skew`, `executor`, `scopes_probe`). The file carries over
to any product as is. Live measurements in Recruiter: a quick check takes 0.38 s; the full
check catches "Target … is unavailable" (a sleeping listener) and advises launching the
Extella app.

Every check is tagged with a failure class from `FAILURE_CLASSES.md` (`class`: A/C/E/F), so the
report reads like a map, not a list.

## Teeth: machine self-check

A promise to "check the environment itself" without a watcher that can fail on its own is a
mistake that will come back (`FAILURE_CLASSES.md §G`, canon H74). That's why the doctor has a
CLI and `--selftest`:

```
python3 tools/extella_doctor.py path/to/product          # quick check
python3 tools/extella_doctor.py path/to/product --full   # plus network/clock/permissions/executor
python3 tools/extella_doctor.py --selftest               # run inside run_all_gates.sh
```

For each guarded class, `--selftest` plants trouble into the passport/environment (an old
Python, a missing library, no space or permissions, a cloud folder, a foreign program on the
port, an unreachable platform, clock skew, a sleeping executor, a 403 with no permissions) and
requires red, and green on a clean passport (§G.4, the leftover check). The product describes
itself with `doctor_passport.json` or the `доктор:` key in `MANIFEST.yaml`; no passport — the
doctor answers "there was nothing to check" (not "passed"). How to call it — `tools/GATES.md`.

## Why this is a standard, not one product's feature

90% of the checks know nothing about the subject domain — that's the pain of every app in the
store. One shared doctor means: the same words across every product, one error class fixed
once, and "it doesn't work for me" turns into "the doctor said: check the date on your
computer."
