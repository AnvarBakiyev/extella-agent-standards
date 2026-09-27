<!-- source: CONTRIBUTING.md sha256:2eeba7b278191b3e56654f8a36ebae122e606c1bfd225eb01554165c3d271f1a -->

# How to make changes here

The repository is public: **anyone in the world can see it, only members with
write access can write to it.** An outsider can fork it and send a proposal;
the owner decides whether to accept or reject it.

## Order

1. Branch off `main`, make the change, commit.
2. Pull request. GitHub itself runs **all gates on a clean machine**.
3. Red gates — no merge. This isn't a formality: the very first run on a clean
   machine found two gates that were green only for the author (a missing
   library; a test was waiting on a response that only happens on macOS).
4. One approval — and merge.

`main` is protected: **history can't be rewritten, the branch can't be
deleted.** The owner (admin) can merge something urgent directly — this is a
deliberate loophole for one person, not a mode of working.

## What checks itself

```bash
bash tools/run_all_gates.sh
```

Run this **before** submitting: it's exactly the same as CI — it runs this
same script. How many checks are in the set is reported by the script itself
at the end of the run; there's no number in the text because it goes stale
with every new gate (on 25 Sep 2026 this said "29" when the actual count was
74). Every check can fail on purpose
(`--selftest`) — a gate that can't fail isn't a gate.

## Three rules the machine doesn't check

* **A refuted rule is removed not just from the text but from the gate too.**
  Otherwise it keeps living and keeps obligating people.
* **Acceptance is what a human sees on screen**, not response codes and files
  existing. A report of "200 ✓ file ✓ service ✓" was already true of every
  link and false about the whole.
* **Editing someone else's file** is flagged, reverted down to the byte, and
  left as a copy alongside.

Details — `README.md`, canon — `DEPLOY_REQUIREMENTS.md`, build order —
`AGENT_BUILD_GUIDE.md`.

## If you're editing text, not code

You don't need to install git or figure out branches. It's all done in the
browser, five steps:

1. Open the file on github.com and click the **pencil** (Edit this file).
2. Make your edit.
3. At the bottom — **Commit changes**. In the dialog choose **Create a new
   branch** (GitHub will suggest a name itself) and click **Propose
   changes**.
4. The proposal page will open — click **Create pull request**.
5. From here on, don't do anything yourself: the checks will run on their
   own, a green checkmark will appear, and the owner will merge the edit. A
   red checkmark means something in the files doesn't line up; write in
   chat and we'll sort it out.

**In the commit, write WHAT changed and WHY.** Not "edits", but "the error
state color led to the palette: #D4944A instead of blue, there is no blue in
the palette." A month from now this line will be the only explanation.

**You can't write directly to `main`** — that's built in on purpose, so no
one can touch someone else's work with one wrong click. The platform refusing
a direct write is not a bug, it's a rule.

### What matters to know about design rules

The source of appearance rules lives separately — `DESIGN_CODE.md` at the
root of this repository (the former `DESIGN_RULE_FOR_APPS.md` and
`UX_CANON.md` sit in `archive/` as history), and here lies a **copy** for
those building agents. Its completeness (fonts, palette, scales,
prohibitions) is checked by `tools/check_design_rule.py`.

That means the edit needs to be made **in the source**, and carried over
here. If you fix it only here, the gate turns red and the fix won't merge:
that's protection against the two places quietly drifting apart.


## Several chats editing the canon at the same time — two rules

Measured 22 Aug 2026: ten chats worked in ONE git folder and in their
branches assigned H-numbers from memory. Result — branch switches were
chasing each other underfoot, other people's files ended up in other
people's commits, and H34–H39 and H51–H53 got duplicated. The gate only
catches a duplicate once it's merged into main; between branches in flight,
it stays silent.

**1. Each chat gets its own working directory (git worktree), not a shared
folder.**

```bash
git -C ~/Documents/Extella/extella-agent-standards worktree add \
    ~/Documents/Extella/standards-<chat> -b <chat>/canon origin/main
```

From then on the chat works only in `standards-<chat>`. History is shared
(origin), but the working tree and HEAD are its own. Branch switches stop
chasing each other, and other people's edits don't end up in your commit.
Remove your own directory when done:
`git worktree remove standards-<chat>`.

**2. Get the H-number from the checker, not from memory — and accounting for
branches in flight.**

```bash
python3 tools/check_canon_numbers.py --резерв
```

Returns the number above all those taken in ALL branches of origin, not just
main. The `check_canon_numbers` gate (in the full run) won't let a duplicate
merge in, but `--резерв` lets you avoid a collision ahead of time.
