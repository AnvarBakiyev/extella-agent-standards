<!-- source: templates/app-recipe/qa-checklist.md sha256:7472cf687d376235ad6131a56c1bbc8738be83d501fc26486b73c7d1c5e52cd6 -->

# Checklist before rollout

## Locally

- [ ] `python3 tools/check.py` is green.
- [ ] `python3 tools/build.py` built the zip; `index.html` is at the zip's root.
- [ ] Opening it with no network doesn't turn into a blank screen.
- [ ] Empty input explains the next step; it doesn't call the expert.
- [ ] Every scenario changes both the number and the table/chart.
- [ ] You can't enter a negative value, infinity, or text instead of a number.
- [ ] Empty, waiting, error, done all exist; the status has `aria-live`.
- [ ] No `prompt`, `alert`, `confirm`, no calls to localhost/internal address.
- [ ] Clicking again doesn't start two identical requests.
- [ ] Export, copy, and navigating to another app show confirmation only after the
      result.

## In Extella OS

- [ ] The window launches from a shortcut, not only via a direct link.
- [ ] H106: the first `app-agent/run` without `targets` returned `pageRoute.targetId`
      or `device`.
- [ ] H106: the second call went out with `targets: [the device received]` and
      returned the name of the same machine.
- [ ] H104/§46: on `Execution Error … (<container>, line 1)`, the reason, a Device ID
      field, and a "Work through this device" button are shown.
- [ ] H104/§46: the entered Device ID is verified with a targeted call; after the
      window closes it isn't kept in `localStorage` and is asked for again.
- [ ] The main button: expert success, expert error, timeout.
- [ ] A longer-than-usual response doesn't break the layout; a large result isn't
      passed to the UI in full.
- [ ] Working in an empty profile/on a second device doesn't rely on the first user's
      localStorage.
- [ ] Open → run → close → open: the promised result/file is where it's said to be.
- [ ] All buttons, tabs, scenarios, adding/removing rows, and mobile width are checked.

## Store

- [ ] Version, name, icon, description, and screenshots match the actual product.
- [ ] A closed listing and owner acceptance come first.
- [ ] Verified that `published` stays `false` until a separate decision to publish.
- [ ] No keys, tokens, personal data, or internal URLs in the archive or the log.
