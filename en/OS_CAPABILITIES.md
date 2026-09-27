<!-- source: OS_CAPABILITIES.md sha256:dbe6c9e36bc46f3e923e94ae3a09af8ad9cdeca5f080326d84c7b91210b4cc46 -->

# Map of OS desktop capabilities

Measured on the live frontend on 21 Aug 2026 — file `desktop.bf512c0e78dc.js`, 165 KB, 2265 lines.
Every statement was checked by reading the code, not the documentation. To re-check:
`curl https://os.extella.ai/desktop`, take the name `desktop.<хэш>.js` from the response, download
it from `/os-static/` and read it.

**Caveat on completeness.** The toolbar in this measurement is only partly examined: its
composition is listed, but not the behaviour of every button. Add to it by reading the same file,
not from memory.

**Caveat on safety.** Three capabilities here run someone else's code next to the account token:
right-click actions, store extensions, and headers with `{{token}}` substitution. The write-up is
in `DEPLOY_REQUIREMENTS.md`, section H33. Below they are described from the benefit side, and each
one carries a link there.

---

## Part 1. Underrated

Four capabilities that exist in the shell and are almost never used.

### Instruction — a library of ready-made tasks for agents

`+` → `Instruction` creates a task object: a name and text. The value isn't in storing it but in
sending it: right-click the object → **`Open with…`** → pick an agent, and the text goes to the
agent's input field. It is serialized as `<instruction> name: text</instruction>`, and the agent
receives it via `?prompt=`.

This is a ready-made library of repeatable tasks: worked-out phrasings sit as objects on the
desktop and are launched at one agent with a click, instead of retyping the text every time.

**Naming trap.** `Open` and a double-click open a text **editor** — nothing gets sent anywhere.
Only `Open with…` sends it. The name gives no hint of the difference.

### A whole folder goes to the agent with one click

`Open with…` on a folder sends its contents: files, tasks, links to web apps and agents — as a
single message, nested folders included, up to 32 levels deep. An assembled folder works as a
ready-made set of materials for the conversation.

Web apps get the same message differently — via the `X-Attachment-OS` header, meaning the app's
server side can read it.

### Substitution headers — signing in to an external service under an Extella account

Headers are set in the web app's settings, and the OS proxy substitutes values into them:
`{{token}}` — the account token, `{{email}}` — the email, `{{agent_id}}` — the agent's identifier.
The raw token is never visible to the external site: the proxy does the substitution, and the page
loads without it.

The practical meaning: an external web service recognizes the person without a separate
registration.

**Caveat.** `{{token}}` is the full account token, not a restricted key. The consent dialog comes
up once and is remembered; for `{{agent_id}}` it never comes up at all. The write-up is H33.

### Store extensions — the seller extends the buyer's browser

Installing an app can bring along the seller's JS, which runs on the user's pages. Entries are
marked with a lock and the word Store, cannot be edited, and updates are pulled by polling once
every 12 seconds while the embedded browser window is open.

The strong side: the seller delivers an improvement without reinstalling the product. The flip
side — H33.

### Cloud desktop — state follows the person, not the machine

Icon placement, folders, tasks and settings are stored on the server: read and write go through
`/api/desktop-state`, the change marker is `/api/desktop-rev`. This is not browser storage: the
desktop is the same on any machine where you're signed in.

**A risk measured in practice.** The endpoint overwrites the whole state; there is no separate
call to delete a single icon. Once, an empty write wiped a desktop that had eleven icons on it. A
write failure isn't shown either: the error handling is empty, and the person finds out about the
loss only by seeing an empty screen.

---

## Part 2. Naming traps

Three places where the name promises something other than what the code does.

| Item | What's expected | What actually happens |
|---|---|---|
| `New App` | create an app | opens the store publish form (`/publish`) |
| `Linked file` / `Linked folder` | link a file or folder | a stub: only the **name** goes to the agent, with no content and no path — the path stays empty, and the message says outright that it gets set later in the app |
| `Copy` | copy to clipboard | duplicates the desktop icon; it's **`Copy URL`** that puts the address on the clipboard |

---

## Part 3. The rest of the inventory

A listing with caveats; behaviour was checked only selectively.

**App icon menu.** `Open in browser` opens an OS window, not the system browser. `Rename` —
renames it. `Move to Desktop` — works only for an icon inside a folder. `Hide from All apps` —
hides it via `/api/purchase/hide`. `Move to Trash` — to the trash.

**Toolbar** (only partly examined): the store, a list of all apps, search with a type filter, dark
theme, a button to return to the desktop, embedded browser windows with tabs, a screen snapshot
via `getDisplayMedia`, a `+` button for creating objects.

**Desktop organization.** Nested folders, `Clean up` — arranging into a grid, rubber-band
selection, drag-and-drop with grid snapping, a trash with delete, restore and empty.

---

## Part 4. What changed by 24 Sep 2026

Re-shot on build `desktop.240a89750c7f.js` (191 KB, 2700 lines) against the August
`desktop.bf512c0e78dc.js` (165 KB, 2265 lines). Extella app 1.3.0 from 23 Sep. The platform
doesn't publish a changelog — `/changelog`, `/api/changelog`, `/api/version` all answer 404 — so
what follows is a measurement, not a retelling.

**Provably new** (this wasn't in the build yesterday, checked with a live window on 23–24 Sep):

* **App permissions and consent.** `GET/POST /api/app-permissions/<listing_id>`: `requested`,
  `granted`, `labels`, `hints`, `token: {token_name, granted_at, agent_id}`. When a window opens,
  if permissions haven't been granted, the OS shows "Allow and open / Open without access."
  **Before consent, `app-agent/run` calls answer 403** — an app that worked yesterday goes silent
  today until the person allows it. The permissions screen revokes rights one at a time or all at
  once ("Revoke all"). Closes §47 of the letter, opens §48.
* **Deleting an app's agent** — `/api/agent/delete`: tears down rules, concepts and experts; the
  purchase and the files on the device remain. Half of §42.
* **Credit transfers between accounts.** The desktop polls `/api/billing/pending` every 4 seconds;
  on an incoming transfer it shows a confirmation with a countdown and the buttons
  `/api/billing/transfer/<id>/confirm` and `/decline`. A separate session — `/api/billing-auth`.
  This is money moving inside the OS; it wasn't in our documents at all.

**Present in the build, not described in the August snapshot** (may have appeared earlier — check
if it matters): multiple desktops with a switcher, a launchpad, custom right-click actions
(`customActions`), a web app's own headers (`/api/webapp-headers/<id>`), hover hints, an "Agents"
tab in the `Open with…` send dialog.

**Fixed compared to the August snapshot:** `Linked file` / `Linked folder` is no longer an empty
stub — files are uploaded to `/api/attachments` and the agent receives a short-lived permit link,
not a made-up path and not the account token. The naming trap from Part 2 is closed.

**Gone:** the screen snapshot via `getDisplayMedia` is no longer in the build (it was in the
toolbar in August).

**Unchanged, though we asked:** `etb_init` only carries the theme and language, the
`etb_run_expert` handler isn't in the build (H106); the body of `POST /api/purchase/<version_id>`
has no device field, you still can't choose a machine at install time (§45); `/api/desktop-state`
still overwrites the whole state.
