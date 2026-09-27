<!-- source: DESIGN_CODE.md sha256:69aea0121f585192ae92aaebf21a15431e6c6bb81b3ed39783ad15dbbf0ff6e7 -->

# Extella Design Code

**Status: canon since 31 Jul 2026. Supersedes previous rules (Source Sans 3, radius 4–6, mono-caps labels).**

**This document's home since 04 Sep 2026 is this repository** (`extella-agent-standards`). The author and
owner is the designer; changes are made at her word. The previous home, `extella-toolbar-src`, is closed.

This is not an inspirational document but a working corpus. The rule is simple: **if the decision
isn't here, it doesn't exist.** A new screen, panel, modal or plugin counts as done when it passes
against this file in full.

The document describes Extella OS windows (the desktop, the store, app windows), app panels, the
Library and the Builder — that is, everything a person sees. Values are given as tokens; a
hardcode in place of a token is a defect, not a minor issue.

---

## 1. Color

The canvas is warm, not white. One cool accent marks the system, one warm accent marks action.
There is never a third: if a third one shows up, it displaces one of these two.

### Light theme (primary)

| Role | Token | Value |
|---|---|---|
| Page canvas | `--bg` | `#FAF9F5` |
| Card, modal surface | `--s1` | `#FFFFFF` |
| Second surface (headers, tabs) | `--s2` | `#F5F3EC` |
| Third, fourth | `--s3` / `--s4` | `#EFECE2` / `#E5E1D4` |
| Ordinary border | `--bd` | `#D7E0DC` |
| Accented border | `--bd2` | `#B7CEC9` |
| Primary text | `--tx` | `#0A0A0A` |
| Second-level text | `--tx2` | `#2A2A2A` |
| Third-level text | `--tx3` | `#6E6E6E` |
| **Action** (buttons, what gets clicked) | `--act` | `#A5632A` deep bronze |
| **System** (active states, labels, trust marks) | `--a` = `--petrol` | `#2F6B66` petrol |
| Warm brand (decoration, categories — where there is no text) | `--brand` = `--act-decor` | `#C57E33` |

Amended 14 Aug 2026, based on contrast measurements (a design decision). The previous values
failed AA: `#8C8C8C` on white was 3.4:1, white on `#C57E33` was 3.3:1, against a norm of 4.5.
Now labels at `#6E6E6E` are 5.1:1, buttons at `#A5632A` are 4.75:1.
Rule: **there is never text on light bronze `#C57E33`** — it lives in decoration, category
stripes and marks, where there is nothing to read. Button hover is `#8F551F`.

### Dark theme

`--bg #0A0A0A` · `--s1 #141414` · `--s2 #181818` · `--s3 #1E1E1E` · `--s4 #262626` ·
`--bd rgba(243,238,229,.09)` · `--bd2 rgba(243,238,229,.18)` ·
`--tx #F5F3EE` · `--tx2 #C9C3B8` · `--tx3 #8C8C8C` ·
`--act #D4944A` · `--a` = `--petrol` `#5FA8A0`.

### Color rules

- **Bronze is action only.** The screen's primary button, "Install", "Add". Never a heading,
  never a frame, never a block's background.
- **Petrol is system only.** The active tab and chip, a section label, the "Verified by Extella" caption.
- **A category's color** lives in a stripe on top of the card and in a type label — and nowhere else.
  A button inside a card never takes the category color: otherwise "Install" is a different color
  in every row.
- Text contrast ≥ 4.5:1, large text ≥ 3:1. We do not use pure black `#000`.
- No gradients. No shadows — depth comes from a 1px border.

---

## 2. Fonts

| Role | Typeface | Where exactly |
|---|---|---|
| Interface: everything that's read and clicked | **Nunito** 400–700 | leads, cards, buttons, chips, tabs, fields |
| Headings | **Source Serif 4** | section H1, modal titles |
| Utility | **JetBrains Mono** | section labels, object type in a card, machine text: `agent_`, build hash, terminal command |

The rule that settles any dispute: **mono is about the object (metadata), Nunito is the object
itself and the action.** "Process the documents" is human speech, Nunito. "MCP", "Ready-made
database", "Work and career" are facts about an object, mono.

### Delivering the font files — a mandatory part

The token asks for a family, but the actual weight file must physically be present in the
document. The weight files sit as a ready-made file with a data: URI (Cyrillic + Latin; Nunito,
Source Serif 4, JetBrains Mono):

1. **Extella OS** — `web/extella-fonts.css` in the `extella-os` repository; pages get it as
   hashed static content.
2. **Author apps and panels** — `assets/extella-fonts.css` in this repository: paste it into
   `<head>` whole, do not download or connect anything from a CDN.

If you add a new surface, it must obtain the font files by one of these two routes. Symptom of
the mistake: the interface looks "foreign", headings fall back to Georgia, text falls back to the
system sans-serif.

---

## 3. Typography

**The size scale has six steps, no others exist:**

| px | Role |
|---|---|
| 11 | section labels, object type, trust captions. Absolute minimum |
| 13 | card descriptions, chips, buttons, secondary text |
| 15 | body text, leads, card titles, tabs |
| 20 | a block heading inside a section |
| 26 | section H1 |
| 40+ | marketing surfaces only, never used in the product |

**Nothing smaller than 11px exists.** Apple holds a minimum of 10pt; 8–9px is not a style, it is
an oversight.

**Weights — three:** 400 body text · 500 captions and labels · 600 buttons, headings, card titles.
700 is the one exception: **a card title in a grid**, because when scanning a shelf it has no
other distinction besides weight. A button doesn't need weight — its shape and color mark it.

**Line height:** body text 1.5–1.6 · headings 1.2 · buttons 1.
**Tracking:** 11px labels — `.06em`; small text — `.015em`; H1 — `-.01em`.
**Numbers in tables and counters** — `font-variant-numeric: tabular-nums`.

⚠️ **Buttons, fields and lists don't inherit the font.** Without the rule
`button,input,select,textarea{font-family:inherit}` the browser sets them to Arial. That's how it
was on 82 elements for us — the entire button interface was set in the wrong font.

---

## 4. Spacing and air

**Base 4px. Scale: 4 · 8 · 12 · 16 · 24 · 32 · 48.** Values off the scale don't exist
(5, 6, 7, 9, 10, 11, 13, 14, 18, 22, 26 are forbidden). Lines of 1–3px are hairlines, not spacing.

**Grouping rule:**

- **binds** at 8–16px: a label ↔ its text, a heading ↔ its shelf, elements inside a card;
- **separates** at 24–32px: shelf ↔ next shelf, block ↔ block;
- 48px only between large semantic parts of a screen.

**Only the one that starts a new group separates.** In a grid, spacing doesn't collapse: if both
the bottom of the previous block and the top of the next one set separation, they add up. That's
how we got 80–88px gaps. A block that's ending doesn't add a bottom margin.

**The first element has nothing to separate from** — the first section label gets `margin-top: 0`.

Component reference points: card padding 20 · card grid 16 · chips between each other 8 ·
lead paragraphs 16 · lead to cards 16.

---

## 5. Shape

| Element | Radius | Token |
|---|---|---|
| Cards, panels, modals, windows | 12px | `--r` |
| Small controls: chips, fields, badges, tabs | 8px | `--r-sm` |
| Action buttons | pill | `--r-pill` (999px) |
| Round icon buttons | 50% | — |

Borders are `1px solid var(--bd)`. **No shadows** — `--shadow: none`. No radii exist outside
these three roles.

---

## 6. Icons

- **Library — [Iconoir](https://iconoir.com), linear variant only (regular).** In the OS, symbols
  sit as a sprite in `web/desktop.html` as `<symbol id="ic-*">` and are placed via
  `<use href="#ic-…">`; an author's app carries its own sprite the same way.
- Size 15–17px inline, 24px in a tile. Line weight is uniform — an icon must not be heavier than
  the text next to it.
- **Emoji are forbidden in the interface.** The one exception is the agent's avatar, where the
  person chooses the emoji themselves. A type label, category, status, button, empty state — a
  linear icon or nothing.

---

## 7. Copy

- Address the person as **"ты"** (informal "you"), exactly as in the storefront.
- **A button is a promise of what will happen.** "Delete", not "Deletion".
- **An error says what to do,** and names the button by name: "…check the connection and press
  'Refresh'".
- **An empty state is not an error:** "Nothing here yet" + what to do, not "List is empty".
- Headings have no periods, no all-caps, no exclamation marks.
- **Forbidden words in the interface.** These must not appear in labels, descriptions and
  captions: pseudo-anonymization · user · assistant · wizard · deploy · token · scope · endpoint ·
  PID · PORT · localhost · bridge · registry (in the sense of "the user's list") · worker ·
  channel · panel device · placeholder · snapshot · instance · config (the last six from the
  panel audit of 14 Aug 2026).
  These are machine terms: they say nothing to a person, and they take up space.
  Replacements: "Pseudo-anonymization" → **"Hide personal data"**; "PORT 8765 · PID 1063" →
  **"running" / "stopped"**; a raw link `localhost:8765/…` → an **"Open"** button.
  The rule is one-directional: a name a person has already chosen is never replaced by a machine
  term.
- **Clarity matters more than brevity.** The phrase must be understandable to a person who is
  seeing the screen for the first time and doesn't know our internals. There is one test: cover
  the rest of the screen and read the line out loud. If it's unclear what happens after the click,
  rewrite it.
- **Don't explain twice.** If there is already an explanatory line below, a caption above it isn't
  needed. A duplicated explanation reads as noise, not as care.
- **No embellishment.** Signs of "written by AI": a metaphor instead of a fact ("a brain that
  carries out the task"), a joke instead of value ("will toss out ideas before your coffee gets
  cold"), a pretty pair joined by a dash ("an hour of conversation — and it runs itself"), pathos
  ("turns routine into results"). Write what the program does and what the person gets:
  "Answers from your documents", "Assembles a report from statements every Monday".
  Test: remove the adjectives and imagery — if the meaning survives, they were excess.
- **Minimize em dashes.** If a phrase lives without a dash, it lives without one. A dash is
  replaced by whatever the phrase asks for by meaning: a colon ("Describe the task: Extella will
  find it"), a conjunction ("and it will pick the right one"), a comma or a period with a new
  sentence. A dash is justified only where the grammar breaks without it.
- **Section names don't duplicate.** One word — one list. If two places hold different sets under
  the same name, one of them gets renamed, rather than the difference getting explained.
- **Russian typesetting:** single-letter prepositions don't hang at the end of a line (`&nbsp;`),
  phrases wrap by meaning.
- **Russian has four number forms, not three:** `_one` (1, 21), `_few` (2–4), **`_many` (5–20,
  25…)**, `_other` (fractions). Without `_many` the interface silently falls back to English. If
  `{{count}}` sits right next to the word, all forms are mandatory; a template like "devices:
  {{count}}" is safe.

---

## 8. Buttons and panels

- **One primary action per screen.** Exactly one is marked with a fill and the warm color.
  Everything else is outline or text. Two gold buttons calling to the same place is not a choice,
  it's an argument (this happened in the Builder: "Wizard" in the panel and "Take the
  interview with the Wizard" in the hero).
- **Order top to bottom: where am I → what is this place → what can I do here.** Navigation comes
  before a section's action. A "+ Add…" button sitting above the tabs offers an action before the
  person has chosen a section.
- **Related controls are one group, not five pills in a row.** Choosing a project, archiving, and
  creating are one matter: a shared frame, dividers inside it.
- **Dangerous stands apart.** Deletion doesn't sit right next to an ordinary action and doesn't
  repeat its shape; the confirmation names the consequence ("The program will be removed from the
  computer").
- **The same action looks the same.** "Install" is the same color in every card; a category's
  color lives in a stripe, not in the button.
- **A button responds right away.** After the click — a state ("Launching…"), then a result or the
  reason for a refusal. A button that just goes dark for three minutes reads as broken.

---

## 8. How to check that everything is followed

**Measure, don't look.** A sweep of computed styles across all tabs is the only way to catch a
discrepancy that the eye lets through:

```js
// in the console of an open storefront
const f={},s={},w={},r={};
document.querySelectorAll('#grid *, .hdr *, .tabs *').forEach(e=>{
  if(!e.getBoundingClientRect().height) return;
  const cs=getComputedStyle(e);
  r[cs.borderRadius]=(r[cs.borderRadius]||0)+1;
  if(![...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())) return;
  f[cs.fontFamily.split(',')[0]]=(f[cs.fontFamily.split(',')[0]]||0)+1;
  s[cs.fontSize]=(s[cs.fontSize]||0)+1; w[cs.fontWeight]=(w[cs.fontWeight]||0)+1;
});
console.log({f,s,w,r});
```

Norm: **3 families** (Nunito in bulk, Serif on headings, mono on labels), **no more than 7 sizes**,
**3–4 weights**, **radii only 12 / 8 / 999 / 50%**.

**Machine gates:** `tools/check_panel_canon.py` in this repository — font delivery, sizes,
weights, radii, spacing, shadows, "ты", machine words, emoji. Zero violations is a condition for
accepting any panel; in the OS `tools/safe_push.sh` runs it before every push.

**A checking rule drawn from our own mistakes:** a translation counts as done when **the screen
has shown it with its own eyes**, not when the line was found in a file. Same for design: a token
declared ≠ a token applied.

---

## 10. Anti-patterns — all of these happened to us

| Symptom | Cause | How not to repeat it |
|---|---|---|
| "A different font" on buttons | buttons don't inherit `font-family` | the rule `button,input,select,textarea{font:inherit}` |
| 80–90px gaps between blocks | separation set on both sides of the seam, spacing added up | only the one that starts a group separates |
| "Sticks together" | binds at 10px, separates at 14px — weights are the same | 2–3× contrast between "binds" and "separates" |
| English in the middle of a Russian screen | no `_many` form | four number forms |
| A caption is readable only right up against the screen | 8–9px size | minimum 11px |
| Headings in Georgia in an app panel | the token is there, the weight file isn't in the document | deliver `@font-face` to every surface |
| "Install" button a different color in the same row | the button takes the category color | one color for action, category is a top stripe |
| The interface looks "childish" | emoji in labels and statuses | Iconoir, emoji only for agent avatars |

---

## 11. Sources this canon stands on

- Analysis of the designer's references (refero.design): **Passionfroot**, **Tuple**, **replit**,
  **mymind** — common to all of them: a warm non-white canvas, one accent, flat cards with a 1px
  border, large body text, air between groups.
- **SaaS UI Trends 2026** — "calm interface": typography instead of icons and frames, one primary
  action per screen, complexity behind disclosure.
- **Apple HIG (macOS)** — minimize the number of typefaces, avoid light weights, minimum 10pt,
  comfortable density without strain.
- Typography practice: ≤2 families (+mono as a role), 6–8 sizes, 3–4 weights, vertical rhythm step
  = half the line height.
