<!-- source: checklists/DoD.md sha256:81b5345d84f1b6b9dff2ed264729830d118855aae18d6ff4d97647e4ac79212b -->

# Is the agent READY FOR RELEASE (for work at the client's)

**This checklist applies to the `prod` stage** — the product is sold and installed
for any buyer. It does NOT apply during the build: see `BUILD_STAGES.md` and
`python3 tools/stage_gates.py --stage <стадия>`.

## Build — done when three items line up

- [ ] **The scenario runs through completely** on live calls, not in pieces.
- [ ] **A refusal is visible in words** — there is no blank screen anywhere.
- [ ] **Stop rules are observed**: external writes are drafts, there is no other
      people's data, no destructive rights, nothing live is touched, no secrets in
      the archive.

Nothing more is required during the build — until the facts below appear.

## By facts (client data / someone else's machine) — plus

- [ ] A passport (agent or automation) linked to `platform_agent_id`.
- [ ] The agent's rights are trimmed down; there is no `delete_*` without a reason.
- [ ] Personal data is masked if it passes through the product.
- [ ] Work-in-progress is visible (`docs/RULE_WAITING_STATES.md`).
- [ ] The installer is non-interactive, the exit code is honest, the agent binding
      is recorded.

## Prod — full list below

A capability is ready for release when all items are checked:

- [ ] **The contract is versioned**
  The capability's interface has a version number — changes do not break whoever depends on it.

- [ ] **The success scenario and errors are tested**
  Both the normal scenario and behavior under failures are checked — not only "when everything is fine."

- [ ] **Rights are minimal**
  The agent has access only to what the task needs, and nothing more.

- [ ] **Destructive and external actions are confirmed according to policy**
  Deletions and outward-facing actions (emails, payments, changes at the client) go through confirmation under the adopted policy.

- [ ] **A disconnect and a re-run are handled safely**
  A disconnect or a re-run do not lead to duplicates or half-finished work.

- [ ] **The result is re-checked**
  The agent's output is verified by a separate step, not taken on faith.

- [ ] **An evidence trail is formed**
  After the work, an evidence trail remains: what was done, when, and why.

- [ ] **Secrets and PII do not end up in forbidden layers**
  Passwords, tokens, and personal data do not leak into logs, chats, prompts, or someone else's storage.

- [ ] **There is observability and cost limits**
  It is visible how the agent works (logs, metrics), and there is a spending ceiling — the bill will not run away.

- [ ] **There is a suitable user-facing or operational surface**
  The person has a convenient place to watch the agent's work and manage it.

- [ ] **There is an operational owner**
  A specific person is assigned who is responsible for the agent after launch.

- [ ] **Agent Passport is linked to a stable platform agent ID**
  `agent.platform_agent_id` is specified; a match by display name does not count as a link.

- [ ] **Shared Genes have stable IDs**
  Every shared element is declared in `shared_genes[]` with `gene_id`, kind, version, and
  `provenance: global`; consumers are not counted by name.

- [ ] **There is a staged rollout and a verified rollback**
  The rollout goes in stages, and the rollback has actually been verified, not just described.

- [ ] **The screen has a "? How this works" explanation — with a "what we do NOT promise" section**
  The user can understand for themselves what the capability does, what is guaranteed, and where its limit is — without explanations from the developer.

- [ ] **Limits are stated honestly (limits in the passport)**
  It is written what the capability does NOT do. Without this, release is forbidden — the checker will not let it through.

- [ ] **The interface and explanations are ready in two languages: Russian and English**
  Not "we'll translate it later": an English-speaking client must see a finished product, not a half-made one.

- [ ] **Documentation reflects the actual implementation**
  The docs say what actually works, not what was planned.

- [ ] **The brand is observed: words, colors, interface tone**
  No "helper / assistant / bot / neural network" and no "How can I help?" greetings; colors are from the Extella palette; Gold and Petrol are not placed on each other. Rules: `BRAND_FOR_AGENTS.md`.

- [ ] **The product's own agent in Extella appears by itself after deployment**
  The product does not wait for a person to create an agent and enter the number: the agent is created automatically after a successful deployment, idempotently, with confirmation by reading and a receipt (§3.27). Binding to someone else's agent — only by the owner's deliberate decision.

Automated checks:

```
python3 tools/check_agent_passport.py путь/к/паспорту.yaml
python3 tools/check_agent_passport.py путь/к/паспорту.yaml --json
python3 tools/check_brand_copy.py путь/к/интерфейсу.js путь/к/странице.html
```

Evolution Console uses the second call and the same `check_report(doc)` calculation,
not a risk check of its own.
