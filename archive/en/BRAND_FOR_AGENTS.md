<!-- source: BRAND_FOR_AGENTS.md sha256:fbfcf1b3fae366e81a7b58bd96146615efc9e557a857899bc6ef6a4289c47214 -->

# Extella brand in agents — what a developer must follow

Owner: CEO · Date: 26 Jul 2026 · Version: 1.0
Source: `Extella_BrandBook_JULY_v2` (the full brand book is with the owner, here only the executable part).
Check: `python3 tools/check_brand_copy.py <interface files>`

**Why this file, if there's a brand book.** The brand book is a strategy document: positioning,
pricing, go-to-market, competitors. An agent developer needs a different thing: **exactly what
must not be written in the interface and which color must not go on a button.** Here is only the
part that's executed in code, and it's checked by a machine, like the rest of our standards
(`EVOLUTION_PHILOSOPHY.md`: a rule that only conscience checks doesn't work).

---

## 1. Name, category, words

| Rule | Correct | Wrong |
|---|---|---|
| Brand name | **Extella** | "Extella AI" in the product and in marketing (allowed only in legal documents and in the handle `@extella_ai`) |
| Category | AI platform · AI execution system · AI-orchestrated execution platform | "smart assistant", "chatbot" |
| Action | executes / completes / runs · выполняет / исполняет / делает | helps you / helps with · помогает / помогу / поможет |
| Our entities | Expert, Pipeline, Concept, agent, Ex-object | bot, script, "neural network" |

**Forbidden words** (checked): помощник · ассистент · бот · чат-бот · нейросеть · AGI ·
сознание · helps you/with · smart assistant · "Чем могу помочь?".

**Allowed since July 2026:** "agent", "agent platform", "multi-agent teams" — the brand book lifted
the previous ban, so our names (Agent Passport, Agent Cabinet, Agent Genome) do **not** contradict
the brand.

**Exception:** someone else's entities are called by their own words. "Telegram bot", "@BotFather"
— that's someone else's product, it can't be renamed. The checker knows this exception.

## 2. Palette (the only colors allowed)

**Light theme.** Accent: Gold `#C57E33`, hover `#D4984F`, accent text `#A5632A`.
Text: Ink `#0A0A0A` (headings), `#1A1A1A` (body), `#2A2A2A` (secondary).
Second accent — Petrol `#2F6B66`, hover `#3D8078`, dark `#24544F`, border `#B7CEC9`.
Surfaces: Paper `#FAFAF8` (background), Cream `#F5F3EE` (cards), Divider `#EBE8E1`,
Border Gold `#D4B896`, Silver `#8C8C8C` (meta), Silver Light `#AAAAAA`.

**Dark theme.** Gold `#D4944A`, hover `#E0A85E`; Petrol `#5FA8A0`, hover `#6BB3AA`;
text `#F0F0F0` / `#D8D8D8` / `#B0B0B0`; background `#0E0E0E`, cards `#181818`, hover `#222222`,
terminal `#000000`.

**Logo:** `#C49C70` — in the mark only. This color must not appear in the interface.

### State colors (approved by the owner 26 Jul 2026 — an addition to the brand book)

The brand book didn't have these, so every product invented its own green. Now they exist:

| State | Light theme | Dark theme | Contrast (passes AA) |
|---|---|---|---|
| Success | `#1F7A4D` | `#57B37E` | 5.09 on Paper · 7.50 on dark |
| Error | `#A63A2E` | `#E8705F` | 6.15 on Paper · 6.36 on dark |
| Warning | `#A5632A` (Gold Dark) | `#E0A85E` (Gold Light) | 4.55 on Paper · 9.13 on dark |

Warning **doesn't introduce a new hue** — it's the existing gold, so the palette doesn't grow.
Success in the dark theme gives 7.50 — exact parity with Gold `#D4944A` (7.48), so statuses don't
read louder than the accent.

**Color is never the sole carrier of meaning:** a word or a mark (`✓`, `✕`) must sit next to a
status, otherwise the state is lost for color blindness and in black-and-white print.

### Four contrast bans (checked by machine)

1. **Gold and Petrol never on each other** — contrast 1.9:1, fails every WCAG level. Separate them
   with a neutral background.
2. **Silver `#8C8C8C` is meta-text only** (time, identifiers). Never as readable text on a dark
   background. For text on dark, use Paper `#FAFAF8`.
3. **Petrol is information and process** (data, statuses, secondary links), **never an action
   button.** The action button is always Gold.
4. **A state color is never placed on a colored accent** (success on gold, error on petrol, and so
   on — contrast 1.0–2.0:1). Statuses live on neutral surfaces: Paper, Cream, the dark background.

## 3. Typography

| Role | Font |
|---|---|
| Interface, documents, letters | **DM Sans** |
| Code, terminal blocks, metrics, author signature | **JetBrains Mono** |
| Display (logo, hero) | "rounded futuristic techno" — **the font's name isn't given in the brand book** |

**A gap worth knowing:** until the display font is named, every developer picks their own — and
surfaces stop looking like one product. **Until the owner decides, we don't pick a display font on
our own: an agent's interface uses DM Sans.** We don't ship hero copy in someone else's font.

## 4. How the interface speaks

| Principle | Right | Wrong |
|---|---|---|
| Result, not process | `Expert executed in 1.2s` | "Working on your request…" |
| Concrete numbers | `4 experts · 8.7s · done` | "Completed successfully" |
| No exclamation marks | `Expert saved` | "Expert saved!" |
| No filler greetings | straight to the action | "Hi! How can I help?" |
| Logs — terminal aesthetic | JetBrains Mono, lowercase commands, `✓` + time | spinners and "magic" |

Terminal language: `extella  run_expert  ✓ Expert executed in 1.2s` (two spaces between segments,
`·` as a separator, checkmark in gold, process lines in Petrol, meta in Silver).

## 5. Two languages — and how this meshes with the brand

Rule §3.26 (Russian and English together) applies. How it combines with the brand:

- **names are not translated:** Extella, Expert, Pipeline, Concept, MiniApp, Agent Passport, Agent
  Genome, Evolution Console — the same in both locales (see `NAMING.md`);
- **interface phrases go in both languages:** `Эксперт выполнен за 1.2 с` / `Expert executed in 1.2s`;
- the brand book's reference examples are written in English — this is **not permission** to ship
  an English-only interface without a Russian version.

## 6. Brand tone and honesty: which wins (important)

The brand book demands strength: "we execute, we don't explain", "result, not process", no weak
phrasing. Our standard demands honesty: every capability has a named limit, a refusal is explained
in words, a partial result is never passed off as finished.

This is not a contradiction, and the order is this:

> **Brand tone decides HOW we speak. The honesty standard decides WHAT must be said.
> Tone never removes a boundary.**

In practice:

- "What we do NOT promise" is written **confidently and briefly**, not apologetically:
  "Works within verified areas. Direct chats with the agent are not tracked." — strong and honest;
- the ban on "helps" applies to positioning, not to acknowledging a refusal: an error message says
  plainly — "couldn't: no access to the folder; retrying is safe";
- **the brand does not allow calling something unfinished finished.** That's a coarser violation
  than any tone breach.

## 7. What is deliberately NOT checked by machine here

- **Rounded corners, shadows, gradients, "sharp corners".** The brand book itself suspended bans
  §8.4–8.5 until a new visual specification (the current materials use soft plasticity). A
  suspended rule can't be checked.
- **Colors outside the palette are a warning, not an error.** State colors were approved only on
  26 Jul 2026, and live surfaces still carry a legacy of homemade shades (80 of them in the
  wizard). Rule: **new surfaces ship with `--strict`**, old ones are converted gradually. A gate
  that can't pass is itself a defect.
- **Comments in code.** The checker doesn't distinguish a comment from interface text — if it
  flags a comment, that's not a product defect, but the wording is still worth fixing.

## 8. Open questions for the brand owner (the owner)

1. **State colors.** Success / Danger / Warning are needed in the palette (they don't exist now,
   and products invent their own). Without them the palette rule can't become a gate.
2. **The display font's name.** Until it's named, hero copy diverges between surfaces.
3. **Category.** The brand book declares a future category, **AE (Artificial Extelligence)**,
   `NAMING.md` declares the category **Agent Evolution Platform** for Extella Evolution. These are
   levels of different scale (a platform, and a product within it), but which category statement
   wins is worth settling, or materials will carry two competing claims.

## 9. How to check before release

```
python3 tools/check_brand_copy.py path/to/interface.js path/to/page.html
```

Checks: forbidden vocabulary, brand name, filler greetings, colors outside the palette,
Gold-on-Petrol, Silver on dark, exclamation marks, the logo color in the interface.
Self-check of the tool: `python3 tools/check_brand_copy.py --selftest` (21 checks).
