# We measured the thing Anthropic's code-execution post left as a caveat

*27 September 2026 · Anvar Bakiyev, CEO, Extella. Runtime designed by Timur Ryspekov, CTO and co-founder.*

On November 4, 2025, Adam Jones and Conor Kelly published "Code execution with MCP": let the agent write code against its tools instead of calling them one by one, and token use on a Drive→Salesforce workflow fell from 150,000 to 2,000. They also wrote the sentence this post is about: "Running agent-generated code requires a secure execution environment with appropriate sandboxing, resource limits, and monitoring."

We have been building that environment since 2024. Here is a small, honest measurement of what it does — and what it doesn't.

**The setup.** One repetitive task (an order-approval rule with three conditions), 100 orders with a computed ground truth, one model on both sides at temperature 0. Side A: the model reads the rule and the order every time, like a skill. Side B: the model writes the code once, then the code runs without it.

**The numbers.** Skill: 329 tokens per run, 28% correct. Expert: 403 tokens to create (one attempt), 0 per run after that, 100% correct on all 100. Break-even at run 2. The ratio grows linearly with repetition (82× at 100 runs), so the number to quote is the break-even. Determinism check: rerunning the skill on the same 10 orders changed 0 answers — consistently wrong is still wrong.

**What we don't claim.** The model is a local 9B (qwen3.5), not Claude — token volume transfers, accuracy of the skill side does not. The task is simple and deterministic on purpose; where the job is language rather than rules, a skill is the right tool. Creation is the expensive part: this pays off only on repetition. And our skill prompt, at 288 input tokens, is the most favourable case for the skill side; real agents carry tool definitions into context on every step, so this understates the code path's advantage.

**What the container adds beyond the pattern.** Each expert carries its own environment (incompatible stacks in one pipeline), runs where the data is, and is written in a language the interpreter controls. In addition to sandboxing, that gives a second layer: remove "delete" from the language and no generated code can express it. The runtime was designed by our CTO and co-founder Timur Ryspekov.

Published international application WO 2026/102343, priority date November 8, 2024. We'd like Extella experts to be usable as Claude skills that execute on the user's device. If that's interesting to the MCP and Developer Platform teams, we're easy to find.

Method, data and code: [README](README.md) in this folder — `metodika.md` (method, written before the run), `otchet.md` (report), `results.json`, `zamer.py`, `expert_code.py`.
