<!-- source: USER_ONBOARDING_CANON.md sha256:0aacc2753c2e2ce8f2a10b58921f932d46a36fb9a66f90f67c88559fdf88bd9f -->

# The welcome tour — the user onboarding canon

Why. The buyer opens the app for the first time and sees numbers and buttons with no
explanation. The question "where do I click" comes up before the desire to figure it out, and
the product gets set aside. The canon was born on 8 Sep 2026 on the "Claims Accounting for a
Logistics Operator" app: a tour of eight tooltips closed the questions of a first opening
before they were even asked.

Acceptance before Publish (DEPLOY_REQUIREMENTS, "first run in a clean state") already requires:
"onboarding greets the user." This canon defines what onboarding consists of and how the
machine checks it.

## When it's mandatory

Every page-type product with more than one screen or action greets its first user with an
interactive tour: dimming, highlighting of a live element, a short tooltip next to it.

## Markup contract

Checked by a gate — a machine check run before release. The gate checks the class, not a
specific product's names, so the markup is declared through attributes:

- the tooltip container carries `data-onboarding="tour"`;
- the next-step button is `data-onboarding="next"`;
- the "Skip" button is `data-onboarding="skip"`;
- the restart element is `data-onboarding="restart"`; it's always visible in the regular
  interface (for example, a "How to use this" menu item), because tooltips are also needed by
  a second person at the same screen;
- the fact of completion is saved under a key with the suffix `tour_done`;
- every access to browser storage is wrapped in `try`: storage can be unavailable (a private
  window, a preview), and the tour must still work in that case rather than crash the page.

## Content rules (checked by a person at acceptance)

1. The tour starts on its own at the first opening and doesn't appear on repeat visits: being
   pushy drives people away faster than not knowing something does.
2. Three to ten steps; each one has a "step X of N" counter, so the person sees how much is
   left.
3. Each step highlights a live element and says what will happen after clicking it. Retelling
   section names doesn't count as a tooltip.
4. "Skip" is available at every step except the last: the tour is a suggestion, not an
   obstacle.
5. The last step answers the buyer's main question: how to carry out the product's core action.
   If, in the current version, that action happens outside the product (a message to the agent,
   a file in a folder) — the tour says so directly, because an honest "that's how it is for
   now" retains people better than staying silent about a missing button.
6. The copy follows WRITING_RULES and the brand book.

## Gate

```
python3 tools/check_user_onboarding.py <path-to-page.html>   # check the product
python3 tools/check_user_onboarding.py --selftest             # check the gate itself
```

Gate red — publication is forbidden. Reference example of compliance: the "Claims Accounting
for a Logistics Operator" app page (the logistics-operator project, os-app/index.html).
