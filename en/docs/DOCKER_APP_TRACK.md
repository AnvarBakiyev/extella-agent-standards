<!-- source: docs/DOCKER_APP_TRACK.md sha256:4ea44274e196f81fc1a7a24e3455782f0028ea34d4b50002ac6c979fe0d2236c -->

# Docker track: server app → container → OS window

Laid down on 20 Aug 2026 on Uptime Kuma ("Watcher"). Everything below is measurements, not opinions.
The executable source is `tools/install_docker_app.py` and `tools/cabinet_server.py`
(proxy mode); if the text and the code disagree, the code wins.

## Why this track

Demand mining on 19 Aug 2026: by star mass, ≈65% of the apps people want are the
server docker class (Immich 112k⭐, n8n 201k, Vaultwarden 66k, Stirling-PDF 90k, Jellyfin 56k),
browser statics are ≈6%. The browser pipeline catches the tail of demand; this track catches the head.

## How to install an app

    python3 tools/install_docker_app.py \
        --образ louislam/uptime-kuma:1 --slug uptime-kuma --имя "Сторож" \
        --порт-внутри 3001 --том /app/data \
        --лицензия https://raw.githubusercontent.com/louislam/uptime-kuma/master/LICENSE \
        --глиф activity

Installer steps: Docker is alive → compose and container (on the internal port) →
proxy with the shim facing out → probe by restart → license → Bronze
Engraved tile, card, window. From there by hand: fill in listing.json, publish it
as a pre-release, Publish — the owner. A pre-release is a version of the product
that only the author sees.

## Track rules — each one pinned down by a self-check

- **Port only 127.0.0.1.** A container on 0.0.0.0 serves the app to every
  neighbor on the network — a stranger's laptop at the same café gets your watcher.
- **Data lives in a volume at `~/extella-cabinet/docker/<slug>/данные`**: visible as files,
  gets backed up, survives the container being recreated.
- **Restart is an installation step, not a promise.** The container restarts and
  must answer again, or the install did not happen.
- **`restart: unless-stopped`** — survives a reboot together with Docker Desktop;
  the container doesn't need a LaunchAgent (the proxy does, and the installer sets it up).
  Docker Desktop must start at login — check the box in its settings.
- **The owner sets the initial password.** The agent does not create accounts or choose
  passwords, even inside a local container.
- **A passwordless local perimeter — on the owner's word** (owner's decision on
  21 Aug 2026: "the login is already guarded by Extella"). Two standard paths: turn off
  the app's own auth (Kuma: setting `disableAuth`) or the proxy's auto-login —
  `cabinet_server --автовход <json {путь, тело}>`: on a 401 the proxy logs in itself
  with a machine secret (a 600 file next to .env, never shown to the person) and
  repeats the request; the session is held by the cookie jar. The port stays ONLY
  127.0.0.1 the whole time — the passwordless mode never leaves the computer.
- **Login isn't always a cookie.** Measurements on 21 Aug 2026 on Memos: (1) the token
  arrives as a RESPONSE BODY FIELD (`accessToken`), not Set-Cookie — the config
  `"кука_из_тела": {"поле": "accessToken", "как": "bearer"}` puts it in the jar under a
  special key, and the proxy sends `Authorization: Bearer` (a cookie with the same token
  gives 401, Bearer gives 200); (2) the app sets the refresh cookie via the service header
  **`Grpc-Metadata-Set-Cookie`** (the usual connect-rpc path) — a collector looking for the
  name "Set-Cookie" doesn't see it, and the window shows the login form while the token is
  still alive. The proxy collects both headers, both at login and on every proxied response:
  without the second one, the session breaks mid-work when the token rotates.

## OS window sandbox: the full list of doors (paid for in blood)

The OS window is a sandbox with no address (`Origin: null`). For the docker class,
the container serves the pages, and a shim can't be inserted into files — so **the proxy
faces outward**, and it stitches the shim in on the fly. Everything that killed the window,
in the order it was discovered:

| Door | What it looks like | The fix |
|---|---|---|
| localStorage / sessionStorage | silently loses the work | shim: storage → a file on disk |
| document.cookie | throws SecurityError | shim: an in-memory cookie jar |
| IndexedDB | a "polite refusal" hung localforage in an eternal Loading state | shim: `indexedDB = undefined` — "no databases", every build handles that. Side noise: builds that call `indexedDB.open` without checking throw a TypeError "reading 'open'" — the shim's reporter doesn't count this as a failure (measurement on 20 Aug 2026, the Board was working, the loading bar was burying it) |
| **History API** | `replaceState` throws; the SPA router dies in a loop — a white window | shim: try the native one, swallow the refusal |
| **X-Frame-Options** | the container sends SAMEORIGIN; the browser downloads the document and SILENTLY does not paint it inside the embed — a white window with no errors and no requests for scripts | the proxy strips XFO (and CSP) |
| **Sixth door: Cross-Origin-* + network cookies** (21 Aug 2026, tududi/helmet) | `Cross-Origin-Resource-Policy: same-origin` chokes every script and fetch INSIDE THE SANDBOX (the window's origin is null, so everything is "cross"): in a normal tab the app is alive, in the OS window it's white. Plus the sandbox cuts network cookies — the login session doesn't survive. And a duplicate ACAO breaks CORS entirely | the proxy strips the whole Cross-Origin-* family and Set-Cookie (the proxy's cookie jar holds them in memory and glues them onto requests), and it answers the preflight for proxied paths itself; ACAO is sent ONLY from end_headers — once |
| **Eleventh door: worker threads (Worker)** (21 Aug 2026, Stirling-PDF) | the document is added, the viewer says "Loading tool…" forever; in the console — `Refused to cross-origin redirects of the top-level worker script` | the window has had its origin taken away (null), so ANY normal address is foreign to it, and the browser refuses to load the worker's main script from a foreign address. Libraries (pdf.js) try to get around it with their own blob wrapper, but inside that wrapper they still pull the same foreign address. The shim fetches the worker's code itself (with a normal request) and hands it to the worker inside a blob — there's nothing left to load from outside. The intercept must come FIRST in the shim: placed later, it's too late — the app grabs the native constructor first |
| **Thirteenth door: live channel (WebSocket)** (23 Aug 2026, Browser Robot) | the app is open and running, but the spot where the live picture should be shows an eternal "RECONNECTING…". The proxy only knows "asked — answered" and tears down a channel that's held open | flag `--живой-канал ПУТЬ=ПОРТ`: the proxy passes the handshake through word for word and then pours bytes both ways without parsing the content. **Also check the port forwarding:** the live channel is often NOT on the app's main port (for the Robot — websockify on 54311 next to the app on 11345), and without its own forwarding there's no picture even in a plain browser. Check: the handshake through the WINDOW's port answers `101 Switching Protocols`, followed by content (for VNC — `RFB 003.008`) |
| **Twelfth door: cross-site request forgery protection (CSRF)** (23 Aug 2026, Browser Robot) | the app opens and runs, but EVERY button action answers with a `CSRF_INVALID_ORIGIN` refusal. The app checks the Origin header against its own address, and the OS window has no origin at all — it sends "null" | the proxy identifies itself honestly: it substitutes the Origin and Referer of its own internal address on ALL proxied requests (not only auto-login — that's where it started: `CSRF_MISSING_ORIGIN` on the machine login). Security doesn't suffer: the port only listens on 127.0.0.1. Check: the action that used to fail with CSRF now answers on the merits |
| **Ninth door: Web Locks** (21 Aug 2026, Stirling-PDF) | the app opens, but the tool says "Loading tool…" forever; in the console `Failed to execute 'request' on 'LockManager': Access to the Locks API is denied` | the shim grants the lock itself (there's nothing to share within one window). **A trap that cost a whole round of fixes:** checking whether `navigator.locks` EXISTS is useless — the object is there, only the CALL throws. A substitution guarded by "if missing" never kicks in at all; install it always, and try the native locks inside |
| **Tenth door: browser databases, third attempt** (21 Aug 2026) | Stirling keeps the files themselves IN THE DATABASES: on "no databases" its manager doesn't fall back to another path, it just spins the "My Files" spinner forever — the document can't be opened | three states were tried in sequence: a "polite refusal" via an event (hung the Table app through localforage, 19 Aug) → `indexedDB = undefined` (saved the Board and the Table, hung Stirling) → **a small real database living in the window's memory** (open, stores, keys, brute-force indexes, cursors). Operations complete honestly, the app sees an empty store. The cost is named in the loading bar and in the card: these databases live only until the window closes |
| **Eighth door: a window on a bare "/"** (21 Aug 2026, Notes/memos + PDF/Stirling) | the app loads and runs inside (the proxy log: all 200 responses), but the person sees only the Extella logo — even after a restart. In the OS log: `[overlay] ready → boot` with no transition back | this isn't the sandbox, it's the OS shell: `updateOverlayForNavigation` treats the `/` route as an "unfinished router transition" and holds the overlay until a real route shows up. Apps that move off the root by themselves are saved (tududi → `/today`); apps whose home page IS the root are not. The fix on our side: open the window on an explicit route (`--путь /explore`, `--путь /home`). The tool warns if the route is left at "/" |
| **Seventh door: navigator.serviceWorker** (21 Aug 2026, tududi) | merely READING the property throws SecurityError — the loader dies before it even starts; the real cause only shows up once the proxy marks the scripts crossorigin (otherwise it's an empty "Script error.") | the shim removes the property ("no workers here"), not the browser — a silent stub |

**"Open in a separate window" in Electron is a myth**: the new window inherits the same
sandbox. There is no fallback path, only a fixed main one.

## cabinet_server proxy mode

    python3 cabinet_server.py --папка <любая> --порт 34788 --имя <slug> \
        --данные ~/extella-cabinet/данные --прокси-на 44788 \
        --шим ~/extella-cabinet/storage_shim.html

Everything except the service paths (`/_extella_storage|_version|_action`) is proxied
to the internal port; the shim is stitched into `text/html`. Stripped: CSP (it would
cut off our embedded script), X-Frame-Options (see the table), compression (a shim can't
be inserted into gzip). Sockets (socket.io) live on long polling through the proxy — our
server doesn't do WebSocket, and it turned out not to be needed.

## How to diagnose a white window (the three-round method)

0. **First ask: does the app even load?** The proxy's `--журнал` flag
   (`cabinet_server --журнал`) prints every request. If 200 responses come through
   and the person still sees the logo — it's not the sandbox at fault, it's the OS
   overlay (the eighth door).
1. **The hunting log**: turn on the request log on the proxy, ask the owner to
   refresh the window once. No requests — it isn't getting there; HTML is present but
   no assets — the document isn't rendering (look for XFO/CSP); everything is present —
   the script is dying.
2. **The reproducer**: the app's page plus the sandbox's locks (throwing on
   localStorage/cookie/IDB/History) opened somewhere the console is visible.
   Remember: XFO is NOT visible in the reproducer — it only hits the embed.
3. Fix only from a fact in the console or the log. Three doors out of five were
   found exactly this way; not a single "from memory" guess was ever confirmed.


## Window storage: two rules paid for in blood

**Write to disk WITH A DELAY (400 ms).** Apps check whether storage is alive like
this: they write a key with a random name, read it, immediately delete it. Stirling did
this by the dozen — 20 out of 27 keys in the work file ended up as `lswt-…`. Every probe
went out as a separate write and bumped the version counter, and the versions counter is
the signal "someone else changed the work": the window offered "Refresh", and when idle it
re-read itself on its own. The owner saw an app that blinked on its own. The delay collapses
the "wrote-then-deleted" pair into one write: the final result goes to disk, the garbage
never gets there. Anything unwritten is flushed on `pagehide` (sendBeacon).

**The app returns to the root ON ITS OWN — and that's the main part of the trouble.**
Opening the window on a route isn't enough, and moving the root away on the proxy isn't
enough either: the app's router shifts the address to "/" with its own pushState half a
second later, without a single network request (measurement on 21 Aug 2026, Notes: `/home`
→ `/` in 500 ms, the overlay dropped every time the tile was clicked). The shim is what
holds the address: it swaps any attempt to land on the root for the window's start route,
and it fixes the target of "home" links. Check without the OS window: open the app in a
browser and watch `location.pathname` for several seconds straight — it must stay on the
route.

**Auto-login CANCELS the root redirect if it's placed at the same spot.** My own
regression on 23 Aug 2026 (Browser Robot): turning on `--автовход`, I replaced
`--корень-на` with it, the window slid to a bare "/" — and the owner again saw the shell
restart. The flags are independent, set both. The check before shipping — three conditions
at once: the root answers with a redirect to the route, the route holds for several
seconds straight, the page finishes loading (`loadEventEnd`), zero hanging requests.

**A bare "/" must not exist for the app.** Opening the window on `/home` isn't
enough: inside the app there's its own "home" button that leads to `/`, and the OS
overlay drops again — right in the middle of work (measurement on 21 Aug 2026, Notes).
So the redirect is done by the proxy: `--корень-на /home` moves the person's navigation
from the root to the real route, and doesn't touch data requests.

**An eternal event stream stops the page from finishing loading.** The OS window
drops the overlay on the "page loaded" event; an open SSE stream delays it. Either pour
the stream through (the proxy can do that), or mute it: `--глушить /api/v1/sse`. Check
without the OS window: `document.readyState` and `loadEventEnd` in the browser — on a
healthy page, load happens within hundreds of milliseconds.

**The version counter isn't the same thing as "the work changed".** Before treating
an edit as someone else's, ask: did I just make it myself (the counter is "in flight"),
and does it mean anything to the person?

## When someone else's app can't do it — finish it inside it, not next to it

The built-in PDF viewer in the window wouldn't start: the engine lives in a worker
thread, and threads are dead in the sandbox. The temptation is to install a second app
for reading. The owner's word: "why would I need two tools". The right answer is to
finish it inside the same window.

How it was done (the shim, a "rescue viewer"): if the preview area hangs for more
than a few seconds, the shim takes the document FROM THE APP'S OWN STORAGE (our stub
database — it's already there, the person opened it) and shows it with its own layer on
top: pages, paging, zoom, close. The library sits next to the app
(`/_extella_page/lib/`), computes on the main thread.

Measurement on 22 Aug 2026: the document was found in `stirling-pdf-files`, shown
as "1 / 27", the page was rendered. The user stays inside one app.

**Embed INSIDE THE AREA, not over the whole window.** A full-screen layer works
technically, and that's exactly why it's deceptive: the document is visible, the
measurement is green — but the app is gone. The file list on the left and all the tools
on the right disappear, and the person can't compress or recognize text until they close
the preview. The owner's remark on 22 Aug 2026: "look at what happened". The right way is
to sit inside the same container where the app was showing its spinner, and take the
window's theme: the panels stay in place, and no foreign black bar shows up in a light
window.

**The check for this:** after showing it, make sure the app's panels are still in
place (`встал_в_область`, tool names are visible) — otherwise "it works" means "it
replaced itself with the app".

**The encoding of text files.** The app serves html/txt/csv into an embedded frame
via a temporary address; without an encoding marker the browser picks one itself, and
for Cyrillic it picks the wrong one ("Ð–ÑƒÑ€Ð½Ð°Ð»" instead of "Журнал"). The shim appends
`charset=utf-8` when it creates the temporary address — it doesn't touch the content.

**Take the library FROM THE APP ITSELF, not your own.** Your own copy, being a
different version, fights the one already loaded over the shared registry and fails with
"The API version … does not match the Worker version …". The trickery is that this passes
in a browser, but not in the window: there, the app manages to load its own copy first.
Look for it among the loaded scripts (`script[src*="/assets/"]`); your own copy stays as
the fallback path.

**Removing a product from the storefront** (came in handy right away: the separate
reading app turned out to be redundant, the owner ordered it removed entirely): the
HTTP method DELETE on `/api/listing/<id>` and the header `X-Extella-Token` — the plain
`X-Auth-Token` gets a 401, and "paths with delete" (`/api/delete-listing/…`) answer 404
and lead you astray. The response is `{"status":"success"}`. Removing the tile from the
desktop is a separate step: a listing is the product's card in the store, and a tile is
a shortcut on the desktop, and those are different layers.

**This can be checked without the OS window:** the flag `#extella_no_workers`
turns on sandbox mode as a whole — dead threads, the stub database, the rescue viewer.
Take the flag FROM THE HASH: the app loses address parameters during its own
navigation.

## The memory ceiling and long-running work: two silent killers

**The memory ceiling chokes heavy operations.** Setting `mem_limit` is the right
thing to do, but the number isn't picked out of thin air: for Stirling, 2 GB is enough
for opening and ordinary operations, but text recognition ran into the ceiling — the JVM
exited out of memory, the container restarted, and from the outside it looked like "the
app has gone silent" (measurement on 22 Aug 2026). At 4 GB, OCR went through: 27 pages
in Russian in 42 s. **Check the ceiling with the heaviest operation, not with startup.**

**Long-running work must not be cut off by a proxy timeout.** A minute and a half
isn't enough: apps do multi-minute work in a single request. The proxy waits 30
minutes.

**Recognition languages aren't part of the image.** Stirling ships with six of
them, and neither Russian nor Kazakh is among them: the request answers "none of the
selected languages are valid". The language files are placed in a volume at `tessdata`
and survive the container being recreated.

## The container looks out at the world from its own burrow

The container has ITS OWN 127.0.0.1 — that's the container itself, not the Mac. A
monitor for a local service at `http://127.0.0.1:34786` answers "ECONNREFUSED"
(measurement on 20 Aug 2026, the owner's very first monitor). The road from the
container to the Mac's services is the name `host.docker.internal`: verified from
inside the container, services on the Mac's 127.0.0.1 answer through it. External
addresses (https://…) work as usual.

## Acceptance

The install has happened when: the container answers after a restart · the data
sits as files in a volume · the port doesn't stick out externally · the tile and the
card are on the storefront · **the owner sees the interface inside the embedded OS
window and gets through the initial setup themselves**. Watcher passed all of it on
20 Aug 2026.

## Portability: three systems

The core isn't nailed to macOS: the windows' proxy is plain Python, app images
ship for both Intel and ARM. Four spots were nailed down, all small ones.

| Spot | What it was nailed down by | How it was solved |
|---|---|---|
| Service autostart | its own `plist` inside the installer | `tools/автозапуск.py`: launchd (macOS) · user systemd (Linux) · Task Scheduler (Windows). One promise: the service stays alive, comes up after a reboot, comes back up after a crash |
| Service name | Cyrillic went through fine on the Mac | systemd rejects Cyrillic in a unit name (`Invalid unit name`) — the name is converted to Latin in one place, `безопасное_имя()` |
| Path to tools inside experts | hardcoded to `~/Documents/Extella/...` | it's searched for: `EXTELLA_TOOLS`, then the usual locations; not found — a clear refusal |
| Path to Python | hardcoded to the python.org Python | the live one is used: `sys.executable`, then `which` |

**A separate Linux headache invisible on the Mac:** a person at their own desk has
their own systemd bus, but it doesn't exist on a server or inside a container — there
the service won't come up at all. Fixed with `loginctl enable-linger $USER`; the
installer says so in words, it doesn't stay silent.

**Measurement on 23 Aug 2026 (Ubuntu 24.04 LXD container):** the service is
installed, the window answers 200, the process is force-killed — the service brings it
back up itself (`NRestarts=1`), the window answers 200 again.

## The third track: Sources and Targets — capabilities with no window

The owner gave it the name on 23 Aug 2026. The words weren't invented: the
`источники.json` registry and the `ПОЛУЧАТЕЛИ` list in `скажи.py` had lived in the code
for six months — they simply hadn't been surfaced to a person.

| | source | target |
|---|---|---|
| Answers the question | where we take data from | where we put it |
| Form | HANDS OUT one of five | ACCEPTS any of five |
| Format passport | yes | not needed |
| Examples | Page Reader, Listing Builder | Delivery into apps |

The split isn't cosmetic: dump them into a single type, and you lose exactly what
gives you an N+M combination instead of N×M.

**Installation:** `tools/install_capability.py`. It installs only what has
**proven it works**: the tool is run with `--selftest`, and the exit code is checked
TOGETHER with the content of the output.

> **The exit code alone isn't enough.** Measurement on 23 Aug 2026: tools with no
> self-check also answer with zero — they simply don't understand the flag and exit
> silently. Checking by code alone would let anything onto the shelf. We require traces
> of real work: at least one check passed, shown in the output.

**Taking it off the shelf doesn't touch the expert on the platform:** other
people's agents can be using it, and cleaning up your own doesn't get to break someone
else's work.

## Archives in iCloud — only as a single file

The owner's rule from 25 Aug 2026: what goes into iCloud is an **archive**, not a
folder.

A `.git` folder is thousands of small files (the portal's history had 5681 of
them). iCloud transfers those badly: part of it stays "in the cloud", never
downloaded, and the folder quietly turns unusable. A single archive either arrives
whole, or it doesn't — there is no third option.

**Procedure:** pack it with `tar -czf`, **unpack it back and check** (count the
commits and make sure what the archive was made for is actually inside), and only after
that remove the unpacked copy from disk.

**What breaks the check:** `git ls-tree` escapes Cyrillic names (`$ЗЕРКАЛО` →
`$\320\227…`), and a string search gives a false zero — "there's nothing in the
archive" for a whole, intact archive. Read it with `-z` and decode it yourself.

Location: `~/Library/Mobile Documents/com~apple~CloudDocs/Extella-архивы/`.

## The app's name lives in TWO places

`editions/<slug>/listing.json` is the **source**. The OS desktop doesn't read the
name from there, but from the **store's storefront**, and a fix to the source does NOT
reach the person: the repository already has English, the desktop still has Russian,
and no error shows up at all (measurement on 25 Aug 2026 — the owner noticed it
himself, asking "did you translate my apps for me?").

**Getting it to the storefront:** `POST /api/edit-listing/{listing_id}` with the
fields `name`, `description`, `tags` (see `tools/deploy_page_product.py`).

**Check it by READING the storefront,** not by the response to the write: `GET
/api/listing/{listing_id}` and compare the name against the source. A "200" response
only says the request was accepted.

**We don't rename what belongs to someone else.** Products run by other people
(1C Agent, Recruiter, telecom-operator panels) keep their own names: renaming someone
else's live product is forbidden by the canon.

## The installer: why the app "installs" and still doesn't work

Measurement on 25 Aug 2026. A colleague of the owner installed an app from the
store — the install succeeded, the app didn't work. The version contained **a single
window page** pointed at `localhost` on her machine; the program itself wasn't there
and couldn't have been: it was only installed on the author's machine, by hand.

| In the storefront version | Our window (as it was) | A product that works for everyone |
|---|---|---|
| page | ✓ | ✓ |
| program in the archive | **0 MB** | present |
| experts | **0** | 5–15 |
| `installer_expert` | **empty** | specified |

**The person didn't do anything wrong — she was sold an empty package.** And the
store gave no warning: the button did its job, the tile appeared.

**The fix — a device-type product:** an archive + `install.py` at its root. The
platform runs the installer on the buyer's machine (the rules are in section B of
`DEPLOY_REQUIREMENTS.md`). Package build: `tools/build_device_package.py` from the
list in `editions/<slug>/package.json`.

**Three things verified by a probe on a clean machine, not by reasoning:**

1. **Reinstalling broke the install.** A running service holds its own port, and
   searching for a "free" one drifted to the next one over: the service is on the old
   one, the window is looked for on the new one, and the installer honestly fails.
   First we take down our own service, then we look for a port, and we stick with the
   previous one.
2. **The exit code must be honest** (B3): 2 on breakage, 0 on success. Zero on
   breakage means the buyer gets blamed for a broken install.
3. **Success is proven by the thing working** (C3): after installing the service,
   the installer knocks on the window and waits for an answer. "Service created" ≠
   "window answers".

**What breaks the check:** `$?` after `| tail` shows `tail`'s exit code, not the
installer's — measure the exit code without a pipeline.

## A device-type product: three misses in a row on one Board

A colleague of the owner installed the Board from the store three times, and it
was "successful" three times. Each time the cause was DIFFERENT, and from the outside
all three looked the same — the window stays silent.

**1. The version had no program.** Only a window page pointed at `localhost` on
her machine. The fix: an archive with `install.py` at the root.

**2. `installer_expert` is the NAME OF AN EXPERT, not of a file.** I put
`install.py` in there; the platform looked for an expert with that name, didn't find
one — and the install quietly didn't happen. The expert lives in the scope of the
source agent (scope is the set of objects available to a particular agent; rule C1)
and downloads the archive from `/api/app-archive` itself, unpacks it and runs
`install.py`.

**3. The product type is fixed WHEN THE LISTING IS CREATED.** The old card was set
up as a "Web app" (`source_type: extensions`), and no new version changes that:
`source_id`, `installer_expert` and `attach_agent` get written, but `source_type` is
read back as the old one, `expert_count` stays zero. A device-type product needs a NEW
listing, created from the start with `source_type=agent`, `source_id=<agent>`,
`attach_agent=1`.

**How to tell a working listing from an empty one — with a single read:**

```
source_type: agent     expert_count: >0     archive_mb: >0     has_agent: true
```

Zero in `expert_count` with a non-empty archive means there will be no one to do
the installing.

**The archive is zip, not tar.gz.** The installer-expert opens it as a zip and on
a tar.gz answers "the version's archive is not a zip".

**We don't break the old card:** people have it installed. A new one is set up
alongside it, and the old one is unpublished after people have moved over.
