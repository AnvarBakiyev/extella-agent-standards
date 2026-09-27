<!-- source: templates/help_card.md sha256:3ce2a63de5077a6f109a4a4551e72fc031037f85e9f9bf59ec5203290a620e7a -->

# Template for the "? How this works" explanation (mandatory for every surface)

Fill in four blocks — **in Russian and in English at the same time** (rule §3.26).
Ready-made working window code: `templates/help_widget.js`. A live example in the
product: the `XTL_HELP` reference in the Builder's interface (5 filled-in entries — can
be viewed as a reference).

The rule is simple: **an explanation without the boundaries block is worse than no
explanation at all.** The client must learn a capability's limit from us upfront, not
after the fact while working.

---

## Block 1. How it works — steps (3–4 items)

What the person does and what happens in response. No technical terms.

| RU | EN |
|---|---|
| 1. … | 1. … |
| 2. … | 2. … |
| 3. … | 3. … |

## Block 2. What's guaranteed

Only what has actually been verified and can be shown. No "usually", "as a rule",
"almost always".

| RU | EN |
|---|---|
| • … | • … |

## Block 3. What we do NOT promise — MANDATORY BLOCK

At least one honest boundary. The source is facts, not imagination: the format matrix,
known limitations, dependencies on external systems, cases where the capability
honestly stops.

Good example wordings:

- "Images and scans aren't read — data in a photo will stay there."
- "Works from an export; a live source is connected as a separate step."
- "The build sometimes asks you to retry: code preparation isn't 100% predictable. A
  retry is an honest stop, not a breakage."
- "There's no role separation yet — a \"view only\" access level can't be granted."

| RU | EN |
|---|---|
| • … | • … |

## Block 4. Who can disclose the result or roll back a change

Who has access to the source data, who confirms the action, how to go back.
If the capability changes nothing and discloses nothing, this block can be omitted.

| RU | EN |
|---|---|
| • … | • … |

---

## How to embed it (3 steps)

1. Connect the canonical `templates/help_widget.js` from the pinned version of
   `extella-agent-standards`; don't maintain a separate copy of the logic in the
   product.
2. Add an entry to the reference: the surface key + the four blocks in two languages.
3. Put a button on the screen: `? How this works` → `openHelp('key')`, and call
   `helpFirstTime('key')` when the surface opens — so the person sees the explanation
   automatically the first time.

## How this is checked

- In the Agent Passport (`templates/agent_passport.yaml`), every capability has
  `help_surface` (where the explanation is) and `limits` (boundaries, at least one
  line) filled in.
- `agent.languages` contains `ru` and `en`.
- The checker won't let a release through without these fields:
  `python3 tools/check_agent_passport.py мой_агент.yaml`
