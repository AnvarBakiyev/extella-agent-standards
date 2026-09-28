<!-- source: DEPLOY_REQUIREMENTS.md sha256:889297bd2a686b4f3799eff30496298a2e8edc7ad2ca026696976382f5b2c9a8 -->

# Agent requirements for a rollout to happen

**The document's canonical home is this repository** (`extella-agent-standards`), moved
from the portal on 12 Aug 2026 so colleagues read it from GitHub. A pointer remains in the portal.

Verified live on 10 Aug 2026 on the Recruiter Agent: the product went through the path **store → device
→ panel → live model response** in two delivery modes. Below is exactly what must be
done for that path to work for any next product.

Every item is written from fact: next to it is what verifies it and what breaks without it.

---

## Words that keep recurring below

**Scope** is the set of objects available to a specific agent; each agent has its own.
**Listing** is a product's card in the store.
**Pre-release** is a product version that only the author sees.
**Gate** is a machine check that must be able to fail.
**Mnemonic** is a stand-in symbol used instead of the real value.

---

## Product type decides the scope of requirements (edit 11 Aug 2026, from a review with the platform's author)

**Products on different delivery channels need a different scope of requirements.** The previous edition knew
only the device-type kind and demanded the full set from everyone — hence extra work on every
product. Below is a comparison of the two main channels; the full list of channels is in the next section.

| | **Page-type** | **Device-type** |
|---|---|---|
| What's attached on publish | the **`page`** field: HTML or a zip with `index.html` | an archive + **`installer_expert`** |
| Where the UI runs | on the Extella web, **in a sandbox** | on the user's machine |
| localhost | **not needed at all** | needed: the installer brings up the service |
| Token and email | `{{app_token}}` and `{{email}}` in index; don't request the full `{{token}}` (H5) | the product reads the binding file |
| When to choose it | logic in the browser or in the agent's capabilities | local data, 1C, a service, an environment (docker, exe) needed |
| Sections of this document | A, D, E, H | A, B, C, D, E, F, G |

### Delivery channels: there are four (edition 23 Sep 2026)

The word "product" is overloaded and causes arguments, so the type is defined not by "product-ness"
but by the **delivery channel** — how the thing reaches the buyer:

| Channel | What it is | Which requirements |
|---|---|---|
| **Page** (`page`) | an interface in the Extella web sandbox; no files on disk | A, D, E, H (+ H106: `{{app_token}}` and `app-agent/run`) |
| **Archive + installer** | installed on the buyer's machine, lives in `~/extella_apps/<name>/<version>` | A, B, C, D, E, F, G |
| **Container** (a special case of the archive) | the installer brings up a docker container, the OS window looks into it through a proxy | same as the archive, plus `docs/DOCKER_APP_TRACK.md` |
| **Capability** (`kind: source`) | an expert with no interface: a data source or an agent ability | A, D, E; it never has a page or an archive (see H98) |

Most often there's no need to choose "either-or": **one version carries both a page and an archive** (H10).
That's how the Recruiter is built — the window is page-type, the working part is on the device.

A **command-line program** (a ready binary plus a wrapper expert) doesn't have a dedicated track yet:
it's delivered as an archive, and the wrapper is a regular expert. Set up a track
on the first such product, not before.

**The "inside the toolbar" channel was removed on 23 Sep 2026.** The toolbar was taken down on 12 Aug 2026, and the "embedded
component" stopped being a channel at all: everything that rode inside it must move
to the storefront. Evolution Console is a live example: it used to be classed as embedded for two reasons
that died the same day ("a page can't call an agent" and "it rides inside the toolbar").
Today its only home is the storefront. If someone's copy of the canon still lists the toolbar as a third channel,
that copy is a month and a half behind.

### How to choose the type: three questions, in order

**0. Does it even sell through the storefront?** If the thing rides inside another product
(a toolbar component, the Wizard panel) — it's an **embedded component**, go no further:
storefront requirements don't apply to it, its own repository's process applies.

**1. Does the product need something on the user's computer?** Local files, 1C, a service,
data that must not leave the machine. Yes → **device-type**. (Example: the telecom operator's pack.)

**2. Does the interface call the agent or experts live?** ~~Yes → device-type: you can't
call an agent from the sandbox.~~ **THIS IS WRONG as of 12 Aug 2026 — the question is closed.** A page calls
both its own agent and its experts (`app_token`, H5), and it **reaches the buyer's device**
(H5-bis, the `device.run` permission). The only question now is the cost of the call: 13–17 seconds, so
**one snapshot call** instead of frequent small ones.

The phrase above is kept struck through on purpose: **it's exactly what two chats used to justify halting work**,
a day after it stopped being true. If you see it in someone's copy —
that copy is behind.

**3. How many calls per second does the interface need?** Many small, instant ones (a cockpit,
an editor, a live table) → a local part, i.e. an **archive**. One or two per minute (a summary,
a report, a dialogue) → a page will do.

**4. Both "no"?** Logic in the browser or in the OS's own API → **page-type**. (Example:
the telecom operator prototype — pre-built scenarios, nothing computed on the device.)

In one line: **the type follows where the data lives; the surface follows how many calls per second.**
And remember H10: one version carries both an archive and a page, so there's usually no
"either-or" to choose.
Having an agent does NOT determine the type: a page-type product can have an agent (the
`{{agent_id}}` link is created) — it's just that a person in chat will talk to it, not the page's buttons.

Words from the platform's author (call on 11 Aug 2026): the installer expert is **optional**, it's needed
only where an environment must be deployed; "for 95% of web-coding apps, attaching an archive is
enough." A separate origin for apps is **already done** — through a sandbox, not through a
separate domain. localhost remains exactly for the case where the installer brings up a service itself.

**Before applying sections B, C, F, G — make sure the product is actually
device-type.** They don't apply to page-type, and demanding them is exactly the extra work
that keeps a product from reaching the customer.

---

## A. The product's brain

*Applies to both kinds of product.*

**A1. The product has ITS OWN source agent.** The storefront copies **its own source agent's scope**.
Publish from a shared working agent, and the buyer gets your workshop: the `Lawyer` storefront
listing, published from `agent_extella_default`, ended up with **4,518 experts and
1,019 concepts** in the version. A snapshot from the product's own agent gave exactly **4 experts, 6 rules, 5 concepts**.
*Check:* the `stats` in the publish response equal the product's composition, no more.

**A2. The source agent is created in the interface, not through the API.** An agent created through the API or by the
store itself answers `pro_key_required` and doesn't think; one created in the interface gets the
account's key and works. This is a platform limitation, worked around by choosing the creation method.
*Check:* `POST /api/agent/run` with an `input` field returns 200 with no `error.code`.

**A3. The role is flashed into the source agent.** Otherwise the buyer gets the source's role: the first
test came back with the role of an **SMM content manager**, because that's what the test agent had.
*Check:* `agent/get` shows the product's own instructions, not someone else's.

**A4. Tools are narrowed down to what's needed.** The platform copies the source's set: the first test
came with **48 tools, including `agent_delete` and `delete_expert`** — the purchased
automation could delete the buyer's other agent. The Recruiter has six left.
*Check:* nothing with `delete` is in `tools`, unless the product genuinely needs it.

**A5. The product's rules and concepts live in the source's scope** (`global: false`). Global
entries are what grew into the registry with 186 duplicate names and 198 extra rows.

---

## B. The device-type part

*Device-type product only. A page-type product has neither an archive nor an installer.*

**B1. There's an `install.py` at the archive's root.** The installer finds it; without it the device-type
part doesn't deploy.

**B2. `install.py` is non-interactive.** It's run as a subprocess with captured output and a
timeout: any `input()` = a hung purchase. Everything needed arrives through the environment:
`EXTELLA_AGENT_ID`, `EXTELLA_APP_NAME`, `EXTELLA_APP_VERSION`.

**B3. The exit code is honest.** Zero on an actual failure = the buyer gets charged for a broken
install. This is now a matter of money, not tidiness.

**B4. The installer writes the agent binding.** `EXTELLA_AGENT_ID` → the product's file
(`~/extella_<product>/agent_binding.json`, the `agent_id` field). Without this the panel doesn't know
which agent to work with. *Warning:* Baga's and Predictive's passports still have the **Recruiter's**
binding file — someone else's.

**B5. Dependencies are installed working around PEP 668.** On macOS with Homebrew, `pip` refuses
system-wide; the second attempt goes into the user environment, and both attempts failing must
fail the install, not get swallowed.

**B6. The panel comes up on its own.** Neither the platform nor the store starts the local server.
The product sets up its own autostart; on systems where that isn't supported, the installer must honestly
print the start command.

**B7. There are no secrets or internal documents in the archive.** The archive goes to the buyer whole.

---

## C. The installer as an expert

*Device-type product only: `installer_expert` is optional and is needed only for deploying an environment.*

**C1. `installer_expert` lives in the product's brain, not globally.** The platform calls it under
the header of a **new** agent: no global entry was found in that scope, and the first purchase
failed with `Expert not found`. Inside the snapshot it arrives together with everything else.

**C2. The installer is idempotent.** Reinstalling doesn't create duplicate entries and doesn't break what's already there.

**C3. The installer proves delivery, it doesn't take it on faith.** After a write, it reads back. The word
`success` from the platform is not a fact: on delete, it arrives without a `deleted` field.

**C4. In "into an already-chosen agent" mode, the installer appends the product's role.** The platform
flashes the role only when creating a new agent. Append, don't overwrite: someone else's role
belongs to the agent's owner. Don't narrow someone else's agent's tools — warn instead.

---

## D. The storefront

*Applies to both kinds of product.*

**D1. The version is published as a draft.** `POST /api/publish` creates it with `published=0`, while
`publish-stream` **publishes it immediately** — I once put a test probe into the store this way.
It's only taken down by an explicit `{"published": 0}`: the same address with no body switches publication back on.

**D2. Price and model are visible before purchase.** The model is chosen by the agent's owner, but
the buyer pays for the work — they must understand the rate beforehand.

**D3. The name is in Latin script.** The platform strips Cyrillic from an agent's name: "Рекрутёр" turned
into `________`.

**D4. The OS extension is JavaScript.** An HTML file in `ext_files` is silently ignored
(`extensions: 0`), a `.js` one is accepted (`extensions: 1`). The extension runs on the OS's domain,
so it gets its authorization and doesn't need a local service. A panel on `localhost` does
**not** get the token substitution from the proxy — the proxy only works for non-local addresses.

**D5. One product, one icon.** A purchased storefront listing already appears in the grid as `MY APP`;
the shortcut from the installer adds a second one, `WEB APP`. The shortcut's name must differ
("— open panel"), otherwise the buyer sees two products.

---

## E. Product readiness (what breaks after install)

*Applies to both kinds of product.*

**E1. The interface collects every required input of the capability.** For the Recruiter, `Generate`
on the candidate card never works: the product requires `company`, but the panel doesn't
ask for it or store it — an empty string comes through and an honest refusal follows, "missing input:
company." A company profile is needed in settings.

**E2. The bridge's positional arguments are labeled.** The panel's bridge passes `args` **by order**.
A one-slot shift doesn't break the call, it quietly corrupts the meaning: in my run, `first_touch` ended up
in the `company` slot, and the candidate's email came out as "I'm from the first_touch team."

**E3. Waiting for work is visible.** The Recruiter already does this right: an overlay, a spinner, "Generating
outreach for: …", a "Generating…" button. The rule is `docs/RULE_WAITING_STATES.md`.

**E4. The error reaches the person.** The handler must show the `message` from the response. The Recruiter
does this (a toast), and my first conclusion, "a mute refusal," was wrong — I took the screenshot after
the notification had already faded.

**E5. Data in the interface doesn't contradict itself.** The candidate card shows both
"Skills (0)" and "Skills: 8" at the same time.

**E6. The window has one language.** Right now it's mixed: «Критерии оценки» next to "Scorecard — criteria by
which AI evaluates candidates," buttons `Configure`, `← Vacancy`, `Next: Candidates →`.

**E7. The page doesn't run sideways.** On the candidates screen, the table is wider than the window and
a horizontal scrollbar appears for the whole page.

---

## Deployment acceptance order

**For a device-type product — seven steps:**

1. the source's `agent/run` answers with no `pro_key_required`;
2. publishing gives `stats` matching the product's composition exactly;
3. a purchase in `new` mode and in `existing` mode goes through to the `done` event;
4. files have appeared on the device, along with a binding carrying the real `agent_id` and a running panel;
5. the agent answers with **its own role**, not the source's role;
6. one product scenario runs live from start to finish;
7. the product is represented clearly in the OS grid, with no duplicates.

**For page-type — five, and there's no device step among them:**

1. the source's `agent/run` answers with no `pro_key_required`;
2. publishing gives `stats` matching the product's composition exactly, and `page` is accepted;
3. `GET /app-page/{lid}` returns the product's page, not a 404 "This app has no web page";
4. the app requested access, the person confirmed it, and the page received the token via headers;
5. one product scenario runs live from start to finish.

Passed on the Recruiter Agent (device-type) on 10 Aug 2026, on all seven points. Acceptance
of a page-type product hasn't been passed even once yet — the first run will be proof, not a
formality.

Passed on the Recruiter Agent on 10 Aug 2026, on all seven points; the remainder under section E
(E1, E5, E6, E7) is open product fixes.

---

## F. A native window inside the OS (verified 10 Aug 2026)

*Device-type product only: this is about the panel on localhost. A page-type product opens as a window on its own.*

The product opens as a **window inside Extella OS**, with no hosting and no separate tabs.
The data stays on the user's machine; the condition is that the computer is on. Here's how it works:

**F1. The OS is opened inside the Extella app, not in a regular browser.** In the desktop's code:

```js
var _IS_DESKTOP = /Electron/i.test(navigator.userAgent || '');
if (isLocalHost(urlHost(url)) && !_IS_DESKTOP) { /* the "Open localhost" card */ }
```

In a regular browser (Arc, Chrome), an https page has no right to embed http://localhost,
and the OS honestly shows a card with an "Open localhost" button — the panel escapes into a separate
tab. Inside Electron that branch doesn't fire, and the local address embeds directly.
On top of that, `PROXY()` returns local addresses as-is — the proxy doesn't touch them,
so the `{{token}}` substitution doesn't work for a local panel (and isn't needed: access is taken
from the binding file).

**F2. The token is passed via the address's hash, not a dialog.** The OS asks for the token through `prompt()`,
which doesn't exist in Electron — hence the endless "Loading your desktop…" There's a built-in workaround in its own
code: `#etk=<token>` — the OS picks it up, stores it, and clears it out of the address. The hash isn't
sent to the server.

**F3. The OS card in the app's storefront listing is type `local_server` with `ui.url`.** It's exactly this
toolbar branch that draws the iframe (`router.js:6168–6183`). Type `hosted` never reaches it and falls
into the pointer card "Plugin loaded, work through chat."

The final chain: **the Extella app → the "Extella OS" card → the desktop → the product's
folder → the panel's shortcut → a native window.** Passed in full on the Recruiter Agent.

### What this means for the platform (from section F)

None of the three steps F1–F3 is documented anywhere: they were found by reading the OS's source.
An unfamiliar developer won't get to them — they'll see "Open localhost" and decide the product is broken.
This is exactly the cost of the missing contract mentioned earlier: the mechanisms **exist**, but
the default behavior leads to a dead end.

---

## G. Interface speed (measured 10 Aug 2026)

*The measurements apply to both kinds; rules G1–G3, G6, G7 apply to device-type.*

This section came out of the owner's question: how do you make logic reliable
and the interface fast at the same time. The answer turned out not to be about picking a transport, but about **what
exactly makes the user wait**. Below are numbers, not impressions.

### G0. Latency measurement (owner's Mac, 10 Aug 2026)

| What | Median |
|---|---|
| The product's local server | **6–17 ms** |
| Network to the platform, round trip (ping) | 256 ms |
| Core, a non-existent path (zero work) | 810 ms |
| Core, `health` | 1,260 ms |
| **Reading one KV key** | **1,700–2,900 ms** |
| OS domain, `/api/balance` | 1,600 ms |
| **Expert call** | **13,000 ms** |

The main conclusion follows: **there is no fast layer over the network.** A second
is spent before any work even starts (256 ms on the road + ~500 ms TLS). So "an interface
built on expert calls" is unfit as a transport — not "slow," but unworkable.

### G1. Data and operations go to the local server, not over the network

A list, a card, saving an edit must all be served locally: that's 6–100 ms
against 1,700 ms for KV. Everything that happens on a click is local.

### G2. The page arrives over https, the data comes from localhost

Verified live: an https page on `os.extella.ai` calls the local panel and
gets **real product data in 104 ms** (10 out of 10 requests). The condition is that
the local server answers with headers:

```
Access-Control-Allow-Origin: https://os.extella.ai
Access-Control-Allow-Private-Network: true   (in the response to the OPTIONS preflight request)
```

Without them, the browser rejects the request ("Failed to fetch"), and this is **easy to mistake for
a browser prohibition** — the earlier conclusion, "https can't reach localhost," was wrong.
The implementation is `platform_client.cors_headers()` + `do_OPTIONS` in the panel's server.

This removes all the pain of localhost as an **address**: there's no shortcut to localhost,
no "Open localhost" card, no separate tab. The local server remains a
quiet service attached to the product.

### G3. Answer the preflight with 200 and an empty body, not 204

Under HTTP/1.1, a 204 must not have a `Content-Length`; the combination "204 + Content-Length"
breaks keep-alive, and **every other POST fails** with "Failed to fetch." There's a second
trap in the same place: the handler must **drain the request body**, otherwise it ends up
attached to the next request as its request line (`{"args":[]}POST /api/ping` in the log). Both
defects gave the exact same symptom in the first probe as a browser prohibition.

### G4. The model is never waited on synchronously

The model's work takes seconds to minutes, and no transport fixes that. So: a click
queues a task (`task_id`, status via `/api/tasks/check`), the card is marked
"in progress," the person keeps working, the card fills itself in. It's the
card that freezes, not the window. The wait stays honest per
`docs/RULE_WAITING_STATES.md`.

### G5. One call returns the whole screen

Five calls for one page turn 100 ms into half a second, and over the network, into five
seconds. The screen's state arrives in a single response and is held in the page.

### G6. Autostart points at a permanent interpreter

A live defect found during this check: the Recruiter panel's autostart pointed
at a Python from the `uv` cache
(`~/.cache/uv/archive-v0/.../bin/python`). The cache was cleared — the service started failing
with `EX_CONFIG` and **the panel was dead**, while the product was still considered working.
The installer must write in a path that isn't removed when caches are cleared.

### G7. A shell on the OS's domain — how to live without localhost today

The headers from G2 solve half the problem: they let an https page **fetch data** from
the local server. But the browser doesn't allow **embedding** a local address as the page itself at all —
there's no exception for embedding a document. So in a regular browser
a localhost shortcut falls into the "Localhost opened in a new tab" card, while in
the Extella app (Electron) the same shortcut works: there's no prohibition there.

Until the platform serves the product's static files, the OS extension serves the page:

* the shortcut leads to an OS-domain address with a tag — `https://os.extella.ai/health#rec-panel`
  (the page is tiny, 200, no authorization; the OS loads it through its own proxy, the tag
  stays visible in the window's address);
* the extension checks the tag and does nothing in other windows;
* it pulls the interface from the local server (`GET /app.html`) and replaces the single
  place where the interface calls the bridge: `fetch('/api/' + method)` → the local address;
* the page's scripts are **recreated** as elements: through `innerHTML` they don't
  execute, and the interface would render as a dead picture.

Measured on the Recruiter Agent on 10 Aug 2026: a 338 KB interface arrives in **5 ms**,
a bridge call takes **4 ms**, and moving through the vacancy's steps works. There's no more
"Open localhost" card: the page is already https.

**This is a replacement for a missing mechanism, not a mechanism.** The extension can't be removed
by platform means, and it's mixed into every OS window — hence the mandatory
tag check as the first line.

### What this means for the platform (from section G) — status as of 11 Aug 2026

Three requests, formulated on 10 Aug from the measurements' results. Two of them were already closed **at the
very moment I wrote them**: the mechanisms existed, I just hadn't found them. The items are left with
notes, because an integrator's mistake is as much a fact as a platform defect.

1. ~~**Serving the product's interface over https**~~ — **CLOSED, and was closed from the start.**
   The mechanism exists: the `page` field at publish time and `GET /app-page/{lid}`. The request arose from
   my own mistake: publishing went out without `page`, and I declared missing what I hadn't looked for.
   Details — section H.
2. ~~**A separate origin per app**~~ — **CLOSED.** Done, but not through a separate domain,
   through a sandbox: each page is isolated and gets only allowed resources.
   The observation about `PROXY()` is still true and remains valid for pages that the OS
   opens NOT as a product's app.
3. ~~**Deleting what the platform lets you create**~~ — **CLOSED, my probe was wrong.**
   `DELETE /api/listing/{lid}` and `DELETE /api/version/{vid}` work: they answer `409`,
   "unpublish it instead of deleting," while purchases exist. Yesterday's `405` came from me not having worked out
   the route. The practical inconvenience stays narrow: a storefront listing someone has bought (including
   your own test purchase) can't be deleted — only unpublished.

**A new and the only live request (found by the 11 Aug 2026 measurement): let a page-type
app call its own agent.** Right now it can't: the `api.extella.ai` core has no
CORS for `Origin: null`, the OS proxy only accepts `GET` (POST → 405), and the OS has no
endpoint at all for running experts. So "agent + web app" declares a link, but there's no way to use it from
the browser. Either of two fixes is enough: CORS on the core for the sandbox, or proxying
the expert call through the OS. Details — H5.
4. **A minor point, on the same subject:** `/openapi.json`, `/docs`, and `/redoc` on the OS are open with no
   token. The data is protected, but the full map of 53 endpoints, including billing, is visible to anyone
   who knows the domain.

---

## H. Page-type product — the short path

Checked against the official developer guide (`Extella_OS_Developer_Guide.docx`, v1.0,
Aug 2026) and live probes from 11 Aug 2026. Sections B, C, F, G don't apply to a page-type
product: it has no archive, no installer, and no local service.

### H1. What gets attached

The **`page`** field at publish time, two formats:

| Format | Limits |
|---|---|
| one self-contained `.html` (CSS/JS inline) | **≤ 3 MB** |
| a `.zip` bundle with `index.html` at the root | **≤ 20 MB** compressed, ≤ 60 MB unpacked, ≤ 500 files |

A single top-level folder in the zip is collapsed; macOS junk is dropped; `..` in paths is
a 400 refusal. Without `index.html` at the root, the bundle isn't accepted. Other limits: archive ≤ 100 MB,
extension file ≤ 512 KB, icon ≤ 5 MB, tags ≤ 10.

The platform creates the shortcut to `/app-page/{lid}/` itself and writes it the headers
`X-Extella-Token`, `X-User-Email`, `X-Agent-Id`. **No installer expert is needed** — it's only needed
to put something on the device.

### H2. The token arrives as a substitution in `index`, not only as a header

The server replaces four placeholders in **index** (and only in index, not in the assets):
`{{token}}`, `{{email}}`, `{{agent_id}}`, `{{attachment}}`. The recommended approach is a single
inline script in `<head>` that assembles `window.EXTELLA`.

**A trap that will leak the token.** The replacement is a plain text search over the whole index.
If a placeholder is mentioned in **visible text** (documentation, a hint, a code example),
the server will write the user's real token right there. Write literal mentions only as
HTML mnemonics (`&#123;&#123;token&#125;&#125;`).

And the reverse: if the page was opened **not** through the OS shortcut, no substitution happens and
the raw `{{…}}` stays in the strings. The page must recognize this and say so in words, not
fail silently.

### H3. The bundle's assets are public — there can be no secrets in them

`GET /app-page/{lid}/{path}` is served **with no token**, with `Access-Control-Allow-Origin: *`.
That means everything sitting in the zip next to index is available to anyone. Keys, private data,
and internal documents don't go in there.

The shortcut must end with a slash (`/app-page/{lid}/`): the proxy inserts `<base href>`, and
without the slash, the assets' relative paths don't resolve — the classic symptom of "a page with no
styles."

### H4. The sandbox: what's allowed and what isn't (verified by measurement)

The page opens in an `iframe sandbox="allow-scripts allow-forms allow-popups
allow-modals allow-downloads"` — **without** `allow-same-origin`. Consequences:

* **you can** call the OS's own API: its CORS is explicitly set for `Origin: null` —
  verified, `access-control-allow-origin: null` comes back and
  `x-extella-token` is allowed;
* **you can't** reach the desktop, `localStorage`, cookies, or an environment token;
* **you can't** reach `localhost` — if local data is needed, the product is
  device-type (sections B–G);
* **extensions aren't injected into the sandbox** — they're only for regular sites in the OS's browser.
  (Which means our extension shell from 10 Aug is inapplicable to page-type products in principle.)

### H5. A page CAN call its own agent — through the app-token

**The limitation was lifted by the platform on 12 Aug 2026.** The previous edition of this section said
"a page can call neither an agent nor an expert" — that was true right up until the
`app_token` mechanism appeared. Verified by a live probe the same day.

**Confirmed a second time on 19 Aug 2026, by someone else's measurement on a hybrid product.** The same conclusion
came independently: the page gets a state snapshot with one expert call on a
pinned device, which needs permission to run the expert and to reach the device.
A caveat from that same measurement: detailed local actions still stay in the archive
part — the page takes a snapshot, it doesn't do the work.

**How it works.** `{{app_token}}` is substituted into index — an encrypted, expiring
capability (TTL 2 hours, refreshed by reloading the page), holding the pair
`{token, listing_id, expiry}`. Two narrow endpoints accept it:

| Endpoint | Body | What it does |
|---|---|---|
| `POST /api/app-agent/run` | `{app_token, expert_name, params}` | runs an expert of the page's own agent |
| `POST /api/app-agent/message` | `{app_token, payload}` | a dialogue with the agent |

The binding is re-read on every call from the purchase and nailed down by a header — you can't reach someone
else's agents. Limits: 30 calls per 60 s, body ≤ 64 KB. Leaking an app token costs
an attacker only "this app's agent until it expires," not the account.

**Measurement (live probe, page-type product, pre-release):**

| Check | Result |
|---|---|
| `{{app_token}}` substituted | yes, 204 characters |
| `app-agent/run` with a non-existent expert | **channel open**: 3,656 ms, core response "Expert not found" |
| `app-agent/message` | **doesn't work**: `422 {'loc':['body','agent_id']}` — see below |
| Core directly (`api.extella.ai`) | closed, and rightly so: CORS for pages was never opened |
| The OS's own API | 200 |

**What this changes for choosing the type.** The question "does the interface call the agent or experts?" no
longer automatically sends a product into the device-type channel: a page-type product can now
do this too. What decides remains the first question — **does something need to be on the user's
computer** (local files, 1C, services). Data on the machine → device-type; logic
in the browser or in the agent's capabilities → page-type.

**Two open observations (reported to the platform's author on 12 Aug 2026):**

1. `app-agent/message` always fails: the core requires `agent_id` not only as a header, but also
   in the request body. The same class as the error already seen with `agent/run`.
2. **`{{token}}` is substituted into index unconditionally** — regardless of `page_headers`.
   The page receives the buyer's full account token (36 characters, the same one that
   opens the core). That means a seller who wrote `{{token}}` into their page gets the
   buyer's whole token. As long as this is the case — **use `{{app_token}}` in your own products
   and don't request `{{token}}` at all**: you don't need it, and you're the one
   responsible for it.

### H5-bis. A page REACHES THE DEVICE — measured 12 Aug 2026

The most important measurement: can a store page launch an expert that runs
**on the user's computer**, not in the cloud. This determined whether products
with local data (1C, files, services) could move into the storefront.

**The answer: it can.**

| Call from the page | Result | Time |
|---|---|---|
| `app-agent/run` with no pinning | **device**: machine name, id `24f37e45…`, home folder | 17.3 s |
| the same with `targets: [<device id>]` | **device**, the same response | 13.6 s |

The measurement tool is the expert `probe_where_am_i`: it checks whether the listener's file
(`~/.extella/device.txt`) exists and returns the machine's name. There's no such file in the cloud, so "where"
tells execution on the device apart from execution in the cloud with no guessing.

**Consequences:**

* **the question "does the interface call the agent or experts?" no longer determines the product's type.**
  The only thing that decides is **where the data lives** and whether it must stay on the machine;
* products tied to a device can move into the storefront;
* the cost of a call is **13–17 seconds** (page → OS → core → listener → back). This is the physics of the
  route: such calls are queued as a background task with a visible wait (G4), not waited on
  synchronously.

**Hence the rule for porting device-type interfaces: one snapshot call, not many small ones.**
The local bridge answered in **6 ms** — two thousand times faster (G). An interface built on
frequent small calls will become unworkable if ported "as is," and the reason will be
not security but the **number of calls**. It has to be rewritten so that: an expert gathers
state on the device and hands it back **in a single response**, and the page then works with what's already
in hand. Whatever doesn't fit that model — leave it in the local version and **say so
in words on screen**, rather than leave it to silent guessing.

**CORRECTION a few hours after the measurement: this now requires the `device.run` permission.** That
same day the platform rolled out app permissions (H12): `targets` goes through **only** if
the buyer granted `device.run`, otherwise it's stripped, and the expert runs in a container, not on the
machine. Our measurement was done before that, which is why both calls went to the device.

In practice: **the page-type part of a device-type product must request `device.run` at
publish time.** If it doesn't, no snapshot will come from the machine, and the product will look like it works.
The buyer revoking the permission is also a normal situation: say so in words, don't show a blank screen.

**What the measurement did NOT prove (don't pass this off as proven):** it was done on the owner's account, where
the buyer and the author are the same person, and the listener is guaranteed alive. Whether the path to the device
works the same way for an **outside buyer** hasn't been checked. It's checked by one purchase with a colleague.
And the obvious point: **if the buyer has no live listener, there is no device at all** — the page
part must work honestly without one, not show a blank screen.
### H5-ter. Purchase mode decides whether the agent will be new — and this is easy to miss

Observation from a measurement: after a repeat install, the page got a different `agent_id`
(`agent_x8qw…` → `agent_3UNL…`), and the call failed with `Expert not found` — the expert stayed
in the scope of the previous agent.

**Correction 12 Aug 2026 (owner).** This is not automatic reinstall behavior: the purchase asks
for a mode — deploy a **new** agent or install **into an existing one**
(`deploy_mode: new | existing` + `target_agent_id` in the API). The new agent appeared because
the "use existing" button was not pressed. So the cause is **a mode choice,
not an inevitability**; but this choice is made in passing, and its consequences are quiet.

* **The product's scope does not survive an agent change.** The experts that the installer
  lays out will arrive again on their own; but everything a person or a chat put into the scope AFTER install —
  rules, concepts, tweaks — stays with the previous agent. From the outside it looks like
  "the product suddenly forgot its settings."
* **Check `agent_id` after every reinstall**: if it changed, a new agent was deployed,
  and everything tuned stays with the old one.
* **Agents multiply:** one listing produced three agents over three reinstalls.
* So store product settings somewhere an agent change won't lose them (KV under an explicit
  product key, a file on the device), not "in the scope, because it's convenient."

### H5-quater. Field asymmetry between `expert/save` and `expert/get`

`POST /api/expert/save` expects **`name` / `description` / `code`**; `POST /api/expert/get`
accepts `name`, and returns the code in the **`expert_code`** field.

**`description` is mandatory: without it `expert/save` returns `422`** (reported by the Recruiter chat
on 13 Aug 2026; our REST canon didn't have this). The refusal looks like a problem with the expert's code,
though the issue is the missing description — and the first thing people do is rewrite the code.

You write under one name — you read under another. A cross-check written on intuition reads `code`,
gets emptiness, and is **always green**: it will never see the discrepancy. This exact class of
defect was caught by one of the chats in its own check. Hence: compare **by content**
and make sure the check is able to fail.

**Full composition of the `expert/get` response (captured live on 12 Aug 2026):** `status`, `expert_name`,
`expert_description`, `expert_code`, `expert_prompt`, `expert_params`, `cspl`, `group_name`,
`createdAt`, `updatedAt`, and **`global`**.

Hence two corrections to what chats believed was a platform limitation:

* **`global` is present in the response** — scope can be checked by reading it, no need to invent workarounds;
* **there is also a second, independent signal:** the same `expert/get` called as **another**
  agent returns `Expert not found`. Two different ways to tell scope apart, instead of "indistinguishable."

And a trap when reading this field: `global: true` **does not mean "visible to all agents."** A live
example — an expert with `global = True` that two other agents cannot find at all. The field states
a property of the record, while scope decides visibility (see the canon on shadow scopes). Check
availability by name against a specific agent, not by the flag's value.

### H5-quinta. Two silent shortcut dead ends

Both look like "the product is broken," though nothing is actually damaged:

* **a page added to a version AFTER purchase does not create a shortcut** — the platform places it
  at install time. Only the agent will remain on the desktop; clicking it opens the chat, and the person
  will conclude there is no interface.

  **The fix is not a reinstall — correction 13 Aug 2026 from the Recruiter chat.** The canon said
  "reinstall the purchase," but a reinstall also resolves the agent question and can produce
  a **new** one, breaking the product's binding to the current one (H5-ter). Cheaper and more reversible —
  create a shortcut of the same shape as the working ones: `POST /api/desktop/shortcut` with the address
  `/app-page/{lid}/` **with the trailing slash** and **with not a single header** (H5-quinta below). Verified:
  a shortcut created this way works, and the desktop went from 7 to 8;
* **a shortcut created by hand returns `401 X-Extella-Token header required`** — and this is exactly where my
  previous wording was not just incomplete but harmful.

> ⚠️ **CORRECTION 13 Aug 2026, and it matters: the shortcut does NOT need a token header.** This used to
> say "setting up a shortcut by hand is two steps: create it, then attach headers." From that it
> read as "add `X-Extella-Token: {{token}}`" — and one of the chats told the owner exactly that.
>
> **Measurement:** on a live desktop **seven app shortcuts, all with zero headers** — and they
> work, including the published guide and the ticket-analytics demo. The page identifies the caller by the
> internal `X-OS-Caller`, which the OS proxy substitutes itself for requests to `/app-page`.
> The token header is only a fallback path for a direct call that bypasses the OS.
>
> **So `401` doesn't mean "no header," it means "the request didn't come through the OS proxy."** Causes
> by frequency: an address without a **trailing slash**; an address that isn't `/app-page/{lid}/` but something else;
> a shortcut created as an ordinary web app pointing to an arbitrary URL.
>
> **The fix is not a header but the correct shortcut:** the one the platform creates itself at
> install time (`/app-page/{lid}/` with the slash). It's already on the desktop after purchase; if it's missing —
> reinstall the purchase, don't add headers.
>
> **Why this isn't a small thing:** `{{token}}` in a shortcut's headers hands the page a **full-rights
> account token** and triggers a consent dialog for the buyer (H11). So the advice "add the
> token" turns a working install into a product with excess privileges — and that's exactly what gets it turned away.

### H6. Attachments: a product can open desktop objects

Right-click on an object → "Open with…" → our product gets `X-Attachment-OS`
(backend) or `{{attachment}}` (static page), percent-encoded, truncated to 6000
characters. Forms: `<file>path</file>`, `<folder>`, `<list>` recursively, `<instruction>`,
`<agent>agent_id</agent>`, `<web_app>url</web_app>`.

**The attachment is one-time only:** on a window refresh (⟳) it will be gone. So it must be read and stored
in the app's memory right away, on the first render.

### H7. Pay-per-action — without a user token

The app creates a request via `POST /api/billing/transfer` (no authorization; the gate is the payer's
confirmation), polls `GET /api/billing/transfer/{id}` every 1–2 seconds, and the OS itself
raises a dialog for the payer for **30 seconds**. Confirming or declining programmatically is
**impossible**: the confirmation is protected by a signed httpOnly desktop cookie and an Origin
check — any call from a page, script, or curl gets a 403.

Hence: the app **does not need the buyer's token**, `{{email}}` is enough for prefill.
The "pay per action, not per install" model is technically available; the decision on it is up to
the product owner.

### H8. Publication, versions, deletion

Publishing creates a **pre-release** (`published=0`): visible only to the author. Into the store —
`POST /api/listing/{lid}/publish` with `{"published": true}`.

The agent snapshot is frozen at the moment of publication: further edits to the agent will land only
in the next version (`POST /api/add-version-stream/{lid}`).

A purchase is pinned to a version. **The index is served by the purchase's version, while the bundle's
assets come from the latest version that has a page.** This means: an incompatible change to the assets
will break buyers pinned to the old index. Change assets only compatibly.

Deletion (verified 11 Aug 2026, and this is a **correction to my earlier conclusion**):
`DELETE /api/version/{vid}` and `DELETE /api/listing/{lid}` **exist and work** — they return
`409` while purchases exist ("unpublish it instead of deleting"). The earlier note "nothing to delete
with, 405" was wrong. The practical consequence stands: a storefront listing that even one person has bought
(including our own test purchases) cannot be deleted — only unpublished.

### H9. The charge happens after install

Order: balance check → rollout → installer → **charge to the buyer**. Money is not yet credited to
the author automatically: sales are exported and paid out manually, automatic crediting is in progress
(the owner's word, 27 Sep 2026). A failed install does not leave the buyer having paid for nothing;
reinstalls and free listings are not charged. Hence the earlier rule about an honest
installer exit code (B3) — it's about money, not tidiness.

### H10. One listing carries BOTH an archive AND a page — this is not two products

The common fork "archive or page" is actually false. One version accepts **three
separate files** (`POST /api/publish-stream`, `multipart/form-data`, checked against the OS schema
on 12 Aug 2026):

| Field | What we put in | What the buyer gets |
|---|---|---|
| `archive` | product zip + `install.py` | the local part: services, `.state`, keys, file access |
| `page` | interface zip with `index.html` | the surface in the OS window, a desktop shortcut |
| `icon` | 512 px PNG | the icon |

Hence **the hybrid is a standard product type, not a compromise one**: data and keys live on the machine
(the archive), the interface is served from the OS (the page), and between them is an expert call that
executes on the device (H5-bis). Client data does not leave the perimeter in the process — only what
the person already sees on screen goes out.

**External fonts work inside the sandbox** (verified 12 Aug 2026 on a live OS window): the page
pulled in Google Fonts, and serif headings rendered. Fallbacks are still mandatory —
the font may fail to arrive, and the text must still be readable.

**A page can be replaced without creating a new version — VERIFIED LIVE on 13 Aug 2026** on an already
published listing ("Development on Extella," version 1.0.0). `POST /api/edit-version/{vid}`
accepts `page` (and `archive`); `remove_page` removes it. What was confirmed in the live run:

* the new text is visible in the window right away; it wasn't there before the edit;
* **the version number did not change** — no new version appeared;
* **`Publish` is not needed again** — the listing stayed in the store;
* nothing broke for those who already installed the product: the shortcut is the same, no reinstall is needed.

So editing the interface is an operation at the level of "change a file," not "ship a release." This changes
the economics of page-type products: text, hints, and layout can be edited daily.

The flip side from H8 remains: the index is served by the purchase's version, while assets come from
the latest version that has a page. For a single HTML file this doesn't matter (the index is the whole
product); for a zip bundle — change assets only compatibly.

### H17. The expert's response arrives in TWO wrappers, and the dict is not serialized as JSON

**Caught on a live product on 14 Aug 2026.** The page opened, wrote "log on your
machine," and showed "solutions: **undefined**." Not a single error in the console: another silent refusal,
this time in our own product.

Two causes, both non-obvious:

1. **There are two wrappers.** The OS gateway puts the core's response into `result`, and the core puts
   the expert's result into **its own** `result`. Parsing just one wrapper gives an object that lacks
   the needed fields — and the code calmly moves on;
2. **The dict returned by the expert is serialized with Python's `repr`** — single quotes,
   `True`, `None`. This is **not JSON**, and `JSON.parse` won't take it.

**The fix is in the expert, not the page:** return `json.dumps(...)`, i.e. a **JSON string**.
Then the response parses unambiguously, and the rule holds for any product.

**And the broader rule behind this case:** success is not "a response arrived,"
but **"a response of the shape we expect."** The page must check the shape (in our case — that
`всего` is a number) and say in words if something else arrived. Otherwise the product cheerfully reports
success while showing `undefined`.

### H19-quater. An extension update leaves the old copy on the desktop

Measurement on 14 Aug 2026 while updating an edition's theme: after reinstalling to a fresh version,
the account library has **one** entry (the new one), but the desktop has **two**: old and new.
Both execute.

Hence two things:

* **the re-run guard must include the version.** Our flag was shared
  (`__тема_ИЗДАНИЕ`), so the old copy claimed it first and **blocked the new one** —
  the theme update silently failed to apply. In the template the flag is now versioned;
* **the stale copy can be removed from the desktop**, and it does not come back — but only if it's
  **already gone from the library**. This is the exact rule that refines yesterday's mistake:

> **A desktop-state edit holds if the entry is not in the account library.**
> If the entry is in the library, the OS will bring it back.

Verified twice with a pause of 10 and 25 seconds: the removed stale copy did not come back,
the removed live one (13 Aug) — did come back.

### H19-ter. A theme only colors what it knows the variable names of

**And this cancels the alarm I raised myself.** I installed the edition theme for the owner and wrote
that his accent color had changed. **Nothing had changed** — I didn't check, I just said it.

Measurement by reading the OS shell: it has **its own** variable names —
`--p` accent, `--ph` on hover, `--ps` backdrop, `--bg`, `--card`, `--t`, `--tm`, `--tb`,
`--brd`, `--r`, `--rsm`. It **does not know** our interface tokens (`--a`, `--s1`, `--tx`).

So a theme that changes `--a` colors only our own pages, not the shell.
It "worked" and did nothing. The template is fixed: for the shell we write its names,
for our own pages — ours.

Consequence for editions: **before coloring someone else's interface, read its variables.**
A theme written against your own tokens silently doesn't work — another refusal without a single error.

### H21. Pinning by tag doesn't save you from a stale tag

Measurement on 14 Aug 2026 while assembling the first edition. The manifest referenced `v0.1.0` — correct
in form, since a floating branch is forbidden (H14). But the tag pointed to **26 July**: **21 files
against 191** in today's `main`.

That is, the edition would have delivered the person **a canon three weeks stale**, and he wouldn't have
noticed: files in place, checks green, just old rules. The same ailment that
was eating up our days — only delivered by the installer.

> **A tag fixes WHAT will arrive, but does not guarantee it is fresh.**
> The tag is updated when an edition ships, not created once.

In practice: before shipping an edition — a new tag on the current canon, and the reference in the manifest
is updated along with it. A stale tag is worse than a floating branch: a branch will at least bring
today's state.

### H20. For a published listing, EVERY new version goes to the store immediately

**Found by the Codex-bridge chat, verified by measurement on 14 Aug 2026.** Our rule "exactly one
irreversible action — `listing/{lid}/publish`" is true **only for a new listing**. Beyond that it
is misleading.

Measurement: the guide's listing is readable **with no token at all**, `published: 1`, and publicly lists
**all five versions** — 2.0.0 … 3.0.3. A version **has no publication flag of its own**:
`published` is a property of the listing, not the version.

> **Hence: `add-version-stream` on a published listing is a public release.**
> There is no separate button for a version. A chat that added a version "just to take a look"
> has already shipped it to everyone.

Practical consequences:

* **the owner's permission is needed not only for the first Publish but for every version
  of a published product.** Our deployer and the standard's text account for this:
  the first release is a pre-release, and any version after that only with explicit sign-off;
* **a pre-release for testing something new is done as a separate listing**, not as a version of the live one;
* **intermediate versions cannot be deleted** if purchases point to them — including your own
  acceptance purchases. This is correct platform behavior: a buyer is pinned to a version.

The check before adding a version is one line: read the listing's `published`. A value of one
means "everyone will see it right now."

### H19-sexta. THE OS LOOK IS NOT CHANGED BY AN EXTENSION — my mistake, which cost the owner time

**Measurement on 14 Aug 2026. I claimed that an "edition theme" was possible via an extension, built it,
published it, and installed it for the owner on a live machine. It did not work, and here is why.**

In the OS shell page (`GET /desktop`) there is **not a single mention of mixing in extensions** —
no `extension`, no `userScript`, no `inject`. Extensions are mixed in by **the OS's built-in browser
into the pages it opens**; the shell itself is not a browser page.

So:

* **the OS look is not changed by an extension.** Not the color, not the background, not the order on the desktop;
* **the windows of your own apps — yes** (a historical confirmation: the Recruiter panel's shell worked
  exactly this way), but a product already colors its own window with its own CSS, no extension needed.

**What follows from this for editions, and this is the third reversal in a day:** "an edition changes the look
of the environment" is not possible today. An edition can give **a consistent look inside its own windows** and
a common set of apps. Nothing more.

**How I fell for this.** I checked the shell's CSS variable names (`--p`, `--ph` — matched),
saw the match, and considered the mechanism proven. What matched was the **names**, not the **fact that
the code was delivered**. Rule: you must prove the whole path, not the link that's easiest to check.

The theme listing has been deleted, the desktop entry removed, the extension library is empty.

**A trace in the gate (14 Aug 2026, evening).** `check_edition` kept REQUIRING a theme file for every
edition — that is, forcing a knowingly dead file into the manifest and promising in green
that it did something. The requirement has been removed: the theme is checked only if the edition declared it;
declared but missing is still an error. Both cases are proven by the self-check.
General lesson: **a refuted rule must be removed not only from the text but also from the gate** —
otherwise it keeps living and keeps binding.

### H30. A SECRET FOR AN EXPERT: where it lives and how to read it. Measured from the inside

**A colleague's question on 17 Aug 2026:** an expert needs a third-party service key; via the MCP `get_kv`
the value arrives as `$enc:IV:base64`, while a direct POST from the expert returns
`401 Authentication required (user_id missing)`. Checked by a scout on the device.

**1. There is NO built-in function for reading a secret in the expert's runtime.** Of the expected names
(`get_kv`, `get_secret`, `kv`, `extella`, `platform`, `mcp_call`), exactly one is available:
`include`.

**2. `$enc:` is how it looks from the MCP side, not a storage method.** The same key over REST with three
headers arrives **as plain text** (measured: 30 characters, no prefix). There is nothing to
decrypt — you need to read it a different way. `~/.extella/vault.key` plays no part in this: the file
does not exist on the machine at all.

**3. The listener PUTS a token into the expert process's environment** — `EXTELLA_API_TOKEN`
(36 characters). Alongside it, `EXTELLA_BRIDGE_SECRET`, `EXTELLA_BRIDGE_ACCOUNT_BINDING`,
`EXTELLA_BRIDGE_PORT` — not needed for KV. Hence the reason for the 401: there were no headers at all.
With a token but no agent — `422`, the `x-agent-id` field is mandatory. **Three headers → 200.**

**4. `X-Agent-Id` does NOT arrive in the environment, and that's not a small thing.** KV lives in the agent's scope:
the same key with someone else's id gives **`500 Key not found`** (measured), not an empty response. So the
agent id is something the expert gets as a PARAMETER; you cannot take it from `~/extella_wizard/app/config.json`
— it might hold a different agent, and you'll get "key not found" on a key that exists.

**5. No `api_key_name="…"` convention with automatic key substitution was found** either in the runtime
or in parameter behavior. Don't expect it; the CTO handles a closed KV with input through the OS
interface separately.

**6. A recipe verified on a live key:**

```python
$extens("include.py")
def мой_эксперт(агент="", ключ="qwen_api_key"):
    include("import requests", ["extella-pip install requests"])
    import json, os
    токен = os.environ.get("EXTELLA_API_TOKEN", "")
    if not токен or not агент:
        return json.dumps({"ошибка": "нужен параметр агента; токен даёт листенер"},
                          ensure_ascii=False)
    о = requests.post("https://api.extella.ai/api/kv/get", json={"key": ключ},
                      headers={"X-Auth-Token": токен, "X-Profile-Id": "default",
                               "X-Agent-Id": агент}, timeout=60)
    if о.status_code != 200:
        # 500 «Key not found» = ключа нет В ЭТОМ скоупе, а не поломка платформы
        return json.dumps({"ошибка": f"KV ответил {о.status_code}"}, ensure_ascii=False)
    секрет = о.json()["value"]      # открытый текст: в ответ и в журнал не кладём
```

**The secret is not printed anywhere** — the expert's response is seen by the chat, and the chat is seen by the person.

**7. For a buyer from the store,** the key is put in by the buyer themselves, into their own KV and in
their own agent's scope. A page-type product works differently: `app_token` + the `kv.read` right via
`app-agent/run`, where the agent is implied by the purchase. Someone else's key is not accessible from a
sold copy — and that's how it should be.

**CORRECTION 17 Aug 2026, same day: the token in the environment may NOT BE THERE.** Measurement on two
machines:

| machine | what's in the expert's environment |
|---|---|
| owner's Mac | `EXTELLA_API_TOKEN` (36 characters) + bridge variables |
| colleague's machine | **only `EXTELLA_API_URL`**, no token either via `run_expert` or via `run_agent` |

So the injection depends on the machine or the listener version, and the "token from the environment" recipe
is not universal. I presented it as universal — that was a mistake that cost the
colleague a round of debugging.

**The order is now this, not the other way around:**

1. **the primary path is a file next to the product** (`~/extella_wizard/app/<name>.key`, permissions
   600) and an honest refusal if the file is missing. Works in any context, on any machine;
2. **the environment is a nice bonus**: if `EXTELLA_API_TOKEN` is present, we read the agent's KV and
   get a key tied to the account rather than to the machine;
3. **never treat a missing token as a platform breakage** — it's a difference in the launch
   context. A refusal must name what's missing, not just say "it didn't work."

**What we recommend.** Your own perimeter — the agent's KV. Someone else's machine — a file next to the
product and an honest refusal if the file is missing. From the listener's environment you can rely only on
`EXTELLA_API_TOKEN`.

### H29. A FALSY PARAMETER DOES NOT REACH THE EXPERT. Verified with an echo expert

**A finding by the AGP team (the first external user), verified by us on 17 Aug 2026** with an echo expert
that returns `repr()` of what it received:

| sent | arrived at the expert |
|---|---|
| `False`, `0`, `""` | **the default value** — all three |
| `True`, `7`, `"text"` | as sent |
| `"False"`, `"0"` as strings | as sent |
| `" "` (a single space) | **the default value** |
| nothing sent | the default value |

**1. False and zero are indistinguishable from "not passed."** The expert cannot tell that a person
explicitly said "no": it sees its own default. Hence the rule — **safe behavior must
be the default value, and turning on something dangerous must go through a truthy value**. A flag
`подтверждено=False` does not protect; `подтверждено="да"` does.

**2. A string made only of spaces also disappears** — beyond the AGP finding. A space as a meaningful
delimiter cannot be passed as a parameter.

**How to catch this yourself.** A five-line echo expert that returns `repr()` of each parameter
is the fastest contract check that exists.

### H28. THE REQUEST LIMIT IS SHARED PER MACHINE, AND THE PANEL MUST NAME THE REFUSAL

**Found by the Recruiter panel chat on 17 Aug 2026.** The person clicked the button twice, the panel
responded "The app did not respond." The limit is counted **per IP address**, and in that same minute
four other things were firing from one machine: the hourly task agent, deploy-time checks, the installer,
and the panel itself.

**1. The request budget is shared per machine, not per product.** Everything that ticks on a schedule
must yield to a live person: spread itself out over time, back off on a refusal, not hammer with
retries. Automation that clogs a minute for a client is a defect, not background noise.

**2. The panel has no right to turn any refusal into "did not respond."** A named cause is
part of the product: "request limit, wait a minute," "no permission," "service stopped."
One phrase for every case is the same silent refusal, just a polite one: the person doesn't know
what to do and repeats the click, finishing off the limit.

**Measurement 17 Aug 2026: there is no way to learn the remainder.** Neither on a successful core
response nor on a refusal is there a single header about the limit — no `X-RateLimit-Remaining`, no
`Retry-After`. A request to the platform: return these, and a `429` with a body instead of a `500`.

**The real cause of that particular case turned out to be different** (and this is a separate lesson): the
interface passed five arguments to the method, and the method accepted four. The limit was a coincidence,
and "did not respond" hid both problems. The `check_ui_api_contract` gate now checks the
argument count.

### H24-bis. THE THREE SANDBOX DOORS behave differently

**Clarified by the Schemes Board chat on 16 Aug 2026.** "Storage is closed" is actually three different doors:

| door | behavior | what to close it with |
|---|---|---|
| `localStorage` / `sessionStorage` | stays silent, work is lost silently | a substitute → a file on disk |
| `document.cookie` | throws `SecurityError` | an in-memory jar |
| `IndexedDB` | throws `SecurityError` | a polite refusal via an event |

**The silent door is dangerous with data, the throwing ones bring down the whole app.** Excalidraw crashed
on the very first line that read a cookie: a white screen, with the cause in a console that doesn't exist
in the OS window. All three need substitutes, but only where the native behavior throws: you must not
break something that works for the sake of a safety net.

**Four more errors from the same family:**

* an app may **intentionally not save in a background tab** — check only in the
  visible window, or you'll declare someone else's optimization a defect;
* **a service worker claims the entire port**; renaming files isn't enough — the registration lives
  separately in the browser, a new port is more reliable;
* **your own stub must flag its own refusal**, otherwise the window will declare a working app
  crashed on its own polite refusal;
* **metadata sent with a version lands on the version.** The CARD's name, description, and tags live
  on the listing and are changed separately — `POST /api/edit-listing/{id}`. This is a correction to H23.

**The method that worked after five blind rounds: make the window name the cause itself**
— "the browser didn't let it in" / "the app is silent" / "the app crashed: name, message,
file:line, stack." **Build diagnostics as the first step, not the seventh.**

### H32. MICROPHONE AND CAMERA ARE UNAVAILABLE IN THE OS WINDOW. And it's the same hole as with storage

**A colleague's finding on 20 Aug 2026, confirmed by reading the OS's live code.** Verified on two
independent products: the tender system and HR Desk. In both, the page does the recording, while the
device-side part only decrypts the finished file.

The OS window creates a frame with this set:

```
sandbox="allow-scripts allow-forms allow-popups allow-modals allow-downloads"
```

What's missing: `allow-same-origin`, the `allow=` attribute entirely, `allow-popups-to-escape-sandbox`.
Consequences: `getUserMedia` is rejected; a workaround through a separate window doesn't work, because
the popup window inherits the same sandbox.

**What the sandbox does NOT cut off — downloads.** `allow-downloads` is in the set, verified by
reading the live code on 21 Aug 2026. A counter-finding from another chat explained a blocked
download by the absence of this permission — that explanation is wrong, and following it would have fixed
the wrong thing. The real cause is different: the message `Blocked host (internal address)` is printed
not by the shell but by the proxy, which cuts off internal addresses; there is no such string in the shell's
code at all. The working workaround is the same one that chat found: the device drops a copy of the file
straight into the person's downloads, and the download button is hidden in page mode.

**The cause is stated directly in the code**, and it's a sound one: seller pages are served from the
OS's own domain, so without the sandbox such a page would reach `window.top`, the storage,
and the user's token.

**Hence the main point for the conversation with the platform: this is the SAME hole as with storage (H24).**
Both grow from the same thing — the page lives on someone else's origin. So there aren't two separate asks:

| what to ask for | what it closes |
|---|---|
| **its own origin per listing** (a subdomain) | storage, cookies, IndexedDB, AND device permissions all at once |
| `allow="microphone; camera"` on the frame | devices only, and only if the origin stops being empty |

The second may not work on its own: a frame without `allow-same-origin` has an empty
origin, and the browser has nothing to attach the permission to. This is worth checking with a measurement
before proposing it as a ready-made solution.

**What the product should do until this is fixed.** Accept a ready-made recording file and **do not advise
going into system settings**: the sandbox responds with the same `NotAllowedError` as a person who
clicked "Deny." The advice "allow it in settings" sends the person to a place where everything is already
allowed. How to tell the difference — in the `extella-ui` skill, section 4b.


**Addendum from the console chat, 19 Aug 2026.** The refusal recurred when reading a receipt, meaning
this isn't a one-off oddity. A working parsing approach: strip ONLY the named wrappers, and
parse the Python dict safely — via an allowed subset, without executing code. After
parsing, a strict check of schema, namespace, state, and fingerprint is mandatory:
parsed doesn't yet mean correct.
---

### H33. The desktop's origin holds the token: someone else's code sits right next to it

**Measured on the live OS frontend on 21 Aug 2026** — the file `desktop.bf512c0e78dc.js`, 165 KB.
Not a retelling of documentation: every statement below was verified by reading the code. To re-check:
`curl https://os.extella.ai/desktop`, take the name `desktop.<hash>.js` from the response,
download it from `/os-static/`, and read it.

**The root cause is stated right in the OS's own code.** Seller pages open in a sandboxed frame
WITHOUT `allow-same-origin`, and a comment explains why: the proxied page lives on
the OS's origin, and without the sandbox it would reach `window.top`, `localStorage`, and the
user's token (H24 and H32 cover the same thing).

The app in the window is evicted from the token. **Three other surfaces are not.** They execute
code right in the desktop's own origin, where the token lives.

**1. Custom actions — right-click menu items.** The script runs as
`new Function('app','os', code)` directly in the desktop's context. Browser globals are available,
so `localStorage` and the token are available. Nearby there's a "Load from file…" import: someone else's
script arrives as a file.

**2. Store extensions — the seller's code in the buyer's browser.** When installing an app, the
`/api/purchase` response can bring along a `store_extensions` field: the seller's JS, which
runs on the user's pages. Entries are flagged `fromStore` and `locked` — on screen there's a
lock icon and the word Store, and it cannot be edited. Updates are pulled by polling
`/api/my-extensions` once every 12 seconds while the built-in browser window is open.

**3. Custom headers with substitution.** The OS proxy replaces `{{token}}` with the full account
token, `{{email}}` with the email. The app gets the right to call the entire Extella REST
on the person's behalf. There's one barrier: a consent dialog before the first run.

**Two caveats to the third point, both from the code.** Consent is asked once and
remembered (`tokenGrants` in state); it does not come up again. And only the presence of
`{{token}}` or `{{email}}` is checked: the third substitution, `{{agent_id}}`,
does not raise the dialog at all.

**Rule.** Someone else's action script, someone else's extension from the store, someone else's header with
`{{token}}` are not installed without reading the code. Your own — fine; someone else's — never. This means
running someone else's code in your own cabinet right next to the token, which is more dangerous than any app
from the store: the sandbox holds an app back, these three surfaces do not.

A map of the desktop's remaining capabilities is in `OS_CAPABILITIES.md`; the same three
surfaces are described there from the benefit side, with a link back here.

---
### H48. DIRECT URL TILE IS FRAGILE: HTTP/1.1 and app-page instead of it

**Measurement from the "Documents" chat, 21 Aug 2026.** Two errors with one root cause: a
shortcut pointing to a direct local address instead of the listing card looks broken while
the app is running.

1. **The OS window requires HTTP/1.1 with keep-alive.** A local server on HTTP/1.0 without
   keep-alive sometimes hands the OS window "The site didn't render" while the server is
   alive — the requests are in the log, but there is no render. It did not reproduce after
   switching the server to HTTP/1.1. Rule: the product's local server speaks HTTP/1.1. This
   is the same class already recorded for `X-Frame-Options` and `Cross-Origin-*` — the
   window downloads the document and silently refuses to draw it.

2. **The favicon of a direct shortcut is cached forever.** The desktop takes the direct
   URL's icon once and holds it in the Electron cache: the server is already serving
   `favicon.png`, but the tile stays a globe even after the state refreshes. It looks like
   "the cache didn't refresh," even though the server is serving the icon.

**The fix for both is canonical and single:** not a direct URL tile, but the listing card
and the page at `/app-page/{lid}/` — the storefront supplies the icon, and the window is
rendered through the verified proxy. A direct local address on the desktop is for debugging
only, not for the product. This confirms what has already been said about shortcuts: a
direct address is fragile, the canon runs through app-page.

---

### H49. INSTALLING THE BRIDGE AT THE CLIENT: source form and access from the keychain

**Log of the "Building on Extella" chat, 21 Aug 2026. Two errors of the same class in a
row — "works for the author."**

1. **A private source repository installs only for the author.** The bridge install
   failed with the refusal "Codex could not add the verified Extella source," with no
   reason given. It worked for the author because access to the private repository sat in
   the macOS keychain — the author himself doesn't see this. Fix: distribute from a PUBLIC
   repository.
2. **The `github` source form clones over SSH even for a public repository:**
   `Failed to clone repository: git@github.com: Permission denied (publickey)`. Publishing
   the repository only fixes the previous step — a second error of the same class surfaces
   at `plugin install`. Fix: the form
   `{"source":"url","url":"https://…git","ref":"vX.Y.Z"}` — HTTPS, tag pinning is
   preserved.

**Correction to the earlier rule about SSH.** `claude plugin marketplace add` now switches
to HTTPS itself and says so (`SSH not configured, cloning via HTTPS`). But it's the Claude
Code client that got fixed, **not the platform**, and only the first step: `plugin install`
still goes to SSH if the source is declared with the `github` form. Exactly the first half
of the rule is lifted; the second half stands — declare the source with the `url` form.

The class is shared with installing the Recruiter at the buyer's: everything is installed
and working for the author, silently not for the client. Verify on a clean machine, not on
your own (test stand, `tools/bench/`).

### H50. A REASONING MODEL SILENTLY RETURNS EMPTINESS AT A SHORT TOKEN CEILING

**Log of the "Building on Extella" chat, 20 Aug 2026.** A reasoning model, under a short
token ceiling, returns an **empty `content`**; `finish_reason` is populated, there is no
error code. A silent wrong result: the interface receives emptiness as a valid answer.

Fix: for streaming work, take a non-reasoning model, and in the refusal name the
`finish_reason` instead of returning emptiness. Measurement of the same task: 1.6 s versus
47 s.

This is the same class as "no data is a legitimate answer": an empty answer must be named,
or the product will lie with its result. Related to the measurement of LLM-judgment
reproducibility.

---

### H45. STOREFRONT CHECK: verify the artifact through the buyer's eyes, not the author's

**Log of the "1C Agent" chat, 20–21 Aug 2026. A clean-install test stand confirmed this
class live: version 1.11.1 did not install for a single buyer, caught before the first
one.**

Root cause. A listing version's snapshot **freezes the archive** on `add-version`, but the
buyer gets experts from the LIVE source agent. Any refresh of the source after the version
is created makes the pair drift apart: a clean buyer gets an honest refusal
`release_mismatch: the archive carries release X, but the installer is flashed with Y`. On
team machines this is invisible — local release directories cover up any mismatch.

Two rules follow from this:

1. **Rollout in one pass:** flash → source → archive → version. Don't refresh the source
   before the next re-release.
2. **The storefront check is an accepted practice in the canon.** After rollout, verify the
   artifact the way the BUYER sees it: download the archive FROM THE STOREFRONT by the same
   path the installer uses to download it (`/api/app-archive`), pull the release
   fingerprint and check it against the expert's flash read from the LIVE source via
   `expert/get`. Checking your own build on your own machine does NOT count — the author's
   environment masks exactly the class that kills a clean install. The check is built into
   the version-creation script (`os_app/add_os_version.py::storefront_consistency_check`)
   and won't let rollout close on a mismatch.

This is the same principle as the `tools/bench/` test stand: proof is not "green for the
author," but "works for the buyer on a clean machine."

### H46. INSTALLER ON POSIX ≠ WINDOWS: layout and teardown permissions

**Log of the "1C Agent" chat, 21 Aug 2026. Permission patterns copied from Windows examples
break silently on Mac/Linux.**

1. **`os.chmod(path, stat.S_IWRITE)` on POSIX is `0200` — "write without read."** On
   reading and traversing the directory this is `Permission denied` on its own folder:
   `rmtree` cannot even list the contents, and an interrupted reinstall leaves behind an
   unreadable wreck. Correct: `0o700` for directories, `0o600` for files, and `unlock_tree`
   before teardown.
2. **Sealing to read-only is mandatory on POSIX too.** An installer that lays out a release
   without clearing the write bits fails the integrity guard ("directory is mutable") even
   with an intact layout. Invisible on Windows — the guard skips `nt`. Correct: `seal_tree`
   (files `0444`, directories `0555`) after layout AND in the "already installed" branch —
   old intact layouts get sealed by a reinstall without re-downloading.

**Correction to the earlier rule.** "`chmod u+rwX` the release directory before packing" —
obsolete within a day and dangerous (see point 1). Correct: copy the release to a temp
folder and pack the copy, don't touch the live directory.

### H47. CHECK THE SNAPSHOT'S EXPERT COUNT BEFORE ROLLOUT

**Log of the "1C Agent" chat, 20 Aug 2026.** An extraneous expert (the claude.ai bridge)
self-registered into the local scope of the storefront's source agent — and would have
shipped to every buyer in the version snapshot. The only visible trace was the counter in
`add-version`'s stream progress: `total: 7` instead of the expected 6.

This is a leak of internals to buyers, and it's quiet: nothing fails. Rule: before every
rollout, check the snapshot's expert count against the product's expected composition.
Delete the extra as a local copy (`/api/expert/remove`, `global:false` — the global one
stays intact) and re-create the version. Related to the silent duplication by the MCP
`save_expert`, which writes into someone else's scope.

---

### H34. The launch device and the listing form: three spots where the request body decides the wrong thing

**Findings from the chat building on Extella, 20–21 Aug 2026. The points about the device
were independently re-verified here; the ones about the icon and the listing form are
accepted with a correction, given below.**

**1. REST does not accept the `target` field at all.** A lone `target` responds with 422:

```
{"type":"extra_forbidden","loc":["body","target"],"msg":"Extra inputs are not permitted"}
```

Re-verified on 21 Aug 2026 against `POST /api/expert/run`. **Sending both fields at once
drops the request exactly the same way** — the same message, about `target`. So the old
habit of sending `target` and `targets` together for compatibility is now not a safety net
but a guaranteed refusal.

**What this overturns.** Previously a lone `target` was accepted silently and the work went
to the default device — a quiet handoff to someone else's machine. Now the field is
rejected explicitly. For REST there is one rule: only `targets: [device_id]`, as an array.
For the JS bridge (`etb_run_expert`), `target` is still needed — these are different
contracts, and they must not be confused.

**2. A sleeping listener responds with 500, not a meaningful refusal.** `targets: [device]`
against a sleeping device gives `500 Target … is unavailable`. Reads like "the device is
dead," though it's fixed by bringing the listener up. Tell it apart in advance:
`search_targets` shows `available: false` before the listener is up — check there, not by
the response code.

**3. A page-type product cannot be published attached to an agent.** Publishing with
`source_type=agent` and `attach_agent=1` sets the product up as an add-on to the agent,
with no window: there's an icon on the desktop, but the web app doesn't open. On top of
that, the platform creates a clone agent **for every install** — each one gets its own
identifier in the purchase list. A page-type product is published without `source_type`,
`attach_agent`, and `source_id`.

**4. The icon isn't saved on the first publish.** The `icon` file in the multipart request
is accepted, there's no error, but the icon doesn't end up on the listing. Deliver it as a
second step: `edit-listing/{lid}` with the `icon` file. This is the same class already
described for adding a version: only `edit-listing` changes the icon.

**7. A boolean field arrives as a number.** The listing list returns the publication flag
as `1`, not as a boolean truth. A check that compares directly against a boolean truth
treats the published listing as absent — and the next run either creates a duplicate or
continues a closed operation on a public product. Cast to a boolean type before comparing,
look up the listing regardless of its publicity, and on ambiguity refuse rather than
continue (measurement from the connectors chat, 19 Aug 2026).

**6. The expert's code lives in `expert_code`, and length is counted in characters.** Your
own reread, if it reads `code`, always gets an empty string and "passes" on an empty run —
the check goes blind without ever turning red. This was found independently twice: on 29
Jul 2026 by one chat and on 21 Aug 2026 by another, almost a month apart. The first time,
the finding stayed in a personal log and never made it into the shared canon, so the second
chat spent time on it again. Compare by content, not by length: length arrives in
characters, while Cyrillic takes two bytes, so a size comparison diverges exactly where the
text matches.

**Correction to the original finding.** It said that the icon field is absent from the
listing list entirely. The 21 Aug 2026 measurement says the opposite: both
`GET /api/listing/{lid}` and `/api/my-listings` carry `has_icon` and `icon_ext`. There's
something to check the result with, and it must be checked — by `has_icon`, not by the
card's appearance.

**5. A split package tears links between its own pages.** After one product is broken up
into several listings, internal links keep pointing at files that moved to a neighboring
app; the button opens a white screen with `{"detail":"No such asset"}`. Fixed in two
passes: first publish, to learn each listing's identifier, then rewrite the other links to
absolute `/app-page/{lid}/…` and a new version. Links turn up both in single quotes and in
nested folders — build the map from the actual file composition, not from the root.

---

### H35. A listing version is a SNAPSHOT: reinstalling silently rolls back an expert edit

**Finding from the Data Privacy product chat, 20 Aug 2026. Severity: blocking.**

A version in the store carries a snapshot of the agent's experts, taken at the moment of
publication. A live edit to an expert doesn't make it into the snapshot. Every reinstall
unpacks the snapshot on top of the live code and **brings back the old version**.

**How it looks.** The expert is edited, a reread confirms the new code, everything checks
out. After the reinstall the method is gone. There's no error at any step. Measurement: the
code shrank from 12673 to 8393 bytes — that is, the rollback is visible only by size, and
only if you specifically measure it.

**What to do.** After editing an expert, release a NEW version (`add-version-stream` with
`source_type=agent` and `source_id`): the snapshot will capture the current code. The
check: reinstall and confirm the edit holds. A listing that has another party's buyer
cannot be deleted: `DELETE` responds with 409, leaving only adding a version.

**Why this is more dangerous than an ordinary rollback.** The edit looks applied for
exactly as long as nobody reinstalls the product. For the author this might not happen for
weeks; for the buyer, on the very first update.

---

### H36. Product assets are served without a version in the address: people are left with the old one

**Measurement, 21 Aug 2026.** The icon (`/icons/{lid}`) and the page (`/app-page/{lid}/`)
live at permanent addresses, with no version and no content fingerprint.

**How it looks.** After an update, some people are left with the old icon and the old page
on the desktop. The server, meanwhile, serves the correct new bytes — verified by
downloading. The mismatch is entirely on the client side.

**Workaround.** Remove the icon and add it again; or reload with cache clearing. It
resolves on its own once the cache lifetime expires. The real fix is up to the platform: a
version or a fingerprint in the resource address.

**Related, from our own measurement on 20 Aug 2026.** A heavy icon gets stuck in the
desktop cache more reliably than a light one. Keeping the icon small — 256 points, tens of
kilobytes — is cheaper than explaining cache-clearing to people.

---

### H37. An expert that will run for anyone calls nothing external

**Practice from the Data Privacy product chat, proposed for the shared canon on 21 Aug
2026.** Three rules with one root cause: anything the expert expects from outside may be
absent at the client's — and the absence will be silent.

**1. Don't import the engine from files sitting at the author's.** The code is embedded in
the expert itself. An import from a neighboring directory works on the author's machine and
nowhere else.

**2. Don't rely on installing packages at runtime.** Installing a package from the network
doesn't go through in the listener's sandbox, and the install path never even executes for
the author — the package is already there, so the refusal doesn't reproduce. Parse formats
with the language's own means: office-suite documents are an archive with markup inside, no
separate library is needed to read them.

**3. Create the key or state yourself.** Don't expect a key to already exist. Measurement:
the mapping table wasn't saved, because it was encrypted with a key the second person
didn't have. The masking ran fine, the reverse operation created a file, and the markers
stayed inside: zero replaced, not a word about the error. The product must create the key
itself, and always write the table — with no encryption library available, in plain text
with owner-only permissions.

**The check for this practice is the only one that proves anything.** Run the expert on a
clean machine that has none of the product's source and not a single package installed. It
works — it's ready for the client. This catches the whole "works for the author" class
before someone on the other side catches it.

**A related trap from the same measurement.** Markup parsing: some writer libraries encode
Cyrillic as numeric references like `&#1048;`, and the standard reverse-conversion function
doesn't expand them. The engine saw references instead of a word and **failed to mask
personal data, without reporting it**. A custom parser for numeric references is needed, in
both forms, decimal and hexadecimal.

---

### H38. A gate at the surface's exit: reread the artifact, don't trust the transformation

**Practice from the Data Privacy product chat, accepted into the canon on 21 Aug 2026.** A
companion to H37 along a different axis: H37 is responsible for the expert **running** for
anyone; this section is responsible for what it produces being **safe** for anyone. Both
are needed, one doesn't replace the other.

**The principle in one line.** At the boundary of every surface stands a machine check that
re-derives the fact from the finished artifact using the same detectors — and doesn't trust
the transformation's own report of success. This is the earlier rule "success is not the
same as fact," raised from the level of a request to the level of a file.

**Where it stands.** At the pipeline's exit, the moment the artifact crosses the boundary.
One scanner per CLASS of surface, not one general scanner for everything.

**The client surface — a personal-data scanner.** It runs the same detectors as
de-identification, but as a separate pass over the finished file, not over the string the
transformation returned. The **repacked** document is scanned: the archive is unpacked, and
every text node is walked — body, headers/footers, the string table, comments. This is
exactly what catches the case of "replaced in the body, but left in the footer." The tool's
own markers are skipped; any match of a supported type in a checked area is flagged as
residual risk.

**The demo surface — a real-values scanner.** The list of forbidden values is taken from
the source dataset the demo was generated from: values, names, identifiers. The synthetic
build is scanned. Even one match means a refusal: a demo must be at zero real data.

**An honest wording is part of the mechanism, not decoration.** The gate never says there
are no leaks. It says: no residual matches were found for the supported types and checked
areas — and it prints the coverage matrix. What wasn't scanned — images, documents from
snapshots, macros, nodes not walked — is flagged explicitly, not swallowed into a general
"passed."

**Refusal policy.** Client surface: a residual greater than zero — the artifact is flagged
as risk, no clean label is issued. Demo surface: one real value — a hard ban on publishing.

**The condition without which this practice doesn't work.** The check must be a SEPARATE
pass over the artifact, not the same code path that did the de-identification. Otherwise
the bug hides in both at once, and the gate confirms itself.

**Addition to the mechanism, from our own measurement on 21 Aug 2026.** A separate pass
isn't enough: the scanner must prove it can find things. Before trusting a zero, a
deliberately bad value is planted into what's being checked, and the check must name it.
Measurement: a secrets search across 72 history entries came back zero, because a shell
variable with Cyrillic in its name silently fell apart and the search pattern went out
empty. The planted value exposed this in a second. Before that there was the same class:
the "icon updated" check compared the value against itself and always passed.

A zero produced by a check that has never once shown red is not proof of cleanliness — it's
the absence of a check. Compliance with this part is guarded by `tools/check_output_gate.py`.

---

### H38-P. Addendum: what to reread after writing to the platform

**Sent in by the connectors chat on 21 Aug 2026 as a ready-made set.** H38 says WHAT to
do — reread the artifact instead of trusting the report. This addendum says EXACTLY WHAT to
check after writing to the platform, so that the call to "verify the meaning" stops being
just a call.

**Order of steps.**

```
read before write → write → transport confirmation → independent reread
→ semantic invariants → artifact fingerprints → live-path check → next step
```

If even one point doesn't match, the operation counts as unfinished, even if the platform
responded with success.

**Transport and addressee**

1. Transport success doesn't count as a result. A 2xx code, a stream-completion event, and
   a success field only mean the request was accepted. An independent reread is mandatory
   after them.
2. It is exactly the target object that gets reread: the identifier exists, belongs to the
   current owner, and matches what was meant to be changed. The identifier is not printed
   to diagnostic output.
3. No duplicates: after creation, exactly one listing is found under the canonical name. A
   repeat rollout reuses it instead of creating a second one.

**Edit layer and publicity**

4. The layer matches the intent. Card level — name, description, tags, icon, publicity.
   Version level — number, price, rights, page, archive, source snapshot, installer.
   Editing the card doesn't change versions, editing a version doesn't count as updating the
   card.
5. Publicity is cast to its meaning: true, one, and equivalent forms all mean public. A
   direct comparison against a boolean truth is forbidden.
6. Publicity hasn't changed as a side effect: after editing the card or a version, the
   state equals what it was before the operation, unless a separate publish command was
   issued.
7. H20 is checked BEFORE adding a version: for a public listing, a new version becomes
   public immediately, so the step is blocked until the owner gives separate approval.

**Version composition**

8. Exactly one version exists: one record with the expected number, belonging to the right
   listing, with a new version identifier.
9. The source snapshot is attached: the reread version names the chosen source, the
   correct type, and the attachment turned on. An empty source is forbidden for a product
   with an expert.
10. Experts are checked by composition, not by count. All the required names are present;
    wherever the interface allows it, each one's code is reread and compared against the
    source. A single counter is not enough. Measurement, 19 Aug 2026: the counter showed
    four with three unique names — the fourth record was the installer's representation. A
    check for "exactly three" turned red on a sound product, so the store's record count
    and the count of unique names are checked separately.
11. The installer is both named AND actually ran: the installer field equals the expected
    name, and then the consequence on the device is checked. A single launch flag is not
    enough.
12. Rights match exactly: the requested ones equal the declared ones. Not "at least" — an
    extra right is also a failure. After granting, the granted rights are separately
    verified.

**Artifacts by fingerprint**

13. The page is read through the store: the address responds with code 200, the token
    substitution is done, there's no account token in the response, and the launch marker
    and expected version are in place.
14. The archive is actually downloaded. Having the extension in the description is not
    enough: the archive is fetched by the same path the installer will use, and its
    fingerprint matches the local candidate.
15. The installed files match the archive: the full canonical list, each file's
    fingerprint, and the absence of extra state files and secrets.
16. File permissions are respected: executables with the expected mode, owner binding, and
    local secret files — owner-only.

**State and purchase**

17. The reinstall didn't touch the state: connections, grants, the log, provider settings,
    and owner binding are compared before and after. The executable part gets replaced;
    user state doesn't go into the archive and isn't overwritten.
18. The purchase is pinned to the right version, not just present.
19. The icon points to a stable listing address: after a new version it stays linked to the
    listing, opens the current purchased version, and doesn't contain a temporary address
    tied to a version.

**Live path and refusal**

20. The real working path is checked: after installation, a page call, a state snapshot,
    and one safe read-only request are performed — through the store page, execution on
    behalf of the app, the expert in its own scope, and the device runtime.
21. The response is parsed by its domain shape: the wrapper is only stripped on a provable
    transport signal. The presence of a `result` field is not such a signal (see H40).
22. Immutable fields really haven't changed: after a targeted edit, the publication state,
    version list, price, rights, source snapshot, and purchase bindings are compared
    against the pre-write snapshot.
23. The refusal is visible to the person: if an invariant doesn't match, the next
    irreversible step doesn't run, the interface gets a named refusal, and the pending flag
    is cleared regardless of outcome.
24. The rollback is verifiable, not just described in words: a snapshot or the prior
    artifact is saved before the write, and the same set of rereads is run after the
    rollback.

**The fact chain for a hybrid delivery.** Sent by the same chat on 21 Aug 2026: after any
external action, it's not the service's response that's checked, but the whole chain —

```
exact listing identifier → version → purchase → product agent
→ pinned device → archive in place → first expert call
→ visible result in the interface
```

By measurement, this chain caught three different refusals at once: duplicate listings, a
completed purchase with no install, and work happening in someone else's scope. Its value
is that none of the three is visible at its own step — each is only detected by the next
link.

---

**The danger cuts both ways — measurement from the console chat, 19 Aug 2026.** The object
update actually got written, but returned an unexpected wrapper. The client judged the
response unsuccessful and didn't trigger a rollback, because it marked the start of the
write too late. The result was a silent partial success: the object was changed, but the
system thinks it wasn't.

Two corrections to the order follow from this. The "write started" flag is set BEFORE the
request, not after the response: otherwise there's no way to know whether an attempt was
made. And before the change, a receipt is saved listing the affected objects — the rollback
touches only those, and is likewise confirmed by a reread. On uncertainty, the retry starts
with reading the state, not with writing again.

---

### H42. Deletion responds with success and doesn't delete

**Measurement from the bridges chat, 16 Aug 2026.** Deleting a rule returns a success code
and the body `{"status":"success","deleted":false}` — the rule stays in place. Over MCP the
same call returns `false`. The desktop wrapper, on top of that, swallowed the refusal and
sent the page a success flag.

**What to do.** Delete from the creator's scope. Treat `deleted:false` as an error, not as
information: the word about success refers to the request, not to the consequence. Reread
the list after any edit. The wrapper is forbidden to report success to the page until the
object's absence is confirmed by a reread (this is a special case of H38-P, point 1).

---

### H43. A shared expert: `global` grants visibility, but does not carry execution

**Measurement from the bridges chat; re-verified here on 21 Aug 2026 — and the result
diverged.**

Original finding: `save_expert` with the shared-access flag doesn't guarantee execution
from every scope. Search and read find the expert from different scopes, but launch only
works from the one that saved the record last; saving again moves availability to the new
scope. The launch device and the access code have no effect on this.

**The re-measurement gives a different result.** An expert saved once with the
shared-access flag launched from three different scopes in a row, and all three responded
with success. So the refusal doesn't always reproduce, but on a NAME COLLISION: when the
same name is saved from several scopes, the one that saved last wins. A single copy of a
single name works from everywhere.

**What to do.** Don't rely on the shared flag as a way to distribute execution, and watch
for name uniqueness across the account. The measured workaround for a name collision is a
separate copy in each calling scope with a character-by-character check; it wasn't rolled
out into the product because of the risk of copies drifting apart.

**Why it diverged matters more than the finding itself.** The two measurements contradict
each other, and the rule is recorded not as "works" or "doesn't work," but with a named
condition. An unconditional rule here would be harmful in both directions: one would force
copies to be bred where they're not needed, the other would leave the product with a broken
launch.

---

### H44. An expert's name in an agent's rights doesn't make it a model function

**Measurement from the bridges chat.** The rights interface saves and returns experts'
names, but they're not in the model's function list: only the names of platform tools
materialize. An install step that checked for the name's presence in the rights was giving
a false green.

**What to do.** Remove the false check, call the expert directly. Bring back distribution
through the agent's rights only once an adapter from expert to function exists and has been
measured. This is an adjacent facet of H31: there the platform accepts tool names that
aren't in the runtime; here, expert names that never become functions at all.

---

### H39. A thin page in an OS window: its own transport, its own forms, its own windows

**Findings from the connectors chat, 17–18 Aug 2026.** Three traps with one root cause: a
page in an OS window lives inside someone else's shell, and familiar web-page tricks break
exactly that shell.

**1. A native form submit replaces the whole window with the service's response.** A
button inside a `form` sends the window off via navigation, and browser navigation doesn't
carry the access header. Instead of the interface, the person sees a raw response like
`X-Extella-Token header required` — the interface is gone, with nowhere to go back to.
Fixed by not using forms on such a page at all: a container instead of `form`,
`type="button"` for the button, and a click handler. The shell, on top of that, intercepts
the submit at the capture stage, before the panel's handlers.

**2. Overriding `fetch` intercepts the shell's own transport.** The panel installs its own
wrapper over `fetch`, and the shell's very first call to the platform falls into this
wrapper — the result is recursion, the app doesn't open and complains about connectivity.
Fixed by saving the real transport BEFORE installing the wrapper
(`const osFetch = window.fetch.bind(window)`), routing platform calls only through it,
while the wrapper serves only the panel's own requests.

**3. The authorization window must be created synchronously from the click.** Otherwise the
browser won't open it, and the connection stays stuck in a waiting state forever: the card
hangs, the person doesn't know whether anything is happening, and clicks again. Besides
opening it synchronously, a visible "waiting" record is needed right after the click, the
words "finish signing in," and a separate status-check button. A hidden endless poll
instead of this is the same silent refusal.

---

### H40. An expert's response has a ceiling around 200 KB, and it isn't named as an error

**Measurement from the connectors chat, 18 Aug 2026.** Small responses go through fine, a
full directory snapshot returns 200 with no usable result, and parsing then fails on the
page side. The threshold, in practice, is about 200 kilobytes.

**Workaround.** A response above the threshold gets compressed, encoded, and flagged with a
separate field; the shell recognizes the flag and decompresses it with the browser's own
means, inside the general wrapper-parsing loop. If an old window lacks this capability, it
must give the person the words "update Extella," not a blank screen.

**The same class on a different layer, measurement 18 Aug 2026 (the embedded-product
chat).** A large database's schema didn't fit the old limit for a field description, and a
sound read came back with code 500. To a person this looked like "the source isn't
responding," though the issue was size. The limits were raised to 64 kilobytes for a
composite description and 256 kilobytes for the whole envelope, and now exceeding them
responds with a precise code, not raw exception text and not a false five-hundred. General
rule: a size limit must name itself, or it gets mistaken for the source being broken.

**Related, from the same measurement.** A live call confirmed several nested wrappers, some
of them strings with markup inside. The platform makes no promise about their exact number,
so the rule is phrased as a safeguard, not as a measurement: **parse with a bound, at least
to depth ten**. Ten is the limit of the protective loop, not a measured count; this must not
be confused, or the next reader will conclude the platform guarantees ten.

The transport parser must be kept separate from parsing the domain response: a domain
object can also have a `result` field, and a shared loop will eat the data together with
the wrapper. Strip the wrapper only on a provable transport signal; the mere presence of a
`result` field is not such a signal. The fix was made right here too: parsing on the guide
page was raised from four levels to ten and stops as soon as it sees a domain response.
Verified against seven wrappers and against a domain object with its own `result` field.

---
### H41. A key and its scope: two silent ways to lose a secret

**Findings from the connectors chat, 19 Aug 2026.**

**1. Default-agent substitution writes the key into someone else's scope.** When the
binding to the agent isn't set explicitly, the code substitutes a pre-configured agent,
and the write goes into someone else's scope. The key exists, but the product in its own
scope gets a refusal "key not found" — this looks like lost connections or a platform
defect. Binding must be mandatory: either from the environment, or from a verified local
binding. Scope unknown — the product refuses in words and writes nothing.

**2. A piece of the secret in a record's description comes back through search.** The
interface may show nothing, while search over the store returns the record together with
the value. The description must carry only the record's permanent purpose — no key, no
start or end of the value, no fingerprint. This is locked in by a check that forbids even
the first eight characters of the value in the description.

**Adjacent, from the same source.** An extra layer of encryption on top of the platform's
store turned out to be an unnecessary assumption: the store itself keeps the value
encrypted, and a homegrown key file added a new failure mode — once it's lost, the value
can no longer be decrypted. The homegrown layer can only be removed after checking the
boundary: the model must not have read or search access to the store, and the plaintext
value must reach only the device.

---

### H54. `app-agent/run` IS SYNCHRONOUS: the expert returns terminal state as a value, not as a task

**Debrief with a colleague's chat, 22 Aug 2026.** `app-agent/run` is sugar over
`expert.run`, and it **waits for the expert's return synchronously**, then relays its
value to the page. Measurements: without pinning it returned the device and its data in
17.3 s; a nonexistent expert returned a terminal error "Expert not found" in 3656 ms.
There's no separate "wait" flag — waiting is already built in.

**This is the root of a common mistake.** If the page gets NON_TERMINAL, it isn't the
platform returning early — it's the **device expert returning a non-terminal**: it
created an internal task and handed back a handle, instead of blocking and returning a
ready result. `app-agent/run` honestly relays whatever the expert returned.

Rule: **the expert on the device returns a terminal result AS A FUNCTION VALUE** — it
does the work inline and returns the finished result. No internal task + waiter: the
platform's own wait inside `app-agent/run` serves as the waiting. Then a single scoped
`app_token` call gives a terminal result without browser polling, without a `task_id` in
the browser, without `api.full`, and without a second expert run.

Exact form:
```
POST /api/app-agent/run     header X-App-Token: {{app_token}}     scope expert.run
body:     {"app_token": "<short-lived key>", "expert_name": "<expert>",
           "params": {...}, "targets": ["<device_id>"]}  # targets requires device.run
response: the expert's returned value, unwrapped from the transport envelope; the call blocks
```
The base is `POST /api/app-agent/call {op:"expert.run", payload:{...}}`. The `global`
field is not allowed in the scoped channel. `targets` is kept only when `device.run` is
granted separately; without it the gateway strips the pinning, and the expert goes to the
container. The order of device determination and pinning is set by H106.

**The one boundary.** `app-agent/run` has a timeout: work longer than that won't manage
to return a terminal result, and the page will get a non-terminal again. This is already
a platform gap — a scoped task-check by `app_token` (passed on to the platform team). But
more often the expert returns early and fast — that's an async expert, fixed by a
synchronous return, not by waiting on the platform.

---

### H51. The purchase completed, but nothing landed on the device

**Measurements from the hybrid-product chat, 12 Aug 2026 and again 17 Aug 2026.**

The purchase responds with completion, the page opens — but the product's local part
isn't on the machine: no data, no key bundle, no state file. Outwardly this looks like an
empty or broken product, and people start debugging the interface instead of the install.

**What to do.** Don't treat purchase completion as the fact of installation. After it,
check that the archive arrived and unpacked, and distinguish two refusals in words:
there's no archive, and there is an archive but installation failed. Both refusals need a
visible next step — reinstalling from the desktop.

**The second half of the same failure: there's nothing to pin the device to.** The shell
sometimes doesn't pass the agent identifier to the installer, and the binding doesn't get
created. Before an explicit message was added, this looked like "it installed, but the
app doesn't see its own files." The installer must refuse BEFORE writing state if the
identifier wasn't passed, and after installation re-read the device binding. A half-done
state is worse than an honest refusal: afterward there's nothing to tell it apart from a
working one.

**Related, from the same source.** Substituting the account's shared agent for the
product agent was removed entirely, not patched: the product agent is read only from the
local binding, there's no fallback path. A fallback path here isn't a safety net — it's a
way to quietly do the work in someone else's scope (see H41).

---

### H52. A shortcut leads only to the direct address of the product page

**Measurement from the same chat, 16 Aug 2026.** A page opened through an arbitrary web
app or through a proxy doesn't get a shell session: instead of the interface, the person
sees the service's response demanding a header.

**The shortcut canon.** Only the direct address of the form
`/app-page/{listing identifier}/`, with a trailing slash. Don't create a second shortcut
by hand. Don't add token substitution or custom headers to such a shortcut — they belong
to external web apps, and here they produce exactly the refusal they're meant to cure
(see H33).

---

### H53. Publishing created a second listing instead of a new version

**Measurement from the same chat, 14 Aug 2026.** Rollout via publication created a NEW
listing, not a version of the existing product. Duplicates appeared on the desktop and in
the store, and it became impossible to say which icon opens which version.

**What to do.** For the canonical listing, use only version addition. Check the exact
listing identifier before the write and after it. Show the version in the product's own
interface: without it a person can't tell a duplicate from a working install, and support
can't tell from a screenshot.

---

### H55. Immutable release: the expert keeps running on the old code

**Measurement from the embedded-product chat, 13 Aug 2026.** After the rebuild, the
expert kept referencing the previous immutable release. Old releases are deliberately not
deleted, so nothing failed: the live call executed successfully — on the old code.
Externally this came out strange: the page got "method unavailable," even though the
method was already sitting in the repository.

**Why it's dangerous.** The refusal shows up somewhere other than the cause, and isn't
about it. People debug the page and the method, while the real issue is which release is
flashed into the expert.

**What to do.** The fact that "a new release is installed" isn't enough. Use a separate
check to make sure the exact release identifier is flashed INTO the expert itself, and
re-read the expert's body with a request rather than trusting the install report. This is
a special case of H38-P: an operation's success is not a fact.

---

### H56. A response in someone else's shape: one expert's envelope applied to another

**Measurement from the same chat, 18 Aug 2026.** The parser applied the neighboring
experts' common envelope to the intermediary's response and looked for a nested result
field. The panel decided the channel was inactive and offered a repair — even though
processing had responded about sixteen seconds earlier.

**What to do.** Each expert's response shape is its own and is parsed by its own
contract: the canonical response is read from the root, without expecting someone else's
wrapper. The contract is locked in by a structural check, not by an assumption based on a
neighbor.

A neighboring facet, H40: there the wrapper was stripped too greedily and domain data was
lost; here, a wrapper was sought where there was none, and a live channel was declared
dead. It's the same mistake — the response shape was taken from imagination, not from the
contract.

---

### H57. Channel health can't be measured by an operation that grows with the log

**Measurement from the same chat, 12 Aug 2026.** The channel watchdog crashed while
reading an oversized system log against an eight-second cutoff. The timer kept ticking,
but the service stayed in a failed state, and the dead heartbeat had to be revived by
hand. By that point the log had grown to 921 megabytes.

**Rule.** A liveness check must have a constant cost. An operation whose time grows with
the data doesn't fit this: it will itself become the cause of failure exactly when it's
needed most. Limit log reading to a number of lines and give it its own cutoff; limit log
growth on the server.

**And how to check the channel properly — a template from the same measurement.** Not by
the sign "the window is open" and not by a single heartbeat, but by an end-to-end probe
on the agent's behalf: first a fresh heartbeat and a free queue, then EXACTLY ONE probe
request, waiting for a response with the same request identifier, checking the state
transition from waiting to execution to completion — and an empty queue on exit. Save the
first raw response in full; parse it separately afterward.

---

### H58. An expired task is closed once — a late reply doesn't revive it

**Measurements from the same chat, 3–12 Aug 2026.** A late reply arrived after the task's
lease had expired and again took part in completing what was already closed. The queue
and the panel looked stuck, even though the original task had long since expired.

**What to do.** An expired task is closed by a single receipt with an explicit expiry
reason; a late reply doesn't replace it. Don't treat the absence of a heartbeat DURING a
synchronous call as the executor's death — a long read has its own time limit, separate
from the heartbeat.

**Related, from the same product.** A profile created through the shell wasn't getting a
device binding: the card promised pinning on the first check, while preparation kept
refusing — the profile was dead from the moment of creation. A promise to pin later is
acceptable only when the pinning actually happens; otherwise it's a half-done state with
nothing to tell it apart from a working one.

---

### H59. `global` on an expert: the flag is needed both on the record and IN THE READER'S REQUEST

**Resolving a contradiction, measurement 22 Aug 2026.** Three different products arrived
at three different conclusions about the same thing: one said a shared expert is visible
to everyone, another said it runs only from the scope that saved it last, a third said a
foreign agent doesn't find it at all and gets "expert not found." A direct measurement
explains all three.

| how it's read | result |
|---|---|
| `expert/get` **with** `global: true` in the body, from four different scopes | all four see it |
| `expert/get` **without** `global: true`, from a foreign scope | HTTP 500, "Expert not found" |
| same without the flag, from the owner scope | sees it |

**Conclusion.** The shared-access flag on the record is half the condition. The second
half: **the reader must itself ask for a shared search**. A client that doesn't know this
gets the refusal "the expert doesn't exist" — a wording that misleads: the expert exists,
the request is just missing the flag.

**What to do.** Check visibility not by the record's property, but by a live read **on
behalf of each agent that needs the expert**, with an explicit shared search. The
record's property is not proof of availability.

---

### H60. Editing the page with a new version multiplies versions and agents

**Measurement from the console chat, 14 Aug 2026.** Every page edit was released as a new
version, and the purchase update ran in create-new mode. **88 versions** of one product
piled up, along with **26 excess agent instances**; the account's fleet grew to 65 agents
with no product reason.

**What it looked like.** The purchase, the icon, and the open page ended up on different
snapshots. The owner edited the page and didn't see the fixes — because they were looking
at the wrong version.

**What to do.** Editing the page means changing the same version, not releasing a new
one. Updating the purchase — only in existing-install mode, with the exact current agent
identifier. Before and after, check the purchase's version, rights, icon, and version
count. After an authorized cleanup, the fleet shrank from 65 to 39.

---

### H61. Rate limit: parallelism doesn't get around it, it makes it worse

**Measurement from the same chat, 13–14 Aug 2026.** Reading the fleet made about 97
requests to the core for 48 agents. The limit is **120 requests per 60 seconds**.
Parallelism of eight didn't speed the work up and made the average time worse: the check
took about 26 seconds and ran into a rate-limit refusal, after which the retry started
over on agents already checked.

**What to do.** Keep parallelism below the limit with margin. After a rate-limit refusal,
don't launch a new batch. Save confirmed results and on retry continue only with the
unchecked ones. Show the person the stated wait time and a countdown, not silent waiting.
Read the initial opening as a short list; details on request.

**The general part.** A rate-limit refusal isn't a malfunction, it's a normal state: it
has a stated time after which it will pass. A refusal with a known time must show that
time, otherwise the person hits retry and extends the limit on themselves.

**Related, from the same source.** Revoked or ungranted rights give the same feeling of
an empty product: the interface loads fully, but every call answers with an access
refusal, and the list stays empty. An access refusal is framed as a recoverable state:
name the required right and action, and don't turn the last confirmed snapshot into
zeros.

---

### H31. AGENT RIGHTS: the platform accepts names that don't exist at runtime

**a designer's finding, 18 Aug 2026, confirmed by an independent measurement the same day.**

The platform has two generations of tool names. The new generation starts with a verb
(`search_concepts`, `list_rules`, `get_kv`), the old one with a noun (`concept_search`,
`rules_list`, `kv_get`). The live MCP server serves **only the new one**.

The platform accepts the old names silently: `agent/create` responds 201, `agent/get`
returns the list back in full, the checkboxes are checked in the interface. Such a tool
never comes up at runtime, and the agent only finds out at the moment it's called.

**Measurements.**

| what was measured | declared | available at runtime |
|---|---:|---:|
| designer's agent, freshly created | 12 | 4 |
| "Travel agent," live client one | 18 | 5 |
| two one-off agents, both name generations | 6 and 6 | launch unavailable, see below |

For "Travel agent," runtime showed `web_search`, `get_expert`, `run_expert`,
`check_task`, `get_default_target` — and not a single `kv_*`. The product declared its
own memory and didn't have it. It doesn't have blanket allowance, so no substitution
happened: thirteen rights simply weren't there.

One-off agents created via `agent/create` couldn't be run: the platform returns
`pro_key_required` for any run of an agent created via the API. That's a separate, known
refusal unrelated to the names.

**What to do.**

1. Declare rights using only new-generation names. The mapping of old to new names is in
   `tools/check_agent_tools.py`, which also names the ones with no replacement.
2. After flashing rights, **ask the runtime**, not `agent/get`: one run asking it to list
   the available tools. The rights list on the agent's card doesn't prove this.
3. The `check_agent_tools.py` check is now red on old-generation names. On the account as
   of 18 Aug 2026, 28 of 30 agents carried them. A census from the "Building on Extella"
   chat, 21 Aug 2026: of 69 agents, 51 can run experts, 32 can find and run them;
   `agent_extella_default` can't do it at all (confirmed by the gate).

**Addendum, 20–21 Aug 2026, from someone else's measurement.** Re-flashing rights via
`agent/update` does NOT fix the mismatch: the declared list is again accepted in full,
while runtime still has the same old four. The working workaround is not to fight for the
right, but to wrap the missing one in an expert: a knowledge search calls
`/api/concept/search` itself with the device token, and the agent calls it through the
available `run_expert`.

**And a consequence for the instruction text.** The agent executes a short tool name as
an expert name: an instruction to call `rules_list` turns into `run_expert("rules_list")`
and ends with the refusal "Expert not found." In the instructions, name tools by their
full runtime name (`rules_list_mcp_extella`) and state explicitly that it's a tool, not
an expert. Don't mention tools that don't exist at runtime at all — the agent will try
them.

**Why this is more dangerous than an ordinary typo.** A wrong name causes no error either
on write or on read. The agent's card looks correct, the passport checks out, the rights
gate passed. The failure shows up in the client's live work and looks like a broken
product, not a missing right.

---

### H24. A THIRD-PARTY APP IN THE OS WINDOW: five failures, and each one is silent

**Measurements, 15–16 Aug 2026.** Three ready-made web apps (excalidraw, drawio, pdf.js)
were put into the OS window in the OS, and a day was spent figuring out why "everything's
green" and nothing works. Five causes, and none of them produces an error in the logs.

**0. WHY this happens — read in the OS code on 16 Aug 2026, and it is NOT a browser
defect.** The shell opens the seller's page in a frame with `sandbox` WITHOUT
`allow-same-origin`. The OS's own comment explains the decision: the proxied page lives
on the OS's origin, and without the sandbox it would be able to reach `window.top`,
`localStorage`, and the user's token. The sandbox gives the frame an "opaque" origin:
scripts, forms, and windows work, but access to anything else's doesn't.

All five failures below follow from this. And it also follows that asking to "allow
storage" is pointless: that's a request to remove the seller's isolation from the user.
The right request is to **give the sandbox its OWN storage from the OS** (for example,
messaging with the shell, or KV scoped to the listing), while keeping the isolation.

**THREE DOORS, AND THEY BEHAVE DIFFERENTLY** (clarified by the Schemes Board chat,
16 Aug 2026):

| door | behavior | what to cover it with |
|---|---|---|
| `localStorage` / `sessionStorage` | stays silent, work is lost silently | substitute → file on disk |
| `document.cookie` | throws `SecurityError` | in-memory jar |
| `IndexedDB` | throws `SecurityError` | polite refusal via event |

**The silent door is dangerous for data, the throwing ones crash the whole app.**
Excalidraw crashed on the very first line reading a cookie: a white screen, with the
cause sitting in the console, which the OS window doesn't have. Hence the rule: all three
must be substituted, but only where the native one throws; you must not break something
working for the sake of a safety net.

**1. The OS window is a foreign page, and storage there is closed.** The product opens in
an iframe inside `os.extella.ai`; the app becomes a "third party," and the browser closes
off `localStorage` for it (`SecurityError`). App behavior differs, and the second is more
dangerous than the first:

* **drawio** shows its own English "Error loading page. Please try refreshing";

* **excalidraw** OPENS and silently loses drawings when the window is closed.

Hence the acceptance criterion: not "the page opened," but **"the work survived a window
reload."** Everything else is self-deception.

**2. The app's service worker takes over the whole port.** excalidraw and drawio install
an SW with scope `/`, and any address on that port serves their copy — our file next to
the app never gets through at all. As long as the SW is alive, edits to `index.html`
don't reach the browser. Fix: remove the SW file (`service-worker.js`, `sw.js`) — on a
404 the browser unregisters it itself.

**3. A script with Cyrillic before `<meta charset>` silently doesn't execute.** The
browser reads the Russian text as Latin characters, gets syntax garbage, and quietly
skips the block. Insert your own code only AFTER the charset declaration, and if there
isn't one, declare it yourself, inside a marked block (otherwise removal will leave the
declaration in someone else's file).

**4. The browser serves the old `index.html` from cache.** The edit is in the file, it's
in the `curl` response, but it's not in the window. The app's server must serve pages
with `Cache-Control: no-store` and declare `charset=utf-8` — `http.server` does neither.

**5. Not every app is fit for the window.** drawio refuses to work inside a foreign frame
EVEN when it's given storage — that's its own decision, not our breakage. Such an app
gets removed from the lineup; you can't sell as a product something that only opens as a
separate window. **"Open in a separate window" is a workaround, not a solution** (the
owner's word, 16 Aug 2026).

**What comes out of this that actually works.** The app's storage is moved to disk: our
own server serves a storage endpoint, and an injection into the page substitutes
`localStorage` with a write to a file. The work stops depending on the browser, it's
visible as a file, and an agent can read it. Ready-made pieces: `tools/cabinet_server.py`,
`templates/storage_shim.html`, `tools/inject_probe.py` (the edit is marked, removes
cleanly, with a `.до_пробы` copy alongside).

**Editing someone else's code — only this way:** marked, idempotent, removable down to
the byte, with a copy alongside. Verified by the tool's self-check, not by eye.

**Four more failures, each one cost an hour** (Schemes Board chat, 16 Aug 2026):

* **the app may DELIBERATELY not save in a background tab.** Test only in a visible
  window, otherwise you'll declare someone else's optimization a defect;
* **your own page interceptor (service worker) takes over the whole port** and serves the
  old copy. Renaming files isn't enough: the registration lives separately in the
  browser. The most reliable fix is **a new port**;
* **your own stub must mark its own refusal** (`__extella_ожидаемо`), otherwise the
  window will declare a working app crashed — over its own polite refusal;
* **meta sent with a version lands on the version.** The CARD's name, description, and
  tags live on the listing and are updated separately — `POST /api/edit-listing/{id}`
  (confirmed by reading the storefront). This is a correction to H23: the tag with the
  version is mandatory, but it doesn't change the card.

**The method that worked after five blind loops: make the window name the cause
itself** — "the browser wouldn't let it in" / "the app is silent" / "the app crashed:
name, message, file:line, stack." **Build diagnostics as the first step, not the
seventh.** This is worth more than every other rule on this page: without it you fix
things blindly, and every loop is "free" only in words.

### H27. WHERE A PAGE-TYPE PRODUCT STORES ITS WORK: with us, not in the browser

**The owner's word, 16 Aug 2026:** "shouldn't this be solved by our experts? Embed
experts, write the storage rules into them." Correct, and this removes half the question
to the platform: a page in the sandbox has no browser storage, but it has an `app_token`,
and therefore an expert and KV.

**Rule.** A page-type product does NOT store state in the browser. Everything that must
survive the window closing is written by our expert (as a file on the buyer's device) or
to KV. `localStorage` is unavailable in the sandbox, and relying on it means silently
losing the person's work.

**Cost, measured 16 Aug 2026** (core directly; through the OS gateway one more hop is
added):

| | |
|---|---|
| KV: write | 1.8–3.0 s |
| KV: read | ~1.4 s |
| KV: value size limit | about 50 KB; 52 KB of JSON returned **HTTP 500** three times with no explanation |
| expert on the device | 8–17 s |
| browser storage | milliseconds, but closed off in the sandbox |

**What follows from this by product type:**

* **rare and small saves** (a decision to the log, settings, a report) — KV or expert,
  and this is the right path: the work is visible to the agent and survives the browser;
* **editors and drawing tools** (tens to hundreds of KB, continuous saving) — KV doesn't
  fit, either by size or by cost. Here it's a file on the device through your own expert,
  with writes no more often than once every few seconds;
* **a third-party app that only knows `localStorage`** — substitute its storage with your
  own (`templates/storage_shim.html`), rather than relying on the browser.

**Why KV costs this much — found out on 16 Aug 2026.** On a 64 KB value, the refusal
finally named the cause: `Embedding error`. That is, **`kv/set` computes an embedding for
every value** — our KV isn't a "key-value" store, it's a vector store. Hence the
one-and-a-half to two seconds per operation, and the ceiling of about 50 KB: app state
can't be put there — not out of malice, but by design.

Measurement after the OS was sped up 74x (16 Aug 2026, evening): write 2.0–2.2 s, read
1.37–1.44 s — **unchanged**. The speedup affected the shell, not the KV core; the rules
above remain in force.

**What to ask the platform for:** a KV mode without embedding — a plain key-value for
state. The CTO is right now splitting KV into open (agent memory) and closed (input via
the OS interface); the direct question to him: does the open mode compute an embedding.

**A defect worth naming:** a value over the limit answers with `500`, not "too large." A
silent refusal on save is the worst kind of refusal.

### H26. PUBLISHING IS REVERSIBLE, DELETION IS NOT. A correction to what I repeated all day

**Checked on 16 Aug 2026 at the owner's prompting.** We treated `Publish` as a point of
no return and built the rule "the chat stops, the person presses the button" on that.
Half the rule turned out to be wrong.

| action | address | reversible |
|---|---|---|
| show in the store | `POST /api/listing/{id}/publish` `{"published": true}` | **yes** |
| remove from the storefront | same address, `{"published": false}` | **yes** |
| delete the listing | `DELETE /api/listing/{id}` | **NO**: tears down the listing and ALL versions |

There's no separate `unpublish` address — it's the same `publish` with a flag (read in
`store.js`: the "Unpublish" button calls `setPub(id, 0)`). You can check whether an
address exists without changing anything: `GET` on it answers `405` if the address
exists, and `404` if it doesn't.

**What changes in practice.** `Publish` remains a PUBLIC action and stays with the
owner — not because it's irreversible, but because everyone can see it. The cost of a
mistake dropped from "forever" to "minutes on the storefront"; fear of the button is no
longer justified. Tool: `tools/set_published.py <id> --показать|--убрать` — with
mandatory verification by reading back, because "success" without a re-read has already
cost us trust.

**What did NOT change.** H20 remains in force: for a published listing, every new version
goes to the store immediately. And deletion is still irreversible — its tool deliberately
doesn't do it.

### H23. THE STOREFRONT CARD: icon, description, tags — at rollout time, not "later"

**Census, 14 Aug 2026, across ten of our listings:**

    no icon        — 4 of 10
    no description — 3 of 10 ("1C Agent AI", "Telecom Demo", "Lawyer" — name only)
    name with version and boilerplate words — occurs

This isn't about looks. The icon is the only thing by which a person finds their window
among twelve identical ones. The description is the only thing by which they decide
whether to install it. Tags are the only thing the store will ever use to assemble
shelves. While there are five products, the mess is unnoticeable; at fifty it's
irreversible, because every card will have to be fixed retroactively and by hand.

**Rule.** A product isn't rolled out without an icon, a description of at least 80
characters, and two tags, one of which is the product type (`приложение`, `издание`,
`агент`, `демо`, `инструмент`; for a product with an English name, the English
equivalents `app`, `edition`, `agent`, `demo`, `tool`: the tag language follows the
name's language). Checked by `tools/check_listing_meta.py`, which is also wired into
the deployer before rollout: a red card stops the rollout the same way a red
passport does.

**The icon must be produced by a command, otherwise it won't exist.**
`tools/make_icon.py <sign> <path>` draws an icon from the Extella palette without a
single external package: 512×512, a geometric sign (a letter at 64 pixels is unreadable).
While the icon was "separate work in an editor," it never appeared, not once out of four.

**A tag is mandatory on EVERY version (measured 15 Aug 2026).** The platform started
answering `400 At least one tag is required` on `add-version-stream`, while the rollout
only sent tags when creating the listing — four products silently stopped updating. The
refusal got lost in the process: the stream wrapper explained it as "the platform didn't
send completion." **A response code != 200 is a response, not a dropped connection:**
print the reason verbatim.

**Where the meta actually lives, technically.** At the LISTING level: `name`,
`description`, `tags`, `has_icon`/`icon_ext`. The icon travels as a separate `icon` field
in the same multipart upload as `page` and `archive` (H10) — until 14 Aug 2026 the
rollout didn't send that field at all, hence the four gray squares.

**A desktop shortcut has NO meta.** Measurement: `POST /api/desktop/shortcut` with the
fields `icon`, `description`, `tags` answers 200, but reading it back returns only `name`
and `url` — the platform silently swallows the rest. Demanding meta from the shortcut is
pointless; the shortcut inherits its look from the listing.

**Careful with the desktop.** `POST /api/desktop-state` **overwrites the entire state**,
it doesn't append: an empty body zeroes out the desktop (checked the expensive way — 11
shortcuts, folders, and extensions disappeared and had to be restored from a backup taken
a minute earlier). Add a shortcut only through `POST /api/desktop/shortcut`. The OS has
no targeted shortcut deletion (`DELETE /api/desktop/shortcut/{id}` → 404) — remove it via
a full state write, and **only with a fresh backup**.

### H19-quinta. CLOSED 14 Aug 2026: both deleting our own junk and removing an extension

The platform fixed two things on the same day, and both remove limitations of ours:

**1. `allowed_origins` persists, the forwarding proxy works.** Measurement: the field is
written and read back, `ext/fetch` to an allowed address returned content **in 1.8
seconds**, an outside address still gets `403`. So the path "page → third-party API" is
open — and it's **seven times faster** than a call to the device (1.8 s versus 13–17 s).

**2. Your own listing can be deleted even if the author bought it themselves.** The
earlier refusal "1 buyer(s) purchased this app" referred to your own test purchase.
Measurement: **11 out of 11 junk listings were deleted**, zero refusals.

**This also closes the extension question**, which I had declared hopeless: an extension
is removed by **deleting its listing** — the record in the account's library goes away
along with the listing. After that, the record is removed from the desktop by editing the
state, and it **does not come back** (checked with 10- and 30-second pauses). The rule
from H19-bis remains true: a desktop edit holds only if the record isn't in the library.

### H19-bis. CORRECTION: there's nothing to remove an extension with, editing the desktop state doesn't help

On 13 Aug I wrote down: "an extension is removed by editing the desktop state, it stays
in the library." **The first half is wrong.** On 14 Aug the removed extension **came back
to the desktop on its own** — the OS rebuilds the list from the account's library.

How I got caught by this: I read the state **right after the write**, saw the extension
was gone, and considered the matter done. The state reconciled later — and brought
everything back.

> **Rule: "read right after the write" is not the same as "verified."** Where a foreign
> process reconciles the state, you must read it again, after some time has passed.

~~In practice: there's nothing to remove an installed extension with.~~ **Retracted on 14
Aug 2026** — see H19-quinta: it's removed by deleting the extension's listing. It's fine
to mark the edition topic "to try."

### H16. A device target is credentials, not an identifier

**Correction, 14 Aug 2026.** I claimed that a foreign device is out of reach. The owner
corrected me, and he's right: **if a person gives their own target, you can run your own
experts on their machine**; and with someone else's API token you can act on behalf of
their entire account.

Confirmation from our own history: colleagues' tasks once **executed on the owner's
machine** — panels weren't pinning the work to their own device, and someone else's
contract was being read on someone else's Mac.

Hence a rule that matters more than the argument:

> **A target ID is equated with a secret.** Giving out a target means giving the right to
> execute code on your machine. It doesn't go into logs, chats, repositories, or product
> cards — same as a token.

And a consequence for future exchange between users: the "Extella ↔ Extella" channel is
built exactly on this — and that is exactly why it requires explicit, revocable consent
from both sides, not "just send me your id."
### H15. Forward proxy: a page can call the core and third-party APIs (deployed 13 Aug 2026)

Checked against the live OS schema: `/api/ext/core/{path}` and `/api/ext/fetch` are **live**, and the publish
field `allowed_origins` **exists**. That clears two of our blockers at once.

The mechanics are the same throughout: the sandbox never goes straight to a third-party domain (opaque origin, CORS
blocks it), and the raw token is never handed to JS. So the request is made by the **OS proxy** on the server,
which returns a response with CORS that the sandbox accepts.

| Путь | Куда ведёт | Чем открывается |
|---|---|---|
| `/api/ext/core/{путь}` | `api.extella.ai` — **any** core method; the OS substitutes the real token on the server | the **`api.full`** permission |
| `/api/ext/fetch?url=…` | the developer's **own** API; their own authorization is passed through, no Extella token is added | origin in the version's `allowed_origins` — **broken as of 14 Aug 2026, see below** |

Authentication is the same `{{app_token}}` (as the `X-App-Token` header; for core, `X-Auth-Token`
is also accepted, so an app can get away with just swapping the base URL). Limit is **120 calls / 60 s**,
body ≤ 10 MB. Redirects are not followed — there's no way out past the allowed-origins list.

> ✅ **CORRECTION 19 Aug 2026: `allowed_origins` IS PERSISTED.** A probe on a one-off
> listing: the field went out with `publish-stream`, came back on read as
> `["https://example.com"]`, and `edit-version` did not lose it. The platform
> fixed this. The text below is the history of a refusal, not a current limitation. The
> `ext/fetch` call itself from a live app hasn't been checked yet: the field persists, but
> whether the request actually goes through still needs checking.
>
> ⚠️ **History (14 Aug 2026): `allowed_origins` silently wasn't being saved.**
> Probe on 14 Aug 2026, reproduced **three** ways on the live product: `edit-version`
> with a JSON array, `edit-version` as a string, and `add-version-stream` with an array. All three
> reply `success`, yet reading the version back shows `allowed_origins: ''` — even though
> `app_scopes` from the same request is saved. Consequence: every call returns
> `403 origin ... is not in this app's allowed-origins list`, and the "page → third-party API"
> path is closed entirely.
>
> Until it's fixed — integrations with external services are done by the device part.
> (Fixed 19 Aug 2026, see the correction above.)
> Worth noting separately: **the proxy's own refusals are honest** and name the fix
> ("grant Full Extella API access…", "origin … is not in the allowed-origins list") —
> this is a case where the platform doesn't stay silent, it explains.

**What this changes for us:**

1. **Managing an agent fleet from a page has become possible.** The earlier conclusion was: `app_token`
   is pinned to its own agent, so Console either asks for the full-permission `{{token}}` or stays
   device-only. Now there's a third path — the `api.full` permission, with the token **never reaching JS**:
   the proxy substitutes it. The buyer sees the permission before installing and can revoke it.
2. **A page-type product can call a third-party API** — Tourvisor, Bitrix24, a CRM — without a local
   server and without the provider having open CORS.

**Three honest caveats, or the rule will be read as broader than it is:**

* **`api.full` is the whole account.** Asking for it for a product that only needs its own agent is
  the same defect as `delete_*` in tools. It's for management apps, and only for them.
* **`ext/fetch` does not solve the secrets problem.** It passes through **your** authorization: the key still has to
  come from somewhere. There's no place for it in page code — so the user enters the key and the product
  stores it, or the device path remains. The proxy removes CORS and guards against calling an
  arbitrary address, but it does not replace a key store.
* **Separate from the proxy**, a checkbox for the `X-Auth-Token: {{token}}` header has appeared in the header set.
  It sends the **full token out**, unlike the proxy. For us — trusted server-side integrations only,
  and off by default.

### H14. Updating without a redeploy: three ways, and they cost differently

Checked live on 13 Aug 2026 on a published guide. The full breakdown and a working example are in
`store_app/` in this same repository.

| Что меняется | Как | Что нужно от человека | Когда видно |
|---|---|---|---|
| **text, data, settings** | commit to the content file; the page reads it from the repository | nothing | within 5 minutes |
| **shell: markup, scripts** | replacing the page on the same version (H10) | attach the file | immediately |
| **code on the buyer's machine** | download a fresh product archive | confirm the update | immediately |

**The first way — the classic "fixed it on my end, everyone got the update."** `raw.githubusercontent.com`
returns `access-control-allow-origin: *`, so the page in the sandbox reads a file from a **public**
repository with no tokens, no app permissions, and no agent. Probe: a commit to the content only →
the window showed a new section and noted "updated to …", even though the page had not been rebuilt
and had not been uploaded to the store.

Four conditions, without which this method is a defect, not a convenience:

1. **A snapshot of the content is baked into the page.** The first frame is drawn instantly and without the network.
   A page that waits on an external source shows a blank screen when that source is unavailable —
   and that breaks the stop rule "a refusal is visible in words."
2. **What comes from the network is data, not code.** Strip `<script>`, `on*` handlers,
   and `javascript:` before inserting it. Otherwise a content update turns into a delivery channel for someone else's code.
3. **The repository is public.** A private one requires a token, and there is no place for a token in page code (H11).
4. **The cache is five minutes, and it can't be busted.** Neither `Cache-Control: no-cache` nor a URL parameter works —
   `source-age` in the response shows the age. That's fine for a guide; for data that needs
   freshness in seconds, this source won't do.

**A fifth condition, found on our own product on 13 Aug 2026: an update must refuse to go
backward.** The first version of the guide treated "version not equal" as "version is newer" — and a stale
source **silently rolled the page back** from a newer embedded snapshot to the old text. This is the
same class of bug as "the pack was a rollback machine": every "update yourself" returned the previous state.

The fix is comparing versions part by part, not with "not equal": apply only strictly newer,
and never apply a version that can't be parsed. And this needs to be checked specifically — in an ordinary run
the defect is invisible, because the source is usually the newer one anyway.

**The third way — code on the device, and here the rules are stricter.** Technically this is `install.py`,
which pulls a fresh version. But a code update arrives **inside someone else's perimeter**, so:

* **by release tag, not a floating branch.** "Updating from `main`" means "I'll run whatever
  someone happened to push";
* **verify the checksum** before running;
* **say in words what changed**, and let auto-update be turned off;
* **prefer the store**: `GET /api/app-archive?app=ИМЯ` returns the product archive with resumable download and
  an `ETag`. It's the same code of yours, but under the platform's versioning — and it knows who has what installed. With an
  update from GitHub, nobody knows that, and support turns into "which commit are you on?"

A ready-made module with both sources, checksum verification, and rollback is `templates/self_update.py`.

### H13. CANCELLED 13 Aug 2026 — token-based isolation no longer exists

**The section below describes behavior that no longer exists.** It's kept in full because
decisions relied on it (the guide being published manually by the owner, reading the token from a separate
file) — and because it's a textbook example of a fact that went stale within a day.

**Probe on 13 Aug 2026, the same device token:** `my-listings` returns **19 listings**,
`my-purchases` — **21 purchases**, including everything the owner saw on screen ("Тест 1",
"Recruiter Panel Shell", "Lawyer", "Telecom Demo"). A day earlier the same token saw **4**.
What exactly changed on the platform side — unknown; the platform's author was working at the time on
token management with access levels.

**The rule now in force:** an account token sees the account's storefront. The workaround "only the
owner publishes, by hand" is no longer needed, and neither is the separate file with the storefront token.

**What remains useful from H13:** a quick diagnostic. If the list from the API disagrees with what a
human sees on screen — don't argue and don't declare a defect, instead **check the specific
`listing_id`**. Our account has two different listings with similar names living on it
("Predictive Sales" and "Predictive Sales (OSINT)"), and one of them **has no page at all**:
a request to it replies "This app has no web page". Mixing them up is a ready-made false diagnosis.

### H13 (historical text). The storefront belongs to the TOKEN, not the account (12 Aug 2026)

**The most expensive finding of the day, by time spent.** I published an app, the owner
opened his store on the same account — and didn't see it at all.

The reason is written in the platform's documentation, but wasn't read as a consequence: the owner's
internal key is `sha256(token)`, and "all user data (desktop, purchases, listings,
balance) is isolated by **token** owner."

**That means one account has as many parallel stores as it has tokens.** Our
live account has **eleven** of them (`list_tokens`): service tokens, auto-created ones, invites for
colleagues, a toolbar session. Publishing with a service token went into its own container:
the API honestly showed the listing, the interface honestly didn't show it — and both were right.

Signs by which this can be seen, not guessed:

* one name differs between the interface and the API (in our case — "Predictive Sales (OSINT)" vs.
  "Predictive Sales"): these are **different listings in different containers**, not a rename;
* the listing count is off by multiples (14 vs. 4);
* a freshly published one is missing from the interface, but `my-listings` returns it.

**Rule:** publish with **the same token** the owner uses in the interface. The token from
`~/.extella/api_token.txt` is **not fit by default** for publishing into their storefront — first
make sure it's the right one. Quick check before publishing: compare `my-listings` with what the
owner sees on screen. If it doesn't match — don't publish, ask.

**What must not be done:** brute-forcing the account's tokens to find the right one. That looks and works
like credential brute-forcing, the environment stops it — and rightly so. Colleagues' tokens
(`invite: …`) must not be touched at all: someone else's data sits behind them.

**A simple workaround with no tokens at all:** the owner publishes a page-type product himself through
the OS form — the interface file in the Web page field. Then, by construction, the listing lands in the
container the owner works in.

**Platform's answer received 12 Aug 2026 (the platform's author): this is intentional, for now.** A
separate token-management page with access levels is in the works, and then isolation will stop being
a problem. So this is **not a defect but the current model** — the question is closed, no need to raise it again.

Until that page appears, the rule above stays in force: publish with the token the
owner uses in the interface, and treat a mismatch between `my-listings` and the screen as a stop signal.
When token management appears, recheck this section: isolation will most likely become
configurable, and the ban on "don't publish with someone else's token" will turn into "pick the right access
level."

### H12. App permissions (`app_scopes`) — a new mandatory publish step

**Appeared on 12 Aug 2026, deployed the same day.** Checked against the live OS schema: the
`app_scopes` field is present in publishing, the `/api/app-agent/call` and
`/api/app-permissions/{lid}` endpoints are live. Between my two checks within the same day
the schema changed — **check live, not against yesterday's notes.**

**The main rule, breaking which kills the product silently:**

> **An empty `app_scopes` = the app cannot call the agent's API at all.**
> Nothing is granted by default.

The page will still open and look intact — while every call returns `403`. A product
published without declared permissions looks like it works, and doesn't.

| Permission | What it grants |
|---|---|
| `agent.run` | conversation with the agent |
| `expert.run` | running the agent's experts **in the container** (cloud) |
| `device.run` | `expert.run` + `targets` — **running on the buyer's device**, a separate permission |
| `expert.read` | `expert.list` / `get` / `search` |
| `concept.read` / `concept.write` | agent memory |
| `kv.read` / `kv.write` | key-value |
| `rules.read` / `rules.write` | agent rules |
| **`api.full`** | **the whole account** via `/api/ext/core` — for management apps (H15) |

Calls go through `POST /api/app-agent/call {app_token, op, payload}`; `/run` and `/message` are sugar over
`expert.run` and `agent.run` and require the same permissions. The `global` gateway always strips it out. It lets the
`targets` field through only when `device.run` has been granted; without that permission the call runs
in the container. A scoped operation never reaches beyond the buyer's agent.

**Three consequences for our work:**

1. **Declare the minimum.** The buyer sees the requested permissions on the card before installing. A product
   asking for `*.write` "just in case" looks dangerous — and rightly so. It's the same
   stop rule as the ban on `delete_*`, except now the client sees it.
2. **Permissions can be revoked at any time** (`POST /api/app-permissions/{lid}`, `[]` — a full revoke),
   and the check runs on every call. So `403` is a **normal, expected state**, not an emergency:
   the product must say in words "permission revoked, turn it on here", not show a blank screen.
3. **The agent's own front end ≠ fleet management — but a way out appeared the same day.** `app_token` is pinned
   to the agent of **its own** install; other people's agents are out of reach through ordinary permissions. The earlier
   conclusion that "Console therefore needs the full-permission `{{token}}` or the device path" is **lifted**:
   there is the `api.full` permission and the forward proxy (H15), where the token never reaches JS at all.
   Asking for `api.full` for a product that only needs its own agent is a defect.

### H11. Purchases can be read — but not from the page (checked 12 Aug 2026)

Checked with live requests: `GET /api/my-purchases` and `GET /api/my-listings` **exist and
reply 200**. The app page is served from the same domain as the API (`os.extella.ai`),
so there is no wall between them.

One thing is missing: **these endpoints only know the account token**, and you can't
present them an `app_token`.

**CORRECTION the same day, after guidance from the CTO.** I wrote "`{{token}}` is forbidden to use."
More precisely: it's **full-permission and expensive**, not forbidden. The platform supports it
deliberately — before the OS first opens it shows the buyer a "Data access" consent dialog
(with a "don't ask again" option), and the platform author's recommendation matches ours: don't
issue it without extreme necessity, `{{app_token}}` exists for your own agent (H12).

Rule: `{{token}}` — only when a product needs **more than its own agent** (our case is
fleet management), and then an honestly declared consent dialog is part of the UX. In all
other cases — a defect.

**What to do until the platform improves this.** The source of "what the user has" is not purchases
but **core objects**: agents, their experts, rules, devices. The adapter expert reads them
today, and that's enough for an automation-management panel. Purchases are enrichment
("delivered from the store, such-and-such version"), not the foundation. If a field is missing — say so in words
in the interface, don't hide it.

**The platform's answers on 13 Aug 2026 to our requests:** putting the listing icon on the web-app shortcut —
**will be fixed** ("I'll fix it quickly"); deleting your own purchase — **hiding is planned**
with return via the store, not deletion. Until then, our own test products stay
in the launcher: there is no purchase-deletion in the API, and a listing isn't deleted while a purchase for it exists.

**The request to the platform — partly closed the same day.** App permissions (H12) gave the page
legitimate narrow read access: `expert.read`, `kv.read`, `rules.read`, with consent and revocation. What's left
unclosed is only listing **purchases** by `app_token` — and listing **other agents**,
which is deliberately closed by the design of the model.

### Acceptance order for a page-type product

0. **`app_scopes` are declared and minimal** (H12). Empty — and the app won't be able to call the agent
   at all, which is only visible on a live call, not at publish time. The device part needs
   `device.run`;
1. the source's `agent/run` replies without `pro_key_required` (if an agent is attached);
2. publishing returns `stats` on the product's composition, `page` is accepted, the listing is in pre-release;
3. `GET /app-page/{lid}` returns the page, not a 404 "This app has no web page";
4. in the opened page, `{{token}}`/`{{agent_id}}` were substituted, and there are **no**
   placeholders left in the visible text;
5. one product scenario runs live from start to finish.

Not run even once — the first run will be evidence, not a formality.

### What follows from this for our products

**CORRECTION 12 Aug 2026 to this section.** It used to say below that Recruiter could not be moved to
`page`, "because there's nothing to call an expert with from the sandbox." That's **wrong** — H5 and
H5-bis proved the opposite the same day. I'm leaving the wording corrected rather than deleting it:
that exact phrase is what two chats used to justify stopping work.

**Recruiter** can have a page-type surface, and the only question now is the cost per call: its
screens are built on frequent calls to `rec_*`, and each one from a page costs 13–17 seconds.
It's worth converting as a hybrid (H10), and only after rewriting the adapter for a snapshot call.

**The telecom operator's pack** stays device-only for two reasons, and neither is about feasibility:
93 MB (the `page` limit is 20 MB compressed), and real client data that must not leave
the machine.

**What's worth making page-type is anything whose logic lives in the browser or in the OS API** — desktop
management panels, report storefronts, builders, attachment viewers via "Open with…".

---

## Before Publish: acceptance is mandatory, and gates don't replace it (calibration 12 Aug 2026)

Three chats in a row brought the owner to the Publish button right after green gates — which means
the instructions stayed silent, not that the chats made a mistake. Rule:

**Green gates do not authorize publishing.** Acceptance is mandatory before Publish:

1. publish as a **pre-release** (visible only to the author) — not straight into the store;
2. purchase it yourself;
3. **the first run in a clean state** — as a buyer would see it, without the owner's configs and
   keys: onboarding greets you, every "not connected" is stated in words, not as errors;
4. only after that — Publish, and a human clicks it.

**The boundary of client keys.** A product has two kinds of external dependencies, and confusing them
is a mistake either way:

| | Ours (platform, experts, bridge, install) | Client's (Tourvisor key, WhatsApp number, CRM) |
|---|---|---|
| Acceptance requires | work live | the product **is honest without them**: it leads to the key field, empty states in words |
| Is their absence a blocker? | yes | **no** — it's a designed-for state |

For a product with client keys, an "end-to-end live scenario" means a scenario
**up to the key boundary**. Requiring a live third-party key before publishing is the same mistake as
requiring a passport from a prototype.

---

## Finishing the build: the chat gets it to pre-release, a human clicks Publish (rev. 12 Aug 2026, evening)

The first edition said "the chat prepares the artifact, a human uploads it" — and that created a bottleneck:
the chat would hit the ceiling of "zip + instructions", and all of acceptance queued up for the human.
In one day, four products out of five failed to reach deploy for exactly this reason.

We're splitting apart two different actions that used to be called by the one word "publish":

| Action | Who | Why |
|---|---|---|
| Publishing as a **pre-release** (`published=0`) | **the chat, itself** | a pre-release is visible to no one but the author: no risk |
| **Purchasing it yourself** and installing | **the chat, itself** | it's a check, not a giveaway |
| First run in a clean state, the scenario | **the chat, itself**; a human watches with their own eyes | acceptance |
| **Publish to the store** (`published=1`) | **human only** | visible to everyone; REVERSIBLE — undone with the same address with `{"published": false}` (H26) |

**The target handoff state:** "the pre-release is published, purchased for yourself, the install went
through, the first run in a clean state passed, the scenario ran live — only one click of
Publish remains." The chat must get exactly to this point and attach evidence: `listing_id`,
`version_id`, what the first run showed, what didn't line up.

The artifact (zip) is still put in the named location — it's needed for republishing
and for the case where the OS form turns out to be more convenient than the API.

### H72. `/api/app-agent/run` envelopes also carry a `status` — the domain check goes blind on it

**Probe on 22 Aug 2026, the "Developing on Extella" page, 3.7.0.** The response from the buyer
route arrives in two wrappers, and both look like a domain response:

    {"status":"ok", "agent_id":"…", "result":
      {"status":"success", "expert_name":"journey_capabilities", "result":"{…json строкой…}"}}

Envelope-stripping had a guard: "a domain response must not be stripped: it can
have its own `result` field", and the marker of a domain response was taken to be a **string `status`**. On this
route the guard fires on the very first envelope: what gets returned upward is the envelope,
its `status === 'ok'`, and the domain check `!== 'success'` fails silently — no
error in the console, no refusal on screen, simply nothing happens. Stripping one
layer made it worse: the execution envelope carries `status:'success'`, the check lets it
through, but it has none of the response fields, and the page honestly draws "no credits,
no model, no Board" while there are 51557 credits and a model already up.

**The marker of transport is not `status`, but a pair.** An envelope is given away by the `result` field
together with `status === 'ok'` **or** with `expert_name`. The platform sets both;
a domain response answers `success/error/empty/refused` and never
carries `expert_name`. Strip while that pair holds — and only then check the
domain (a continuation of H56: transport and domain are separated completely, including
the marker used to recognize transport).

**Why this is more dangerous than an ordinary breakage.** The local bridge `/api/expert/run` returns
a different shape, and the same code passes on it. So the check on the bridge is green, while
for the buyer **everything** is dead — not one call, every call. The buyer route must
be checked with a buyer call.

### H73. The dereference gate must see an id that has moved into an argument

**Same probe.** The canon already had the "blind dereference" gate written into it: it checked
literals inside `getElementById(...)` against the markup's ids, and last time it caught 24
mismatches. This time the id had moved not into `getElementById`, but into an argument —
`открыть(2,'ш2')` with the button `дп-ш2`. Eight transitions between acts went out to the
store silently: the first step worked, the second button stayed permanently
disabled, the story ran into a dead end, and the gate was green.

**Norm.** The gate checks against the markup not only literals inside `getElementById`,
but also strings that travel as an argument to wherever an id gets dereferenced. General rule:
you need to check **every place an id can reach a dereference from**, not just one
familiar way of writing it — otherwise the gate guards against the past mistake, not the class of it.

### H74. An unbounded page self-repeat — a task pipeline behind a frozen button

**Probe on 22 Aug 2026, a Claude install at a buyer's.** The button held "Connecting…" for
four hours, the device's task counter grew from 201 to 279 — 78 tasks in
232 minutes, about three minutes per task — with **three** button presses and zero
active tasks. It wasn't a human generating the tasks: inside the frame-based install path lived a
watcher — a `status` poll every 90 seconds, which had **neither a limit on
attempts nor a death on handoff**: an eight-second fallback exit
handed the install off to the direct path, but never set the completion flag, and the watcher lived on
as long as the window was open. It could not read "done" because of H72 — an envelope landed in its hands
instead of a response — and every one of its polls became a real task on the
device. 90 seconds of waiting plus the time of the call itself — that's the three minutes
per cycle; the arithmetic matched the counter.

**Three norms.**
1. **Every page self-repeat is finite.** Polling, a watcher, a retry after a
   deferred task — all of them have a limit on attempts or time, and once it runs out,
   honest words that it didn't work and what to do. The advice "press again" with no limit
   built in is just shifting an infinite loop onto a human's fingers.
2. **The watcher dies together with the wait.** Any path that hands work off to
   someone else (a fallback exit, a channel refusal) must extinguish its background
   repeats with the same flag that extinguishes success.
3. **A retry is not new work.** Polling reads state (`status`), it doesn't
   restart the stage; stages are idempotent, so that pressing again
   continues rather than multiplies.

Checked by the page contract (`test_page_contract.mjs`): limits on the watcher and
the long poll, the watcher's death in the fallback exit, stripping both envelopes
of the buyer path.

### H75. Eyes-on acceptance is done at the size of the real app window

**Probe on 22 Aug 2026.** The product's page passed acceptance in a 551×860 browser and
shipped to the store. The owner opened the real app window — it's three times wider —
and got three defects right at the door: a button overran a caption (a negative margin
on the caption with a button row and no bottom one), the story heading broke
mid-word onto the next line, and canvas labels ran together and got clipped. The cause of all three hid from the
narrow window: a media rule collapsed the grid into a single column, and inside it everything
looked healthy.

A separate lesson inside: **max-width inside max-width doesn't work.** The story
block was given its own 1120 inside a 760 container — a child limit wider than the
parent is dead code, and it silently means the intent of a "wide" layout was
never carried out even once. A spot like that isn't a trifle, it's a sign: nobody
has ever seen the wide layout.

**Norm.** Eyes-on acceptance is done at a minimum of two sizes: the width of the real
app window (today that's ~1700 logical pixels) and a narrow window (~550). A
green narrow run says nothing about the wide one: they run different branches of
CSS. Horizontal overflow is checked with a number
(`scrollWidth − clientWidth === 0`), not by eye.

### H76. A version's scope is a frozen snapshot of expert code

**Probe on 22 Aug 2026.** The expert `journey_publish` was rewritten, saved via
`/api/expert/save`, read back and diffed character by character — the account's record is new.
The direct path (`/api/expert/run` with `X-Agent-Id`) runs the new code. But
the buyer path (`/api/app-agent/run` with the app token) replies
"unexpected keyword argument" — it runs the **old signature**: a version's scope
stores not the experts' names, but frozen copies of their code, taken at the moment of
`add-version`.

**Consequences.**
1. `edit-version` only changes the page — it never
   updates buyers' expert code.
2. `expert/save` updates the agent's record — the direct path sees it, but the
   buyer path doesn't.
3. The only way to get new expert code to buyers is a new listing
   version (for a published one it's public immediately, H20). The snapshot
   is then rebuilt from the source-agent's experts at the moment of add-version.
4. Checking that "the expert has updated" must go through a buyer call, not
   `expert/get`: reading shows the agent's record, while the buyer runs a copy.

### H77. A product that creates products must place the icon itself

**Probe on 23 Aug 2026.** The "Day One" storefront was creating an app draft with no
icon. On the desktop it stood as a nameless gray square among the Bronze Engraved
tiles — a reward for a completed journey that looked like litter, and the owner
asked to have it removed. The storefront gate (`check_listing_meta`) requires an icon for
repository products, but it doesn't apply to listings the product creates
**at runtime**: there's no folder there to check.

**Norm.** Any step that creates a listing attaches `icon` in the same
`publish-stream`. The tile is not drawn on the spot: there is one style canon —
`tools/bronze_icon.py`. There's no Chrome or Lucide set on the device, so the
tile is rendered ahead of time by the canonical generator and baked into the expert
as an image (base64). Your own "almost identical" generator inside the expert is a second
source of style, exactly the class of divergence the gates exist to prevent.

What needs checking is not a response field but the storefront: `has_icon` in `/api/my-listings`.
The expert's response only says that it **sent** the icon.

### H78. Refusal handling lives in one place, or copies drift apart silently

**Probe on 23 Aug 2026.** A buyer saw this line on screen

    ОС ответила 502 · core /api/expert/run failed: HTTP 500: {'status':
    'error', 'message': 'Target устройство-… is un

— the core's raw response together with a Python dict. On a neighboring screen of the same
product the same cause had been translated into words: "Device unavailable.
Fully quit Extella (⌘Q)…". The answer isn't on the platform's side: refusal handling
existed **in two copies** — the install path and the storefront path. The translation for
`Target … is unavailable` was added to one of them, the other stayed as it was, and no one
noticed: both "worked."

**Norm.**
1. Translating the platform's refusals is **one** function for the whole product. A second
   handler with the same branches isn't code duplication, it's guaranteed
   behavioral drift.
2. The platform's raw text is **never** shown to a human, including for an
   unfamiliar cause: it goes into the window's log, and the human is left with words and
   a next step. Truncated English with curly braces isn't diagnostics,
   it's an admission that the product didn't understand its own refusal.
3. The "cause unknown" branch must exist too, and it must also give a step.
   Checked by the page contract: singularity of the function, both calls,
   absence of raw text, and a live run against the platform's verbatim response.

### H79. Your own free draft places itself on the desktop and stays deletable

**Probe on 23 Aug 2026.** The product created an app and left it sitting in the
store: for a tile to appear on the desktop, a human had to find the
card and click "Buy & Deploy". Nobody guessed this, and meanwhile the page
wrote "already on the desktop" — a plain falsehood.

**What was checked live.** `POST /api/purchase-stream/{version_id}` with an empty
body on **your own free, unpublished** draft:

* replies 200 and sends a `webapp` event with `shortcut_id` — a tile on the desktop;
* after that, `DELETE /api/listing/{id}` still replies **200**, and the listing
  disappears.

So the earlier caution — "a purchase makes a listing permanent" — applies to
**published** listings (H26) and to other people's purchases, and does not
apply to your own draft. This should have been checked earlier: because of an unverified assumed ban, the install
step was done by hand for years.

**Norm.** A product that creates an app for a human takes it all the way **to the
desktop**, not just to a card in the store. The full step is publish-stream
(page + icon) plus purchase-stream (tile), about 15 seconds together,
within the deferred-task limit. If the second step fails — say so directly and
name the manual path, rather than promising a tile that doesn't exist.

### H80. A tile on the desktop and a listing in the store are two different things

**Probe on 23 Aug 2026, a continuation of H79.** Installing puts a shortcut on the desktop
(`shortcuts` in the desktop state). Deleting a listing (`DELETE /api/listing/{id}`)
does **not** take the shortcut with it: after four trials, three dead
tiles were left on the owner's desktop, pointing at deleted pages. Purchase records
disappeared along with the listings — meaning the shortcut outlives both the purchase and the listing.

**Where shortcuts live.** `GET /api/desktop/items` returns the desktop broken into sections
(`folders`, `links`, `instructions`, `shortcuts`) — this is NOT a flat list, and a
naive `len(response)` gives zero. The state itself is `GET/POST /api/desktop-state`:
`{state:{pos, shortcuts, folders, sys, trash, links, instructions, …}, rev}`.
There is no separate `DELETE` for a shortcut; it's removed by writing the state without it.

**Norm.**
1. Make edits to the desktop state minimal and **verify before sending**: how many
   keys change, and which ones. A human's desktop is not our draft — it holds their notes,
   links, and trash.
2. Take a copy of the state before writing — a rollback must exist.
3. The product should not promise "deleted with one click": removing it fully means
   the tile into the desktop trash **and** the draft in the store. A promise that sounds
   simpler than the truth comes back as litter on someone else's desktop.
### H81. The entry point contradicted the prompt, and the entry point won

**Measurement, 26 Aug 2026.** The ready-made prompt forbade it: "don't ask to forward
the token in chat." The README, step 1, instructed exactly the opposite: "ask the user
to write in the Extella chat 'Generate me an API token,' and have them send you the
string." A contradiction inside the single entry point — and **the README won**,
because the prompt itself sends the agent to read the README as the source of truth.
A person who doesn't know Extella hit a dead end: which chat, what to write, where to
paste the secret.

**There was no need to ask at all.** The key needed is the same one MCP uses.

> **AMENDMENT 28 Sep 2026 — two claims in this paragraph turned out to be wrong.**
> First: the key does NOT appear on disk by itself — app 1.3.0 does not write it, and
> an issue screen does exist (`Library → System → Tokens`), see H108 and the
> measurement of 24 Sep 2026. Second, and this one costs more: **a handshake proves
> nothing.** `initialize` with a deliberately wrong key answers HTTP 200 with
> `"result"`, and `tools/list` returns the tool catalogue with no authorisation at
> all. A check built on the `"result"` substring declared "connected" for any string
> in place of a key — and the newcomer went looking for the fault where there was
> none (audit of 28 Sep 2026, F01). There is exactly one proof: **calling a reading
> tool and parsing the answer field by field** (`isError`, `error`). An empty list on
> a new account is a legitimate success.

**Norm.** A step that a person cannot complete without knowing the platform is not an
instruction but a command: `tools/connect_mcp.py`. Three rules inside it:
1. **The key is verified by a call — not by the file's presence and not by a
   handshake.** The file outlives an account switch, and the handshake passes with any
   rubbish in place of a key. The honest proof is `tools/call` on a reading tool with
   `isError` parsed.
1-bis. **`X-Agent-Id` is mandatory in MCP headers — and only in MCP.** Measured 28 Sep
   2026: the same `tools/call` with a valid key but without this header answers
   `isError: true` and the text "Failed to resolve dependency 'token'" — the message
   blames the key, though the key is valid. **This does not carry over to REST:**
   `POST /api/agent/list` with the same key and NO `X-Agent-Id` answers HTTP 200. One
   header's requirement is not extended to every method without checking its contract.
   A non-empty value is enough (a non-existent agent id gives the same answer as a real
   one — verified on `list_agents`; tools that work INSIDE an agent's scope need a real
   one). So connecting is possible on an empty account, and the person creates their
   own agent afterwards.
   **One text for two causes:** MCP answers with the same wording both for a wrong key
   and for an empty agent header — the answer cannot tell them apart.
1-ter. **Ask REST for the cause of an MCP refusal.** Measured 28 Sep 2026: for a wrong
   key REST answers `HTTP 401 {"error":"Invalid or expired token"}`, while MCP at the
   same moment answers HTTP 200 with the text about a "token dependency". The honest
   channel exists and must be used: if REST returns 200, the key is VALID and the MCP
   headers need fixing, not the token. Retelling the MCP wording as the cause is
   forbidden — it names the wrong thing to fix.
2. **The secret goes into neither the config nor the arguments.** Claude Code has
   `headersHelper` for this — the script hands over headers at call time. Codex has
   no such thing; the key goes into `~/.codex/config.toml` — the file is set to 600,
   and this is stated out loud, not left unsaid.
3. **What is already configured is not overwritten**: the person may have a binding
   to a different account.

**A small thing that would have caused a silent failure.** `claude mcp add-json`
without `--scope user` writes the server into the scope of the CURRENT folder
(`projects.<cwd>` in `~/.claude.json`). The agent would have reported "connected,"
while in any other folder the binding would not exist.

**The format for Codex was fixed along the way.** The README showed it the
`mcpServers` JSON — that's the Claude Code format. Codex keeps MCP in TOML
`[mcp_servers.*]` (`~/.codex/config.toml`); by the old example it wouldn't connect.

### H82. A recipe module without a check and a imprint is a lottery, not a product

**Owner's concept, 26 Aug 2026.** A capability is sold not as a program but as a
recipe: an agent assembles it for the person on the spot out of the platform's
building blocks. The concept is sound — an expert, a rule, a concept, and an agent
are all created programmatically, so a module is an instruction for how to assemble
them. This opens the module market without a single change to the platform.

**Where it falls apart.** A prompt is not a product but a promise of a product. The
same text on two machines, with two models, on two different days will give a
different result. A store where the module is assembled anew every time is selling
uncertainty.

**Norm: a module is three parts plus a imprint.**
1. **Recipe** — what to build and how; read by the agent.
2. **Passport** — what is needed and **what the module does NOT do**; read by the
   person. The boundary is mandatory: without it the module promises everything and
   is answerable for nothing.
3. **Check** — a machine test capable of failing; it has its own negative control.
   Without a check, "it installed" means nothing — this corpus records three
   separate cases of green checks on a dead product.
4. **Module Imprint** — a file with the expert's code, frozen after the first build.
   The recipe is needed once; after that everyone gets the same thing.

**A module imprint and a version snapshot are different things.** We make the imprint; it
sits as a file in the repository. The platform makes the snapshot when a version is
released: it copies the experts' code inside the version, and the buyer gets a copy
of that, not whatever the author has right now (H76). The words sound alike, the
layers are different — the owner tripped over this in the 27 Aug 2026 conversation,
so anyone will trip over it. Write it out in full in the text: "module imprint,"
"version snapshot," never just "imprint" for the platform sense.

**The recipe's boundary.** A recipe assembles what already exists and adds nothing
that is missing. "Speech recognition" cannot be assembled by a recipe today: the
microphone in the window returns a mute track instead of a refusal. The passport
must state this before the purchase, not after.

**The first module as a sample.** "Contract reading": reads with a local model, does
not send the text outward (a contract is client data), does not parse a PDF at
random and instead refuses in words, and names in its response what it read with and
where. Measurement 26 Aug 2026 — 6 fields out of 7, 14.7 s through the platform on
the device. The miss on one field is recorded in the passport: the check requires a
threshold, not perfection, otherwise the test gets tuned to a lucky run.

Checked by the gate `tools/check_toolkit.py`.

### H83. The recipe reproduces the skill, but not the contract

**Experiment, 26 Aug 2026.** Two independent agents assembled the "contract reading"
module from the same recipe, without seeing a finished implementation. On the same
contract:

| | sample | agent A | agent B |
|---|---|---|---|
| fields out of 7 | 6 | 7 | 7 |
| text sent outward | no | no | no |
| passed the module check | yes | yes | yes |
| **keys in the response** | **16** | **22** | **19** |
| `file` field | present | present | **absent** |

**The capability reproduced fully**, and both third-party builds turned out better
than the sample: the agents refined the model's task themselves and recovered the
seventh field. **The response's shape did not reproduce**: a different number of
keys, different wording for three fields, one build has no `file`. An app written
for one build breaks on the other — and that is exactly what a buyer counts as the
product being broken.

**Norm.** A module's check must pin down the **response's shape**, not just
behavior: the list of required keys is checked against a live response. Verified in
reverse — under the new rule, the build without `file` goes red, and the sample
build passes.

From this comes a second point: **the imprint is mandatory**. It is the contract that
the buyer receives; the recipe gives the skill, and sameness is given by the imprint.

**A caveat about the experiment's purity, important for the conclusions.** The exact
value of the consent parameter matched across all three not because the recipe sets
it — it does not. It is named in the passport and in the check, which sit in the
same folder. So the measurement showed the reproducibility of THREE PARTS together,
not of the recipe alone. For the market the framing is correct — the buyer gets all
three — but the claim that "the prompt is enough" is not confirmed by this
experiment, and cannot be.

## Finishing the build: previous edition (for the record)

Lesson from the telecom operator's rollout, 11 Aug: the chat "prepared the rollout,"
but it only shipped after the owner asked for an archive to be assembled and
uploaded it by hand through the OS publication form.

Norm: **the result of the build is a ready file** (a zip of the page-type bundle or
an archive of the device-type product) at a named location, plus a three-line
instruction — which fields to fill in the publication form and where to click. The
person uploads it and clicks "Publish."

Why this way and not publication via the API: the form works and takes a minute;
publication via the API trips up chats (our own experience); and the button that
publishes to the store is pressed by a person — accidental publication is ruled out
by construction.

---

### H62. The app is an inner panel: outward only by message, there is no direct request

The product page consists of TWO parts, and confusing them is costly. The platform
provides the wrapper: it holds the app's token and makes the request to
`api/app-agent/run` itself. Inside the wrapper lives a sandbox frame, and **the
author's app is that frame**. The frame has no origin of its own (it's empty), so a
request from the panel outward does not go through in principle: the browser
refuses even before it reaches the network.

Hence the only legitimate path: the panel talks to the wrapper **by message**
(`etb_run_expert` outward, `etb_expert_result` back), and the wrapper is the one
that reaches the platform.

Confirmed 23 Aug 2026 by a measurement on the live Agent 1C: the wrapper holds both
`app-agent/run` and both halves of the message protocol at once; the inner frame is
created by the wrapper's code. Proven separately by contradiction — a utility
script run inside the frame could not send a request outward and only reached the
observer by a message upward.

Without this rule the author writes a direct request in the panel, gets "failed to
get a response," and hunts for a breakage in the platform that isn't there.

Correction to the earlier entry: the phrasing "two different ways to communicate,
pick the fitting one" is wrong. There is one way; the two parts are the platform's
wrapper and the author's panel.

### H63. Without `data-testid` hooks, an app is unverifiable by machine

Every element a person uses — a field, a button, a tab, a toggle — carries a
`data-testid`. The hook is mandatory, not for looks: acceptance on someone else's
machine can fill in fields and press buttons, but it will **only** take hold of
marked elements. Buttons without hooks do not exist for the check.

Why not "press everything in a row": acceptance runs on a live product, and
guessing at buttons on someone else's data is not acceptable. For the same reason,
buttons with words for deleting, posting, sending, and paying are never pressed,
even with a hook.

Measured 23 Aug 2026: in the Agent 1C panel, the acceptance robot found six working
buttons and not a single hook — meaning there was nothing to check "do the buttons
work for the buyer" with. On a skeleton with hooks, the same robot filled in a
field, pressed the action, and got a real result.

Checked by an acceptance run: the "click-through" section either names the number
of buttons pressed and how many responded, or honestly says "nothing to take hold
of."

**A hook's name must be unique and stable.** Permanent locations (menus, tabs, main
actions) are marked explicitly. Deriving the name from the label is a safety net
for forgotten buttons, not the main method: the label contains counters and changes
along with the data.

Three rules drawn from live breakages, 24 Aug 2026:

- **One name for several buttons is a silent lie.** The check presses whichever one
  comes first and reports "pressed," while the neighboring ones are never checked.
  Caught on the Agent 1C panel: three buttons for going to the registry carried a
  shared semantic attribute and collapsed into one hook.
- **Numbers in the name don't survive.** A hook built from a label with a catalog
  counter will change along with the catalog, and the check will start looking for
  something that no longer exists.
- **Whether a name is taken is decided by the live document, not by an accumulated
  list.** Screens get redrawn dozens of times; an ever-growing list drives the
  sequence suffix upward, and the same button ends up getting "-13" one time and
  "-44" another. A removed button must free up its name.

Acceptance checks this itself: the "click-through" section names duplicate hooks
and names containing numbers as separate lines.

### H64. An app's skeleton is taken ready-made, not drawn from scratch

A new app starts from a copy of a working skeleton that already has a form, result
output, four states (empty, waiting, error, ready), a bridge to the platform with an
allow list of experts and a single timeout, a local mode for checking the interface
without an expert, and `data-testid` hooks.

The point of the rule isn't "saving time" but sameness: a product assembled from
the skeleton passes acceptance by construction, while one drawn from scratch each
time brings its own opening-day defects.

The skeleton lives in `templates/app-recipe/` in this repository: the panel, the
bridge, the build, quick checks, an acceptance sheet, and auto-click-through of the
panel itself.

Cross-check, 23 Aug 2026: the ready-made skeleton's colors and fonts matched the
design section in `AGENT_BUILD_GUIDE` — no discrepancies, so a second copy of the
palette is deliberately not given here (two copies of the palette have already
drifted apart once).

### H65. The app page gets cached — the cure must live in the page itself

The platform serves `/app-page/{lid}/` **without a single caching header**: no
`Cache-Control`, no `ETag`, no `Last-Modified` (measurement 24 Aug 2026, a live
listing). Each browser decides for itself what to do with such a page, so a product
update reaches the buyer hit-or-miss, and differently on different computers.

**Releasing a new version by itself does NOT fix delivery.** The window's address
doesn't change, the browser takes the same copy, and the buyer sees the old version
again. Publishing is still necessary, but treating publication as the means of
delivery is a mistake.

The cure lives in the page itself and has been verified in production since 21 Aug
2026 (found by a colleague's test on a listing updated three times): the page
carries a version stamp, pulls itself past the cache on launch, checks the stamp,
and, if it has diverged, reloads with a bypass parameter.

```js
async function healStaleCache() {
  const response = await fetch(window.location.pathname, { cache: "no-store" });
  if (!response.ok) return false;
  const fresh = await response.text();
  const match = fresh.match(/const PANEL_VERSION = "([^"]+)"/);
  if (match && match[1] && match[1] !== PANEL_VERSION) {
    window.location.replace(window.location.pathname + "?fresh=" + Date.now()
      + window.location.hash);
    return true;
  }
  return false;
}
// вызывать ПЕРВЫМ делом при запуске; если вернуло true — дальше не идти
```

**A limit of the remedy that must be understood in advance:** the self-cure will
only reach those who have already opened the version that has it. Wherever a copy
without it has stuck, it will not appear until the browser refreshes the page on
its own. Hence the rule: the remedy is put into the product **as early as
possible**, not once an update is already needed.

For those where it's stuck, a one-time visit to the address with a parameter
(`?fresh=1`) helps — verified, it returns 200 and lands in a separate cache entry.

The platform still needs `Cache-Control: no-store` on the wrapper: the self-cure
costs an extra request on every open and does not save copies that are already
stuck. The item has been logged on the list for the platform team.

### H66. The first showing happens early, and the machine offers it, not the person

Owner's observation, 24 Aug 2026: people took this repository, assembled an app,
and got stuck — the finished build did **not** end up in Extella by itself, and no
one said the words "deploy to Extella" because the person doesn't know them. The
development path is known to the machine, not the person, so the machine must
lead.

The requirement has three parts.

**Tell it in advance.** Before starting — three to four steps in plain words and a
time estimate. There must be no names of tools, modes, or platform entities in this
account.

**Show before it's finished.** The first visible result is placed at the start of
the path, not the end: as soon as there is a skeleton that opens, the machine
itself offers to show it in Extella. A ready-made skeleton for this lives in
`templates/app-recipe/`.

**Offer it as a question.** Working phrasing: "Ready to show you how it looks in
your Extella — it'll take a minute. Show it?" Waiting for a command in jargon
("deploy it," "push out a version") counts as a defect of the path, not the
person's inattention.

The showing is backed by evidence, not words: right after a private rollout,
`templates/app-recipe/tools/show.py <listing_id>` opens the app on a clean test
stand as an outside buyer would and places alongside it a screenshot of what the
person will see. This way the first "wow" also catches the class of bug "it opened
for the author, a blank screen for everyone else" — before the buyer learns about
it.

The showing is a private version for the owner. Publishing to the store is still
done by the person (see the section on finishing the build), and the offer to show
it does not replace their decision.

Why this is a requirement and not a wish: until the person has seen their thing
alive, every next step looks to them like extra work, and the build breaks off
halfway — exactly where it broke off for the users observed.

### H67. A new subject-matter area is connected as a CSPL domain, not as new access

When an agent needs to act in someone else's system — a database, mail, files, a
government registry — the temptation is to give it broad access and rely on an
instruction. An instruction is not a boundary: it lives in the prompt, and is
therefore negotiable. The boundary is CSPL: the model sends **the operation's
name**, not code, and the handler decides according to a policy that lives with the
client and does not go into the prompt.

Measurement 27 Aug 2026: in the live CSPL-1C, 81% of the code does not depend on
the subject-matter area. So connecting a new area costs **an operation registry,
adapters, and a default policy** — the skeleton is taken ready-made
(`templates/cspl/`). Two domains assembled this way came to 128 and 130 lines.

**What the domain must declare.**

Every operation names its effect before execution — `read`, `export`, `draft`,
`write`, `post`, `delete`, or `development` — and the right it requires. An
operation that doesn't exist yet is declared with a "not implemented" mark: a
refusal of "this operation isn't done yet" is understandable to a person, while
"unknown operation" looks like a breakage.

**What must be decided by policy, not code.**

Rights, scope (environments, roots, limits), and which effects require approval.
The policy lives with the client, does not go into the prompt, and is not
overridden by the agent's server-side instruction. The model cannot request a
right for itself: it can only ask for what is already permitted.

**Anything dangerous goes through approval tied to the plan's fingerprint.**

The `plan` phase does nothing and returns a fingerprint; the `execute` phase
requires that fingerprint back together with an idempotency key. The fingerprint
is computed over WHAT will be done: the phase, the key, and the approval block
itself are not part of it — otherwise consent taken at the plan stage would never
match the execution (caught by a self-check while building the core; in CSPL-1C
this was done correctly from the start).

**A product-level ban is set with two locks.**

The right is switched off in the rights, and the effect is separately marked
forbidden. Then turning the right back on by mistake does not open up the action.
This is how sending mail is set up: the canon "the person sends it" stops being a
wish and becomes a mechanism.

**Checked by the domain's self-check**, which must be able to fail: what is
allowed goes through; going outside scope, an unknown operation, an extra input
field, a policy ban, and substituting approval with someone else's fingerprint —
are all rejected.

### H68. A language of your own is connected as a container, and four things break it silently

The mechanism was verified live on 28 Aug 2026: a Rust expert was built and
executed on the Mac through real CSPL, output `{"привет": "мир", "сумма_1_10": 55}`.

**A language handler is registered as an ordinary expert in `fython`.** No special
rights are needed: the expert calls `disnet.Disnet(...).container(code=…,
func_name="<язык>", container_path="<язык>", args=None, kwargs=<конверт>,
cspl_type="fython", push=False)`. After that, any expert declares
`cspl="<язык>"`, and its source gets this handler. The handler itself runs as
`fython` — the language is added without changing the platform.

Four things, each of which produces a silent or deceptive refusal.

**First: `save_directory` is the containers folder itself, not its parent.** By
default the value is relative (`containers_folder`), and that is correct, because
the expert executes with the listener's working folder. A parent directory in this
field means the container will land next to the folder, the registration will
answer "written," and the language will not appear.

**Second: `push=True` sends the container to the server, while the listener takes
the local file.** Locally it writes `push=False`. A response of "sent" without a
local write means the previous version of the handler is running and the fix was
not applied.

**Third: the service has a stripped-down environment.** The desktop app launches
the listener with `PATH=/usr/bin:/bin:/usr/sbin:/sbin`, so tools from
`~/.cargo/bin`, `/opt/homebrew/bin`, and similar places are invisible. The refusal
looks like "compiler not installed" on a machine where it is installed, and the
advice "install it" doesn't help — the install will land in the same place. The
handler must look for the tool itself and add its directory to the build
environment.

**Fourth: the source arrives in the `filtered_source_code` field.** A handler that
only accepts `code` gets an empty string and complains about an empty file — for
compiled languages this looks like "no main function." Accept both names.

**Fifth: backslashes do not survive the path through `fython`.** A regex-based
grammar check inside a built-in handler silently stops working: a valid `SELECT`
was rejected as "not a read query," even though the handler received it in full
(measurement 28 Aug 2026). In handlers that travel as a string, checks are written
as simple string operations, without regular expressions.

The full envelope the handler receives (measured with a separate diagnostic
language): `code` arrives **empty**; the expert's source sits in
`filtered_source_code`; the run parameters are in `kwargs`; `func_name` contains
the name of the EXPERT, not the language; alongside them come `args`, `cspl`, and
`run_time`.

Separately, about the device: the run is pinned with `targets=["<device_id>"]`
(the identifier sits in the listener's working folder). Without pinning, the job
goes by default routing to another device, where there is neither the container
nor the tool, and the refusal reads as the language being broken.

### H69. Acceptance is passed by the final ZIP in a clean room, not the source tree

The Odoo builder product passed dev-smoke and then crashed for the buyer twice in a
row (measurement from an external chat, a build on the Docker track, versions
0.1.1 and 0.1.3). Both times the cause was not in the product's code but in the
fact that **what was checked was not what would ship to the client**.

**Rule.** Before `add-version-stream` and before Publish, run the **final ZIP**
(not the source tree) in a clean room equivalent to the buyer's machine:

- an empty home directory for the product and empty volumes — nothing left over
  from previous runs;
- **the exact, stripped-down environment of the installed Expert**, not the
  developer's PATH;
- the same mounted directories and the same sequence of states:
  `not installed → ready → restart → ready`.

A dev-smoke with a different PATH does not count as acceptance. If it doesn't
pass, don't create the remote version: a version in the store is immutable (H8), a
fix will only ship as a new number, and a botched version stays forever.

Two specific failures under this rule, both from the service's stripped-down
environment — **the same root cause as H68**:

- **A stripped PATH hides an external tool.** `docker` from a stripped PATH
  couldn't find its credential helper, and the install stalled. Exactly like the
  CSPL handler not seeing `go`/`rustc` from `~/.cargo/bin`: the desktop app gives
  the service `PATH=/usr/bin:/bin:/usr/sbin:/sbin`. Look for the tool yourself and
  add its directory to the build environment, rather than relying on the bare
  name.
- **A mounted shell file in Docker Desktop does not execute** (`Permission denied`
  on the host mount). Pass the command as content — for example, SQL via stdin —
  rather than relying on an executable bind mount.

### H70. Ambiguous output before a destructive operation means "stop," not "no data"

A check for "does the database exist" read `psql`'s output as
`.strip() == "1"`. With any warning before the one, the string stopped equaling
`"1"`, and the code concluded "no database" — that is, it went on to delete and
recreate on live data. Caught by a separate audit before release, but by
construction it was a landmine.

**Rule.** Before a destructive operation (deletion, recreation, cleanup), a tool's
output is parsed **fail-closed**: an explicit, expected answer — we continue;
anything else, including empty or "close enough" — **we stop and report**, rather
than interpreting it as absence. "Unclear" never means "safe to erase."

### H71. Diagnostics print only allowed fields — never the raw response or environment

An account token ended up in the raw output of a diagnostic command run by an
external chat, and later a raw HTTP measurement printed temporary session and CSRF
data. There was a ban on printing secrets, but it gets bypassed not by ill intent
but by the habit of printing "the whole response, just to look."

**Rule.** Diagnostic output is assembled from a whitelist of fields: we print only
fields named in advance (the response code, the length, a specific key). The raw
response in full, the raw environment, and full headers are not printed — not to
chat, not to a log, not to a receipt. Whatever isn't on the whitelist is not
output.

### H84. Acceptance of a windowed product must click through client-side surfaces

The Odoo builder product passed `ready → restart → ready` and all 71 checks, yet
for the buyer the app-menu button hung the window and produced a gray screen
(measurement 4 Sep 2026: four `Extella Helper (Renderer)` crash reports,
`EXC_BREAKPOINT / SIGTRAP`). At those moments Odoo, the database, and the gateway
were **healthy**, with **no** 4xx/5xx errors.

The cause is a class, not a single product: the tile button draws a **client-side
overlay without contacting the server**. So the health check and
`ready → restart → ready` acceptance **cannot see it by construction** — the
server responds while the renderer crashes. A renderer crash is not an HTTP error.

**Rule.** For a windowed product, acceptance must go over the **client-side
surfaces**, not just the server responses: open the app menu, open every root app,
touch overlays and modal windows, close and reopen. The sign of failure is a
gray/white frame, a hung DOM, or a new renderer crash report with a healthy server
and zero 5xx. This is the same requirement as H63 (without hooks a product is
unverifiable by machine), but for surfaces that never touch the server at all:
checking them is not replaced by either a health check or
`ready → restart → ready`.

An honest caveat: a full machine check of an actual window cannot be assembled
right now — it runs into Extella Desktop lacking renderer-crash hooks and a test
mode (an item for the platform). Until they exist, a person goes over the
client-side surfaces from a short list, taking a minute, rather than "clicking
through everything."

### H85. An indicator is a live ping, not the presence of a setting

A product showed a green "connected" as soon as a key was entered — but the key
could be wrong and the login not actually alive (measurement in the FDE track: a
deceptive green on key entry; a separate case — Telegram 2FA, where Telethon
creates `me.session` with a DC key BEFORE the user logs in, and the indicator lit
up falsely).

**Rule.** A status indicator reflects **the result of a live check**, not the fact
that a config exists. Green is set only after a real ping (the status loaded, the
service answered), and it goes off if the check fails. For a multi-step login
(2FA) — green only once everything is there: both the session and the key. "The
setting is filled in" ≠ "the login works."

### H86. A test must hit the same path as production — otherwise green masks dead

Three products in the FDE track independently ran into the same class: **the test
is green, but production is dead.**

- A test mocked `s.send_whatsapp=…` — thereby **creating** a name that didn't exist
  in production (the function was named differently): sending failed with
  `NameError`, tests green.
- A test triggered the button handler **by calling the function**, while in
  production the button couldn't be clicked (broken `onclick` markup): the defect
  went unnoticed.

**Rule.** A test checks the same path production takes: a button by a **real
click** (`dispatchEvent`), not by calling the function; a name that actually
exists in the code. If a test mocks a function that doesn't exist in production,
it's masking it — before mocking, check with `grep -c 'def '`. Replace inline
`onclick` in generated strings with `data-*` plus delegation (see H63): this way
the click path becomes checkable.

### H87. Destructive tests are never run against the owner's production database

Running destructive settings tests against the production database wiped out the
owner's personal rule (restored from an earlier snapshot). The owner's data —
rules, history, cabinet — is their data, not a testing ground.

**Rule.** Destructive tests (creation, overwriting, cleanup) run only against a
disposable test database, never against the owner's or a client's production
database. The owner's database is separated from the tests before they run, not
after the loss. Related to H70 (fail-closed before a destructive operation) and to
the boundary "client data stays within the client's perimeter."

### H88. Patches — as raw strings, with dedup and a check afterward

A recurring time-loss across several chats: `\n` collapses in f-strings inside a
heredoc, slice patches breed duplicate definitions (the last one wins), and "the
fix didn't take." A mass `replace` once hit a line inside a function and caused
recursion.

**Rule.** Write patches as raw strings (`r'...'`), and after patching, check:
`python -c "import ast; ast.parse(open(...).read())"` and `grep -c 'def '` (there
should be no duplicate names). Check a mass replacement for landing inside a
function body. "The fix didn't take" almost always means a duplicate or a
collapsed line break, not a stubborn bug.

### H89. An empty `agent_id` is the legitimate "not deployed," not a failure

An OS fix: the `/app-page/{lid}/` page for the buyer is now always the latest one,
and `{{agent_id}}` can arrive **empty** — the agent was deleted, but the purchase
is alive. A page that expects a non-empty id crashes on this.

**Rule.** An empty `agent_id` is the legitimate state "product purchased but not
deployed," not an error. The page survives it and states this clearly: it leads to
reinstalling (`Reinstall`), rather than showing a blank screen or crashing. There
is now one piece of advice in the banner — "click Reinstall"; the earlier phrasing
"Buy & Deploy → Existing agent" is outdated: the form now targets the installed
agent on its own.

Apps have access to storage (`kv.set/get/list` via app-agent with Storage scope)
and `POST /api/app-agent/whoami` — a stable account id and a verified email for
binding data. Authors often don't know this and complain that "the app doesn't
remember anything"; this is a documentation issue, not a missing capability
(`whoami` itself is an item for the letter to the platform team).

### H90. "Zero actions from the person" was written for macOS: on Windows the token isn't written to disk

A measurement with a colleague on Windows: the app is open, login is done, the
listener is alive (uvx, python, ten processes) — but this build puts only
`device.txt` into `~/.extella`. The `os.extella.ai` token lives in the app's
memory and goes out as a request header; unlike on macOS, it is not written to
disk. The connection script (`platform_client.py`) looks for
`~/.extella/os_token.txt` — and, not finding it, used to lie "open the app, the
file will appear on its own," even though the app was already open.

**Rule.** The promise "zero actions from the person" only holds where a platform
component itself puts the token on disk; that's macOS. On Windows there is no such
component — the promise is false, and it's a gap in the platform, not a broken
machine. Until the build is brought into line:

- the script must **honestly** say that the file is missing and why
  (`platform_client.py` has already been fixed), rather than giving the useless
  advice "open the app";
- before sending the person into the browser console, check whether the app
  persists the login in its own storage (on Windows — `%APPDATA%`): the absence of
  the string `os_token` in the app's code does not prove there's no token on disk
  under a different name. If it's there, an expert on the already-authorized
  device reads it — zero steps for the person;
- manually seeding the file (console → clipboard → file) is a last resort, done
  once, and the token's value is not printed either to chat or to the screen.

The proper fix is on the build side: the Windows app should write the token to
disk the same way macOS does. Then "zero actions" will become true (an item for
the letter to the platform team).

### H91. Listener state files don't sit at a fixed path — don't use their absence to conclude "no listener"

A measurement on a test stand (VPS, user ubuntu, 5 Sep 2026): there is no
`~/.extella/device.txt`, even though the listener is working and executing jobs —
it stores the device differently. Experts that look specifically for this file
mistakenly conclude the listener is absent. This is the same ailment as H90 (the
token not on disk on Windows): the path to listener state — device, token — is
**not guaranteed** and varies by OS, user, and build.

**Rule.** Check the listener's presence/operation by fact (a process, a live
response to a job), not by the presence of a specific file in `~/.extella`. If an
expert needs `device_id` — get it through the standard channel, not by reading an
assumed file; the file's absence ≠ the listener's absence.
### H92. The name-duplicate gate looks at PRODUCT experts, not the agent's whole inventory

The chat's fail-closed gate stopped the release of the construction company's product, because
`/api/agent-experts` returned 30 duplicate names on the agent (374 unique out of
404). But the product's own catalog (19 business + 2 diagnostic) is clean and
unique — the 30 duplicates were unrelated historical clutter on the same agent.

**Measurement, 06 Sep 2026, on our healthy agent (Builder):** 380 records, 3
duplicate names, **342 records out of 380 without an `id`**. That is, duplicate names and records
without an addressable `id` are a **platform-wide condition**, present on every
agent, including ours. Demanding "zero duplicates across the whole agent" is meaningless and
unachievable: deletion requires an `id`, and most duplicates don't have one (canon
`docs/INCIDENT_KV_SCOPE_SHADOWING.md`, amendment "deletion works, but not for the
nameless").

**Rule.** The standard forbids duplicates because they make resolution non-deterministic — but this is about
experts that the product ITSELF calls. The duplicate gate checks
**the product's expert names** (its catalog), not the agent's whole inventory. If the
catalog is unique — the product's resolution is deterministic, and unrelated
historical duplicates don't stop the release (§4.5: "duplicates — a fact of life, going forward").
Want a fully clean inventory? Deploy the product to a fresh agent, rather than waiting
for surgery on undeletable platform records.

### H93. A sensitive user key (digital signature): automate the session, not the signature

The agroholding's task: the "Tax Radar" connector could only read the KGD Taxpayer
Cabinet within a live digital-signature session, and the client had to log in by hand every
day. The temptation was — "save the `.p12` file and password and log in ourselves."
A measurement on 09 Sep 2026 showed where the honest line runs.

**Rule.** A digital signature is a person's legal identity, so:

- **The session is automated, not the key.** The login signature is made by the
  standard National Certification Center component (NCALayer) through its own dialog — the person
  chooses the key and enters the password themselves; the product never sees them.
  The resulting session tokens are stored on the device (0600),
  reused and refreshed via refresh while they're alive. The person signs
  again only when the session has actually expired. This removes the daily login
  without adding a single new sensitive point.
- **The key and password never enter the product's perimeter** — not into a config file, not into KV, not
  into agent memory, not onto a server. A fully headless login (storing the `.p12`
  password) is a separate written decision by the key owner, on their own device, after checking
  it against the service's terms; by default, don't do it.
- **Only the login is signed, never documents.** Signing a nonce for
  authorization and signing an act are legally different actions; auto-signing a document is
  impossible by the expert's construction.
- **The key owner starts the live login themselves** (their own terminal/device): a request
  asserting their identity before a government system is their action, not the chat's.

This is the same principle as with the microphone and camera (H32,
`mic_record`, `camera_capture`): the device does what the window and the agent aren't allowed to, and only the
result goes outward. A live example is `experts/kgd_session.py`: the
knp.kgd.gov.kz protocol has been removed from the public bundle, and login by signature and reading
the profile with Bearer have been verified against a real key.

Two frequent mistakes along the way: openssl without a GOST engine **doesn't open the NUC
container at all** (`unsupported: digital envelope` — that is not "wrong password"),
NCALayer being the only carrier of GOST on the device; on connecting, NCALayer first sends a
greeting `{"result":{"version":…}}` — it has to be skipped, and the dialog waits for the human for
minutes, not seconds.

### H94. The runtime executes the FIRST top-level function in the file — keep helpers nested

Measurement from the Recruiter release (19 Aug 2026, FDE): the helper `def
_archive_from_bundle(...)`, which stood before `def rec_install_app(...)`, intercepted
the expert call — the runtime ran it instead of the function named after the expert, and it
failed with "got an unexpected keyword argument". That is, the runtime takes the **first
top-level function in the file**, not the one whose name equals the expert's name.

**Rule.** In an expert's file, the main function is the first and only one at the top
level; all helpers are **nested inside it** (the `rec_call`/`mic_record` style).
Any top-level `def` before the main one silently intercepts the call. Related to
H68/CSPL (the handler is a single entry point).

### H95. RU+EN bilingualism is mandatory for all apps — and it's checked by machine

Owner's decision, 15 Sep 2026: every app ships in **Russian and English at
once**, translating later doesn't count. Previously the rule "Russian and English at
once" lived only in the guide, but the `check_translation` gate treated English as
unnecessary (it stayed silent if there was no translation at all) — a promise without
enforcement.

**Rule.** The interface, explanations, and error texts are in two languages from the very
start, for all apps. A single-language app does not pass acceptance. The mechanism
already exists in the interface canon: an English original, with Russian behind a switch (or
the other way around), and a shared OS-window language switch.

**How it's checked.** `check_translation` now:
- a section with Russian text and no English → **red** (bilingualism is mandatory);
- a started translation must be **complete** (missing for some sections → red);
- a **fingerprint of the Russian** is stored next to the translation; the Russian changed, but
  the fingerprint is stale → the translation has fallen behind → red;
- a translation that points to a different file/anchor while the fingerprint is fresh is caught too.
Fingerprints are stamped by `check_translation.py --отпечатки <file>` after translating,
not beforehand — a fingerprint without a translation guards nothing.

### H99. ZERO IS THE ASSERTION "THIS IS EMPTY," NOT "I DON'T KNOW"

**Source: the 1C Agent chat, interview 21 Sep 2026. It named this the one prohibition
it would put into the canon for all Extella products.**

**Measurement.** The "Debts by Age" screen showed a total of **16,492,475 ₸** and next to it four zero
buckets by age. Everything was computed correctly: the settlement document isn't filled in in the
database, so there's nowhere to get the age from. Next to it stood the caption "older than 90
days — no."

**Cost.** The person sees real money and zeros and decides the product is broken. And "older than 90 days —
no" is **a flat-out lie**: when the age is unknown, there is nothing to assert. An
accountant who believes such a phrase won't go dig into overdue receivables. This isn't
cosmetic, it's the cost of a decision.

**Rule.** It is forbidden to show a computed value where there was nothing to compute it
from, and it is forbidden to state a negation about something the product didn't check. Didn't
compute it — state the amount and the reason in words, remove the empty breakdowns, don't
phrase a negation. Here's how it sounds in production:

> There's nothing to break down by age: 16,492,475 ₸. For not a single amount does 1C store
> a settlement document — either "settlements by document" isn't enabled in the contract card, or the
> debt was carried over during the move to 1C. The total and the breakdown by counterparty are correct, there's
> nothing to compute the age from.

**Check for any new screen:** what will it show if the client doesn't have the needed field.
The answer "zeros" — redo it. Lock it in with a test, not a reminder note: reminder notes are forgotten
at the very first rushed release.

### H100. ROUTE BEFORE RENDER: THE LOCAL ROUTE FIRST, A DEAD ONE IS REMEMBERED

**Source: the 1C Agent chat, live test-stand measurements, 21 Sep 2026.**

**Measurement.** Opening the window with no direct route — **46–59 s** to the first screen, with a direct
route — **13 s**. A single database read through the platform — **11.5–12.0
s**, over the direct route — **fractions of a second**. The 1.78 MB size of the built page as a
single file **was not the problem**: the seconds lived in the network, not in
parsing.

**Cost.** The wrong thing got optimized. The main source of delay turned out to be the route: the
panel went to 1C through the platform even when the window was open on the same computer where 1C is
installed.

**Rule.** Before optimizing the render — **measure which route the request takes**.
If the product can work locally, the local path is tried first, and the result is visible to the
person ("1C connected · directly"). Four mandatory consequences, each from the
measurement:

* **a failed attempt is remembered**: a route that didn't answer twice is set aside for 10 minutes,
  otherwise on someone else's computer every read spends time on a known-dead attempt;
* **a fresh port isn't re-queried** (learned less than 60 s ago — taken as is);
* **bootstrap isn't requested twice at startup** — two races doubled the time
  to the first screen;
* **no copies and no reconnecting on every call**: a session with a queue instead
  of a process per request gave 0.1 s instead of seconds.

### H101. A PRODUCT MUST HAVE A WORKING STATE WITH NO EXTERNAL DEPENDENCIES

**Source: the 1C Agent chat. This is its answer to the white screen — an affliction that
half the products in the storefront suffer from (census 19–20 Sep 2026).**

**Cost.** A white screen instead of an interface isn't caught by script parsing, nor by contract
tests: the crash happens on the very first access to an incomplete data snapshot.

**Rule — five requirements, all from real breakages:**

1. **A splash screen from the first frame.** Before the device responds, the data panel has
   no data at all; without a splash screen, the person sees a bare shell. Show
   exactly what's happening: "Opening your cabinet."
2. **The snapshot is always treated as incomplete.** The panel comes up BEFORE the device's
   confirmation; the first response arrives without settings and without a list of databases — every
   access must tolerate missing fields.
3. **No connection isn't empty — it's built-in data.** The product carries a demo slice and
   opens on it, with an honest caption in the footer, "training database · your own 1C isn't
   connected." **Absence of a connection is a state, not a refusal.** The demo slice
   must cover ALL blocks of the screen: for them, one block said "connect a database"
   while the neighboring ones showed numbers, and half the screen looked broken.
4. **Absence of the external system is an answer, not an exception.** `discover_bases`
   returns an empty list and a hint, rather than throwing an error.
5. **The OS window must not be reloaded from the page** ([[extella-os-window-reload-kills]]): the
   page is only served with a token in the header, and a `reload` on 401 kills the window for good.
   And remember that the window is a sandbox with no origin (`Origin: null`), any external
   `fetch` gives "Failed to fetch" with no explanation.

**The form of any refusal:** what happened → why → what to do. The person never sees an
error code, the code goes into the log. Verbatim from production:

> The computer with 1C isn't responding right now. Wake up the Windows computer and check that Extella
> is running on it (Start), then try again.

Separately, the technique "the screen states what it can't verify" reduces anxiety: "the
counterparty's BIN isn't filled in in 1C — can't verify" instead of a silent guess.

### H102. ROLLOUT: FULL RUN, FINGERPRINT CHECK, CLEAN STATE

**Source: the 1C Agent chat, an eleven-step release ritual.**

**Measurement and cost.** A full run is **1145 tests**, not the "affected" ones: half the
defects were caught in unrelated files. Editing the source during the run drifted apart
from the build — the page hash didn't match.

**Rule.** Before the rollout, three things are mandatory:

* **a full test run**, not a selective one;
* **storefront verification**: print the line "the archive and installer carry `<hash>`" — without
  it a version ends up in the store that doesn't match what was built;
* **a clean repository state after the build**: don't touch the sources during the run.

Two recurring platform quirks that need to be built into the rollout script: publishing a
version sometimes drops out on a timeout (retry the step in a loop until confirmed), and
deleting the previous version returns **409** if someone has it installed.

### H103. BREAKAGES NOT VISIBLE ON THE DEVELOPER'S MACHINE

**Source: the 1C Agent chat. Each one cost a session or a release.**

* **The built page is a template.** It contains `__THIN_INIT_JSON__`, the substitution is made on
  delivery. Opened directly as a file, the page fails with a syntax error and **silently
  falls back to the training database** — the author was recording a video, convinced they were
  working with the production one.
* **A trailing end-of-line comment eats the code after it.** An added `//` explanation
  swallowed a function call: the syntax stayed intact, the tests stayed green, the write goes
  through, the screen stays silent. The person clicks a second time and gets a refusal where
  everything had actually worked.
* **A new package file, not added to the delivery list,** works for the author and fails for
  the client on import. Guard the delivery contents with a test.
* **"Optional" in an external service's description doesn't mean optional.** Two fields of
  ИС ЭСФ are marked `minOccurs="0"`, the production system requires them. This is only discovered
  through a live refusal.
* **The set of required fields for saving and for posting differ.** 1C accepted the
  document for saving and refused to post it. **You must check with the final action**,
  not an intermediate one.
* **Black console windows on Windows.** You need `CREATE_NO_WINDOW` TOGETHER WITH
  `DETACHED_PROCESS`, otherwise the process has no console and every child opens its own window.
  And the flag must be exactly **`0x08000000`**, not `0x00000008` — the typo cost
  frightening windows for the user.
  *Verified by the canon keeper on 21 Sep 2026: `CREATE_NO_WINDOW = 0x08000000`,
  `DETACHED_PROCESS = 0x00000008` — these are different flags, the correction is right.* Keep nearby
  `CREATE_BREAKAWAY_FROM_JOB = 0x01000000`: without it, a process launched inside a
  job (an ssh session, part of the services) dies together with its parent ([[H98]]).


### H104. HOW TO TELL A DEAD DEVICE FROM SOMEONE ELSE'S: TWO PLATFORM RESPONSES

**THE CAUSE WAS FOUND ON 24 SEP 2026 — IT'S THE KEY, NOT THE ACCOUNT.** The listener decrypts the
expert's code with a key derived from the device's PIN: in `extella_listener/listener.py` the
key is computed as `sha1(PIN)` and passed as the `--crypto-key` parameter. If the key is
wrong, undecrypted garbage arrives on the device, and Python reports it as a **syntax
error on the first line of the container**.

The probe that proves this (one line, reproducible by anyone): run any working expert on
**your own healthy** machine, passing a deliberately wrong `pin`.

| run on `24f37e45…` (owner's Mac, answered a second ago) | result |
|---|---|
| without `pin` | `{'status': 'success', 'host': 'Anvars-MacBook-Pro.local'}` |
| `pin: "0000"` (wrong) | `[Execution Error] invalid decimal literal (<container>, line 1)` |

**From this, the correct phrasing of the symptom:** the error means "**the code failed to
decrypt on the device**." Someone else's account is just one of the causes (there, the listener
runs with a different PIN), the others: a wrong `pin` was passed in the call, the listener was
launched with a different `--crypto-key`, the device was re-registered but the key stayed the old
one.

**What to check, in order:** the call's key (whether `pin` was passed and whether it's the
right one), the listener's key (with what `--crypto-key` it was launched), and only then the
account. The earlier edition below is correct on the facts, but named the account as the cause
— read it with this correction.


**Control measurement, 21 Sep 2026.** The same four-line probe was sent with an explicit
`targets=[device_id]` to three devices:

| device | response |
|---|---|
| removed the day before | **HTTP 500** `{"message": "Target … is unavailable"}` |
| a fully made-up id | **HTTP 500** `{"message": "Target … is unavailable"}` |
| alive, but on someone else's account | **HTTP 200** + `[Execution Error] invalid decimal literal (<container>, line 1)` |

**Rule — the discriminator that saves you a day:**

* **HTTP 500 "Target … is unavailable"** — the device doesn't exist, it's removed or
  offline.
* **HTTP 200 with a syntax error on the first line of the container** — the device is **alive
  and responding**, but belongs to a different account: the job arrives, the expert's code
  arrives undecrypted. The error text **drifts** between runs of the same code
  (`invalid decimal literal`, `cannot assign to expression`, `invalid syntax`,
  `leading zeros…`) — real syntax doesn't behave like that.

**A price paid twice.** On this same signature, the Schemes Board chat lost hours, and the canon
keeper — two days and a remote server: they went through Cyrillic in identifiers, the expert
format, the listener version with SHA-256 package verification, the number of listeners,
the encryption key, device re-registration — all on a healthy machine.

**What NOT to do with an empty `targets/list`.** An empty `results` is not a sign that the
record is absent: the list is **scoped** to the agent. Measurement, 20 Sep 2026:
`/api/targets/list` with `X-Agent-Id` returned `results: []` on an account where, in the
same minute, an account-wide search showed five live targets. You have to check with a probe using
an explicit `targets`, not with the list.

**Re-binding the listener to another account has no standard method** (verified 17 Sep and
21 Sep): logging into the app window doesn't carry the listener along, it authorizes with its own
token separately. The working path is to work from the account where the listener lives. Changing
`device_id` isn't free: the store binds the app to the device of its first install
([[§45]]).

### H105. JAVA WINDOWS (NCALayer) ARE DRIVEN BY KEYBOARD, NOT MOUSE. THE PASSWORD — ONLY AFTER CHECKING THE WINDOW

**The origin of this rule matters for trust.** The measurements were made by a colleague on their
own machine, the explanation was given by the 1C Agent chat, **the canon keeper did not
reproduce this**. The 1C chat stated outright that it never touched the window with its own hands: in
the 1C Agent it went a different way — through the **NCALayer protocol**, not through the
interface. Confirm the points below on your own machine before adopting them.

**Measurement (colleague).** The NCALayer 1.4 window is drawn in Java (Swing). Such a window has
**one real Windows window** — the frame; the buttons and fields inside are drawn by Java on
a canvas, and as far as the system is concerned they don't exist. Hence three observations:

* a click on the button's coordinates **misses** — the coordinates are taken from something that
  doesn't exist in the system, and at 150% screen scaling logical coordinates diverge from physical ones
  by a factor of one and a half;
* calling the UI Automation pattern (`invoke`) **returns success and does nothing** — the
  system hands back a stub that formally has the pattern;
* **`Enter` after `set_focus` works** — the keyboard is the only channel that honestly
  crosses the Java boundary: the keypress goes into the window, and from there Java's own focus system
  handles it.

**Cost.** Empty signatures with no error message: the automation "completed successfully," the
document isn't signed. A silent success is the most expensive kind of refusal, no green test
catches it.

**Rule:**

1. **Drive it with the keyboard.** Find the top-level window, set focus, then use only
   `Tab`, arrows, space, `Enter`. No coordinates and no UI Automation patterns.
2. **Wait for the window, don't assume.** Java windows appear before they're ready to accept
   input: wait for a stable indicator → pause → focus → **confirm the window is
   frontmost** → only now send keys.
3. **Branch on the window, not on the script.** NCALayer has two kinds of window (the long
   one with the password and the short "Sign" one) — there can be no fixed key sequence. The
   distinguishing signal (title, class, size) must be **measured on your own setup**, it's
   version-dependent.
4. **The process must declare itself DPI-aware**, otherwise both the coordinates and the
   "did we land in the window" checks lie.

**THE UNCONDITIONAL REQUIREMENT ABOUT THE PASSWORD — not optional.** Focus in Windows can be
stolen by anything: a notification, an antivirus, another program, the person themselves. If at
that moment the robot is typing the digital-signature password, the password goes **into whatever
window happened to be frontmost** — a chat, a document, a search field — and stays there in
the history.

So **immediately before typing the password, get the frontmost window's handle again and
compare it against the target; if it doesn't match — abort and type nothing.** The check is
mandatory, it cannot be disabled.

**And the architectural conclusion, worth more than all four points combined:** if an external
program has a **protocol**, work through the protocol, not through its window. The 1C Agent did
exactly that and got none of these breakages at all. Automating someone else's interface is a
last resort, and for signing a document it's better not to use it at all: the person places the
signature.

### H96. ACCEPTANCE ON WINDOWS — ON x86-64. THE ARM VM HAS WORKED SINCE 20 SEP (correction below)

**Measurement, 20–21 Aug 2026, from device logs.** A Windows test stand in Parallels on an
Apple silicon Mac is Windows-on-ARM. The `extella-listener` package has no `win_arm64`
wheel (there's `win_amd64`, `manylinux`, `macos_arm64`; no sdist is published). The
app's built-in `uv` resolves the platform as `win_arm64` → "no wheels with a matching
platform tag" → the listener fails five times in a row → the device is stuck forever at
"Target unavailable." For users on Windows x86-64 — the wheel exists there and everything
installs.

**Cost:** the test stand was down from 20 Aug, an hour spent parsing logs, the false
conclusion "it broke after the app update."

**CORRECTION, 20 Sep 2026: the rule is outdated, ARM works.** A measurement today on the
owner's same ARM VM (Parallels, Apple silicon): an expert sent by the platform ran
and returned `{'system': 'Windows', 'release': '11', 'arch': 'ARM64',
'python': '3.12.7', 'encoding': 'utf-8'}`. That is, the listener installs and works on
Windows-on-ARM natively — either the `win_arm64` wheel appeared, or it's built from source.
We're lifting the ban on ARM; x86-64 remains preferred for acceptance only because
it's the buyer's mass-market platform, not because ARM "lies."

**Rule (21 Aug edition, before the correction; the part about a "false red" is outdated).** Acceptance testing "will it install for someone else" on Windows is done only on an x86-64 machine
(VPS or bare metal). The ARM VM on a Mac gives a false red from the platform and never gives a
green at all. The ARM workaround (x64 CPython + `UV_PYTHON_PREFERENCE=only-system`) —
only for your own work, not for acceptance: it verifies our workaround, not the buyer's machine.
The owner of the wheel fix is the tech department (`report_issue` sent 21 Aug).

### H97. AGENT/CREATE: THE USER IS TAKEN FROM THE TOKEN, NOT FROM THE BODY

**Measurement (September 2026, public core).** `POST /api/agent/create` with a minimal
body responds `422` and asks only for `provider` and `model` — there's no `user_id` field in
the body at all, the agent's owner is derived from the token. A token with no user
(global/service) passes verification and can read, but on create it responds
`401 Authentication required (user_id missing)` — a measurement from a client (the car dealer, global
token "am-deploy"); the same error as in H30 for a POST from an expert, matches
our measurement.

**Rule.** Agents are created by a user's personal token (from the OS/account). With a service
and global token — read and run. Don't build agent creation with a global token
into the installer: for the buyer this will fail with `user_id missing`, and that's not a
platform breakage, it's the wrong class of token.

### H98. THE DELIVERY SET MUST BE CONSISTENT: archive ⇄ installer ⇄ install.py at the root

**Census of the live storefront, 18 Sep 2026 (50 products, version composition from the store
API).** Four products can't be installed at all, and not one of them reports it; the buyer
sees only "The installer did not finish" with no reason:

| Problem | How many | Example |
|---|---|---|
| archive exists, no `installer_expert` | 3 | Development on Extella (13 downloads), Personal Assistant (6), Lawyer (1) |
| `installer_expert` exists, no archive | 1 | Recruiter (8 downloads) |
| neither a page nor an archive | 2 | Discussion Agent, Мияу |

**Cost: 28 downloads went into products that could not install.**

**Rule — four conditions, each from its own breakage.**

1. **An archive is declared — an `installer_expert` is mandatory.** Otherwise the platform has
   no one to call (Human Atlas: the page exists, a 32 MB archive exists, `device.run`
   permissions are requested, there's no installer).
2. **An installer is declared — an archive is mandatory.** There's someone to call, but nothing to
   deploy.
3. **`install.py` sits at the ROOT of the archive** (a reinforcement of B1). Lawyer has
   it — but one level deeper, inside an extra product folder. The installer can't find it, and
   no expert can work around this: the archive needs to be rebuilt.
4. **`install.py` isn't nailed to a single OS.** Human Atlas called `launchctl` with no
   branching and failed on Linux with `No such file or directory: 'launchctl'` — the product could
   only install on a Mac. Caught by the fact that Mac-specific calls exist, but
   `sys.platform`/`platform.system`/`os.name` don't.

**And the main consequence, verified live on three systems: autostart doesn't decide the fate of
the install.** If the machine won't let you register a service (service accounts and
containers have no session), the installer must lay out the files, start the server, and
PRINT the launch command — not fail. Measurement, 18 Sep 2026: with this branch,
Human Atlas came up and answered `{"ok": true}` both on Linux (VPS) and on Windows
(test stand), where it used to die before.

**Capabilities (`kind: source`) don't fall under this rule** — they never have a page or a
per-device archive. The first edition of the gate gave five false reds on them; a false red
is just as harmful as a miss, because a gate that lies gets disabled entirely.

**Machine check:** `tools/check_installable.py <product folder>` — in the general run and at the
publication stage.

### H106. THE OS PAGE CALLS THE EXPERT VIA APP_TOKEN, NOT VIA THE TOOLBAR BRIDGE

**Live measurement, 22 Sep 2026, in a real Extella OS window through the debug port**
(independently by two performers: the canon keeper and the Codex chat). In
`desktop.*.js` there's no handler for `etb_run_expert`; `etb_init` carries only
`{theme, lang}`; the page's frame has `origin: null`, so a call to
`parent.extellaDesktop` ends in `SecurityError`. The `etb_*` protocol belonged to the toolbar
retired on 12 Aug. A page built on it looks intact, but its buttons
can't call the expert.

**Working contract (checked against the 1C Agent and Recruiter):**

1. Declare `{{app_token}}` in `index.html`. Don't request the full `{{token}}`.
2. Make all calls as `POST https://os.extella.ai/api/app-agent/run` with the body
   `{app_token, expert_name, params, targets?}`. No messages to the parent
   window and no reading its JavaScript API.
3. Send the first call to the dispatcher expert **without `targets`**. From the response take
   `pageRoute.targetId`; the fallback is `device`/`device_id` in the transport envelope.
4. Send all subsequent calls with `targets: [the device received]`. If the
   first response doesn't contain a device, show the person the specific reason and
   keep a retry available.
5. Request the `expert.run` and `device.run` permissions. Respect the channel's limits:
   30 calls per 60 seconds, a body up to 64 KB, an app-token TTL of two hours
   (refreshed by reloading the window), a synchronous terminal response per H54.

**A temporary workaround for §46 until the platform's device selection is fixed.** If
the first call without `targets` returned `[Execution Error] ... (<container>, line 1)`, this
is the H104 signature: the platform picked a computer whose listener is logged into a different
account. The app must explain this in words, show a Device ID field and a "Work through this
device" button, then check the dispatcher with an explicit `targets: [device_id]`. The
Device ID is kept only in the open window's memory: `localStorage` throws `SecurityError` in the
sandbox, so on the next opening the person enters it again. Don't show the field on other errors.
This path was adopted in the 1C Agent's live window, 1.66.0, and re-verified by the H106
pre-release on 22 Sep 2026.

**Machine guard.** The `tools/new_product.py --page` generator and the `templates/app-recipe`
recipe must contain `{{app_token}}` and `app-agent/run`, and the generated page must not
contain `etb_run_expert` or `parent.extellaDesktop`. The gate must reference the
number `H106`, otherwise the rule doesn't count as covered.

**Acceptance.** Only a real OS window: closed pre-release → desktop shortcut →
the first call returned the id of an open device → the second call with that id returned the name of
the same machine. A simulated test stand and a direct HTTP request are useful before release, but
they don't replace this acceptance test.

**Measurement from inside the window's frame:**

| What was checked | Result |
|---|---|
| `etb_init` from the OS | only `{theme, lang}` — no device |
| the `etb_run_expert` handler in the OS build (`desktop.*.js`) | **0 mentions** — the call goes nowhere |
| `getDeviceID` in the OS build | 0 mentions |
| the app window's frame | sandboxed, `origin = null` |
| `parent.extellaDesktop` from the frame | **SecurityError** — the browser blocks it |
| the OS desktop itself | `extellaDesktop.getDeviceID()` exists, returns a UUID — but is unavailable to the app window |

**The first call without `targets` — where it goes.** Measurement, 22 Sep, in a probe window
(listing `40cf6ccf…`, expert `h106probe_where`, the same `app_token`):

| `targets` | result |
|---|---|
| none | `invalid decimal literal (<container>, line 1)` |
| `39f81469…` ("Windows with 1C", listener logged into a different account) | the same error, verbatim |
| `85800354…` (VPS) | success, `host: extella-team` |
| `24f37e45…` (Mac) | success, `host: Anvars-MacBook-Pro.local` |

This is the H104 signature — a computer from someone else's account, not a cloud runtime: the
account's own code would have executed in the cloud. The platform sends the call unpinned to
a machine where it can't be executed (the CTO's letter, §46). The recipe's bridge translates this
signature into a reason stated in words; "Extella didn't report the device, restart" is wrong
here.

**A correction to our own mistake.** On the morning of 22 Sep, the canon keeper wrote here "a
second path — `parent.extellaDesktop.getDeviceID()`," having verified it on a simulated test
stand. In a real window, this path is closed by the sandbox. The lesson is the same as H104: **a
simulated test stand proves the logic, but not the environment** — a rule about the
environment is only accepted after a probe in a real window.

**Verified in a real window** (the recipe's bridge deployed into a real frame, the real
platform): device known → success in 9.5 s, the call pinned; device unknown → a reason
stated in words; a remembered device disappeared → forgotten, one retry. Guard:
`templates/app-recipe/tools/check.py` (comments don't count, permissions, presence of experts
in the delivery) and `tools/new_product.py --selftest`.
### H107. DEVICES AND RECORDS ABOUT THEM: WHO PICKS THE MACHINE, WHEN, AND WHAT DETERMINES IT

**Measurements 24 Sep 2026, live account, probe expert `wz_ping` (returns the machine's name).**
This section answers a question that until now was settled by guesswork: why the work
goes to the wrong place.

**Two different objects, and confusing them is costly.**

* **Device** — the machine itself. The identifier is born at the listener
  (`~/.extella/device.txt`), visible in the app's status line and in
  `Library → System → Devices`.
* **Target record** (`target`) — a named reference to a device inside a scope:
  `add_target {device_id, description, global}`. One device can have several records
  (the owner's Mac is named by three: "work listener", "live listener",
  "Predictive Sales buyer's device").

**Calls take DEVICE identifiers, not record identifiers.** Measurement: `targets` with
the `target_id` of the Mac's record (`efe19380…`) → `Target efe19380… is unavailable`,
even though the machine is on and running. The error lies: this isn't "unavailable",
it's "wrong kind of identifier".

**How the platform picks the machine — by call path:**

| Who calls | What determines the machine | Measurement |
|---|---|---|
| `run_expert` / `/api/expert/run` with `targets` | a list of **candidates in order**, the first available one is taken | `[VPS, Mac]` → VPS; `[Mac, VPS]` → Mac; `[dead, VPS]` → VPS with no error; `[dead]` → `Target … is unavailable` |
| the same call **without** `targets` | the account's default device | before the default was changed → VPS, after switching to the Mac → Mac |
| a product page via `app-agent/run` without `targets` | **the platform's own choice, and it differed from the default**: on 22 Sep the default was VPS, but the call went to someone else's machine (§46 of the letter); on 24 Sep — to the Mac | the platform does not document the selection rule |
| an agent, when it calls an expert itself | **there is nothing to pin with**: `run_agent` has no `targets` parameter | the agent decides on its own; hence "works for me, doesn't work for my colleague" |

**THE DEFAULT — EACH AGENT HAS ITS OWN (measurement 25 Sep 2026, closes an open question
from H107).** `/api/defaults/get_target` asked with different `X-Agent-Id` values on one
account:

| agent | its default machine |
|---|---|
| `agent_extella_default` | VPS `85800354…` |
| the 1C Agent's agent (`agent_9Oig…`) | Mac `24f37e45…` |
| the guide-app's agent (`agent_HiSO…`) | Mac `24f37e45…` |

This explains the case in §46 of the letter: a page call without `targets` went not to
the "account default" device, but to the default of **that app's own agent** — which at
the time was a machine from a different account. There was no randomness in the choice.

**And the default shifts under you.** Measurement from the same day: on 24 Sep the
`agent_extella_default` default pointed to the Mac (verified both by request and by a
run), on 25 Sep — back to the VPS. Several chats work in the account, and any of them
can switch it. That's why rule 3 below isn't nitpicking: **a product that needs a
specific machine must name it itself**.

**Scopes.** Records are scoped the same way experts and keys are: `search_targets`
without `global` returned 3 records, with `global: true` — 8. So some targets are
visible only within the agent's scope, and some to the whole account. **The default is
set with `set_default_target {device_id}`** — per account; in the UI,
`Library → System → Devices → Change default`.

**The rules that follow from this.**

1. **Always pin, and pin with an array.** An installed storefront reads a single
   `target` field, the sources do not; the canon is `targets: [device_id]` (with
   `target` as a string alongside it, when the message format allows it).
2. **The list is a reservation, not "wherever."** Order matters; put the machine
   holding the data first, and a fallback second, if the work doesn't depend on the
   machine.
3. **Don't rely on the default.** It is one per account, changes with a single click,
   and differs across call paths. A product that needs a specific machine must name it.
4. **An agent's work cannot be pinned** — if a task must run on a specific machine, an
   expert with `targets` performs it, not "an agent that goes and does it itself."
5. **`Target … is unavailable` means three different things:** the machine is off; a
   record identifier was passed instead of a device identifier; the device was deleted.
   Check the kind of identifier first — that costs nothing.
6. **A machine from a different account responds not with a refusal but with a syntax
   error** — H104.

**Account hygiene.** Records pile up: the owner had seven records for three live
machines, including a dead one (`11b0c773…`, re-registered 30 Jul) and someone else's
(`39f81469…`, a listener on a different account). Dead records aren't harmless: while
such a record is alive, the platform can pick it for an unpinned call. Cleanup —
`Library → System → Devices`, the "…" menu on the card (appears on hover); `delete_target`
via the API didn't work on every record (§49 of the letter).

### H108. CONNECTING A CHAT AGENT (Claude, Codex) ON A NEW MACHINE IS DONE, NOT EXPLAINED

**Measurement 24 Sep 2026, Extella app 1.3.0.** The app build has not a single mention
of `api_token`, `token.txt` or `~/.extella/` — **the key is not put on disk on any
system**. So on every new computer the chat agent is left without a key. The price is
known: colleagues who moved to new machines all got stuck at once, while our own
installer advised "run the app once — the key will appear by itself," which does not
happen.

**Rule. The product and the agent must close this themselves, in this order:**

1. **Do it.** The `experts/dev_connect_assistant.py` expert is run on the needed machine
   (`targets: [device_id]`): the platform passes it the key, it writes the key to
   `~/.extella/api_token.txt` with `600` permissions via a temp file, **verifies it with
   a live call**, and returns only the path and a fingerprint. The key's value is never
   returned and never lands in the log. Live probe on 24 Sep:
   `{"подключено": true, "ответ": "HTTP 200"}`.
2. **Say it in one action, if it can't be done.** The platform does not always pass the
   key (H5, amendment 17 Aug). Then the person is told exactly one step: in the app,
   `Library → System → Tokens`, create a token and save it to the same file, or pass it
   via the `EXTELLA_API_TOKEN` variable. No "go look for the key somewhere."
3. **Verify by fact, not by the file's presence.** A dead key in the file looks like a
   connection and breaks later. Verification is by calling a reading tool; the
   `initialize` handshake passes with any string in place of a key (amendment of
   28 Sep 2026, H81).
4. **The key is never forwarded.** Not into chat, not to a colleague, not into a ticket:
   it gives full access to the account, up to deleting the agent. Every machine and
   every person has its own key.

**Where this already lives:** the expert — in `experts/`, the step in the connection
installer — `tools/connect_mcp.py` (its refusal leads to the tokens screen), the
"Assistant on a new machine" section — in the "Development on Extella" app
(`store_app/content.json`, RU+EN), onboarding for external chat agents —
`EXTELLA_AI_ONBOARDING.md`.

**A request to the platform** — §32 of the letter: put the key in place at login, or
give a "connect assistant" button. Until it exists, the rule above is our workaround.

### H109. THE KEY FOR THE STORE AND FOR THE CORE IS THE SAME ONE, ONLY THE HEADERS DIFFER

**Measurement 24 Sep 2026** after reviewing someone else's chat, which got stuck on
this. The same `GET /api/my-listings` on `os.extella.ai`:

| what we knock with | response |
|---|---|
| the core key (`~/.extella/api_token.txt`) in the `X-Extella-Token` header | **HTTP 200** |
| the key from `~/.extella/os_token.txt` in the same header | HTTP 200 |
| the core key in the `X-Auth-Token` header | **401 "X-Extella-Token header required"** |

The values of the two keys on the machine are different, but the store accepts both:
what matters is the **header**, not the source file. The core, conversely, requires
`X-Auth-Token` — hence the confusion.

**Rule.** Do not declare publication impossible for lack of `os_token.txt`. The order
is: take any valid account key (a file on disk, the `EXTELLA_API_TOKEN` variable, or one
a person created in `Library → System → Tokens`), address the store with the
`X-Extella-Token` header, the core with `X-Auth-Token`. Verify by fact:
`GET /api/my-listings` on `os.extella.ai`.

**The price of the earlier misconception — the client's paid-for learning.** An
external chat read in our own runbook that "the personal OS token lives in
`~/.extella/os_token.txt`," got a ban on that file from the client, and declared: "the
GUI app is running into a platform limitation, publication is impossible." There was no
limitation: the client had the key, what was missing was the line about the header.
Four days of work went into correspondence and reaching out to developers.

**What else stopped the same chat** (each one a fact from our canon that it did not
find): it judged the expert call from a page via `{{app_token}}` and `app-agent/run`
(H5-bis, H106) to be "not documented in the public `api.html`"; a deferred run returned
HTTP 500 while the work had completed (H54: `running` is not a result, wait for
`check_task`); it tried to pass a 1.56 MB file in a single call (the body limit is 64 KB
— read it on the device or hand it over in chunks). **Conclusion for the canon: the
public `api.html` is not the source of truth.** The source is this compendium and the
runbooks; say so to external chats from the very first line.

### H110. A BAN LIVING IN ONE FILE'S SELF-CHECK DOES NOT CLOSE THE REPOSITORY

**Measurement 24 Sep 2026, continuation of H108.** The wrong advice "open the app — the
key will appear by itself" was banned by the `tools/connect_mcp.py` self-check: it
fails if this text shows up **in its own refusal**. The ban was considered closed. A
repository-wide search found the same advice in three more places a person sees: the
rollout refusal in `store_app/update.py`, both manifest templates in
`tools/new_product.py` (meaning it was copied into **every new product**), and the
"before — after" table in `INSTALLER_CANON.md`, where the wrong phrase stood in the
"after" column — as a model to follow.

Separately: the single entry point `README.md` carried the same promise, because the
H108 fix never touched it. The "one source" rule guards against a second entry point,
but not against the one entry point going stale.

**Rule.** Banning a piece of text means searching the whole repository, not checking
one line. Implemented in `tools/check_assistant_onboarding.py`: the promise is searched
for across all `.md/.py/.json/.html/.txt/.sh` files, narrowed by key-related words
(otherwise a truthful line about an agent that comes up after deployment with no
hands-on step gives a false positive), and **allowed only next to a refutation** — the
wrong advice may be quoted only where it is said to be wrong. The gate skips its own
file: that's where the samples themselves live.

**Check the same way** any rule phrased as "we no longer write it that way": until it
has a tree-wide search, it is closed in one file only.

### H111. TRANSLATION FRESHNESS IS CHECKED IN BOTH DIRECTIONS

**Measurement 24 Sep 2026.** I made the fix about where the key comes from in the
English body of the section and **did not make it in the Russian one**.
`check_translation` only kept a fingerprint of the Russian text: the Russian hadn't
changed, the fingerprint matched, the gate was green. Two different guides under one
name went into the assembled page — the Russian one lied, the English one told the
truth. Caught by eye when checking the assembled page, not by a machine.

**Rule.** Two fingerprints are kept alongside a translation: one for the original and
one for the translation itself. If the Russian changed — the translation has fallen
behind; if the English changed without the fingerprints being rebuilt — the translation
has run ahead. A translation with no fingerprint of its own is declared unprotected: it
can be edited on its own.

**The class is broader than translation.** A one-way agreement check between two copies
does not see divergence in the other direction. Wherever two copies must match, a
fingerprint is needed on both.

### H112. THE AGENT'S ENTRY POINT AND THE HUMAN'S APP DO NOT DRIFT APART

**Measurement 25 Sep 2026.** One workflow is described twice, for two different
readers: the chat agent reads `AGENT_START.md`, a person reads the "Development on
Extella" app. Pairs like this drift apart silently, and always the same way: whoever is
editing fixes whatever is at hand. The price was measured on the client's paid work —
two external chats got stuck on facts that were present in one place and missing in the
other.

The same day also turned up a direct consequence: in the app's English text the expert
was named `dev_connect_agent`, in the Russian one — `dev_connect_assistant`. No expert
exists under the first name; an English-reading user got "Expert not found." The
translation fingerprints matched, the file names matched, and the check stayed silent —
it only compared file names and links.

**Rule.**

1. The app's section on pitfalls declares the list of rules it covers
   (`правила_входа`). Every rule from the pitfalls section must be in that list at the
   entry point. The reverse is not required: the app is allowed to say more.
2. The prompt in the app leads to the same entry point (`AGENT_START.md`), gives raw
   links, and states outright that the public reference `api.html` is not the source of
   truth.
3. **Expert and module names are translation anchors.** They may not be translated "by
   meaning"; they are checked on a par with file names and links.
4. **A retelling leads to the source.** An app section that repeats the entry point must
   give the entry point's raw address: a retelling goes stale before the source does,
   and getting to the source must take one step, not a search. The canon keeper's
   formulation: the fewer copies, the less work for the check.

This is held by `tools/check_entry_app_agreement.py` and the extended anchors in
`tools/check_translation.py`.

**A second copy of the prompt was removed along the way.** It lived both in
`content.json` and as an array of strings in the page template; the copies drifted
apart twice (H81, H110). Now the button reads the same section a person sees on screen —
one source, and the text stays fresh straight from the repository without a page
rollout.

### H113. A NUMBER ABOUT ANOTHER FILE IS NEVER WRITTEN BY HAND

**Measurements 24–25 Sep 2026, four cases in one day.** "116 rules" at the entry point —
an hour later there were 118. "About 10 KB" for the table of contents — 16 KB in bytes.
"9 KB" for the entry point — 6.7 KB. And a fourth, found by the measurement itself:
`BUILD_STAGES.md`, `START_HERE.md`, `CONTRIBUTING.md`, and the "Development on Extella"
app promised «21 gates» in production and «29 checks» in CI, while the machine required
25 and ran 74. People were preparing a release from this text.

**Why it's caught not by the author but by a second reader.** The number describes
ANOTHER file. The author edits one file, the number sits in a different one, and at the
moment of editing it looks correct. Review is powerless here: the reader has the same
text in front of them, not the fact. All four cases were caught by someone other than
the writer.

**Distinguish three kinds of numbers:**

1. **A number about another file — don't write it.** Either a check computes it and
   verifies it against disk (file sizes — `check_file_size_claims`; check counts —
   `check_counted_claims`), or the text names a command instead of a number. The third
   legitimate way out is not to name the value at all, but to name a property instead:
   "large, take it in sections."
2. **A number about the outside world — date it.** There's nothing to recompute
   platform behavior with: "defers at the 51st second," "body up to 64 KB," "the call
   takes 13–17 seconds." Such a number lives with the date of the measurement and is
   refuted only by a new measurement.
3. **A number about what's right next to it — allowed.** "Four rules" above four bullet
   points gets edited in the same paragraph as the list, and doesn't silently go stale.

**Check narrowly.** The first edition of `check_counted_claims` gave four false alarms
out of seven — "not a single check," "self-check 10/10," "There is one check: close the
screen," "(21 checks)" about one tool's own self-check. A false alarm in a gate costs
more than a miss: people stop reading it. So the check also requires a subject —
whether the text is about the volume of a stage's checks or about what CI runs — and
keeps a control probe for each of these phrasings.

**And recheck the neighbors of a fixed line.** Having removed «2 gates» from
`START_HERE.md`, the same line still had «`prod` — 21» left in it: the pattern didn't
see a bare number with no word "gate" next to it. The gate has now been taught this form
too.

### H114. A GATE IS ACCEPTED ONLY AFTER A RUN AGAINST A LIVE SUBJECT

**Measurement 25 Sep 2026 across the whole set.** The `run` command in
`run_all_gates.sh` only runs `--selftest` — it asks the gate "are you working" against
hand-made probes. A live run is a separate line, and five repository gates didn't have
one. What that was hiding:

* `check_surface_classes` is **red on live data**: of 14 desktop cards, 11 have no
  declared class, plus the passport fails on three requirements. In the suite the gate
  had been green the whole time.
* `check_toolkit` **printed not a single line in 120 seconds**. The cause turned out not
  to be the gate: the response-shape check was calling a live local model (180-second
  timeout), and on a machine **without** the model it silently checked nothing —
  emptiness passed for success. Now the contract is checked by reading the code: 0.8
  seconds, and it always works.
* `check_agent_drift` returned 0 with the words "SKIPPED: no passports found": the
  subject is missing from the clone, and emptiness is reported as success.

**And five independent cases of the FIRST edition of a text-based gate lying on the
live tree almost every time:** `check_device_pinning` — 7 false alarms,
`check_file_size_claims` — 2, `check_counted_claims` — 4 out of 7 hits,
`check_surface_classes` in the first fix edition — 11 products at once (any divergence
between copies was declared a refusal, even though a working branch legitimately
differs from the canon), and the path check described in item 6 — 18 hits, all false.
None of these errors is visible on hand-made probes: the author writes probes to match
what they've already thought up.

**Rule.**

1. **A live run is proof of acceptance, and it is done where the subject lives.** A run
   that prints "skipped" doesn't count as proof.

   **"Where the subject lives" also means which clone is the live one.** Measurement 25
   Sep 2026: one product had seven clones on the machine, exactly one of them live. The
   gate took the first one alphabetically — a corpse from a dead branch; the fallback
   rule "look in `~/Documents/Extella`" picked another corpse, a clone from 12 August
   while the live one was from 25 September. Both times the gate judged confidently and
   wrongly. The live clone is determined by the **freshest HEAD**, not by name order or
   by directory convention; a declaration via the `passport:` line takes priority over
   both.

   **A run that found no subject is not acceptance, even if it ran against someone
   else's tree.** The first `check_gate_acceptance` run against the canon keeper's tree
   gave 0 out of 32 and zero false alarms — not because the gate is good, but because
   there wasn't a single acceptance line there. The second run, once the subject
   appeared, became the acceptance. Distinguish "checked against someone else's tree"
   from "checked against someone else's tree where the subject exists."
2. **Every false alarm from a live run becomes a permanent probe.** If there were few
   hits and all of them were false, the check is removed entirely rather than tweaked: a
   false alarm costs more than a miss, because a lying gate gets switched off along with
   whatever good it did.
3. **An acceptance line in the header, with a date.** The word ACCEPTANCE at the start
   of the line, a date, a colon, and what the run produced. The date is mandatory: a
   count of false alarms is a claim about a past measurement (H113). Backticks are
   excluded: otherwise a format example in the documentation counts as a fulfilled
   requirement — this check caught itself on exactly that, and computed 11.1% for
   itself instead of 8.3%.
4. **A gate that doesn't fit into a reasonable time doesn't live in the suite.** 600
   seconds for a subprocess means it will never be run.
5. **Per-product gates don't break the exception.** They need an argument — a product
   folder, a policy file, a repository address — `stage_gates` calls them with a
   target, and they have no live run in the general suite by design, not by oversight.
   There are thirteen of these out of twenty in the suite: before demanding one, tell
   the subject apart.
6. **A link, path, or locator is considered checked only once it has been OPENED**, not
   when it is syntactically correct. Two independent cases from 25 Sep 2026: the
   passport gate checks the shape of `binding_ref` and cannot check whether a file
   exists at that path — the author caught himself having written in a non-existent
   path, and did the right thing by CREATING the file rather than fixing the text.
   Second: the path existed but led to someone else's copy — one agent has six
   passports on the machine across different clones, the gate took the first one
   alphabetically (a copy on a dead branch) and delivered its verdict about that one,
   while the author was writing to a different one. The shape was correct, the subject
   was the wrong one. This is also where the requirement of item 1, "where the subject
   lives," comes from: a live run against the wrong copy is not proof.

   **There is no repository-wide check for this, and here is why.** It was tried:
   search texts for paths inside the repository and open each one. Of 167 paths, 18 did
   not open — and every single one turned out to be a false alarm. Texts legitimately
   reference neighboring repositories with ordinary relative paths
   (`docs/INCIDENT_KV_SCOPE_SHADOWING.md` is explicitly named as belonging to "the
   core-portal repository"), and the `templates/app-recipe/README.md` template
   describes the paths of a FUTURE product, not ours. There is nothing to tell these
   apart with by machine. Per item 2, the check was removed rather than tweaked. Making
   it possible requires a convention: a reference to another repository names that
   repository. Introducing that now is separate work.

   The place this rule actually checks is narrow and different: wherever a gate checks
   a SPECIFIC locator field (`binding_ref`, the path to a passport, the address of the
   canonical copy), it must open it, not just verify its shape. That is a per-product
   gate, not a repository-wide one.

Held by `tools/check_gate_acceptance.py` as a ratchet: the share of accepted gates can
only grow. There is deliberately no flag day — demanding an acceptance line from
everyone at once would mean making fifty edits that nobody will read, and turning
acceptance into a ritual.

### H115. REPOSITORY RAILS: FOUR CHECKS BEFORE THE COMMIT, NOT A CONVERSATION AFTERWARD

**Audit of four employees, 25 Sep 2026, 14 repositories, about 14,000 lines.** The same
result for all of them: in a repository with a written standard, a person works to the
standard; without one, they hand over a working but unprotected prototype. The price,
measured:

| what was found | where | cost |
|---|---|---|
| a full-access database key in a public repository since 08 Jul, valid until 2036 | a product for farmers | phone numbers, land plots, contracts; access codes hashed without salt |
| names and birth dates of 19 employees in a public repository | a congratulations bot | the bot itself appends the data on every command |
| anonymous access to our paid keys with no authorization | a demo agent | our model bill and the client's documents open to the world |
| a Python syntax error in production | an analytics backend | 3 commits out of 5 — fixing one bracket over 13 hours |

**Rule. A repository is considered set up once it has rails in place**
(`templates/repo-starter/pre-commit`, installed with one command):

1. **Syntax** — `py_compile`, `node --check`, parsing JSON before the commit.
2. **Secrets by shape, not by variable name** — JWTs, provider keys, bot tokens.
3. **Personal data — by TWO independent signals** (birth dates with values, distinct
   phone numbers, emails, national ID numbers), not by one.
4. **Build junk** — cache and compiled files.

**Plus three conditions that a machine cannot enforce:** the repository is private by
default; the key lives in an environment variable and nowhere else; everything that
ships to the buyer goes through someone else's read.

**A refusal is bypassed knowingly** (`--no-verify`) and names what and where: a ban that
can't be bypassed gets bypassed wholesale (the same argument as the designer's one in
the design gate).

**Measurement 26 Sep 2026: a live commit found three troubles in the rails themselves,
invisible to the self-check.** It's the same lesson as H114, but this time about our own
guard:

| trouble | what it looked like | why the self-check stayed silent |
|---|---|---|
| one signal instead of two | a form schema was blocked for having a `birth_date` field **with no data**, as was a file with three support phone numbers | the probes were only run on real lists of people |
| a file name in escaped form | `люди.json` slipped past the rails entirely: git renders a non-ASCII name as `"\320\273…"`, and no such file exists on disk | all the probes used Latin-script names |
| `grep -c` counts lines, not matches | three birth dates in a **single-line** JSON counted as one | the sample in the probe was multi-line |

From this come two requirements for any rails: count **occurrences**, not lines, and
have a probe against a **real commit**, not only against file paths. Rails that scream
over nothing get switched off entirely by the team — a false alarm costs more than a
miss.

**Acceptance of the rails, 25 Sep 2026:** self-check 7 probes out of 7 (three classes
are caught, three clean files pass silently); a live run against a real file with a
leaked key — the commit was blocked, the key never made it into the message. A separate
finding about the rails themselves: **bash 3.2 on macOS does not support Cyrillic
identifiers** — the first edition "worked" and silently skipped two probes out of
seven. In shell scripts, names in Latin script, messages in Russian.

**The class is broader than Cyrillic: a substitution in a shell string can silently
mean something else.** Measurement 25 Sep 2026, zsh 5.9 — with `BR=refs/heads/main`,
the string `$BR:tools/file.py` prints `mainools/file.py`. The colon is read as the
history modifier `:t` ("take the file name"): the substitution produced `main`, the
letter `t` was eaten by the modifier, and the remainder got glued on. No error, no
warning.

What follows from the measurement, not from a guess:

* **Curly braces save you:** `${BR}:tools/file.py` prints the correct thing.
* **Quotes do NOT save you.** `"${P:t}"` with `P=some/dir/file.py` prints `file.py` —
  quotes protect against word splitting and globbing, but not against modifiers. The
  advice "put substitutions in quotes" does not prevent this defect.
* **In bash 3.2 there are no modifiers at all:** the same string prints the whole path.
  So the same command means something DIFFERENT in the two shells, and testing in bash
  won't reveal the defect. The team's machines use zsh as the interactive shell, while
  scripts often run under bash; the difference shows up exactly at that seam.

The upshot for the rule: put shell-string substitutions in curly braces, verify the
result by printing it, and keep parsing and logic in Python — there are no
substitutions there.


**Confirmed by a second chat on zsh, and there it's more dangerous.** A Cyrillic name
breaks in TWO ways. The overt one: `for г in ...` — a parse error, the script crashes,
visible right away. The silent one: the assignment `О="path"` doesn't create the
variable at all, then `cp $О ...` gets nothing, and the command becomes a no-op — while
the script still exits successfully. So checking a shell script by "it didn't crash"
isn't enough: **you have to make sure the variables actually expanded**, not just that
there was no error. Run it on the oldest shell the team has, not only on your own.

### H116. RELEASING YOUR OWN WORK RUNS ON A LICENSE, NOT ON PERMISSION FOR EVERY VERSION

**Measurement 26 Sep 2026, bundle 1 (Open Notebook, Stirling-PDF, AFFiNE).** In a day of
work, about ten real defects were found and fixed, two of them giving the user a
SILENTLY WRONG result: PDF cropping was sending zero coordinates while the screen
showed other values, and the "Download" button was saving another file's bytes under
another file's name. Nothing changed in the store during that time: a live
`GET /api/listing/<id>` shows `pre.51`, `pre.31`, `pre.34`, rolled out more than a day
before that. Writing experts into the live account is treated as a standing external
change, and the release gate holds `PROVISIONING_SOURCE_DRIFT` — local code newer than
what was uploaded.

**Why permission for every version doesn't work.** It isn't verifiable: a person
cannot sign off on "seven fixes in the adapter, one hundred five tests, SHA-256 of the
archive" — they can only agree. **A confirmation the person is in no position to verify
adds no safety, it adds delay.** And it comes back on the next version: the cost is
paid every time, and the protection stays illusory.

**What actually protects** — three things, each a machine one: the previous version
stays in the store; the expert's code is saved before being overwritten; after the
write, a read-back and byte-for-byte comparison is performed, and a mismatch means a
rollback.

**Rule.** A product has a permit file, `РАЗРЕШЁН_ВЫПУСК.yaml`
(`templates/РАЗРЕШЁН_ВЫПУСК.yaml`): who granted it, when, which account, which
listings, which expert names, what kind of versions, a daily release ceiling, a
rollback folder. Within that boundary, a release proceeds without separate permission;
`tools/check_release_license.py` checks it and answers "allowed" or names what is
missing. Every release is written as a line in `ЖУРНАЛ_ВЫПУСКОВ.jsonl`.

**Outside the license — always a person:** the first paid release and a price change;
someone else's live product (`ВЕДУТ_ДРУГИЕ.txt`); deleting versions and listings
(hiding is fine); extending `app_scopes` — the buyer's consent is what's on the line
here; a release under a red gate or with no saved rollback.

**Consistent with the H-canon on freezing:** you can always change your own work, but
with a trail and a way back. The license is exactly that recorded trail showing the way
back was arranged in advance.

### H117. A PRODUCT'S SHELL IS BILINGUAL ON EQUAL TERMS WITH ITS CONTENT

**Measurement, 27 Sep 2026, the «Building on Extella» application.** All 19 guide sections and
the header were in two languages and guarded by a gate (H95, H111). The shell — the screen tabs,
the buttons, the statuses, the installer's refusals, the «Day one» demo — was Russian only:
**196 strings of text, 6,659 characters** scattered across 1,733 lines of the template. The
language switch worked all along, and switched the content only.

The first edition of this rule claimed 679 strings and 24,600 characters: the counter treated CSS
class names («дп-строки», «дп-исход») and fragments of markup as visible text, and overstated the
figure threefold. A number inside the rule about numbers turned out to be wrong: H113 applies to
the corpus itself.

**Why this is dangerous.** While the default language is Russian, the defect is invisible. Switch
the default to English and an English reader gets English sections inside a Russian window:
Russian buttons, a Russian demo, Russian refusals. The template itself calls that worse than one
honest language (`переводПолон`). So the request «make English the default» looks like a one-line
edit and in fact requires translating the whole shell.

**The rule.**

1. **The shell's strings live in one file** — `store_app/shell.json`, two languages per key. The
   Russian text stays in the markup as a fallback: if the table does not arrive, the page still
   reads instead of going blank.
2. **A new shell string is created with its English from the start.** The gate holds the untranslated
   remainder on a ratchet: the number can only go down. There is no flag day on purpose —
   translating the whole shell in one pull request means a wall of text nobody will read. This was
   done in six parts: buttons, refusals, the demo, substitutions, the installer, the default.
3. **The default switches last**, when the remainder is zero. Half a window in another language is
   worse than one honest language.
4. **A dead key is a defect too:** a translation nobody will ever see creates a false sense of
   readiness. The gate catches both keys the template calls that the table lacks, and keys in the
   table that the template never calls.

Held by `tools/check_shell_bilingual.py`.

### H118. A TOOL WE TELL PEOPLE TO RUN MUST SURVIVE A NARROW CONSOLE

**Measured 28 Sep 2026, the first CI run on `windows-latest` ever.** The Windows console
runs in `cp1252`, and `print("  ✓ H78: key source…")` kills the process with
`UnicodeEncodeError` on the very first character. The person sees a stack trace instead of
guidance — and BEFORE the tool has done anything. Until that run the README promised "any
OS" while CI only knew ubuntu: we talked about Windows without ever running it.

**Norm.** Every tool that a document tells a person to run switches `stdout` and `stderr`
to UTF-8 at start-up — six lines at the entry point, not failing where a stream has been
replaced. Verified BY BEHAVIOUR: the gate runs each such tool's self-test under
`PYTHONIOENCODING=cp1252` and catches `UnicodeEncodeError`.

**The list is not written by hand.** It is collected from the documents a newcomer reads:
the README, the agent entry point, the copyable prompt, the onboarding and the app's text.
Tell people tomorrow to run a new tool — it falls under the check by itself, without our
memory.

**A full sweep, 28 Sep 2026.** All 107 tools in `tools/` that print Russian are protected,
and so are the templates of the scaffold that `new_product.py` produces (`server.py`,
`smoke_e2e.py`): otherwise every new product was born with a test that falls over on
Windows. The self-test of every changed tool was run under `cp1252`.

**Protection is looked up in the parse tree, not in the text.** The entry-point line also
occurs inside template strings: a text-based sweep put the protection into a template, past
the real entry point, and `new_product.py` was counted as protected because of a `reconfigure`
in a template it generates. The syntax was intact both times — only parsing the last top-level
`if __name__ == "__main__"` caught it. The gate does not let an unprotected tool through.

**The boundary is stated out loud.** The newcomer's path is checked by behaviour; the other
tools by their source. CI runs live on Windows only for the connector and the platform wrapper,
and Windows support is NOT declared by this — that needs an "OS × client" matrix on a live
bench (the open part of F04 in the audit of 28 Sep 2026).

Held by `tools/check_windows_console.py`.

### H119. PUBLISHED ≠ INSTALLED ≠ WORKING: THREE STATES, THREE PROOFS

**Audit of 28 Sep 2026, F07–F08, and findings in our own tools.** A publish was counted as
successful on the stream's `done` event. The publish Expert did not send `tags` (the store
answered 400 — a training participant got stuck on it), called a dry run "the check passed",
promised "the draft is visible only to its owner" (unconfirmed, §24) and handed out a
`/app-page/<id>/` link that answers 401. The publish script bound the agent only when an
installer was present: a "page + agent" product shipped without its agent. And a reinstall with
an empty body, for a product with an agent, risks creating a second agent — a participant got
three agents from three purchases (§55).

**Norm.** The three states are named separately, and each has its own proof:

1. **Published** — the version is READ BACK from the listing (`GET /api/listing/{id}` →
   `versions[].id`). A `done` event proves the stream ended, not that the version exists. Not
   read back — the state is "unconfirmed", not "success".
2. **Installed** — the buyer has EXACTLY this version. A product with an agent is not blindly
   reinstalled until the platform names the repeat-purchase contract.
3. **Working** — the person opened the window and got a result on their own data. Only
   acceptance proves this, not the publish and not the install.

A dry run is called a dry run (`dry_run`, "did not touch the network"), not a successful check.
Hidden from the catalogue is not called closed. No link to the card is given — the path is said
in words.

Held by `tools/check_publish_expert.py` (runs the publish Expert in dry mode) and by the
self-test of `tools/deploy_page_product.py` (agent binding in all three product kinds, the stop
on reinstalling a product with an agent).

### H120. AN EDIT LEAVES NO REFERENCE TO A NAME IT DELETED

**Measurement, 28 Sep 2026.** An edit to a check in `store_app/update.py` removed the variable
`маркер`. It was read **twice** — before the page is sent and after. The first place was fixed, the
second was missed. The result: the page went to the buyers successfully, and then the script died
with a `NameError` in the verification **after** the send. The deployment looked as if it had
failed while it had in fact gone through — and in that situation a person presses the button again,
not knowing everything is already done.

**Why this was not caught.** Python sees it only when that particular branch executes, and the
branch «after a successful send» never executes on a dry run. Compiling the file checks the syntax;
a missing name it does not.

**The rule.** When you remove a name, find **every** read of it, not the first. Held by
`tools/check_undefined_names.py`: by walking the tree, a name used inside a function must be its
local, an argument, an import, declared `global`, assigned at module level, or a builtin.

**The check is narrow on purpose.** It does not replace pyflakes and does not hunt for unused names
or shadowing: a broad check over your own code produces false alarms, and a gate that lies gets
switched off together with its usefulness (H114, item 2). The live run showed exactly that — 18
hits, of which **17 were false**, all on the module name `__file__`, which Python provides itself
and which is absent from `dir(builtins)`. There was one real finding, the one above.

**And about the acceptance line.** I wrote its first edition BEFORE the run, guessing what would be
found: «2 false alarms». The measurement gave 17. An acceptance line describes a measurement, not
an expectation — otherwise it is once again a number living apart from the fact (H113).
