<!-- source: checklists/DoR.md sha256:309399d42ed94d44a6ce988f0019273fee95983cef4e0c9e369372ead6cfb79b -->

# Are you READY TO START building an agent capability

**Applies in full when the product goes onto someone else's machine.** For the
build, the first four items are enough: business goal and owner, inputs-outputs and
success criterion, side effects, level of autonomy. The rest — by facts
(`BUILD_STAGES.md`).

A capability is ready for development when all items are checked:

- [ ] **The business goal and owner are described**
  It is clear why the business needs this and who specifically is responsible for the result.

- [ ] **The inputs, outputs, and success criterion are known**
  What we feed in, what we get out, and how we will know it turned out well.

- [ ] **Side effects are defined**
  What else changes in the world besides the main result (emails, records, files, statuses).

- [ ] **A level of autonomy is chosen**
  It is decided what the agent does on its own, and where it must ask the person.

- [ ] **Applicable rules and concepts are listed**
  Which rules and concepts the agent must take into account in its work.

- [ ] **The scope of visibility is defined**
  What is visible and accessible to the agent, and what is outside its sandbox.

- [ ] **The data and its handling mode are understood**
  What data we touch, where it lives, and how it may be handled (locally, in the cloud, with anonymization).

- [ ] **Confirmations and rollback are described**
  Which actions require confirmation and how to roll back if something goes wrong.

- [ ] **The evidence trail is defined**
  What evidentiary trace will remain after the work: what was done, when, and on what basis.

- [ ] **There are test examples and expected results**
  Concrete examples of inputs and what should come out of them — so there is something to check against.
