<!-- source: AGENT_METHOD.md sha256:79f5d1ab4768ba1cdf0d4dc29aeb18f986d494164a471bdc67416628df3a7a4a -->

# Building agents on Extella: what the measurements showed

Instructions for agents (Claude, Codex and others) that build agents and apps on Extella. Compiled on 10.11.2026 from measurements taken September–November 2026. Every rule below was checked in practice; where it rests on a single experience, that is stated.

**Status: same as `LAB.md`.** The measurements were taken on our own tasks, and the task worlds are synthetic (limits in §7a). This is a method and numbers, not canon: mandatory requirements live in `DEPLOY_REQUIREMENTS.md`. The platform facts in §5 were taken on the live platform; if a fact is more than a month old, re-check it.

Before you start, read the README, `AGENT_BUILD_GUIDE.md`, `APP_FROM_MODULES.md` and `CSPL_GUIDE.md`. This file does not replace them; it adds what the measurements showed: what works, what doesn't, and why.

## 1. The main principle

**The model decides, code computes, the environment keeps order and data.**

A small model (Qwen 9B on a laptop) understands text well and chooses what to do. It is bad at computing over many rows at once and bad at holding a long sequence of steps. Give everything exact to an expert (a saved program). The order of calls is held by the environment, not by the model.

Numbers from the measurements (50 variants of each task, scored against a reference):

| task | model alone | model + checks without code | model + expert, order held by the environment |
|---|---|---|---|
| approving an order against 13 rules | 1 of 50 | rules and concepts: 4–5 of 50 | 50 of 50 |
| weekly purchasing plan for a chain (3 stores, 6 items, 3 suppliers) | 3 of 50, overpaying +88 % | fewer violations, overpaying +120…159 % | 50 of 50, on par with the optimizer |
| same, expert written by a large model | | | 20 of 20, 5 % cheaper than the optimizer |

The confirmed conclusion: **experts and languages work as a mechanism, and their author sets their quality.** The small model reliably calls an expert and does not spoil the result. If the author writes a better expert or language, every agent that uses them immediately works better, with no retraining.

The "model + checks without code" column shows a bad language, not a bad method: our purchasing language worked at the level of quantities, so the model still did the computing itself. How to build a language properly: §3a.

## 2. What an agent is made of and what each part gives

| part | what it is | what it gives, measured | when to use |
|---|---|---|---|
| agent | model + instructions + tools | the base | always; don't touch the instructions (see §5) |
| rules | short directions to the agent | knowing the rules barely raises a small model's accuracy: 4–5 of 50 | few and short; other people's profile rules get in the way |
| concepts | fact cards (products, deadlines, reference data) | facts: the "deadline" field 5 → 38 of 50; without cards the model invents facts in 43 of 50 | for facts the model doesn't know; keep the query to a concept short and specific |
| expert | a saved program (Python, fython) | exact computation: 50 of 50 | anything that is computed, checked, optimized |
| handler (narrow language) | a task language + a program that executes and checks it | NVIDIA Nemotron on 3D parts: 0 of 30 in Python, 17 of 30 in the task language | when the model has to write a program, not pick a call |
| device | the machine where the expert runs (`targets`) | data stays where it is | always pass `targets` |
| sleep | fine-tuning the small model on its own corrections | 4B: 56 → 88 % of corrections | last, if an order or form error remains after the experts |

## 3. Order of building an agent

1. **Break the task down.** Write out what in it is exact (computation, checks, optimization, reconciliation) and what is linguistic (understand a note, pick an option, explain). The exact part goes to experts, the linguistic part stays with the model.
2. **Reference and examples first.** Before building, collect a set of tasks with correct answers or a scoring method (50 if possible) and write down your prediction of the outcome. Without this you can't tell whether things got better.
3. **Experts for the exact part.** The best expert is written by a large model when it gets the separate task "do this as well as possible": in our measurement it wrote a stochastic optimization in 15–20 minutes that beat our fast optimizer by 5 %. Check the expert on the example set and at scale: that same code broke on a chain of more than 9 stores because it parsed store numbers as a single digit.
4. **If the model assembles a solution from parts, build a task language per §3a.** Its checks must check meaning, not form. If a check lets through a plan that does not cover demand, the model learns to write short safe plans: fewer violations, worse money (+159 %). A refusal must say what is wrong and in which line: "milk, S2, Friday, 340 l short".
5. **The environment holds the order of calls.** Give the model tools step by step: one tool is open on a step, the rest are unavailable. If the model answers without calling the required tool, reply "Call X first". Data the model could distort is filled in by the environment, not by the model. On the orders task this gave 50 of 50 instead of 12 of 50.
6. **Leave decisions to the model.** Choosing a strategy, reading a note ("festival near store S2 on Friday"), answering a person. In purchasing, reading the notes saved another 3 % on holiday weeks.
7. **Rules: few.** Each rule must change something in behaviour. Don't copy general profile rules into the agent.
8. **Concepts: for facts.** Catalog, reference data, deadlines, codes.
9. **Sleep: last,** and only on what is visible in the corrections log.
10. **Run it as a ladder.** Add one part at a time and measure each step on the same set. Write the result next to the prediction, including the predictions that didn't come true.

## 3a. How to design a task language

A task language is needed when the model must compose a new solution from parts: a part, a circuit, a route, a contract. If it is enough for the model to choose a call and its parameters, use an expert.

1. **The level of intent, not of result.** The model writes what is needed ("a socket with clearance here", "S1 milk: cover demand with a 1.1 margin, buy from Wholesale", "festival on Friday near S2, ×1.8"), and the language derives the exact quantities. If in the language the model writes numbers that need computing, the language is bad: in purchasing such a language gave +120…159 % against the optimizer; a strategy-level language gave +4.7 %.
2. **Precision is built into the language.** Joints, clearances, supports, minimum orders, shelf lives are built and enforced by the language itself. The language must have no words that can express a violation. A check after generation stays, but for what cannot be built in.
3. **An error names the line and the reason.** That way the model fixes the program on the second attempt (in 3D: 4–6 tasks of 30 solved after the first error). A general error without a line does not help: in Python the model sent the same program again.
4. **The language grows from the model's errors.** Each model error either corrects existing grammar tokens or creates new ones; depending on the error type a check is added as well (forma 3.0 → 3.1 → v31e added print and joint rules). This is done automatically by a separate agent set up for such edits, and a strong model suits it best: a strong model tunes the language for a weak one (platform architect, 10.11.2026). The language adapts to the model; the model is not retrained.
4a. **A rule as a forbidden combination.** The platform architect's example: the language has an action `go` and a signal `red`. The check forbids them to stand together and replies "you may only go on green". This way one persistent model error is closed by one language rule. This is what "read 10 as 15" means: don't change the model, write a rule that brings its answer to the required one.
4b. **The customer defines correctness.** What counts as correct is decided by an industry reference (benchmark) or a person at the company. If the company counts differently from the industry, the language and checks are built for the company.
5. **One language per domain.** The same word means different things in different tasks, so a language and its handler live in their own container.
6. **A library of helpers on a general language does not replace a task language.** Python with `grow` and `check` helpers gave 0 of 30 where the task language gave 17 of 30: the model still had words it could get wrong.

## 3b. What a handler does

A handler executes a task language: the model invents, the handler does everything else with its program. Functions we have checked in practice:

| function | what it does | example |
|---|---|---|
| parsing | reads the program, finds unknown words | the purchasing language |
| checking | rules and constraints, refusal with line number and reason | forma, the 13 order rules |
| turning intent into exact quantities | "a socket with clearance" becomes geometry | forma: joints, 45° supports |
| execution | builds the part, computes the plan, runs a command on the machine | forma, the ee_shell and ee_interp handlers |
| simulation before answering | runs the result through scenarios | 200 week scenarios in purchasing |
| feedback to the model | error by line, the program with marks at the wrong lines | forma v3 |
| calling others | other experts and languages, other machines, a model inside the handler | ship → customs, notes via Ollama with a response schema |

**When to check (platform architect's answer, 10.11.2026).** By default the check looks at the finished program and returns an error. For very small models (around 1B) it is better to check during generation, in chunks or down to every token; the price is speed, since generation and checking alternate. In our measurements on 9B the check always ran after generation, except for the notes handler, where the model was given a response schema.

**A handler is assembled from experts (T3D).** In the latest version of T3D the handler assembles its body from experts at install time (via `get`). The body can differ between companies depending on parameters: if a company considers something else correct, an expert changes and the handler is built differently for it. We have not tested this path; it is described from the platform architect's words.

**Isolation in the CSPL sense.** Each computation and each meaning lives in its own container, both at the action level and at the level of computations and libraries. So any part can be thrown away and redone without touching the rest. This is not protection of programs from each other but a split of the work into replaceable parts.

**Careful with "hallucinations are impossible".** The check doesn't let the model break what is written in the language and the rules. But within what is allowed the model can still choose badly: in purchasing, short plans passed the form check and cost 159 % more. Outside, say "breaking the written rules is impossible", not "hallucinations are impossible".

## 4. Large and small model

Comparison on purchasing (10 identical variants, scored by one function):

| who solves | correct | price vs. optimizer | at 30 stores | five repeats of one input |
|---|---|---|---|---|
| large model in its head | 10 of 10 | −1.1 % | 1 violation in 2, 3–4 % more expensive than the expert | 5 different plans, price within 1.4 % |
| large model writes its own code | 10 of 10 | −5.0 % | | |
| small model + expert from the large one | 20 of 20 | −4.9 % | no violations | one and the same plan |

What follows:
- Don't claim that a small model with the environment is smarter than a large one. At small scale the large model manages in its head.
- The best role for the large model: **author of the expert, once.** The small model runs that expert every day on the customer's machine: no cloud, no tokens, one answer per input.
- The gap grows with scale: the large model in its head starts breaking rules, the expert doesn't.

## 5. Technical platform rules

Checked on the live platform. If a fact is more than a month old, re-check it before building on it.

**Calls**
- REST: `POST https://api.extella.ai/api/expert/run` with `{"name", "params", "targets": [device_id]}`. Always pass `targets`. Without it the call goes to the wrong place: the author's machine, the cloud, or the agent's default device.
- `targets` takes the **device_id**, not the `target_id` from `search_targets`. With a `target_id` you get "Target … is unavailable" while the device is alive.
- A long call returns a `task_id` and the line "deferred, use task_id as reference". That is not the result: poll `tasks/check` until the outcome arrives.
- One call to a device takes 5–9 seconds. The time goes to the queue and the listener's polling, not to execution. Don't make a hundred small calls through the platform one by one: run the fan-out inside a single expert on the device.
- The `app-agent/run` response is nested four layers deep (text, OS envelope, core envelope, the expert's JSON string). A parser limited to four steps loses the last layer: leave headroom and test on a real response.

**Experts**
- The platform calls **the first function in the expert's file**, not the function named after the expert. Put the function you need first, helper code below.
- Packages: `$extens("include.py")`, then `include("import X", ["extella-pip install X==version"])`. Pin the version: `pulp` 3.x changed its interface, and code written for 2.9 fails.
- `expert/save` cuts off the trailing newline. Compare `code.rstrip("\n") == expert_code.rstrip("\n")`.
- Save a product's expert in the product agent's scope (`X-Agent-Id`, `global: false`) and read it back after writing.
- The platform does not pass the API key to an expert. Call the model from an expert via the product agent's `/api/agent/run`.

**Handlers (narrow languages)**
- Registration: a fython expert holding the handler text calls `disnet.Disnet(url="https://disnet.extella.ai").container(code=…, func_name=language, container_path=language, kwargs=…, cspl_type="fython", push=False)`.
- The handler text must contain no backslash at all: `chr(10)` instead of `"\n"`, `[0-9]` instead of `\d`. Otherwise registration "succeeds" and the call gives "'str' object is not callable".
- After registration check: `type(disnet.Disnet(save_directory=…).run(container_path=language))` must be function.
- The built-in modes `shell`, `interpreter`, `parallel_task`, `wait_tasks` don't exist on devices. You need your own handlers.
- The listener on a Mac runs with its own Python and without Homebrew in PATH. Call external programs by full path.

**Agent**
- Never overwrite the agent's `instructions` field: it holds the platform core (~109 thousand characters), and writing `agent/update {"instructions": …}` erases it. Add the hints you need as a rule (`add_rule`).
- `/rules/list` returns the profile's general rules together with yours. A small model loops on them and drops to 0 of 50. In measurements and in working agents, filter the rules down to your own.
- An agent is attached to a product only when the listing is created (`publish-stream` with `source_id`, `source_type=agent`, `attach_agent=1`).
- Installing from the store: `deploy_mode: new` copies the author's instructions and tools; `existing` doesn't carry them over. Install a product with an agent as a new agent.

**Local model**
- There is one Ollama on the machine for everyone. Different `num_ctx` values across parallel clients cause starvation. Keep `num_ctx` at 4096 and don't run two heavy runs at once: a model step grows from a minute to 7–20 minutes.

## 6. How to measure

- Write the prediction before the run, next to the protocol.
- Compute the reference separately and cache it; score with one function for all steps.
- 50 variants for the final result. 20 is fine for scouting, but write the rule for topping up to 50 in advance (for example, "adjacent steps differ by less than 20 points, so we top up both").
- Record predictions that didn't come true too. They are what moves understanding forward.
- Compare against a large model on the same data, otherwise the conclusion "the environment is needed" isn't proven.

## 7. What can be said outside

- Allowed: "a small model on the customer's machine with the Extella environment does the job at optimizer level, with one answer per input, without the cloud"; "a large model writes the expert once, a small one runs it every day".
- Not allowed: "a small model is smarter than a large one"; expert versions and rollback as a finished feature (the platform doesn't have them yet).

## 7a. Limits of these conclusions

The measurements above are not the final word. What limits them:
- **Few domains.** Orders, purchasing, 3D parts, electrical panels. The purchasing and orders worlds are synthetic; we generated them ourselves.
- **The references are ours.** In purchasing the reference is computed by our own optimizer, so "0 % against the reference" on the step with that optimizer means "the model called it correctly", not "found the best plan".
- **Few models.** The small model is almost everywhere Qwen 9B (sleep on 4B), the large model is Claude as a subagent, NVIDIA Nemotron only in the forma measurement.
- **Small samples.** 50 variants per step, comparison with the large model on 10, repeats on one variant.
- **We made our own languages weak.** The purchasing language worked at the level of quantities; a good intent-level language (forma) was made by the platform architect, and we have not repeated it on our tasks.
- **Not measured:** constraining generation with a grammar, automatic evolution of the language from errors, the effect of program length on accuracy separately from the language level, other small models.
- **The platform core is closed.** `executor` and `disnet` are compiled. We know the behaviour from outside, not the internals, so we judge the inner mechanism of CSPL with caution.

If a new measurement disagrees with this file, trust the measurement and fix the file.

## 8. Where the code and data are

The test benches, measurement protocols and experts from the tables above live in the team's internal repository and are not published. If you need a sample (a handler, a REST client that waits for deferred tasks, a handler registrar), ask the Extella team for it.
