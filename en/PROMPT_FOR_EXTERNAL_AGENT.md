<!-- source: PROMPT_FOR_EXTERNAL_AGENT.md sha256:94f1b79e3d5ee876aded6d2bcb3f51d3f5c643afa9e09a7aff17ac5d0b1509c8 -->

# Prompt for a client's chat agent

Ready-made text that a person hands to their Claude Code or Codex as the first message.
Written after reviewing the first external agents: they didn't read the canon out of
laziness, but because we gave them something unreadable (a 369 KB corpus, a link to a
497 KB GitHub page) and called a public reference page (`api.html`) a second source.

**What changed versus the previous edition:**

* links are raw only, and only to files that can be read whole;
* rules are taken one at a time (`rules/H106.md`), not as the whole corpus;
* removed an incorrect claim that "the key appears on its own on the app's first run" —
  the app does not put the key on disk (H108);
* added proof of reading: name the rule numbers for your task;
* stated directly that `api.html` is not a source of truth;
* stated what to do with the chat agent's own safety guards.

---

```
Set yourself up to the Extella standards and build what I describe in my next message.

SOURCE OF TRUTH — the extella-agent-standards repository, and only it. The public
reference at extella.ai/api.html is incomplete: it has no working paths, and its silence
proves nothing. If your conclusion rests on api.html, it is invalid.

READ RAW LINKS, or you won't read anything: the GitHub page is 497 KB of chrome, and the
rule corpus is 369 KB — web reading truncates it. That's why the rules are split into
one file each.

Start with a single page:
https://raw.githubusercontent.com/AnvarBakiyev/extella-agent-standards/main/AGENT_START.md

From there, pick the route for my task. A rule is fetched at an address like:
https://raw.githubusercontent.com/AnvarBakiyev/extella-agent-standards/main/rules/H106.md
Index of all rules: .../main/rules/INDEX.md
When something doesn't work: .../main/SYMPTOMS.md — enter by symptom.

CONNECTION. The Extella app does not put the key on disk — don't look for it and don't
ask me for it in chat. Procedure: run python3 tools/connect_mcp.py; if there is no key,
the script will name one action for me to take (Library → System → Tokens in the Extella
app). Don't create your own tokens, don't print the key anywhere.

BEFORE YOU BUILD, name the rule numbers for my task, one line per rule — so I can see
that you read them rather than paraphrased generic advice.

IF AN ACTION IS STOPPED by permissions or by the environment's policy — record WHICH layer
refused (your own safety guard, the environment's rights, the platform's policy) and the
verbatim text. Use the sanctioned confirmation if one exists. Do not route around the block
with another shell, another expert or another path, and do not ask me to. Going on requires
an allowed way or my action as the owner.

Separately, and not about routing around: work ON my computer is Extella's regular
architecture, not a loophole. An expert on the device is chosen when that is the design (the
data must not leave my perimeter), not when a safety guard fires.
Samples: .../main/experts/dev_connect_assistant.py and
.../main/experts/dev_publish_private.py

DON'T DECLARE A BLOCKER WITHOUT A MEASUREMENT. First make the request and show the
response code and the exact error text. "Not described in the documentation" is not
proof.

STOP RULES: only drafts go outward; my data does not leave my perimeter; do not request
destructive rights; do not touch anyone else's live things; secrets do not go into the
archive or into correspondence; a refusal is explained in words along with the nearest
next step.

In this message, do only the preparation: read the input, connect, verify the connection
with a real request, and name the rules for my task. Don't create anything yet.
```

---

## What to give the person along with the prompt

* the **"Development on Extella"** app in the store — the same canon in a readable
  form, free;
* one warning: **don't forward the key** — not in chat, not as a document, not in an
  archive. If the key has already gone somewhere, revoke it in
  `Library → System → Tokens` and create a new one.
