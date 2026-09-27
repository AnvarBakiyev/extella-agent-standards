# Skill vs. expert: one repetitive task, 100 runs, same model both ways

A small, reproducible measurement of what "write the code once" saves compared with
"let the model apply the rule every time." Run on 27 September 2026.

The Russian originals are next to this file: `metodika.md` (method, written before the run)
and `otchet.md` (report). Raw data: `results.json`. Code: `zamer.py`, `expert_code.py`.

## The question

For a task that repeats, how many tokens does it cost to have a model apply a written rule on
every run (a *skill*), versus having the same model write the code once and then run the code
without the model (an *expert*)? And where is the break-even?

## The task

Order approval, three rules — the same example used in Extella's explainer video:

1. order total = Σ quantity × price;
2. total > 200 000 → route `wait_for_manager`, else `reserve`;
3. any line where quantity > stock is a shortage; list those items.

Chosen because it has an unambiguous ground truth: the right answer is computed, so every
model error is visible.

## The data

100 synthetic orders, fixed seed (`dataset.json`, seed 20260927): 1–3 lines each, totals
from 290 to 3 392 000; 71 orders exceed the threshold, 56 contain a shortage. Ground truth
computed at generation time.

## The two arms

**Skill.** For each order the model receives the same rule text (as a Claude Code skill would)
plus the order, and answers with JSON. 100 calls. We count input and output tokens per call,
correctness against ground truth, and latency.

**Expert.** The same model, given the same rules, writes a Python function once. If the code
fails the ground truth on any of the 100 orders, the model is shown one failing example and
tries again; **every attempt is charged to the creation cost** (max three). The passing code
is then run on all 100 orders with no model in the loop.

Same model on both sides, or the comparison is not fair.

## Instrument

`qwen3.5:9b` locally via Ollama, temperature 0, thinking off. Ollama reports exact
`prompt_eval_count` / `eval_count` — tokenizer counts, not estimates.

Why a local 9B and not Claude: no API key belongs in this repository, and the platform agent
was unavailable at the time. What follows from that, stated up front: **token volume per run
transfers across models — it is set by the length of the rule, the order and the answer.
Accuracy of the skill arm does not transfer**: Claude would err far less often than a 9B model
on this task.

## Results

| | Skill (model per run) | Expert (code once) |
|---|---|---|
| Tokens to create | — | **403** (233 in + 170 out), one attempt, 17 s |
| Tokens per run | **328.7** (288 in + 41 out) | **0** |
| Tokens for 100 runs | **32 871** | **403** |
| Correct out of 100 | **28** | **100** |
| Time per run | 4.8 s | 10 000 code runs: 0.02 s |
| Break-even | | **run 2** (403 ÷ 328.7 = 1.23) |
| Ratio at 100 runs | | 82× |
| Ratio at 1 000 runs | | 816× (linear — the skill pays per run, the expert once) |

Determinism check: the skill arm re-run on the same 10 orders changed **0** answers —
consistently wrong is still wrong.

Error profile of the skill arm (a single run can miss several fields): total wrong in 60 runs,
shortage list wrong in 34, route wrong in 11. JSON was well-formed in all 100. The errors are
arithmetic and comparison — exactly the class of error code does not make.

**The same model that cannot reliably add up an order when asked to, writes correct code for it
on the first attempt.** That is the result we consider most important, and it is not about money.

### On-device check

The model's code was wrapped unchanged in the Extella expert contract, saved as
`zamer_soglasovanie_zakaza`, and executed through the platform on a laptop (not the machine
that wrote it) on order 1004 from the dataset: total 1 666 200, route `wait_for_manager`,
two shortage items — an exact match with ground truth, no model call, ~8 s round trip
including platform routing.

## What we do not claim

- That experts are "82× cheaper" in general. Only: on this task, at 100 repetitions, with
  break-even at run 2. The ratio scales linearly with repetition count and can be inflated
  by choosing a large count; break-even cannot.
- That the skill arm's 28 % accuracy applies to Claude. It applies to this 9B model.
- That this task is representative. It is simple and deterministic on purpose. Where the job is
  language and judgement rather than a rule, a skill is the right tool.
- That the first run is cheap. Creation is the expensive part; this pays only on repetition.
- That our skill prompt is typical. At 288 input tokens it is the *most favourable* case for
  the skill arm. Real skills and agents carry tool definitions and intermediate results into
  context on every step; Anthropic's own example measured 150 000 tokens where code took
  2 000. Our measurement understates the code path's advantage, not overstates it.

## Cost illustration

Per published API prices on 27 September 2026 (claude.com/pricing), applied to token counts
measured on a different model — order of magnitude only:

| Model ($/M in · out) | Skill, 100 runs | Skill, 10 000 runs | Expert, creation |
|---|---|---|---|
| Haiku 4.5 (1 · 5) | $0.05 | $4.91 | $0.001 |
| Sonnet 5 (2 · 10) | $0.10 | $9.83 | $0.002 |
| Opus 5.5 (4 · 20) | $0.20 | $19.65 | $0.004 |

The dollar amounts are small because the task is small. The point is the shape of the curve:
one side grows with every run, the other does not.

## Reproduce

```
ollama pull qwen3.5:9b
python3 zamer.py
```

Writes `results.json`, `expert_code.py`, `zamer.log`. To repeat on another model, replace the
`вызов()` function in `zamer.py`; nothing else needs to change.

## Known limits, in the order people will raise them

1. One model, and a small one. Repeating on Claude requires only a key.
2. One task. Two or three more are needed, including one where the skill *should* win.
3. The task needs no data from the device, so the strongest property of on-device execution
   is not exercised here. That is a separate measurement.

## Context

Anthropic's engineering post "Code execution with MCP" (4 November 2025) recommends letting
the agent write code against its tools instead of calling them one by one, and notes that
"running agent-generated code requires a secure execution environment with appropriate
sandboxing, resource limits, and monitoring." Extella's interpretable containers are one
implementation of that environment: each expert is code with its own runtime, executed where
the data is, in a language the interpreter controls. The approach is described in published
international application WO 2026/102343 (priority date 8 November 2024).
