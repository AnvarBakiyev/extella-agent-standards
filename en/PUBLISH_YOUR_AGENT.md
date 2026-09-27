<!-- source: PUBLISH_YOUR_AGENT.md sha256:747d4cf296681112cd37a65300caa83343ee70cb6ca478f26288adc8afa41e73 -->

# How to publish your agent so it installs into Extella from a link

This page is for a person. You built an agent to the standards and want a colleague or
a client to install it with a single link, without our involvement.

Both **public and private GitHub repositories** work.

A private one needs a GitHub access key — the storefront will ask for it once and remember
it: the refusal window will show an "Add GitHub key" button. Read access is enough. The key
is stored encrypted on the account; the storefront never shows it again and never hands it
to agents.

---

## What the repository must contain

Exactly one required file: **`agent_passport.yaml` at the root**.

This is not bureaucracy or "one more config." The storefront uses it to understand **exactly
what it is installing**: what the agent is called, what it does in the client's words, which
model it runs on, what it does NOT do, and how to roll it back. Without it the install won't
start — and that is deliberate: without a passport the card would go up nameless, and in a
month "Agents" would be a pile nobody can sort out.

Template: `templates/agent_passport.yaml` in this same repository.
A live filled-in example: [extella-1c-agent](https://github.com/AnvarBakiyev/extella-1c-agent)
— look at its passport, it's a real one, not a showcase.

---

## Check yourself before you hand out the link

```bash
python3 tools/check_agent_repo.py https://github.com/<owner>/<repository>
```

The answer comes in two forms, and both are honest.

**"OK to install"** — with the agent's name and what it does. The link can be handed out.

**"Not OK to install"** — with an exact list of what is missing. Not "checks failed," but
"model not specified," "not a single honest line about what the agent does not do." Fix from
the list and run it again.

Run this **before** you write to your colleague. Otherwise the first person to see the
refusal will be them.

---

## What most often fails

**Model isn't Qwen.** Client-facing agents run only on the platform's Qwen 3.7. Claude is
paid, and an agent built on it will spend someone else's money at the client's site. The gate
catches this.

**Empty `limits`.** You need at least one honest line about what the agent does **not** do.
This isn't a formality: a person who doesn't know the boundaries will trust the agent with
too much. "Does NOT write to the database, read-only" is a good line. "Works fast" is not a
line.

**`what` written as a function name.** The `what` field is what your capability gets found by
in search. Write it in the client's words: "finds customers with a birthday coming up and
prepares a greeting," not "scans the database by the `birthdate` field."

**No `rollback`.** How to restore state if the agent did the wrong thing. If a capability only
reads, say so: "not needed, state doesn't change." That's an answer too.

---

## How it gets installed: two channels (clarified 12 Aug 2026)

**Colleague, internal channel:** Storefront → **Plugins** → paste the repository link. The
storefront checks the passport, installs the agent, and puts the card in "Agents" and on the
Desktop.

**Buyer, canonical channel:** the **Extella OS** store (os.extella.ai) — publish as a
pre-release through the OS form, acceptance (buy it for yourself, first run from a clean
state), then Publish; a human clicks the button. Full procedure in `DEPLOY_REQUIREMENTS.md`,
sections "Product type decides scope" and "Before Publish."

If the passport doesn't pass, the install won't start, and the person will see the same
reason the gate showed you. They won't have to guess, and they won't come to us about it.

---

## If you're rewriting something that already worked

Compare against the old behavior, not against what you expect. "The new one started" proves
nothing: we caught two defects that way in a single evening, found only by a line-by-line
cross-check against the old version — one would have wiped the client's data, the other
would have kept two of five plugins from starting. Neither showed up on an ordinary run.

Write down what the old one did. Check that the new one does the same. A discrepancy is
either explained in words or fixed — it never stays unexplained.

And separately: **if your agent downloads anything, the download must carry a checksum**,
and on a mismatch the install must stop. Silently installing "almost the right" code is worse
than not installing it: it will break later, and not on your machine.

---

## What not to do

**Don't put tokens, keys or passwords into the repository** — neither yours nor the client's.
The repository is public: whatever lands there stays there forever, even if you delete it in
the next commit. Secrets come from configuration on the device; the passport only says WHERE
they live.

**Don't put client data in it** — exports, databases, correspondence, IIN, invoices. Made-up
examples are enough.

**Don't hardcode a specific agent's identifier as a fallback in the code.** It will work for
you and fail for the client, and the agent will silently drift onto someone else's. Nothing
mandatory means an honest refusal, not a substitution.

---

## Found a mistake in the standard itself — file a Finding

Does the gate require what the rule forbids? Doesn't the template fit a real agent? Doesn't
an example from the guide work? That's not "my hands are clumsy," that's a finding — and we
collect them deliberately, so the standard gets fixed against real builds, not our
imagination.

File an issue in this repository using the **"Finding"** template: what's wrong / where /
what it hits. The repository is private, so you can write anything there, including security
holes. Accepted findings move into `evidence/findings.yaml` and turn into fixes to the
standard.

---

## If something didn't install

Tell us **three things**, and the investigation takes minutes instead of hours:

1. the link to the repository;
2. what `check_agent_repo.py` showed;
3. the storefront build fingerprint — it's at the bottom of the Desktop, selectable and
   copyable.

The third item isn't a formality. Half the discrepancies between "it works for me" and "it
doesn't for me" come down to different builds: there's no auto-update yet, the storefront only
updates when the installer is run again.
