<!-- source: RUNBOOK_STORE_PUBLISH.md sha256:21e35ce32eff807e59fe08d4dab625d87e519bb18c0c482f3d6d778d7890d5cf -->

# Runbook: publish a product to the OS store (Codex → Store)

A short path for the task at hand, not a 900-line canon. Written after reviewing an
external chat that built a product without this runbook: the Bridge skill describes the
opposite direction (Extella → Codex), and how to publish to the store was nowhere.

The endpoints and forms below were **captured live** from `os.extella.ai/openapi.json`
(cross-checked 03 Sep 2026). Where a form didn't come from OpenAPI but from proven
rollouts, it is marked "proven by rollouts."

## Zero. Where we knock and with what

A **listing** is the product card in the store: name, description, icon and a list of
versions. One listing carries both the page and the product archive.

The store is **`os.extella.ai`**, a separate server (not the core `api.extella.ai` and
not the devices at `disnet.extella.ai`). Store paths are under `/api/...`.

**Only ONE key is needed, only the header name differs** (measured 24 Sep 2026 on a live
account, request `GET /api/my-listings` from three sides):

| knocked with | response |
|---|---|
| core key (`~/.extella/api_token.txt`) in header `X-Extella-Token` | **HTTP 200**, list of product cards (listings) |
| key from `~/.extella/os_token.txt` in the same header | HTTP 200, same result |
| core key in header `X-Auth-Token` | **401 "X-Extella-Token header required"** |

In other words, the store cares about the **header**, not which file the key came from.
The previous edition said "the OS's own token lives in `~/.extella/os_token.txt`," and an
external chat read that as "publishing is impossible without this file": the client had
disallowed the file, the chat declared a blocker and stopped work (reviewed 24 Sep 2026).
The file is just one of the places the key can live; any valid account key works,
including one a human created in `Library → System → Tokens`.

**Never print secrets** (H71): diagnostics should output only named fields (response
code, `listing_id`, `version_id`), never the raw response, headers, or the whole
environment.

## One. Find or create a listing

- `GET /api/my-listings` — your listings. A card carries `id`, `name`, `published`,
  `tags`, `source_type`, `versions`.
- `GET /api/listing/{lid}` — the card with versions and reviews (fully visible to the
  owner; currently also visible to an outsider — that is a platform defect, don't rely
  on it as privacy).
- `POST /api/edit-listing/{lid}` — edit the card.

One listing carries **both the page and the archive** — it's one product, not two
(canon H10).

## Two. Add an immutable version

`POST /api/add-version-stream/{lid}` — the response arrives **as a stream** (HTTP 200,
then SSE events), not a single JSON.

**Request body (NOT described in OpenAPI; form confirmed by two rollouts):**

| field | what goes in it |
|---|---|
| `version` | number, e.g. `0.1.0-private.40` |
| `tags` | non-empty list |
| `app_scopes` | run rights, e.g. `expert.run`, `device.run` |
| `source_id` | build source |
| `page` | the page bundle + its SHA-256 |
| `archive` | the product archive + its SHA-256 |

**Event stream (confirmed by rollouts):** `expert_progress` events arrive with an
increasing `sequence`, ending in a terminal event of `type=done` or `type=error`.
Response code 200 does **not** mean success — success is carried by the terminal event.

**Read the stream to the end and save it to a file — before you analyze anything.** Both
chats whose version failed did not save the events after `expert_progress`, and afterward
there was nowhere to get the exact cause (backend exception, stage) from.

This does not contradict the ban on printing the raw answer above, but the boundary must be
stated plainly (audit of 28 Sep 2026, F05): **saving is allowed, showing and distributing is
not.** The raw stream counts as potentially secret: a file in the diagnostics folder with
mode 600, token-shaped values and headers replaced with `…`, and the file never travels into
chat, into a commit, or into the product archive. Only named fields go into the diagnostics
a person reads.

**A version is immutable** (canon H8): a released version cannot be corrected —
`edit-version/{vid}` edits only the version's card, not its contents. A fix goes out as
a **new number**.

**If a version fails** (terminal `type=error`): the version doesn't appear in the
listing, `app-archive` returns 404 for it. The number itself is **not** claimed — on a
live listing the version numbering is contiguous, failed attempts leave no gaps
(measured 31 Aug 2026). So after a failure you take the **next** number, not the same
one: reusing the same number is the only scenario where a hidden reservation could bite.

## Three. A separate acceptance agent

A purchase creates a **new deployed agent** (measured: response `mode:"new"`, the
purchase row is rewritten to point to the new agent, the old one is orphaned). So put
acceptance testing on a **separate acceptance agent**, not on a live working one —
otherwise reinstalling will rebind its state. `my-purchases` shows the binding:
`deployed_id`, `agent_id`, `version_id`, `update_available`.

## Four. Buy the exact version

- `POST /api/purchase-stream/{vid}` — purchase as a stream (as a rollout).
- `POST /api/purchase/{vid}` — purchase as a single response.
- `GET /api/purchase-check/{lid}` — check whether the listing is purchased.

Buy the **exact `version_id`** of the version you need, not "the latest."

## Five. Cross-check what arrived

- `GET /api/app-archive?app=<lid>&version=<version>` — the version's archive (the `app`
  and `version` parameters are taken from OpenAPI). 404 on a non-existent version.
- Rights / `app_scopes` — match what was declared; there should be no extra ones.
- The product's experts — present and callable.
- Byte-for-byte comparison of the archive and page against their SHA-256 from step two.

## Six. Acceptance in a clean room (canon H69)

Before Publish, run the **final ZIP** (not the source tree) through the buyer's clean
room: an empty home directory and volumes, a **cleaned environment of the installed
Expert** (not the developer's PATH), the same mounted directories, the full sequence
`not installed → ready → restart → ready`. A dev smoke test with a different PATH does
not count as acceptance. If it doesn't pass, don't create the version: it is immutable.

## Seven. Publish — a human action

`POST /api/listing/{lid}/publish` makes the listing visible to everyone. **A human
clicks it** (canon: an accidental publish is ruled out by construction). Reversible at
the same address with `published: false` (canon H26). A pre-release is a version **hidden from the
catalogue** (`published=0`); everything above in this runbook happens on one. **Hidden from
the catalogue does not mean closed:** higher up in this same runbook it says the listing body
is currently visible to outsiders as well. These are two different properties — visibility in
the storefront and access control — and the second one we have not verified. Do not promise a
buyer that a pre-release is private until the platform answers and the probe is repeated
(audit of 28 Sep 2026, F05; the question to the platform is open). The target state to hand off a chat: "pre-release published, bought for myself,
clean-room acceptance passed — one click of Publish remains," plus the evidence:
`listing_id`, `version_id`, what the first run showed.

## Take down a version without touching the listing

`POST /api/version/{vid}/unlist` — hide the version; `DELETE /api/version/{vid}` —
delete it. The listing stays in place.

---

**What here is from OpenAPI, and what is from practice.** The paths and parameters
(`app`, `version`, `lid`, `vid`) are from the live `openapi.json`. The bodies of
`add-version-stream`, `purchase-stream`, `publish` are **not described** by OpenAPI —
their form was taken from two proven rollouts and marked in the text. That is itself a
point against the platform: the rollout's contract is missing from the docs.
