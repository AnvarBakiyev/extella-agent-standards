<!-- source: skills/extella-ui/SKILL.md sha256:b3e59cd5a5f61039f3b161a0b608f157067d5f7d2bd28ab826399dc0df0a0bd7 -->

---
name: extella-ui
description: How to make an Extella agent's interface clear, not generated. Apply it when creating or reworking any screen — a product window, a panel, a page in the OS store, a form, a wizard. Contains clarity rules, the Extella design code, ready-made screen skeletons, and an acceptance checklist.
---

# Extella Agent Interface

A skill for whoever is building a screen. Clarity first, styling second: a beautiful
screen where it's unclear what to do is worse than an ugly, clear one.

The rules below are collected from live post-mortems. Next to each one is what breaks without it.

## 0. When to use this skill, and when to use another

The machine may also have the official `frontend-design` skill installed. It's about
something else, and confusing the two is expensive.

| what you're building | which skill |
|---|---|
| a product window, a panel, a page in the OS store | **this one** |
| a landing page, a site, a presentation, an email | `frontend-design` |

The reason is simple: `frontend-design` teaches you to invent a distinctive palette and
typography for every project. Inside Extella these are **fixed** and checked by machine,
so following it will break the machine's brand and design checks. The reverse is also
true: for a landing page, the Extella design code is overkill.

What's worth bringing over from `frontend-design` into this one: it has strong guidance
on words in the interface — active voice, one name for an action across the whole path,
an error never apologizes and is never vague. This doesn't contradict anything below.

## 1. A screen answers three questions in five seconds

Someone opening the window for the first time must understand, without reading:

1. **where they are** — what this product is and what it does;
2. **what's possible here** — what actions exist;
3. **what to do first** — where to start right now.

If there's no answer to the third question, the person closes the window. An empty
screen that says "No data" answers the first question and stays silent on the third.
Correct: "No data yet. Upload your first contract — button below."

## 2. One task per screen, one main action

A screen has exactly **one** action in bronze. Everything else is a regular button or
link. Two main actions mean the person is choosing instead of working.

If there's more than one task, that's different screens or different tabs, not one
screen split in two.

## 3. Every screen has four states, and all four are drawn

| state | what must be visible |
|---|---|
| **empty** | why it's empty and what to do to make it appear |
| **work in progress** | what exactly is running and that it can't be clicked again |
| **refusal** | what happened and what to do next |
| **done** | the result and the next step |

An undrawn state turns into a white screen. Measurement 15–16 Aug 2026: three windows
out of three looked broken in exactly this way — every link in the chain worked, and the
person saw emptiness.

## 4. Waiting is always visible

A call to the core takes 1.7 seconds, to an expert — 13, a call to a device — 13 to 17.
For all of that time, the screen must not look unchanged.

| response time | what the person must see |
|---|---|
| under 1 s | nothing special |
| 1–10 s | the button is disabled and marked as waiting, in the same frame |
| over 10 s | plus words on what exactly is happening: "The agent is reading the database…" |
| end | a result or a refusal in words, the button goes back to work |

The state turns on **before** the call and clears in `finally`. Without `finally`, the
first error leaves the button disabled forever. A spinner with no caption after ten
seconds is indistinguishable from a hang.

```js
async function сОжиданием(кнопка, подпись, действие) {
  const было = кнопка.textContent;
  кнопка.disabled = true;
  кнопка.textContent = подпись;
  try {
    return await действие();
  } finally {
    кнопка.disabled = false;
    кнопка.textContent = было;
  }
}
```

## 4b. Microphone and camera don't work in the OS window

**Measurement 20 Aug 2026, confirmed on two independent products** — a tender system
and HR Desk. The OS window opens the page in a sandbox with this set:

```
sandbox="allow-scripts allow-forms allow-popups allow-modals allow-downloads"
```

There's no `allow-same-origin`, no `allow=` attribute, no
`allow-popups-to-escape-sandbox`. So `getUserMedia` is rejected, and working around it
with a separate window doesn't help either: the popup inherits the same sandbox.

**The most expensive part here isn't the refusal, it's the advice.** The sandbox
answers with `NotAllowedError` — exactly what a person answers when they click "Deny".
In both cases products write "allow access in system settings", and the person goes to
settings, where everything is already allowed. A dead-end piece of advice is worse than
an honest "can't do it".

You can tell them apart like this:

```js
async function можно_ли_писать_звук() {
  // The sandbox with no common origin gives the page a "null" origin.
  // That's a sign of the store window, not of a human refusal.
  const в_песочнице = window.origin === "null" || (() => {
    try { localStorage.setItem("_p", "1"); localStorage.removeItem("_p"); return false; }
    catch (e) { return true; }
  })();
  if (в_песочнице) {
    return { можно: false, причина: "окно_магазина" };
  }
  try {
    const поток = await navigator.mediaDevices.getUserMedia({ audio: true });
    поток.getTracks().forEach(д => д.stop());
    return { можно: true };
  } catch (e) {
    return { можно: false, причина: e.name === "NotAllowedError" ? "человек_запретил" : e.name };
  }
}
```

Then the messages differ:

| reason | what to tell the person |
|---|---|
| `окно_магазина` | "Recording sound isn't available in this window. Upload a ready-made file — button below" |
| `человек_запретил` | "Microphone access is denied. Allow it in your browser settings and try again" |

**Checking that "a stream was returned" is NOT ENOUGH: the track can be muted.**
Measurement 25 Aug 2026 on a live product: in the desktop window `getUserMedia` wasn't
rejected, a stream came back, the record button turned on, the level bar moved — and the
recording came out empty. To a frame without microphone permission, the browser hands
back a stream with a muted track, and the app can't tell that apart from the person
being silent. This is worse than an honest refusal: the product looks like it's working
and loses the user's recording.

So after getting the stream, you measure the sound instead of trusting it:

```js
const дорожка = поток.getAudioTracks()[0];
if (!дорожка || дорожка.muted || дорожка.readyState !== "live") {
  return { можно: false, причина: "поток_немой" };
}
// and 300 ms after start — whether the level moves at all
```

| reason | what to tell the person |
|---|---|
| `поток_немой` | "The window didn't get sound from the microphone. Record the file your usual way and upload it — button below" |

**What the product should do today.** Accept a ready-made recording file: the person
records it their usual way and uploads it. Or record sound ON THE DEVICE via an expert
(`experts/mic_record.py`): the listener opens the microphone, the window gets back the
finished text, and the sandbox is irrelevant. Transcription on the device works either
way — it never touches the window's microphone.

## 4c. Layout and script in the sandboxed window: three recurring traps

A measurement by the FDE track across several products — all three repeated from chat
to chat.

**The height of a full-screen column is set with `height`, not `min-height`.**
`min-height:100vh` does NOT cap the height: the flex column stretches to fit its content
and runs off the bottom of the window (measurement, 860px window: section 1127px,
"emptiness" −324). The tell is that the page doesn't scroll, but the content is cut off.
Use `body{height:100vh; overflow:hidden}` and scroll inside the section; check
`main.bottom ≤ innerHeight`. In a narrow window, return to `height:auto`.

**Flex children in a fixed-height window need `flex-shrink:0`.** Otherwise they
collapse, and content disappears without an error.

**Inline `onclick` in generated strings is a landmine.** A lost `class` quote or a
backslash breaks the entire script at once, and the button silently stops responding to
clicks. Replace it with `data-*` plus delegation — then the click path can also be
checked by machine (with a real click, not a function call; canon H63, H74).

## 5. Interface text is part of the interface

- **A button promises a result, not an action.** "Build the report", not "Send".
- **A refusal says what to do.** "Failed" is useless. "Key not accepted: check it in the
  service settings" is useful.
- **"No data" is a legitimate answer from the product.** A made-up answer costs more
  than a refusal: a lie looks like it's working.
- **Address the person informally, consistently across the whole window.**
- **No error codes shown to the person's face.** The code goes into the log, the person
  gets words.

## 5b. Form validation can silently turn itself off

Measurement from the "Agent 1C" chat, 20 Aug 2026. New Chrome compiles the `pattern`
attribute with the v-flag. A character class with a trailing hyphen or dot
(`[A-Za-z0-9_.-]`) doesn't compile in v-mode — and the browser **ignores the entire
`pattern` attribute**: the field accepts any input, and the console only shows "Invalid
regular expression /v". Escape the hyphen and the dot: `[A-Za-z0-9_\.\-]`. A silent
class: validation looks like it's working, and it isn't.

## 6. Don't show what the person can't do

A button that always answers with a refusal is a defect. If the action isn't available,
show the reason in the button's place: "Connect the service to send emails." This saves
the person an attempt and explains what to change.

## 7. Choosing the form for the task

| the person's task | form |
|---|---|
| compare many items of the same type | a table: rows are uniform, the eye compares by column |
| pick one out of a few | cards: each has its own image and its own promise |
| work with a list and details | a list on the left, details on the right |
| get through a long input once | a step-by-step wizard, no step longer than a screen |
| watch a long-running job | a log: rows are added at the top, the latest one is visible |

Cards for twenty records of the same type is the most common mistake: comparison
becomes impossible.

## 8. The Extella design code

Paste this paragraph into the generation rules in full.

> The interface is part of Extella, not a separate product. Use only these tokens:
> fonts **Nunito** (the whole interface: text, buttons, tabs, fields), **Source Serif 4**
> (headings), **JetBrains Mono** (section labels and machine text only);
> light theme — background #FAF9F5, surfaces #FFFFFF/#F5F3EC, text #0A0A0A, accent #C57E33,
> petrol #2F6B66, borders #D7E0DC; dark — background #0A0A0A, surfaces #141414/#181818,
> text #F5F3EE, accent #D4944A, borders rgba(243,238,229,.09).
> Font sizes only 11 / 13 / 15 / 20 / 26, nothing smaller than 11px exists; weights 400 / 500 / 600.
> Spacing is a multiple of four: 4 · 8 · 12 · 16 · 24 · 32 · 48, no values outside the scale.
> Radii: cards and panels 12, small controls 8, action buttons are pills (999),
> round icon buttons 50%. No other radii exist.
> The mandatory rule `button,input,select,textarea{font-family:inherit}` — without it
> the browser sets buttons in Arial.
> Bronze is for action only, and there is exactly one main action per screen; petrol is for system only.
> 1px borders instead of shadows, no gradients, no emoji, no all-caps,
> no periods in headings, no custom logo and no custom theme or language switcher.
> Headings are set in the Source Serif 4 serif with no negative tracking — a bold
> sans-serif in a heading is forbidden.
> Take the theme and language from the host's `etb_theme` and `etb_init` messages (light = the
> `data-lm` attribute on `<html>`). Text is informal (ты), a button promises exactly what it does,
> any error says what to do next.

The rule's author is Extella's design owner. Deviation only by their written decision.

## 9. Screen skeleton

Start here, not from a blank file.

```html
<style>
  :root{
    --фон:#FAF9F5; --поверхность:#FFFFFF; --вторая:#F5F3EC;
    --текст:#0A0A0A; --акцент:#C57E33; --система:#2F6B66; --граница:#D7E0DC;
  }
  html[data-lm=false]{
    --фон:#0A0A0A; --поверхность:#141414; --вторая:#181818;
    --текст:#F5F3EE; --акцент:#D4944A; --граница:rgba(243,238,229,.09);
  }
  body{background:var(--фон);color:var(--текст);font:400 15px/1.5 Nunito,sans-serif;margin:0}
  button,input,select,textarea{font-family:inherit}
  h1{font:400 26px/1.2 'Source Serif 4',serif;margin:0 0 8px}
  .метка{font:400 11px/1.4 'JetBrains Mono',monospace;color:var(--система)}
  .карта{background:var(--поверхность);border:1px solid var(--граница);
         border-radius:12px;padding:16px}
  .главное{background:var(--акцент);color:#fff;border:0;border-radius:999px;
           padding:12px 24px;font-size:15px;font-weight:600}
  .главное[disabled]{opacity:.6}
  .обычная{background:transparent;color:var(--текст);
           border:1px solid var(--граница);border-radius:8px;padding:12px 20px}
</style>

<main style="padding:24px;max-width:880px">
  <p class="метка">product name</p>
  <h1>What this screen does</h1>
  <p>One line about what the person will get here.</p>

  <div class="карта" style="margin:24px 0">
    <!-- empty / in progress / refusal / done — all four states live here -->
    <p id="состояние">No data yet. Start with the first step — button below.</p>
  </div>

  <button class="главное" id="действие">Build the report</button>
  <button class="обычная">Settings</button>
</main>
```

## 10. Acceptance checklist, by eye

Check it yourself before showing it to a person:

1. Opened the window for the first time — is it clear what to do? If you had to read to
   find out — redo it.
2. Clicked the main button — is it visible that work has started, and is a repeat click
   blocked?
3. Turned off the network and clicked — does the refusal explain what to do, instead of
   showing a code?
4. Empty, in progress, refusal, done — are all four states drawn?
5. Dark theme — is it readable? Light theme — also?
6. Not a single color outside the palette, not a single emoji, not a single all-caps?

## What the machine checks

From the `extella-agent-standards` repository:

```bash
python3 tools/check_design_rule.py            # the design-code paragraph is present and complete
python3 tools/check_brand_copy.py файл.html   # colors from the palette, forbidden words
python3 tools/check_waiting_state.py файл.html # waiting is visible, repeat clicks are blocked
python3 tools/check_self_check.py путь        # the product's self-check can actually fail
```

The machine catches violations. It doesn't check the screen's clarity — that's items
1–7 and the checklist.
