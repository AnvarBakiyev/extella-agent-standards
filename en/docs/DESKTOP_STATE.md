<!-- source: docs/DESKTOP_STATE.md sha256:aaa81cc2f56297d59234e1634e460367a5dceec9d783a6d25485c31ff04a4e28 -->

# OS desktop: tile ≠ purchase

Measurement on 20 Aug 2026 on "CEO Remote" (six panels): purchases on the server
were flawless, but three tiles out of six didn't show up on the desktop — the same in
the browser and in the app. Reading the desktop's code (desktop.js from the core build)
uncovered mechanics that weren't written down in any of our documents. The executable
source is `tools/ярлык_на_стол.py`; if the text and the code disagree, the code wins.

## The main thing

**A programmatic install creates a PURCHASE, but NOT a tile.** Desktop tiles are
drawn from a separate piece of server state — `/api/desktop-state` (the OS host,
header X-Extella-Token). A purchase through `purchase-stream` / `переустановить()`
adds nothing to this state: the app is bought, it opens at a direct address, but it
isn't on the desktop. The core-build defect has been filed with the engineering
department; until it's fixed, our tool places the shortcut.

## The anatomy of desktop state

`GET /api/desktop-state` → `{state, rev}`. The layers of `state`:

| layer | what it holds |
|---|---|
| `pos` | tile positions `{id: {x, y, f}}` (`f` is the folder's id) |
| `folders` | desktop folders |
| `appShortcuts` | "app" shortcuts `{sid: {lid, name}}`. TRAP: without an agent, a shortcut like this opens the STORE CARD, not the app (measurement on 20 Aug 2026) — no good for page-type products |
| `shortcuts` | **direct links `{sid: {name, url}}` — the RIGHT tile type for an app**: the url `https://os.extella.ai/app-page/{lид}/` (with the trailing slash) opens the window right away, the listing's icon and the ↗ badge fill themselves in |
| `links` | device files/folders |
| `trash` | the trash (tile ids) |
| `vers` | pinned versions of apps |

Write: `POST /api/desktop-state` with the body `{state}` — the whole state at
once. Open desktops pull in someone else's edits on their own (revision polling), no
restart needed.

## Rules (paid for in blood)

1. **A backup before any write.** POST writes the whole state at once: a badly
   put-together `state` means the person's desktop gets wiped out. The tool puts a full
   copy at `~/extella-cabinet/записи/desktop_state_бэкап_<время>.json` before writing.
2. **Only add.** Read the live state, add your own records, don't touch other
   layers. No "rebuild from scratch".
3. **Idempotency.** A shortcut with the same `lid` already exists — don't
   duplicate it.
4. **Race with an open desktop**: its client saves its own state with a 400 ms
   delay; our edit landing between its edits can get overwritten. After writing —
   re-read and make sure the shortcut is in place.

## How to place a tile

    python3 tools/ярлык_на_стол.py <listing_id> --имя "CEO · Маркетинг" [--x 900 --y 300]

Without `--x/--y` the desktop finds a free spot on its own the next time it
loads.
