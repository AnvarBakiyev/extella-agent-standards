<!-- source: SYMPTOMS.md sha256:7319e34939280ca239d9f5e0c36b8339ea812967f818f393635ac63c5c82307a -->

# Entry by symptom: what you see — where to look

The corpus has grown to several dozen sections, and it isn't read start to finish — it's read
once something has already broken. This page is the only door for that case: on the left, what
the person sees; on the right, the `DEPLOY_REQUIREMENTS.md` section and the first action.

A listing is a product's card in the store; the version belongs to it, not the other way
around. The word comes up often below, so it's named here once.

Rule for filling this in: **a row describes an observation, not a cause**. The cause lives in
the section; writing it here turns the page into a second corpus that starts to drift apart
from the first.

Completeness is guarded by a gate — an automated check run before rollout; here that's
`tools/check_symptom_index.py`. Every section of the corpus must be either in the tables above
or in the "no external symptom" list below: it cannot silently fall out of both.

---

## Nothing is visible

| what you see | where | first action |
|---|---|---|
| White window, nothing loads | H24, H24-bis | Check which sandbox door is needed and whether it exists |
| The window opened and stayed empty, no errors | H4, H27 | Check whether the page is writing to browser storage |
| Instead of the interface — a service response about a header | H52, H39 | Whether the product was opened by the page's direct address, not through someone else's app |
| The interface loaded, but there's no data | H61 | Check the permissions requested against the ones granted: an access refusal may have turned into emptiness |
| The product opened, but there's no local data | H51 | Check whether the archive part installed and whether the device binding was created |
| Microphone, camera, or download don't work | H32, H4 | Check the sandbox's set; it isn't what's blocking downloads |
| The button hangs the window, then a gray screen; server healthy, no 5xx | H84 | This is a renderer crash, not the server; acceptance must click through client surfaces |

## Responded with success, but there's no result

| what you see | where | first action |
|---|---|---|
| The operation responded with success, no effect | H38, H38-P | Re-read the object with a separate request; don't count transport success as the result |
| Deletion went through, the object is still there | H42 | Look at the "deleted" flag in the body, not the response code |
| An expert edit disappeared after reinstall | H35 | Release a new version: the version carries a snapshot |
| The edit is in the repository, but old code is running | H55 | Check which release is flashed into the expert itself |
| The purchase completed, the device is empty | H51 | Check the archive and the device binding |
| The response looked like a refusal, but the write went through | H38-P | Mark the start of the write before the request; start a retry with a read |
| In the panel, the request to the platform doesn't go out: "Failed to fetch", no response | H62 | Check whether the panel is sending the request directly instead of a message upward |
| CSPL language is registered, but the expert responds "tool not installed" | H68 | Check the service's PATH and the tool lookup inside the handler itself |
| The indicator is green, but sign-in doesn't work | H85 | The indicator must be a live ping, not just the fact that a key/session exists |
| The product page crashes: `agent_id` is empty | H89 | This is a legitimate "not deployed"; lead to Reinstall, don't crash |
| The script says "the app hasn't been opened yet", although it's open (Windows) | H90 | This build doesn't write the token to disk; seed the file once or align the build |
| The expert considers the listener absent (no device.txt) | H91 | State files don't live at a fixed path; check by a live response, not by the file |
| The gate fails the release over name duplicates across the agent's whole inventory | H92 | Check duplicates among the PRODUCT's experts; platform duplicates (id=null) don't stop the release |
| The product passed dev-smoke and crashed for the buyer | H69 | Run the final ZIP in a clean room: empty volumes, a cleaned PATH for the installed Expert |
| The install stalls: an external tool is "not found" from the service | H69 | The service has a trimmed PATH; look for the tool yourself and add its directory (same root as H68) |

## The response arrived, but it can't be parsed

| what you see | where | first action |
|---|---|---|
| Code 200, but the fields are empty or parsing crashes | H17 | Strip only named wrappers, parse the dict safely |
| Small responses go through, a large one doesn't work | H40 | Check the size: the response has a ceiling, and it isn't reported as an error |
| A live channel is treated as dead | H56 | Read the response by your own contract, not by a neighbor's envelope |
| The model responds with emptiness, no error | H50 | A short token ceiling and a reasoning model |
| A correct read returned 500 | H40 | Check whether it hit the size limit |

## Slow, frequent, expensive

| what you see | where | first action |
|---|---|---|
| Opening takes tens of seconds | H61 | One snapshot call instead of many small ones |
| Refusal on request rate, retrying doesn't help | H61, H28 | Reduce concurrency, show a named wait time |
| The stage goes to the background and doesn't return | H54 | Check whether the device expert returns a terminal value |
| The liveness check itself times out | H57 | Limit log reading: the check must have a constant cost |
| The queue hangs, although the task was closed long ago | H58 | An expired item is closed once; a late response doesn't revive it |

## Not what was expected, in the store and on the desktop

| what you see | where | first action |
|---|---|---|
| Two identical products on the desktop | H53, H60 | A page edit is a version change, not a new listing |
| After a release, people have the old icon or page | H36, H23 | Check the content on the server; the mismatch may be client-side |
| A new version went out to buyers without being asked for | H20, H26 | For a published listing, the version is public immediately |
| The icon leads somewhere wrong or nowhere | H5-quinta, H52 | Check the form of the shortcut's address |
| There are more versions and agents than products | H60 | Updating a purchase is a mode of the existing install |
| After publishing, the buyer keeps the old version, the author has the new one | H65 | Open the page with a new parameter and check which version arrives |
| The app is built, but nothing appeared in Extella; the person is waiting for instructions | H66 | Offer to show it yourself and carry it through to the window, without waiting for a command |

## Permissions, scopes, devices

| what you see | where | first action |
|---|---|---|
| "Expert not found" for one agent, success for another | H59 | Ask for global search in the request itself, don't rely on the record's flag |
| The button stays "in progress" for hours, the task counter grows on its own | H74 | Find the unbounded self-repeat; every poll is a task on the device |
| There are far more tasks than clicks | H74 | The watchdog outlived the handoff of the work — kill it with the same flag as success |
| The layout is broken for the person, but intact on the test stand | H75 | Open it at the width of the real app window: a narrow run executes different CSS |
| The button overlaps the caption, the heading breaks one word per line | H75 | Look for negative margins and a max-width wider than the parent |
| The expert is fixed, but the buyer has the old behavior | H76 | The version's scope is a code snapshot: a new listing version is needed |
| unexpected keyword argument with live new code | H76 | The buyer's path executes the copy from the version snapshot |
| A listing created by the product is a gray square on the desktop | H77 | Attach an icon in the publish-stream; get the tile from tools/bronze_icon.py |
| The person is shown the platform's raw response with a Python dict | H78 | Consolidate refusal translation into one function; keep the raw response in the log |
| One screen explains the refusal in words, another doesn't | H78 | Look for a second copy of the handler: copies drift apart silently |
| The app is created, but it isn't on the desktop | H79 | After the publish-stream, call the purchase-stream: it's what places the tile |
| The tile leads to a deleted page | H80 | The shortcut outlives the listing: remove it with a desktop-state write that omits it |
| The desktop looks empty through /api/desktop/items | H80 | The response comes in sections, not a flat list |
| The agent asks to be sent a token, the person doesn't know where to get one | H81 | The key is already on disk: python3 tools/connect_mcp.py |
| MCP shows "connected", but it's not there in another folder | H81 | add-json without --scope user writes to the folder's scope |
| Codex doesn't see Extella following the README instructions | H81 | Codex reads TOML [mcp_servers.*], not JSON mcpServers |
| The app broke after a module rebuild | H83 | The response shape isn't reproduced by the recipe: the gate must pin it down |
| The module built for one person and failed to build for another | H82 | A recipe without an imprint gives everyone their own result: freeze the first build |
| A module promises a capability the platform doesn't have | H82 | The passport must state the boundary before purchase |
| The button did its job, but nothing changed on screen | H72 | Read the raw response: the domain check may have been comparing the envelope's status |
| Everything shows as empty or zeros while the data is live | H72 | Strip the execution envelope too: the real response sits as a string inside `result` |
| The first step works, the next button is permanently disabled | H73 | Check the ids passed as an argument against the markup's ids |
| The expert is visible, but doesn't run | H43, H59 | Check the name's uniqueness across the account |
| The agent doesn't take the step, the tool is "not found" | H31, H44 | Use the tool's full name; an expert's name doesn't become a model function |
| The key is written, the product can't find it | H41 | Check whose scope it landed in |
| The work went to someone else's device, or a 500 unavailable | H34, H16 | Pass devices as an array; check whether the listener is up |
| The install requires GitHub access | H49 | The source's form and the public visibility of the distribution repository |
| The button check responds "nothing to click through" or repeats hooks | H63 | Mark actions with hooks; use explicit names for permanent locations |
| The agent needs a new system, and there's a temptation to grant broad access | H67 | Connect a CSPL domain: operations with effects, rights, and scope belong in the client's policy |

## Secrets and someone else's code

| what you see | where | first action |
|---|---|---|
| A search through storage returns a secret's value | H41 | A record's description must not carry a piece of the value |
| Someone else's script or extension next to the token | H33 | Three surfaces execute foreign code in the desktop's origin |
| A secret ended up in the product's assets | H3 | Bundle assets are public by construction |
| The product asks to save a digital signature/key password so it can "sign in by itself" | H93 | Automate the session, not the key: signing is a standard on-device dialog, reuse tokens |
| The expert crashes with "unexpected keyword argument", although the code is correct | H94 | The runtime calls the first top-level function; nest helper functions inside the main one |
| The app shipped in only one language | H95 | Bilingual RU+EN is mandatory; check_translation doesn't let through a section without English |
| Diagnostics printed a token, session, or CSRF | H71 | Print only a whitelist of fields; don't output the raw response or environment |
| Before a delete/recreate, the tool's output is unclear | H70 | Ambiguous means "stop", not "no data"; parse fail-closed |
| The listener on Windows crash-loops, the device is forever "Target unavailable", the logs show "no wheels with a matching platform tag" | H96 | Check the package's architecture and version: ARM has worked since 20 Sep; still run the "will it install for someone else" acceptance on x86-64 |
| `agent/create` responds 401 "user_id missing" with a live token | H97 | The token has no user (global/service); create with a personal token |
| The buyer clicks "install", the window responds "The installer did not finish" with no reason | H98 | Check the composition: archive ⇄ installer ⇄ install.py at the root; check `check_installable` |
| The installer crashes with "No such file or directory: launchctl" on Linux/Windows | H98 | install.py is nailed to macOS — needs a platform branch and a fallback path that "prints the command" |
| The app's window in the OS is blank or "nothing happens": the expert call doesn't return, the device shows "—" | H106 | The OS window doesn't listen for `etb_run_expert` and doesn't allow access to `parent.extellaDesktop`; call through `{{app_token}}` + `/api/app-agent/run` (`templates/app-recipe`) |
| `invalid decimal literal` / `invalid imaginary literal (<container>, line 1)`, the text changes from one run to the next | H104 | The code didn't decrypt on the device: wrong key. Check the call's `pin` against the listener's `--crypto-key`, then the account |
| The device responds with HTTP 500 "Target … is unavailable" | H104 | The device doesn't exist or isn't reachable — unlike a 200 with a syntax error (wrong account) |
| The screen shows zeros, although the data exists or is unknown | H99 | A zero is the claim "empty"; if you don't know, say the reason in words |
| The app opens slowly or white while it looks for a route to the data | H100 | Route first, render second; remember a dead route |
| The product doesn't work without the internet, a model, or a third-party service | H101 | There must be a working state with no external dependencies |
| After a rollout, people have the old version or a mix of versions | H102 | A full run, fingerprint verification, a clean state before rollout |
| Works for the developer; for the buyer — console windows, garbled text, the process dies with the session (Windows) | H103 | Process launch flags and console encoding; test on a clean machine |
| The NCALayer/Java window doesn't react to clicks, the password went into the wrong window | H105 | Drive Java windows by keyboard; the person enters the password after checking that the window is in the foreground |

| The work went to the wrong machine, although a device was specified | H107 | `targets` takes the DEVICE identifier, not the record's; the list is candidates in order, the first available one is taken |
| `Target … is unavailable` while the machine is on | H107 | A record's `target_id` was passed instead of `device_id`, or the record is dead — check the kind of identifier |
| A call without `targets` went to a different device than the one shown as default in the interface | H107 | The default is per-agent and gets changed by other chats — name the machine explicitly |
| The agent's task ran on the wrong computer | H107 | There's nothing to pin an agent run to: `run_agent` has no `targets`; an expert with `targets` does that job |

| The chat agent on a new machine doesn't see Extella, "connect an account" | H108 | The app doesn't put the key on disk: run `dev_connect_assistant` on this machine, or create a token in `Library → System → Tokens` |
| Wrong text was removed, but it meets the person again in another file | H110 | The ban lived in one file's self-check; a rule about text is closed by a search across the whole tree — `check_assistant_onboarding` |
| A new product from a template was born with the wrong hint, one that had long been fixed | H110 | The templates in `tools/new_product.py` weren't covered by the gate — check text in the generators too, not only in finished files |
| The sections are in English while the buttons and the demo stay Russian | H117 | Only the content was bilingual; the shell's strings were scattered across the template. Their place is `store_app/shell.json`, and a ratchet holds the remainder |
| On Windows a tool falls over immediately: `UnicodeEncodeError: 'charmap' codec can't encode character` | H118 | The Windows console runs in `cp1252` while the tool prints Russian or "✓". The entry point must switch output to UTF-8; the newcomer's path is guarded by `tools/check_windows_console.py` |
| The script died with a NameError AFTER the action had already gone through | H120 | An edit removed a name that was read twice: the first place was fixed, the second was not. The branch after success never runs on a dry run — caught by `check_undefined_names` |
| A publish "went through" but the version is not in the listing; or the publish Expert answered 400 "At least one tag is required" | H119 | Publish success is a version read back, not a `done` event; tags are mandatory. The sample is `experts/dev_publish_private.py`, guarded by `tools/check_publish_expert.py` |
| Three purchases of one product — three agents in the account | H119 | The repeat-purchase contract is not described (letter to the platform §55). Do not blindly reinstall a product that has an agent — install the version by hand |
| `expert/save` hangs with no answer | H5-quater | A timeout ≠ a refusal. First look the Expert up by its EXACT name in the same profile and agent — it may have been saved; only then retry. Do not require an embeddings key from every newcomer: that is not proven (letter to the platform §56) |
| The whole app is built, yet a large or a second file never reaches the Expert on the device | H106 | A file in the window ≠ a file on the device. Before the full build, prove an end-to-end slice: the person picks a file → the Expert reads it on its device → returns something checkable. The platform has not named a supported path for several/large files (§57) |
| A path in the output is glued together wrong, a letter is missing, no error | H115 | zsh read the colon as a history modifier: `$BR:tools/x` with `BR=refs/heads/main` gives `mainools/x`. Curly braces save you, quotes don't; the defect doesn't reproduce in bash |
| The gate judges a copy from a dead branch, although the work is happening in another one | H114 | There are many clones of the product on the machine, one is live. The live one is determined by the freshest HEAD, not by name order or by a conventional directory |
| A run over someone else's tree found nothing, and the gate still isn't accepted | H114 | A run without a subject isn't acceptance: there was nothing to look for. Acceptance counts from the second run, once the subject appeared |
| The gate says "fails", but the file is written and sitting right there | H114 | The gate opened the wrong copy: there are several copies of one file on the machine across different clones, and the first one alphabetically is taken. Pick the canonical copy explicitly |
| A path in a field is checked by its form, but there's no file at it | H114 | A locator counts as verified only once it's been opened. If the path is wrong, create the file, don't just fix the text |
| The gate is green in the suite, but run it by hand and it's red | H114 | `run` only runs the self-check; a live run is a separate line. The accepted share is held by the `check_gate_acceptance` ratchet |
| The check hangs for minutes with no output | H114 | Somewhere inside it there's a live model call or a subprocess with a timeout of hundreds of seconds; such a gate will never once be run |
| The check prints "SKIPPED" and returns zero | H114 | The subject isn't there where the check was run: emptiness passes for success. A live run is done where the subject lives |
| The text states one number of checks, the machine has another; people prepared from the text | H113 | A number about another file goes stale silently: either the gate counts it, or the text names the command. Caught by `check_counted_claims` |
| The file size in the text is about 1.6 times smaller than the real one | H113 | Characters were counted, not bytes: an undercount for Cyrillic. Web reading cuts by bytes |
| "Expert not found" for an expert name taken from the English text | H112 | The name was translated "by meaning": `dev_connect_assistant` in Russian, `dev_connect_agent` in English. Expert names are translation anchors, checked by machine |
| The agent read the entry point, but the person doesn't find those facts in the app | H112 | The entry point and the app drifted apart; the pitfalls section declares the covered rules, checked by `check_entry_app_agreement` |
| The Russian and English pages say different things, and the translation gate is green | H111 | The fingerprint was stored only for the original: it doesn't see edits made to the translation. Two fingerprints are needed — of the original and of the translation itself |

| Publishing to the store is "impossible": no `os_token.txt`, `my-listings` responds 404 | H109 | There's one key, the header differs: `X-Extella-Token` for the store on `os.extella.ai`, `X-Auth-Token` for the core on `api.extella.ai` |

| A key, people's data, or broken code ended up in the repository | H115 | The guardrails aren't in place: install `templates/repo-starter/pre-commit`, revoke the key, close the repository |

---

## Sections with no external symptom

They aren't looked up by a breakage: they're the corpus's own structure, the rollout order, and
the writing rules. The list exists so that a section's absence from the table above is a
decision, not an omission.

**Rollout order and composition:** H1, H8, H9, H10, H12, H14, H21, H45, H46, H47.

**How the platform is built:** H2, H5, H5-bis, H5-ter, H6, H7, H11, H13, H15,
H29, H30, H48.

**Techniques and working rules:** H37, H64.

**Verification and tests:** H86 (a test hits the prod path — a real click, a real name), H87
(destructive tests never run on the owner's production base), H88 (patches as raw strings,
dedup, verification afterward).

**Desktop extensions:** H19-bis, H19-ter, H19-quater, H19-quinta, H19-sexta.

**A finished fix doesn't reach the buyer:** the gate holds `PROVISIONING_SOURCE_DRIFT`, the
store still has the old version, the fixes sit locally — H116 (release by standing clearance,
not by per-version permission).
