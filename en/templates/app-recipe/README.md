<!-- source: templates/app-recipe/README.md sha256:3e4556f276ac03a610136553a59e9245754b98bd5ddba485521cac9272c29e8c -->

# Recipe for a new Extella app

This is a standalone template. It isn't tied to published apps and doesn't change them.

## 1. Start

Copy the `app/` folder: `index.html`, `styles.css`, `extella-bridge.js`, `app.js`. It
already has:

- one clear task on the screen, an action, and a result output;
- cards, a form, status, a table, and states;
- a single dispatcher for requests to Extella;
- a local demo mode: the interface can be checked without an expert;
- accessible test identifiers `data-testid`.

Open locally: `python3 -m http.server 8080 --directory app`, then
`http://localhost:8080`.

## 2. Design

The tokens live in [`app/styles.css`](app/styles.css). Principle: one warm accent, one
system color, a soft surface hierarchy, numbers aligned as in a table. The empty state
explains the next step; waiting shows the specific action and a cancel; error shows the
reason and a retry; done shows what changed and where to look.

Never use: rainbow gradients, glass panels stacked on glass panels, badges for the sake
of badges, dozens of status colors, huge hero headings in a working window, icons with
no label, endless scroll carousels, pseudo-AI text like "the magic is happening",
random percentages/charts, and animations that hide a change in the data.

## 3. Connection to the platform

All the exchange is collected in [`app/extella-bridge.js`](app/extella-bridge.js): a
single `ExtellaBridge`, many only explicitly allowed expert names, a single
`{ok, data, error}` response. The interface code in [`app/app.js`](app/app.js) knows
nothing about the transport. The method was captured from inside a live OS window on
22 Sep 2026 and verified there (canon H106):

1. The OS substitutes the window's key into `index.html` in place of `{{app_token}}`.
   Outside Extella the placeholder stays as is, and the app runs in demo mode.
2. The bridge itself calls `POST https://os.extella.ai/api/app-agent/run` with the body
   `{app_token, expert_name, params, targets?}`. The `etb_run_expert` protocol and
   `parent.extellaDesktop` **do not work** in the OS window: nobody listens for the
   first, and the sandbox blocks the second.
3. The platform doesn't tell the page which device it's on — the app's **dispatcher
   expert** names it (`routeExpert`; the sample
   [`experts/my_app_where.py`](experts/my_app_where.py) reads `~/.extella/device.txt`
   and returns `pageRoute.targetId`). The first call to it goes without `targets`; the
   bridge pins every following call with `targets:[device]`. Storage in the window is
   blocked by the sandbox, so this memory lasts only until the window closes.
4. The first call (to the dispatcher) goes without a device — the platform picks the
   machine. If it picks a computer signed into a different account, the bridge says so
   in words instead of a "syntax error" (H104).
5. The expert is saved to the agent the app is published from (`--source-agent`), and
   the rollout requests both `expert.run` **and** `device.run` — the second is not
   included in the first.

For a task longer than 10 seconds, the button becomes disabled immediately,
"Calculating…" appears next to it, the last valid version of the result stays visible,
and after 90 seconds the user sees an honest "no confirmation received" and a "Retry"
button. Don't show "done" before confirmation. If the platform pushes the job to the
background (around the 51st second), the bridge says exactly that — retry the
idempotent step a minute later.

## 4. Speed

The main win is not drawing everything from scratch every time. Tokens, components, the
bridge, build/check, and acceptance scenarios get reused. First I build a working local
calculation and interface, then one Extella route, then export/integrations.
Independent checks run in parallel: syntax, the calculation core, the UI contract,
visual snapshots.

Typical path: 15–25 minutes for the skeleton and a real scenario, 20–40 minutes for the
model/settings, 15–30 minutes for integration and verification, then acceptance on a
clean device. This is a guideline, not a promise: external experts and the store can
add waiting.

I deliberately cut: complex animations before real data shows up, a universal form
builder, a second design system, network dependencies for the base screen, and export
before the user sees a correct result.

## 5. Extella pitfalls

| Symptom | Workaround rule |
|---|---|
| `Origin: null` | This is the page's standard sandbox. Don't call `parent.extellaDesktop`; use a scoped `app_token`. |
| `Failed to fetch` / internal address | Don't `fetch` from the page to localhost or internal IPs. Talk to the device only through `https://os.extella.ai/api/app-agent/run`. |
| `Execution Error … (<container>, line 1)` | This is the H104 signature: the platform picked a computer from a different account. Show the reason, a Device ID field, and a "Work through this device" button; verify it with an explicit `targets`. |
| The device wasn't resolved, without the H104 signature | Show the reason in words and leave retry available; don't open the manual field. |
| Need to remember the Device ID | Don't use `localStorage`: the sandbox answers with `SecurityError`. Keep the ID only in the window's memory and ask for it again on reopening. |
| The key expired | `app_token` lives two hours; ask the person to refresh the Extella window. |
| Blank page at `/` | The zip must have `index.html` at the root, not in an extra folder. Checked by `tools/build.py`. |
| Hung `prompt()` | Don't use `prompt`, `alert`, `confirm` in the interface. Only your own modal windows or built-in fields. |
| Response larger than 200 KB | The expert returns a short summary and writes large data to the target app/file; the panel gets a link, an id, or a summary. |
| `async` / Worker behaves unstably | The critical path is plain async functions in the main window. A Worker is only an optional speedup with a synchronous fallback. |

## 6. Verification by another person

You can click through the panel itself automatically:
[`tests/smoke.mjs`](tests/smoke.mjs) launches a browser, changes input, checks the
scenario, the waiting state, and the error. For the expert, it uses `host=mock` mode,
which simulates Extella's response. This catches regressions before rollout.

But the full path on another device can't honestly be considered verified by a headless
test alone. Minimal acceptance: a clean profile/another device → open the installed app
→ go through the main path → check every button → one successful and one failed expert
response → close and reopen → check that the result is saved where promised. In
`qa-checklist.md` there's a ready-made checklist.

## 6b. Show the owner — with proof, not just words

Right after a closed rollout:

```
python3 tools/show.py <listing_id>
```

The script asks the test stand to open the app **as an outside buyer** on live
`os.extella.ai`, drops a screenshot into `dist/`, and reports in plain words: whether it
opens or not, what's going on with the buttons. The person sees their thing live and
proof that it will open for others — not the phrase "all done".

The test stand is set with `EXTELLA_BENCH_URL` and `EXTELLA_BENCH_KEY` (or
`~/.extella_bench.json`). No test stand — the script doesn't fail: it prints the app's
address and how to set up a test stand with one command. The full rule is H66 in
`DEPLOY_REQUIREMENTS.md`.

## 7. Before rollout

See [`qa-checklist.md`](qa-checklist.md). Build: `python3 tools/build.py`; quick
prohibitions and structure: `python3 tools/check.py`. The
`tools/deploy_prerelease.py` script only publishes a closed listing and requires a
token from an environment variable; it doesn't store secrets in code.

## 8. What can be copied

- [`app/index.html`](app/index.html) — the whole panel;
- [`app/styles.css`](app/styles.css) — the palette and components;
- [`app/extella-bridge.js`](app/extella-bridge.js) — the bridge, the device, and
  waiting;
- [`experts/my_app_where.py`](experts/my_app_where.py) — the device dispatcher;
  [`experts/my_app_expert.py`](experts/my_app_expert.py) — a sample working expert;
- [`app/app.js`](app/app.js) — an example of scenarios, states, and a local fallback;
- [`tools/build.py`](tools/build.py), [`tools/check.py`](tools/check.py),
  [`tools/deploy_prerelease.py`](tools/deploy_prerelease.py) — build, checks, and
  closed rollout;
- [`tests/smoke.mjs`](tests/smoke.mjs) — the automatic smoke test.
