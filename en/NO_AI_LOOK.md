<!-- source: NO_AI_LOOK.md sha256:01cfbc5d386daf3582cf71290498700fa0162c1950d87d83d9c4320f28a5f945 -->

# Signs of the AI look. What's forbidden regardless of palette

An app having its own palette and its own character is normal and welcome. Two things are
forbidden: **someone else's fonts** and **a template composition that gives away that a screen was
generated, not designed.** Color has nothing to do with it — what gives it away is the layout and
the typefaces.

This file is not about the Extella canon (that's in `DESIGN_CODE.md` next to it and is mandatory
only for the platform's own windows). This is about the look of the apps our team makes.

---

## Nine signs

**1. An abstract blob instead of a mark.** A rounded organic silhouette, often with a circle cut
out of it, depicting nothing. Such a mark says nothing about the product — it says "a model drew
me".
→ Instead: a letter from the name, a concrete silhouette, or no mark at all.

**2. A scatter of colored dots.** Green and orange circles around a shape, "particles", "orbits",
constellations of dots.
→ Instead: nothing. A dot is acceptable if it's a status indicator and it means something.

**3. A soft gradient background.** A diagonal stretch between two pastel shades, blurred colored
blobs in the corners.
→ Instead: a single flat fill. Depth comes from a 1px border, not a glow.

**4. Someone else's fonts and a giant bold sans-serif in the heading.** A large bold sans with
tight tracking, under it a small gray one-line subheading. Plus a system font instead of our own
font files — the screen instantly stops being part of Extella.
→ **Fonts are shared across all our team's apps, the palette is your own.** The interface,
buttons and fields are set in **Nunito**; headings in **Source Serif 4**; machine text and section
labels in **JetBrains Mono**. The mandatory rule
`button,input,select,textarea{font-family:inherit}` — without it the browser sets buttons in
Arial. Size by meaning, not by effect: sizes 11 / 13 / 15 / 20 / 26.
The ready-made block of font files with a data: URI is `assets/extella-fonts.css` in this
repository: paste it into the document whole, don't download anything.

**5. A feature-card triad.** Exactly three equal tiles at the bottom of the screen with short
two-word headings and one explanatory line.
→ Instead: as many blocks as there is content for. Three is a suspiciously round number.

**6. A full-width button.** A huge slab of a primary action, stretched across the column.
→ Instead: a button the width of its own text.

**7. Glass cards.** A rounded tile with a soft shadow, translucency and blur underneath it.
→ Instead: a flat surface and a border.

**8. An icon for the icon's sake.** An icon next to every item, including ones where it adds
nothing — or an emoji instead of an icon.
→ Instead: an icon where it distinguishes, not where it decorates.

**9. Symmetry for symmetry's sake.** Everything centered, margins equal on every side, not a
single accent.
→ Instead: a composition that has a main point.

---

## Check before shipping

Four questions, each answered in a second:

0. **Are these our fonts?** Open the inspector, look at `font-family` on the heading, the button
   and the input field. Georgia, Arial or system-ui means the font files never arrived.
1. **What's drawn here, and why?** If the answer is "just decoration" — remove it.
2. **Would I recognize this screen among ten others?** If not, there's nothing to recognize except
   the generator.
3. **What's the primary action here?** If there are two or none, there's no composition.

## Prompt insert

> Don't produce a generic, generated look: no abstract blobs or blot-logos, no scatter of colored
> dots or "particles", no gradient backdrops or blurred blobs, no glass cards with shadow and
> translucency, no giant bold sans-serif in the heading, no exactly-three feature cards at the
> bottom, no full-column-width buttons, no icon next to every item. Depth is a 1px border, not a
> shadow.
> Our fonts are mandatory: Nunito for the interface, Source Serif 4 for headings,
> JetBrains Mono for machine text; sizes 11 / 13 / 15 / 20 / 26; the rule
> `button,input,select,textarea{font-family:inherit}` is mandatory.
> Your own palette is fine; your own fonts and a template composition are not. The screen has
> exactly one primary action. Every drawn element must mean something: if it's decoration, it
> doesn't belong.

---

This rule applies to our team's apps. For third-party authors it's a recommendation, not a gate:
their product is their own look, we're responsible for our own.
