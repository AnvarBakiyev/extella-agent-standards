<!-- source: BRAND_SURFACES.md sha256:05f35ecaf708593007f0589c1bf5b5f90200e583b08b041eaadd0d857901a659 -->

# Large surfaces: site, presentations, images

The third part of the corpus. The first two are identity (who we are, the mark, the palette, the
character) and the product design code (`DESIGN_CODE.md`). Here is only what appears on large
surfaces: a landing page, a presentation, a cover, a screenshot.

Shared rules are not repeated: colors, typefaces, accent roles and copy voice are taken from the
design code. If a rule already exists there, it isn't rewritten here.

---

## 1. Large-scale sizing

The product scale ends at 26px: that's enough for an interface and too little for a page.
Large surfaces get their own scale, with mandatory negative tracking: the larger the size, the
tighter the letters.

| Role | Size | Line height | Tracking |
|---|---|---|---|
| Cover-screen heading | 72 | 0.95 | −0.03em |
| Section heading | 56 | 1.05 | −0.025em |
| Subheading | 40 | 1.15 | −0.02em |
| Large text (lead) | 24 | 1.45 | −0.01em |
| Page text | 18 | 1.6 | 0 |
| Caption | 14 | 1.45 | 0.01em |

Headings — Source Serif 4, weight 500–600. Text — Nunito 400.
A heading line is no longer than 12 words, body text is 60–75 characters.
Headings get `text-wrap: balance`, so the last line doesn't end up as a single word.

## 2. Page grid

- **Content width:** 1200px, margins no smaller than 24px on narrow screens.
- **Section rhythm:** 96px between semantic blocks, 64px inside a block.
  On a page this works the same way as the spacing scale in the product: separation is set by
  the block that starts a new topic.
- **Columns:** 12, 24px gutter.
- **One primary action per screen.** On the cover — one button. A second one, if needed, is
  outlined and sits beside it, not underneath.
- **A section explains itself in its first line.** The heading states, the lead clarifies, then
  comes the proof: a product screen, a number, or a short example.

## 3. Images and screenshots

We show the product, not abstractions. Stock photos of people at laptops, 3D shapes and
"neural-network" collages are not used.

- **A product screenshot** is the primary type of image. Taken from a real screen, not drawn.
  Frame: a 1px border in the color `--bd`, radius 12, no shadow.
- **Crop by meaning.** Show the part of the screen that's being discussed, not the whole window.
  Small text that can't be read gets cropped out.
- **Highlight one spot.** If an element needs pointing at, use a 2px petrol frame or a caption
  with an arrow. No more than one accent per image.
- **An illustration** is acceptable as a diagram: lines, rectangles, arrows in the system's
  colors. Line weight 1.5–2px, no volumes and no gradients.
- **Proportions:** 16:9 for covers and slides, 4:3 for interface fragments, 1:1 for social cards.

## 4. Motion

Motion explains, it doesn't decorate.

- **Duration:** 120–200ms for interface reactions, up to 400ms for a section's appearance.
- **Easing:** `ease-out` on appearance, `ease-in-out` on movement.
- **What animates:** a block appearing on scroll (an 8–16px shift + opacity), a button's state,
  a list expanding.
- **What never animates:** text letter by letter, number counters without a reason, parallax,
  autoplaying video with sound, endless background loops.
- We respect `prefers-reduced-motion`: with it on, only opacity remains.

## 5. Slides

A presentation is a different medium: it's read from a distance and in someone else's light.

- **Format** 16:9. Margins 64px, content doesn't cross them.
- **Size:** heading from 40, text from 20, caption from 16. The product's 11–15px sizes don't
  carry over to a slide.
- **One idea per slide, and it's in the heading.** The heading states: "Setup takes a minute," not
  the topic: "Setup."
- **Contrast for a projector:** third-level gray (`--tx3`) is not used on slides — minimum `--tx2`.
  Thin lines lighter than `--bd2` disappear.
- **No more than five lines of text** per slide. Anything longer is two slides.
- **Charts:** our two accents plus neutral gray, labels sit right at the lines, a legend only if
  there are more than three series. No rainbow, no volume.
- **Title and closing slide** are always the same: the mark, the name, one line of substance; at
  the end — one action and a contact.

---

## Check before publishing

- The heading reads from arm's length from the screen.
- The screen has one primary action.
- Every image shows the product or explains a diagram.
- Not a single emoji; icons are linear, from one library.
- The text passes the clarity test: remove the adjectives and imagery — the meaning survives.
