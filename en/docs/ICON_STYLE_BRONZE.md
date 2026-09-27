<!-- source: docs/ICON_STYLE_BRONZE.md sha256:70415a9c8354b5d0d6a6859fb14f34ee269e5cfd241e959b2638a4a592bab5df -->

# Bronze Engraved — the style for every Extella tile

Spec by the owner, 20 Aug 2026. The executable source is `tools/bronze_icon.py`;
if the text and the code disagree, the code wins, and the document is brought into
line. The old geometric generator (`make_icon.py`) is history — don't make new icons
with it.

## The tile (74×74 metric, everything scales linearly; radius = 0.27 × size)

- Background: `linear-gradient(165deg, #FFFDF9 0%, #F0EBE0 55%, #E4DDD0 100%)`
- Border: `1px solid rgba(197,126,51,.35)`
- Shadows: `inset 0 1px 1px #fff`, `inset 0 -3px 6px rgba(140,110,60,.14)`,
  outer `0 5px 14px rgba(90,70,40,.14)`
  (on a dark desktop, outer: `0 6px 16px rgba(60,40,20,.28)`)
- Highlight: a layer on top, `linear-gradient(180deg, rgba(255,255,255,.6), rgba(255,255,255,0) 45%)`,
  `overflow: hidden` on the tile

## Glyph

- Lucide 24×24 grid, size = 0.51 × the tile (38px at 74)
- `fill:none; stroke:#B5722A; stroke-width:1.7; stroke-linecap/join:round`
- Engraving: `drop-shadow(0 1px 0 rgba(255,255,255,.9))`
  (in the generator — a white layer offset by 1px: the SVG filter drifted at the
  glyph grid's scale, measurement on 20 Aug 2026)

## Set rules — checked by the generator's code

- Glyphs ONLY from Lucide (`templates/lucide/`, bundled with the ISC license); don't
  draw them by hand. One glyph = one line, no fills, no text, no logos.
- At most one gold accent — the stroke itself is that accent.
- Third-party apps (the telecom demo, Composio, 1C…) are wrapped in the same tile
  with a monochrome `#B5722A` stroke — we don't show their native PNGs.
- The caption under the tile: DM Sans 11px/500, `#8C8C8C`, at most two lines.
- Export: SVG 1× (the generator places it next to the PNG); raster — 512 for the
  storefront and macOS .icns when needed.

## Glyphs in use

lock=Data Privacy · table=Table · file-text=Lawyer · library=Library ·
bar-chart-3=CSO · presentation=Presentations · network=Shop Floor · arrow-left-right=P2P ·
app-window=Browser · trash-2=Trash · terminal=Agent Remote · shapes=Schemes Board ·
activity=Watcher (Uptime Kuma)

## How to make an icon

    python3 tools/bronze_icon.py <lucide-глиф> editions/<slug>/icon.png

The installers (github- and docker-) do this themselves; the glyph is set with
`--глиф`, defaulting to `app-window`. A new glyph is added to `templates/lucide/`
with the command from the generator's hint.

## Color series (owner's decision, 21 Aug 2026)

The desktop is split into three series by stroke color; the geometry, the cream
background and the engraving are shared. The executable source for the series is
`tools/цветная_плитка.py` (bronze is still made by `bronze_icon.py` as before):

| series | stroke | belongs to |
|---|---|---|
| bronze | `#B5722A` | products and agents |
| petrol green | `#2F6B66` | office tools (Documents, Table, Notes, Tasks, Board, Diagrams, PDF, Data Privacy) |
| steel blue | `#3A6EA5` | management panels (the six "CEO ·") |

Blue isn't a new color: it was already the accent on the telecom-module cards —
the series just locked it in. Glyphs in use stay shared across all series;
`file-text` moved from Lawyer (tile in the trash) to "Documents".
