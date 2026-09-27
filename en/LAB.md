<!-- source: LAB.md sha256:c6e34d072a2c9893b416f84b7c985fd38bdebd1c1c3bf0330776b707c673001f -->

# Lab: what we tried and how it turned out

**This is not canon.** Here are measurements and conclusions about things that worked but are
**not proven as a product**. Reading is fine; acting on it only if you've answered "why" yourself.

Rule for the split: `DEPLOY_REQUIREMENTS.md` gets what was verified **on a live buyer or a live
refusal**. What was verified only on ourselves lives here.

---

## Editions (the publishing house). Closed 17 Aug 2026, code removed

**What was built and measured.** An edition was assembled from several listings; the installer
bought whatever was missing on its own; the storefront showed the composition and status;
everything ran on the buyer's machine. Measurements: installing the set — 11 seconds, page-to-
device — 8–16 seconds, acceptance went through with a live run.

**Why it was closed.** Not a single buyer besides ourselves ever installed an edition. The
assembled "Silent Cabinet" (board, diagrams, reader) was pulled by the owner's decision on
16 Aug 2026:

> it's still just a set of separate apps that the user could install on their own anyway

**The conclusion that's worth more than all the mechanics.** Before bundling a package out of
other people's programs, answer in one sentence: **what can the agent do here that the app itself
cannot?** No answer — no product, just a list of links. What sells isn't the packaging, it's what
the agent does with the contents: "break down this contract," "draw the process I just described,"
"what changed in the new edition."

**The code was removed entirely** — the tools (`check_edition`, `check_compose`,
`deploy_edition`), the `templates/edition/` templates, and the `editions/` folders. Recoverable
from git history: look at commits before 17 Aug 2026. Only what we're responsible for stays in the
repository. **27 Sep 2026:** finished editions and product cards (`editions/`, `products/`) were
moved, along with their history, into a separate `extella-editions` repository. What stays here
are the standards, the templates (`templates/edition/`) and the tools; the tools take the path to
an edition as an argument and don't assume a folder in this repository.
