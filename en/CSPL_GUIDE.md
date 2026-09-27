<!-- source: CSPL_GUIDE.md sha256:3e93c4bec635d05db77f7a740c369bd11a0c54b200c406004f4934895dab9720 -->

# CSPL: when to use it and how

Verified by live runs on 27–28 Aug 2026. Everything called "working" ran on the platform,
not in local emulation: the difference between "the code is written" and "the language is
wired in" cost a whole day and is described here separately.

## What CSPL is

An expert is **source code plus a language name**. The `cspl` field declares which
language the source is written in; the default is `fython`. A language handler is a
separate container on the device that receives the expert's source and does whatever it
wants with it: executes, compiles, parses, renders.

From this comes the main property: **there is one handler for the whole class of
experts**. Editing the handler changes the behavior of every expert in that language,
without rewriting a single one of them. Measured result: three experts in the `sql`
language all got a row limit and phone masking at once, after a single edit to the
handler.

## When to use it: three families

| family | what's in the source | what gives you safety | when to pick it |
|---|---|---|---|
| **intent protocol** | an operation name and fields | the client's policy | access to someone else's system: a database, mail, files |
| **narrow language** | text in a restricted language | the grammar | the model writes the source itself |
| **full language** | code in C, Go, Rust | trust in the code | speed, hardware, ready-made libraries |

**Intent protocol** — when the deal is blocked by the client's fear, not by a lack of
capability. The model names the operation, the handler checks it against a policy that
sits with the client and never enters the prompt. That's how `one_c` is built.

**Narrow language** — when the model writes the source. The dangerous thing isn't
forbidden by policy — it **cannot be expressed**: the `sql` language has no `UPDATE`
keyword, the slide language has no way to say "execute." Grammar is cheaper than any
check and doesn't depend on configuration.

**Full language** — when you need speed or a library that fython doesn't have. Grammar
restricts nothing here, so the code has to be trusted: written or reviewed by a person.
Policy still decides which languages are allowed on the device, and holds the limits on
time and response size.

## When you do not need your own language

If the task can be solved in `fython`, solve it in `fython`. A language of your own is
justified by three reasons: narrowing permissions to the point where the dangerous thing
cannot be expressed, getting someone else's runtime (a compiler, an engine), or giving a
person a readable source that can be edited in words. A language added for its own sake
adds a container that will have to be maintained.

## How to wire in a language

The handler is registered as an ordinary `fython` expert:

```python
import disnet
d = disnet.Disnet(url="https://disnet.extella.ai")   # do not set save_directory
конверт = {"filtered_source_code": "", "func_name": "", "args": None,
           "kwargs": None, "cspl": "<language>", "response_format": None}
d.container(code=<handler source>, func_name="<language>", container_path="<language>",
            args=None, kwargs=конверт, cspl_type="fython", push=False)
```

Run the registration pinned to a device: `targets=["<device_id>"]`.
Five conditions, without which this breaks silently, are listed in
`DEPLOY_REQUIREMENTS.md`, H68.

## How to write a handler

The envelope that arrives at the entry point (measured 28 Aug 2026):

| field | what it holds |
|---|---|
| `filtered_source_code` | the expert's source; **`code` arrives empty** |
| `kwargs` | run parameters (the call's `params`) |
| `func_name` | the expert's name, not the language's |
| `args`, `cspl`, `run_time` | internal/service fields |

The handler must: accept the source from both fields; substitute `{{parameters}}`; look
for the external tool itself, because the service has a stripped-down `PATH`; return a
dictionary with a status and a clear rejection message.

Do not use regular expressions in the handler: backslashes do not survive the trip
through fython, and the check silently stops working — a valid request was rejected as
invalid. Word-by-word comparison is more reliable.

## Examples that work

**Narrow language for reading a database.** The `должники` expert, `cspl=sql`:

```sql
SELECT name, phone, amount FROM clients WHERE amount > 0 ORDER BY amount DESC
```

Running it with the parameters `database`, `maxRows`, `maskColumns` returned two rows
with masked phone numbers and an honest truncation flag. An expert with `UPDATE` in its
source was rejected with the words "the sql language allows only a read query."

**Full language for a calculation.** The `считатель_долга` expert, `cspl=go`: parses the
rows, computes the total and the average, and renders a verdict. It returned
`{"всего": 1680000, "клиентов": 3, "среднее": 560000, "вердикт": "долг превышает миллион"}`.

**Document language instead of an action.** The `отчёт_по_долгам` expert, `cspl=slide`:

```
# Долги клиентов

## Итог по базе
!число {{млн}} | миллиона тенге всего долга
```

The handler escapes all text, so markup cannot be injected into the slide: `<script>`
becomes a visible string, not code.

**A pipeline of incompatible languages.** `sql` → `go` → `slide`: data, computation,
document. No link can call another; compatibility comes from a shared contract — data
travels as a JSON string. That's N languages instead of N×N bridges between them.

## What to remember when chaining links

The platform returns the result in a Python-style representation, not JSON: you need to
parse both ways, otherwise a successful link looks like a failure. The contract allows
whitespace in the JSON — a naive substring search for `"total":` returned zeros on
correct data. Compiled languages are strict: an unused import in Go breaks the build, and
that shows up in the failure text, which is better than a silent zero.
