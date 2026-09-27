<!-- source: FAILURE_CLASSES.md sha256:163e9aa4005414f1a6c072a893d2a70af2a857784c3d453fe6543b82b9264aaa -->

# App failure classes — and what catches each one (proposed standard)

**Source**: 64 documented findings from the "Recruiter" product (Chariot Technologies Lab) over a
month of live buyer support. Numbers like No.NN are references into the product's findings log;
the classes themselves are universal for any store app.

**Rule of the standard**: what gets fixed is not the bug but the CLASS; a fix without a machine
watcher is a bug that will come back. A watcher guards the class with a rule, not with a list of
names.

A digest of 64 findings from a month of the Recruiter's log. Rule for reading it: what gets fixed
is not the bug but the CLASS; a fix without a watcher = the bug comes back. A watcher must guard
the class, not a list of yesterday's names (lesson No.63: a hardcoded list of "six functions"
missed the seventh).

### A. Build and delivery
| Class | Symptom for the person | Watcher |
|---|---|---|
| The build seam cuts out live code (No.51, No.63) | "the page/vacancy doesn't open," everything works locally | universal check: any function from the source that the build calls must survive |
| An edit without a rebuild, two sources for one page | "we fixed it, and nothing changed" | the "build matches source" gate; the panel is RE-READ after going up ("is this us?") |
| The archive carries secrets/personal data/junk | a leak, bloat | an explicit inclusion list + inspecting the contents BEFORE packaging |
| Publish "succeeded," but there's no version | a silently lost release | re-reading the listing after the write — the server's response is not a fact |

### B. Page
| Class | Symptom | Watcher |
|---|---|---|
| Dead handler / typo in onclick | the button "doesn't work" | wiring gate: every handler points to a function declared on the SAME page |
| Modal dead end with no way out (No.53) | the person is locked in the window | gate: if `add('active')` opened it, it must close somewhere |
| "Success" on screen without checking the response (No.49) | "deleted," but it's still alive | a code rule + confirmation tests |
| English stubs ("yrs", "Not provided") | scraps on a Russian screen | the stubs gate; model stubs get normalized into an honest, properly-Russian "Имя не указано" (Name not provided) |
| The screen didn't redraw on a view change (No.47) | "no candidates," but there are some | manually clicking through a run-sheet (not machine-catchable) |

### C. Page↔device bridge
| Class | Symptom | Watcher |
|---|---|---|
| A long call → "deferred, use task_id" (No.44) | a spinner and nothing | a TRANSITIVE gate: any method that reaches the model through a call chain must be in the LONG list (a hand-written list — people forget) |
| Request body >64 KB (No.50) | "one out of three résumés," a 400 | chunked transfer + an assembly test |
| A native OS dialog from a store page (No.45) | "the button doesn't work" | rule: the page is browser-based — files go through FileReader |
| The work envelope gets unwrapped further | an endless wait for the finished result | stop unwrapping at an object that has `state` |

### D. Data
| Class | Symptom | Watcher |
|---|---|---|
| Two writers overwrite each other (No.48, No.33/37) | silently lost work | a lock + merging with disk + a test "two processes, both writes survive" |
| Silently accepting garbage (No.39) | a candidate in a column that doesn't exist | dictionary-based validation + a refusal test |
| Personal data goes to the model | a standards violation | masking BEFORE the model + a test "the model didn't see it, the card does" |
| A new version on top of old data | a crash/corruption after an update | a data schema version + careful reading of both forms (No.33) |

### E. Platform
| Class | Symptom | Watcher |
|---|---|---|
| app_scopes weren't granted | the page is intact, every call is 403 | request BOTH permissions (expert.run + device.run) and re-read them after publishing |
| The purchase's agent has no key (No.32/38) | "bought it — doesn't work" | platform (PR #8); workaround: an agent-selection screen with a test run |
| The executing device is asleep (§22) | every call is a 500 "Target unavailable" | the doctor on every open + a "Check and fix" button |
| A form field gets ignored/becomes required; object ids die | publications break over time | re-read after every write; look up ids by query, don't store them forever |
| The expert runs under someone else's Python (No.43) | "No module named …" only for the buyer | sys.path pinned to the product's environment + the installer re-reading its libraries |

### F. The buyer's environment
Python is old / libraries didn't install / no disk space / no permissions / network is blocked /
the clock is off / the port is busy / the folder is inside cloud sync — ALL of this is caught by
the doctor (§ the "Environment Doctor" standard, PR #28): the installer fixes what it can on its
own, the product checks the environment on every open, and a refusal carries a fix button and a
report for support.

### G. Watchers and process (meta-classes — the most expensive ones)
1. **A watcher guards a list, not a class** (No.63) — any hardcoded list of names goes stale
   silently. Watchers are written as a rule ("any function…", "any method that reaches the
   model…").
2. **The watcher itself is broken or lies** (No.34, No.35) — a new watcher is run against a
   DELIBERATELY broken copy: if it doesn't fail on that, it isn't a watcher.
3. **Diagnosis without a measurement** (No.46) — "probably the limits" cost a day; rule: no
   conclusion without reproducing it first.
4. **Checking the ban without checking what's left** — "no emoji" comes back green on empty
   buttons; every ban needs a check that something live is left where the banned thing was.
5. **A write's response is not a fact** — everywhere: save_expert, add-version, launchctl, pip. If
   you wrote it, read it back.


---
Companion document: DOCTOR_STANDARD.md (the buyer's environment).
