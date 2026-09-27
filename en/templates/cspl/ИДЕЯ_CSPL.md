<!-- source: templates/cspl/ИДЕЯ_CSPL.md sha256:9abbdcade855d781dcd3075890f275faaace0312410a15b659fd1e90388cea6e -->

# CSPL as a product: the idea, what is already done, and what to build next

A document for handing off to another chat. Everything labeled "verified" has been
verified by running it, not by reasoning; measurement dates are given alongside.

## The idea in one sentence

CSPL is needed not where the agent lacks capability, but where it lacks trust. The
client is not afraid the agent won't be able to do something — they are afraid the
agent will be able to do too much. CSPL answers exactly that: **the model sends the
name of an operation, not code**; the effect is known before execution; the rights
live with the client and never enter the prompt; anything dangerous goes through
approval tied to the plan's fingerprint; a receipt remains afterward.

Hence the rule for selecting domains: **take the ones where the deal runs into fear,
not functionality.**

## The generating machine: domain × effect

Functions are not invented, they come from an intersection. The ladder of effects is
one for all domains:

`read → export → draft → write → post → delete → development`

For any system the question comes down to one thing: where is this client's red
line. That is the answer to "what functions are there" — not a list, but a matrix.

## What already exists and works

**CSPL-1C is a live product.** A limited set of operations over 1C, five
implemented: `system.health`, `metadata.list`, `metadata.describe`, `query.preview`,
`query.execute`. Verified by running it on 27 Aug 2026: the `plan` phase returns a
fingerprint and does nothing; an unknown operation and `UPDATE` in the query are
rejected by the schema; writing, deletion, and config patching are rejected by
policy; execution without approval does not go through.

**The core and two new domains — built and verified.** A measurement on live
CSPL-1C: **81% of its code does not depend on the subject domain**. That part has
been factored out into the core (`templates/cspl/core.py`, 222 lines): the envelope,
the two phases, the plan fingerprint, policy checks, approvals, receipts. A domain
now costs an operation registry, adapters, and a default policy:

* `domain_files.py` — 128 lines, self-check `selftest.py`;
* `domain_mail.py` — 130 lines, self-check `selftest_mail.py`.

Both self-checks pass on real files and must be able to fail.

**The canon is recorded** — `DEPLOY_REQUIREMENTS.md`, H67: a new subject domain
connects via a domain, not via broad access.

## What the build showed (two findings that save time)

**A plan fingerprint must not include the phase.** Otherwise the approval taken at
the `plan` stage will never match execution, and writing becomes impossible. Caught
by the self-check on the very first run. In live CSPL-1C this was done correctly
from the start — verified by comparing the plan and execution fingerprints; they
match.

**A product-level prohibition is set with two locks.** The right is switched off in
the rights, and separately the effect is marked forbidden. Then a mistaken
re-enabling of the right does not open up the action. This is how sending mail is
built: the canon "a human sends it" stopped being a wish in the instructions and
became part of the domain's design.

## Domains where Extella already has money or pain

| domain | why the client needs it | where the red line is |
|---|---|---|
| 1C (exists) | reconciliations, reports, data | writing and posting documents |
| mail (exists) | contract negotiations | sending — human only |
| files (exists) | parsing the client's documents | writing and deletion |
| bank statement | allocate payments in 1C | posting into the database |
| ESF / KGD | cross-checking invoices against the state registry | submitting the document |
| government procurement | analyzing lots, assessing the customer's risk | submitting a bid |
| CRM | pipeline, churn, tasks | changing a deal, emails to the client |
| telephony | analyzing calls, service quality | access to recordings — personal data |
| HR | reviewing applications | responding to a candidate |
| warehouse | stock levels, shortages | write-offs |
| client's database | analytics | everything except reading |

## Five modes of use — more valuable than the domains themselves

1. **Approval as a product.** "The agent prepared it, the human approved it" — a
   workflow the client already runs on paper. CSPL turns it into a button.
2. **The receipt as a report.** Every step leaves a trace with the plan's
   fingerprint — a ready-made artifact for audits; it is exactly what removes the
   objection "we won't let AI near our data."
3. **Policy as an appendix to the contract.** The policy file is human-readable and
   attached to the contract.
4. **Acceptance of rights.** The test stand checks not only that the app opens, but
   also that the declared operations match the policy — that is, the product does
   not ask for more than it promised.
5. **Evolution of the class.** Changing the shared handler advances the whole class
   of Experts without rewriting each one (`AGENT_ARCHITECTURE.md`, item 7).

## What is proposed to build

**The first candidate — "Rights Control Panel."** The app shows the client exactly
what the agent is allowed to do and what has already been done: domains, the ladder
of effects, locks, the list of receipts, manual edits to the policy. It makes an
invisible advantage visible, requires nothing external, and is built on the
ready-made core and two domains.

**The second candidate — "bank statement."** Read the statement as a file, prepare
the allocation, posting is left to a human. A direct continuation of the pilot with
accountants, hits an existing pain point.

## Rules mandatory for whoever continues this

* **A domain declares the effect before execution** and honestly marks what is not
  implemented: a refusal of "not done yet" is understandable to a person, "unknown
  operation" looks like a breakage.
* **The policy lives with the client**, does not enter the prompt, and is not
  overridden by the agent's server-side instruction.
* **A domain's self-check must be able to fail** — otherwise it proves nothing.
* **A change to the shared handler is checked as a migration of the whole class**
  (`AGENT_ARCHITECTURE.md`, § 3.17), not as an edit to one expert.
* **A wrapper needs a `def`.** A nohup-style wrapper without a `def` will not pass
  the expert-save validator (`AGENT_BUILD_GUIDE.md`).
* **A skill is pinned to a device.** State `targets=["<device_id>"]` in the agent's
  rule, otherwise the default routing will send the run to the VPS, where the tool
  doesn't exist.
* **Parallelism does not speed things up, it makes them worse** when you hit the
  rate limit: 120 requests per 60 seconds — parallelism of eight slowed the work
  down and caused retries (H61). Stay below the limit, save what is confirmed, and
  do not start a new batch after a refusal.

## Where the code is

`templates/cspl/` of the standards repository: `core.py`, `domain_files.py`,
`domain_mail.py`, `selftest.py`, `selftest_mail.py`. Run the self-checks from this
folder: `python3 selftest.py` and `python3 selftest_mail.py`.
