<!-- source: rules/INDEX.md sha256:ce53434dca481529c12c309c07dc901728c534b988ab88240efb203a595e6207 -->

<!-- Собрано автоматически: python3 tools/split_rules.py -->

# Canon rules: table of contents

Each rule sits in its own file of a few kilobytes — take them one at a time, not the whole corpus (a 369 KB web read gets truncated).

Raw link to a rule: `https://raw.githubusercontent.com/AnvarBakiyev/extella-agent-standards/main/rules/H<номер>.md`

| rule | about |
|---|---|
| [H1](H1.md) | What gets attached |
| [H2](H2.md) | The token arrives as a substitution in `index`, not only as a header |
| [H3](H3.md) | Bundle assets are public — they must never contain secrets |
| [H4](H4.md) | The sandbox: what's allowed and what isn't (verified by measurement) |
| [H5](H5.md) | A page CAN call its own agent — via an app token |
| [H5-bis](H5-бис.md) | A page REACHES THE DEVICE — measured 12 Aug 2026 |
| [H5-quater](H5-кватер.md) | Asymmetry between the `expert/save` and `expert/get` fields |
| [H5-quinta](H5-квинта.md) | Two silent dead ends of a shortcut |
| [H5-ter](H5-тер.md) | The purchase mode decides whether the agent will be new — and it's easy to miss |
| [H6](H6.md) | Attachments: a product can open desktop objects |
| [H7](H7.md) | Pay-per-action — without a user token |
| [H8](H8.md) | Publishing, versions, deletion |
| [H9](H9.md) | The charge happens after the install |
| [H10](H10.md) | One listing carries BOTH an archive AND a page — that's not two products |
| [H11](H11.md) | Purchases can be read — but not from the page (verified 12 Aug 2026) |
| [H12](H12.md) | App permissions (`app_scopes`) — a new mandatory publishing step |
| [H13](H13.md) | CANCELED 13 Aug 2026 — token-based isolation no longer exists |
| [H14](H14.md) | Updating without a redeploy: three ways, and they cost differently |
| [H15](H15.md) | Forward proxy: a page can call the core and third-party APIs (expanded 13 Aug 2026) |
| [H16](H16.md) | A device target is credentials, not an identifier |
| [H17](H17.md) | An expert's response arrives in TWO wrappers, and a dict doesn't serialize to JSON |
| [H19-bis](H19-бис.md) | CORRECTION: there's nothing to remove an extension with, editing desktop state doesn't help |
| [H19-quater](H19-кватер.md) | Updating an extension leaves the old copy on the desktop |
| [H19-quinta](H19-квинта.md) | CLOSED 14 Aug 2026: both cleaning up your own litter and removing an extension |
| [H19-sexta](H19-секста.md) | AN EXTENSION DOES NOT CHANGE THE OS'S LOOK — my mistake, which cost the owner time |
| [H19-ter](H19-тер.md) | A theme only colors what it knows the variable names of |
| [H20](H20.md) | For a published listing, EVERY new version goes to the store immediately |
| [H21](H21.md) | Pinning by tag doesn't save you from a stale tag |
| [H23](H23.md) | THE STOREFRONT CARD: icon, description, tags — at rollout time, not "later" |
| [H24](H24.md) | A THIRD-PARTY APP IN THE OS WINDOW: five refusals, and each one is silent |
| [H24-bis](H24-бис.md) | THE SANDBOX'S THREE DOORS behave differently |
| [H26](H26.md) | PUBLISHING IS REVERSIBLE, DELETION IS NOT. A correction to what I repeated all day |
| [H27](H27.md) | WHERE A PAGE-TYPE PRODUCT STORES ITS WORK: with us, not in the browser |
| [H28](H28.md) | THE RATE LIMIT IS SHARED ACROSS THE MACHINE, AND THE PANEL MUST NAME THE REFUSAL |
| [H29](H29.md) | A FALSY PARAMETER NEVER REACHES THE EXPERT. Verified with an echo expert |
| [H30](H30.md) | A SECRET FOR AN EXPERT: where it lives and how it's read. Measured from the inside |
| [H31](H31.md) | AGENT PERMISSIONS: the platform accepts names that don't exist in the runtime |
| [H32](H32.md) | THE MICROPHONE AND CAMERA ARE UNAVAILABLE IN THE OS WINDOW. And it's the same hole as with storage |
| [H33](H33.md) | The desktop's Origin holds the token: foreign code sits right next to it |
| [H34](H34.md) | The launch device and the listing form: three places where the request body decides the wrong thing |
| [H35](H35.md) | A listing version is a SNAPSHOT: reinstalling silently rolls back an expert edit |
| [H36](H36.md) | Product assets are served with no version in the address: people are left with the old one |
| [H37](H37.md) | An expert that will run for anyone calls nothing external |
| [H38](H38.md) | A gate at the surface's output: reread the artifact, don't trust the transformation |
| [H38-P](H38-П.md) | The app: what to reread after writing to the platform |
| [H39](H39.md) | A thin page in the OS window: its own transport, its own forms, its own windows |
| [H40](H40.md) | An expert's response has a ceiling around 200 KB, and it isn't called an error |
| [H41](H41.md) | A key and its scope: two silent ways to lose a secret |
| [H42](H42.md) | Deletion answers with success and doesn't delete |
| [H43](H43.md) | A shared expert: `global` gives visibility, but doesn't carry execution over |
| [H44](H44.md) | An expert's name in the agent's permissions doesn't make it a model function |
| [H45](H45.md) | STOREFRONT VERIFICATION: check the artifact through the buyer's eyes, not the author's |
| [H46](H46.md) | AN INSTALLER ON POSIX ≠ WINDOWS: rights for laying out and tearing down |
| [H47](H47.md) | BEFORE ROLLOUT, CHECK THE SNAPSHOT'S EXPERT COUNT |
| [H48](H48.md) | A DIRECT URL TILE IS FRAGILE: HTTP/1.1 and app-page instead |
| [H49](H49.md) | INSTALLING THE BRIDGE AT THE CLIENT: the source's form and access from the keychain |
| [H50](H50.md) | A REASONING MODEL SILENTLY RETURNS EMPTINESS UNDER A SHORT TOKEN CEILING |
| [H51](H51.md) | The purchase completed, and nothing was installed on the device |
| [H52](H52.md) | A shortcut leads only to the product page's direct address |
| [H53](H53.md) | Publishing started a second listing instead of a new version |
| [H54](H54.md) | `app-agent/run` IS SYNCHRONOUS: an expert returns a terminal value, not a task |
| [H55](H55.md) | An immutable release: the expert keeps running on the old code |
| [H56](H56.md) | A response in someone else's shape: one expert's envelope applied to another |
| [H57](H57.md) | Channel health can't be measured with an operation that grows together with the log |
| [H58](H58.md) | An expired task is closed once, a late response doesn't revive it |
| [H59](H59.md) | `global` on an expert: the flag is needed both on the record AND IN THE READER'S REQUEST |
| [H60](H60.md) | Editing a page via a new version breeds versions and agents |
| [H61](H61.md) | The request-rate limit: parallelism doesn't get around it, it makes it worse |
| [H62](H62.md) | An app is an internal panel: outward only by message, there's no direct request |
| [H63](H63.md) | Without `data-testid` hooks, an app can't be verified by machine |
| [H64](H64.md) | An app's shell is taken ready-made, not redrawn from scratch |
| [H65](H65.md) | An app page is cached — the fix must happen in that same page |
| [H66](H66.md) | The first showing happens early, and it's offered by the machine, not the human |
| [H67](H67.md) | A new subject area is connected with a CSPL domain, not new access |
| [H68](H68.md) | A language of one's own is connected via a container, and four things silently break it |
| [H69](H69.md) | Acceptance runs on the final ZIP in a clean room, not the source tree |
| [H70](H70.md) | An ambiguous conclusion before a destructive operation is "stop," not "no data" |
| [H71](H71.md) | Diagnostics print only allow-listed fields — never a raw response or the environment |
| [H72](H72.md) | `/api/app-agent/run` envelopes also carry `status` — the domain check goes blind on it |
| [H73](H73.md) | The dereference gate must see an id that has traveled into an argument |
| [H74](H74.md) | Unbounded page self-repeat — a pipeline of tasks behind a stuck button |
| [H75](H75.md) | Visual acceptance runs at the size of the real app window |
| [H76](H76.md) | The version's scope is a frozen snapshot of expert code |
| [H77](H77.md) | A product that creates products must place the icon itself |
| [H78](H78.md) | Refusal handling lives in one place, or copies drift apart silently |
| [H79](H79.md) | A user's own free draft places itself on the desktop and stays deletable |
| [H80](H80.md) | A desktop tile and a store listing are two different things |
| [H81](H81.md) | The entry point contradicted the prompt, and the entry point won |
| [H82](H82.md) | A recipe module with no check and no imprint is a lottery, not a product |
| [H83](H83.md) | A recipe reproduces the skill, but not the contract |
| [H84](H84.md) | Acceptance of a windowed product must click through the client surfaces |
| [H85](H85.md) | An indicator is a live ping, not the presence of a setting |
| [H86](H86.md) | A test must hit the same path as production — or green masks dead |
| [H87](H87.md) | Destructive tests are never run against the owner's production base |
| [H88](H88.md) | Patches go in as raw strings, with dedup and a check afterward |
| [H89](H89.md) | An empty `agent_id` is the legitimate "not deployed," not a failure |
| [H90](H90.md) | "Zero human actions" was written for macOS: on Windows the token isn't written to disk |
| [H91](H91.md) | Listener state files don't sit at a fixed path — don't infer "no listener" from them |
| [H92](H92.md) | The duplicate-name gate looks at the PRODUCT's experts, not the agent's whole inventory |
| [H93](H93.md) | A user's sensitive key (a digital signature): automate the session, not the signing |
| [H94](H94.md) | The runtime executes the FIRST top-level function in the file — keep helpers nested |
| [H95](H95.md) | Bilingual RU+EN is mandatory for every app — and checked by machine |
| [H96](H96.md) | WINDOWS ACCEPTANCE IS ON x86-64. THE ARM VM HAS WORKED SINCE 20 SEP (CORRECTION BELOW) |
| [H97](H97.md) | AGENT/CREATE: THE USER COMES FROM THE TOKEN, NOT FROM THE BODY |
| [H98](H98.md) | THE DELIVERY PACKAGE MUST BE COHERENT: archive ⇄ installer ⇄ install.py at the root |
| [H99](H99.md) | ZERO IS A CLAIM THAT "THIS IS EMPTY," NOT "I DON'T KNOW" |
| [H100](H100.md) | ROUTE BEFORE RENDER: THE LOCAL ROAD FIRST, A DEAD ONE — IS REMEMBERED |
| [H101](H101.md) | A PRODUCT MUST HAVE A WORKING STATE WITH NO EXTERNAL DEPENDENCIES |
| [H102](H102.md) | ROLLOUT: A FULL RUN, A FINGERPRINT CHECK, A CLEAN STATE |
| [H103](H103.md) | BREAKAGES YOU CAN'T SEE ON THE DEVELOPER'S MACHINE |
| [H104](H104.md) | HOW TO TELL A DEAD DEVICE FROM SOMEONE ELSE'S: TWO PLATFORM RESPONSES |
| [H105](H105.md) | JAVA WINDOWS (NCALayer) ARE DRIVEN BY KEYBOARD, NOT MOUSE. THE PASSWORD — ONLY AFTER CHECKING THE WINDOW |
| [H106](H106.md) | AN OS PAGE CALLS AN EXPERT VIA APP_TOKEN, NOT VIA THE TOOLBAR BRIDGE |
| [H107](H107.md) | DEVICES AND THEIR RECORDS: WHO PICKS THE MACHINE, WHEN, AND WHAT SETS IT |
| [H108](H108.md) | CONNECTING A CHAT AGENT (Claude, Codex) ON A NEW MACHINE IS DONE, NOT EXPLAINED |
| [H109](H109.md) | THE KEY FOR THE STORE AND FOR THE CORE IS THE SAME ONE, ONLY THE HEADERS DIFFER |
| [H110](H110.md) | A BAN THAT LIVES IN ONE FILE'S SELF-CHECK DOES NOT COVER THE REPOSITORY |
| [H111](H111.md) | TRANSLATION FRESHNESS IS CHECKED IN BOTH DIRECTIONS |
| [H112](H112.md) | THE ENTRY POINT FOR THE AGENT AND THE APP FOR THE HUMAN DO NOT DIVERGE |
| [H113](H113.md) | A NUMBER ABOUT ANOTHER FILE IS NEVER WRITTEN BY HAND |
| [H114](H114.md) | A GATE IS ACCEPTED ONLY AFTER A RUN AGAINST A LIVE SUBJECT |
| [H115](H115.md) | THE REPOSITORY'S RAILS: FOUR CHECKS BEFORE THE COMMIT, NOT A CONVERSATION AFTER |
| [H116](H116.md) | RELEASING YOUR OWN — BY CLEARANCE, NOT BY PERMISSION FOR EVERY VERSION |
| [H117](H117.md) | A PRODUCT'S SHELL IS BILINGUAL ON EQUAL TERMS WITH ITS CONTENT |
| [H118](H118.md) | A TOOL WE TELL PEOPLE TO RUN MUST SURVIVE A NARROW CONSOLE |
| [H119](H119.md) | PUBLISHED ≠ INSTALLED ≠ WORKING: THREE STATES, THREE PROOFS |
