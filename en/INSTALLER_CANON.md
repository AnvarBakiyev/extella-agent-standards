<!-- source: INSTALLER_CANON.md sha256:942304a443054cc5597bca3cc17726e5f87f0556dfecea1577a598873bde57cb -->

# One-button installer canon

**The document's canonical home is this repository** (`extella-agent-standards`).

Verified live on 15–20 Aug 2026 across three products: the Codex bridge, the Claude Code
bridge, and a local model (LM Studio). Each installs with one button on the product page and
goes through the path **page → user's device → working state** without a single call to a
paid model during installation.

Every point below is written from fact: next to it is what verified it and what breaks without
it. Almost every one was paid for by a real breakage on the tester's machine — so refuted
variants are left in on purpose; they're worth more than confirmed ones.

---

## Words that keep coming up below

**Scope** is the set of objects available to a specific agent; each agent has its own.
**Listing** is a product's card in the store. **Gate** is an automated check that blocks
rollout until a condition is met. **Pre-release** is a product version only the author can see.

**Installer** here is an Expert (the agent's server-side function) that performs the install
step by step. It executes on the user's device, where the Extella app is installed, and
returns a JSON string on every call.

---

## 1. Six model-free steps, each with its own name

The install is broken into short steps, each with its own action name: `preflight`, `install`,
`credentials`/`model`, `bridge`/`server`, `configure`, `verify`. Plus a separate `status` — a
re-read of the state.

Rules common to all steps:

- **No step calls a paid model.** Every response carries the fields `model_called: false`,
  `agent_called: false`, `paid: false`. The page treats the response as successful only if all
  three equal `false`. This is how it's verified that the button doesn't spend the user's plan
  during install.
- **Steps are idempotent.** Calling an already-completed step again doesn't break the install,
  it confirms it. Hence the recovery strategy: on a failure or a pause, it's enough to press
  the button again, and the install continues from the missing step.
- **`status` is not part of the list of "completed" steps.** It isn't performed and doesn't
  stay done — it's a re-read of the rest plus a live health check. An early version reported
  `verify: false` right after the check had returned "ready" — the status contradicted the
  fact.

## 2. The installer's version rides along in every response

Every response contains the `setup_version` field. Without it, you can't tell "the fix didn't
help" from "an old version is responding".

Measurement lesson, 18 Aug 2026: the tester had version 3.2.4 on screen, but pasted terminal
output captured before that version; the investigation burned a round of back-and-forth before
it became clear the versions were different. Since then, the version is visible in every
response and in the text of every refusal.

## 3. A refusal names the next step, not just the problem

A refusal message that gives no way to understand the next action is a defect, even when the
code is formally correct.

Before-and-after pairs from live investigations:

| Before | After |
|---|---|
| "Failed to verify sign-in to Claude Code." | "Sign in to Claude Code: run `claude auth login`, then retry." |
| "The current Extella account is unavailable." | "There's no Extella key on this computer. The app doesn't put one on disk: open Library → System → Tokens, create a token, and save it to `~/.extella/api_token.txt`." |
| "Claude Code is not installed." | "Claude Code was not found. Searched in: `…directories…`. If it's somewhere else, send the output of `which claude`." |

A hardware refusal names both numbers: "there's enough memory (32 GB), but only 1 GB free on
disk, and the model needs 22" — not a generic "not enough space".

## 4. The token is read from four sources in order

The installer needs an Extella account access token. The user doesn't enter it and doesn't
create the file by hand. Reading order (canon `store_app/update.py`):

1. **the process environment** — `os.environ["EXTELLA_API_TOKEN"]`. The app puts the token into
   the executing Expert's environment; this is the standard source.
2. **the file** `~/.extella/api_token.txt` — the app writes it itself on sign-in.
3. **`launchctl getenv EXTELLA_API_TOKEN`** — if the token was already set by a previous
   install.
4. **the app config** `~/extella_wizard/app/config.json`, the `auth_token` field.

Measurement lesson, 18 Aug 2026, on the tester's machine: the first three sources were empty,
yet the Expert executed — meaning the app was authorized, and the token was sitting in exactly
the fourth one. Only the first three had been implemented; hence the rule: if the Expert works,
one of these sources must contain the token, and all of them must be read.

**Only the token is taken from the config, not the agent identifier.** The config may have a
different agent set, and a foreign identifier gives "no key" on a key that exists.

Separately: injecting the token into the environment **isn't consistent across machines** — on
one machine the app puts it there, on another it doesn't. This is a difference in app version,
so relying on a single source isn't possible.

## 5. A gate on hardware AND on disk before a long download

Checking only memory isn't enough.

Measurement lesson, 19 Aug 2026: a 22 GB model download broke off at the eighth gigabyte,
because only 1 GB was left on disk, and `preflight` was only looking at memory. Now the model
is chosen by memory and by free space with a margin, and a refusal names both numbers. The
ladder of models (strong → medium → refusal) picks the top one that clears the hardware.

## 6. A long step runs in the background and is polled, not waited on

The platform defers a call that runs longer than roughly 51 seconds: instead of a result, a
link to a background task comes back, and the page has no way to wait for it (probe-Expert-
with-sleep measurement, 18 Aug 2026; the platform accepts the `timeout` field in the request
body and ignores it, and there's no path for the page's token to wait for the task).

So the one long step — the model download — is built like this:

- the step starts the download in a separate process and **returns immediately** with the
  `finished: false` field and progress;
- the page polls the step once every 20 seconds and draws the progress;
- completion is determined by the installer (`finished: true`), not the page.

The "model is on disk" flag is read by running `lms ls`: partially downloaded files don't show
up in the list, so the read is honest.

## 7. A fuse against endless restart

A dead download isn't a reason to spin an endless loop. An attempt counter per profile: two
deaths in a row produce an honest error with a log tail, not a silent restart. Download state
files are kept separate per profile, so one profile's progress isn't shown as another's.

## 8. An external program has to be both found and made runnable

The app starts from a window, not from a terminal, and inherits a short `PATH`. So looking for
the program via `PATH` almost always misses.

Measurement lesson, 17–18 Aug 2026, on two machines:

- the program (`claude`, `codex`) sat in a Node version manager's directory —
  `~/.nvm/versions/node/<version>/bin` — which isn't in the short `PATH`;
- reading `PATH` from the login shell didn't help: `zsh -l` reads `.zprofile`, but not
  `.zshrc`, and the version manager is configured precisely in `.zshrc`.

A search that works: a hardcoded list of directories **plus** a direct scan through version
managers' directories (nvm, fnm, n, volta) **plus** the `PATH` from an interactive login shell
(`zsh -ilc`).

And even that isn't enough: finding the program is half the job. `claude` from a version
manager is a script that needs `node` next to it. The search directories must end up in `PATH`
**at the moment the program runs**, otherwise it crashes with "node not found" right where it
was itself found.

## 9. Read the status in the response, not the exit code

Measurement lesson, 18 Aug 2026: for a signed-out user, `claude auth status --json` prints
correct JSON `{"loggedIn": false}` and exits **with code 1**. Checking the exit code turned the
most ordinary state — "not signed in" — into "failed to verify sign-in". The output is read
first; the exit code is looked at only when the output is unreadable.

## 10. The version tag in the code must match the listing's version

Measurement lesson, 18 Aug 2026: replacing the version string without checking that it was
actually there silently failed to fire, and the installer's responses named a stale number for
three versions in a row. Now the rollout checks the `SETUP_VERSION` tag in every Expert against
the listing's version and refuses to publish on a mismatch.

## 11. An Expert record is bound to the scope of its last save

`save_expert(global=true)` doesn't create a record shared across all scopes. Reading by name
works from anywhere, but execution only works from the scope that saved the record last; from
the rest, "Expert not found" comes back. Reproduction: seven steps between two scopes (see
`plugins/.../DEFECTS.md`).

Consequence for the installer: you can't hand out one Expert to every agent through a single
`global:true`. The working workaround is to write a separate `global:false` copy into every
scope being changed, and verify each one **by running it**, not by reading it: a record reads
as correct while still not running (measured on one scope out of 38). Distribution happens in
batches, because a full pass over dozens of agents goes into a deferred task (see point 6).

## 12. The page's gateway only sees an Expert from the installed version

Measurement lesson, 19 Aug 2026: a new Expert called through `/api/app-agent/run` responds with
**502**, even though it works through a direct call to the core. Any name outside the installed
version's snapshot gives 502, not 404. So the button on the page will only work once the
installed app has been updated to the version where the Expert appeared.

## 13. Writing the config is atomic and keeps a backup

Switching the app's config (for example, to a local model) is written to a temporary file and
moved into place with a single `os.replace`, while the previous config is kept alongside it
with a timestamp. This way, a partial write never leaves the app with a broken config.

## 14. Shared code — one source, copies get rebuilt

Installers for several products share common code (program lookup, token reading, service
install). The shared code lives in one canonical place, and the copies in the products are
**rebuilt** from the canon, not edited in place. The `check_onboarding_copies` and
`check_platform_client_copies` gates block rollout while a copy lags behind the canon. Order on
a mismatch: update the canon first, then rebuild the copies.

---

## The product page's contract

The page runs inside the app's frame at a local address. What it's able to pass to the
installer is an attack surface, so:

- **A whitelist of fields, not copying.** Only `action` and pre-named fields (batch number, a
  profile out of two allowed values) get through to the installer. Numbers are cast to a
  number, enum values are checked against exact literals.
- **There's no `timeout` field in the request** — the platform ignores it (point 6). Setting it
  would be making a false promise.
- **A deferred task is recognized before the result is parsed**, and it's named in plain words:
  "the stage is continuing in the background, wait and press again".
- **Progress is visible step by step**, with the step's name, not a frozen "Connecting…".

Inside the app's frame, the install can be driven by a host-module receiver, while the page
draws the steps from progress events. Events don't replay after the frame reloads, so the
outcome is recovered by re-reading `status`, not by waiting for a message.

---

## What this canon gives the next product

Every point above was a breakage on a live machine. The next installer, built to this canon,
gets them solved before its first run at a user's: it finds the program wherever it actually
is; reads the token from whichever source is filled in on that machine; doesn't spend the plan
during install; survives a slow download and a lost connection; tells the user the next step
instead of a dead end; and doesn't silently drift apart from the shared code.
