# 🎯 When Reasoning Wins — The Honest Calculus

> *The most expensive mistake in modern AI infrastructure is defaulting to a reasoning model on tasks where a base model does equally well at 1/20th the cost.*

Reasoning models are not universally better. They're better on a specific set of tasks and roughly equivalent (sometimes worse) on many others. This section is the honest task-by-task calculus.

---

## The Framework

For any task, three things determine whether reasoning is the right choice:

1. **Structural fit** — does the task have the "shape" reasoning models were trained on?
2. **Verifier availability** — is there a way to tell good outputs from bad?
3. **Marginal quality value** — does the cost delta pay off in your unit economics?

**All three must be positive for reasoning to win.**

---

## Task Category 1: Reasoning Clearly Wins

**Category signature:** structured problem with verifiable answer, decomposable into steps, benefits from deliberation.

### Multi-step math (word problems, symbolic manipulation)

**Why it wins:** the whole training distribution was this.

**Numbers (approximate, on standardized benchmarks like AIME, MATH):**
- GPT-4o baseline: ~35% AIME accuracy
- GPT-4o with best-of-8 + verifier: ~55%
- Claude 3.7 Sonnet extended thinking: ~65%
- o1 default: ~74%
- o1 high effort: ~78%
- o3 default: ~85%+

**Cost vs quality:** near-monotonic. More reasoning = better answer, up to a plateau around ~85% where marginal gains flatten.

**When to use:** any math tutoring, engineering analysis, scientific computation where the answer is symbolically checkable.

### Competitive coding (algorithmic, correctness-verifiable)

**Why it wins:** unit tests are perfect verifiers. RL on code with tests is directly in the training distribution.

**Numbers (approximate, Codeforces/HumanEval):**
- GPT-4o: solid on easy, unreliable on hard
- Claude 3.7 Sonnet: strong across the board
- o1/o3: dominant on hard algorithmic problems
- On simple "write a function to sort a list": no meaningful difference from a base model

**When to use:** competitive programming, complex algorithm design, novel data structure implementation, debugging with clear reproduction steps.

**When to NOT use:** boilerplate code, template completion, API-integration glue code — base models tie or win because "reasoning" adds latency without adding quality.

### Multi-step logic and deduction

**Examples:** constraint satisfaction, planning problems, formal proofs (with verifier), symbolic reasoning chains.

**Why it wins:** every step is verifiable. Deliberation compounds.

**When to use:** legal reasoning against a codified ruleset, compliance rule evaluation, formal verification, scheduling optimization.

### Complex analytical questions

**Examples:** "Analyze this financial statement and identify red flags. Cite each with specific line items and reasoning."

**Why it wins:** long-context analysis benefits from structured deliberation. Model can hold multiple pieces of evidence in reasoning, cross-reference, avoid premature conclusions.

**Caveat:** you need a verifier (LLM-judge on structured analysis, or human review). Without one, more deliberation ≠ more correct.

### Multi-hop retrieval-heavy tasks

**Example:** "Given these 5 research papers, synthesize the current state of X, identify open questions, and propose a testable hypothesis."

**Why it wins:** the model can hold retrieved context in reasoning while checking consistency across sources.

**Caveat:** hallucination risk increases with reasoning length if grounding is weak. Reasoning models can confidently reason to wrong conclusions if retrieval is bad.

### Debugging and root-cause analysis

**Example:** given error logs, code, and system state, find the root cause.

**Why it wins:** debugging is structured search over hypothesis space. Reasoning models are trained to enumerate and eliminate hypotheses.

**Real production win:** SWE-bench (real GitHub issue resolution) shows reasoning models with 20-40% absolute accuracy improvement over base models when combined with tool use.

---

## Task Category 2: Reasoning Is Overkill

**Category signature:** the task doesn't benefit from deliberation. A base model at fraction of the cost gives equivalent results.

### Simple factual QA

**Example:** "What's the capital of France?" "When was the Eiffel Tower built?"

**Why reasoning doesn't help:** answer is looked up, not derived. Reasoning generates internal deliberation that adds nothing.

**Numbers:** GPT-4o and o1 are within measurement error on simple QA benchmarks. Reasoning is pure overhead.

**Cost impact:** 20-50× more expensive per query. Latency 20-60 seconds instead of < 1 second.

**Verdict:** never use reasoning for lookup-style queries.

### Format-driven tasks

**Examples:** extract these fields from this document; translate this to French; convert this JSON to XML; summarize this paragraph in 50 words.

**Why reasoning doesn't help:** the task is one-shot pattern matching, not deliberation.

**Cost impact:** 5-20× more expensive.

**Verdict:** base model wins. Save reasoning models for tasks with actual decision structure.

### Classification and extraction

**Examples:** "Is this ticket a bug report, feature request, or question?" "Extract sender, date, and amount from this email."

**Why reasoning doesn't help:** discriminative tasks with clear categories. Base model with a good prompt matches reasoning model quality at fraction of cost.

**Cost impact:** 5-30× more expensive, latency degrades user UX.

**Verdict:** base model. If quality is an issue, use best-of-3 with a validator — much cheaper than reasoning.

### Real-time conversational UX

**Example:** chatbot where user expects sub-second first-token response.

**Why reasoning doesn't work:** latency. Reasoning models produce first token 5-60 seconds in. UX collapses.

**Verdict:** never use reasoning models in latency-sensitive interactive UX. Use a base model, and consider reasoning models only for opt-in "deep analysis" side workflows.

### Copilot-style inline suggestions

**Example:** autocomplete, inline code suggestions, writing assistant.

**Why reasoning doesn't work:** Copilot latency budget is < 500ms. Reasoning is DOA at that budget.

**Verdict:** base model, aggressive caching, small default with cascade escalation only when the user explicitly asks for depth.

---

## Task Category 3: Reasoning Actively Hurts

**Category signature:** deliberation degrades output quality. Reasoning model performs worse than base model.

### Creative writing with voice

**Why reasoning hurts:** deliberation stifles creative voice. The reasoning trace analyzes what "good" writing should be, and the answer becomes stilted and safe. Base models trained on RLHF for helpfulness/style produce more natural creative writing.

**Empirical:** measured evals (creative writing benchmarks, human raters) show reasoning models often *worse* on story quality, humor, voice.

**Anti-example:** using o1 for LinkedIn newsletter drafting produces flat, over-structured prose. Use Claude Sonnet or GPT-4o.

### Empathetic dialogue

**Why reasoning hurts:** empathy is fluent, immediate response. Deliberation reads as clinical or robotic. Users feel unheard.

**Verdict:** for emotional support, mental health, sensitive customer interactions — base model. Reasoning models are the wrong emotional register.

### Ambiguous questions where a base model would just answer

**Example:** "What's the best way to learn Python?"

**Why reasoning hurts:** reasoning models sometimes refuse to commit on ambiguous questions, listing all considerations and refusing to recommend. Users want an opinion.

**Base model behavior:** confident recommendation with caveats.

**Reasoning model behavior:** 15-second deliberation, followed by "it depends on your goals, learning style, existing experience..."

**Verdict:** for advice-giving with acceptable ambiguity, base models often produce better UX.

### Simple summarization

**Why reasoning hurts (marginally):** deliberation can inject artifacts. Sometimes reasoning models "reason about" the summary structure and produce meta-commentary or over-organized output. Base models produce cleaner summaries.

---

## The Task Category Matrix

| Task type | Base model | Reasoning model | Recommendation |
|---|---|---|---|
| Multi-step math | 35% | 78%+ | **Reasoning** |
| Competitive coding (hard) | 25% | 70%+ | **Reasoning** |
| Formal logic | 40% | 85%+ | **Reasoning** |
| Root-cause debugging | 55% | 80%+ | **Reasoning** |
| Multi-hop RAG synthesis | 65% | 78% | **Reasoning if budget allows** |
| Boilerplate code | 90% | 90% | **Base** (cost) |
| Simple factual QA | 92% | 92% | **Base** (cost, latency) |
| Extraction/classification | 88% | 89% | **Base** (cost) |
| Format translation | 94% | 94% | **Base** (cost) |
| Creative writing | 75% | 65% | **Base** (quality) |
| Empathetic support | 80% | 60% | **Base** (UX) |
| Interactive chat | UX wins | UX loses | **Base** (latency) |

Numbers are illustrative directional patterns from typical evals, not exact benchmarks.

---

## The Router Implication

The task categories above should drive your model router (see [Folder 2 Model Routing](../../2_cost_engineering/03_model_routing/README.md)).

**Recommended routing tiers for a general-purpose LLM product:**

```
Tier 1 — Cheap fast model (mini-class):
  Simple factual QA, extraction, classification, format tasks

Tier 2 — Standard model (GPT-4o / Claude Sonnet):
  General chat, creative writing, empathetic dialogue,
  moderate-complexity RAG, most Copilot use cases

Tier 3 — Base + best-of-N with verifier:
  Moderately complex analysis with clear correctness signal,
  code review, code generation with tests

Tier 4 — Reasoning model (mini/low effort):
  Complex analysis, non-trivial coding, structured reasoning

Tier 5 — Reasoning model (full/high effort):
  Hard math, competitive coding, formal proofs,
  high-stakes analytical decisions
```

**Router decision:** classify the task into a tier; use the tier's default; allow escalation if the tier's confidence signal indicates need.

**Governance:** monitor per-tier cost and success rate. Tier 5 traffic should be a small fraction of overall volume — if it's not, either the router is misconfigured or the product should be split into higher- and lower-value features.

---

## Real Deployment Patterns

### Pattern 1: Reasoning as an opt-in "deep analysis" feature

**Product:** research assistant.

**Design:** default responses use Claude Sonnet with RAG. Explicit "Deep Analysis" button triggers extended thinking mode. Users see the reasoning trace as it streams.

**Cost impact:** 5% of queries use reasoning (opt-in), but represent 40% of the LLM budget. Product feature that customers pay for.

**Verdict:** works well. Cost isolation via UX.

### Pattern 2: Reasoning tier as agent's planner

**Product:** autonomous coding agent.

**Design:** planner uses o3 for high-level task decomposition. Executor uses GPT-4o for individual code changes. Verifier uses Claude Sonnet.

**Cost impact:** planner is 5% of calls, 40% of budget. But dramatically better task completion vs GPT-4o planner.

**Verdict:** works well. Cost is justified by quality on planning; execution stays cheap.

### Pattern 3: Reasoning as a fallback

**Product:** legal document analyzer.

**Design:** first pass with GPT-4o + RAG. If validator flags ambiguity or the LLM-judge score is below threshold, escalate to Claude 3.7 with extended thinking.

**Cost impact:** ~15% escalation rate. Overall cost 3× base but with dramatic quality improvement on the hard 15%.

**Verdict:** works well. Cascade pattern applied to reasoning tier.

### Anti-pattern: Reasoning as the default

**Product:** customer support chatbot.

**Design:** decided o1 would give "better answers" so routed everything to o1.

**Cost impact:** 40× cost increase. Latency went from 1s to 25s. User complaints spiked ("Why is it so slow?"). Cache hit rate collapsed (reasoning models integrate poorly with prompt caches).

**Verdict:** killed. Reverted to GPT-4o with cache stack from [Folder 2](../../2_cost_engineering/02_cache_hierarchy/README.md).

---

## Files In This Folder

| File | Concept |
|---|---|
| [`task_category_matrix.py`](task_category_matrix.py) | Reference matrix + task classifier |
| [`math_and_logic_wins.py`](math_and_logic_wins.py) | Detailed analysis of where reasoning dominates |
| [`format_tasks_lose.py`](format_tasks_lose.py) | Why format-driven tasks favor base models |
| [`creative_writing_regression.py`](creative_writing_regression.py) | The measured cases where reasoning hurts |
| [`routing_tiers_reference.py`](routing_tiers_reference.py) | 5-tier routing model with escalation |

---

## The Staff Interview Question

*"When would you NOT use a reasoning model, even if you could afford it?"*

**The wrong answer:** "For simple tasks."

**The right answer:**
*"Three categories. First — latency-sensitive interactive UX. Reasoning models take 5-60 seconds to first token. Any Copilot, chat, or real-time UX is dead on arrival. Base model, aggressive caching. Second — creative or empathetic tasks. Deliberation stifles voice and reads as clinical. Measured evals show reasoning models often worse on creative writing and empathetic dialogue. Third — tasks without a verifier signal. Reasoning models are trained on tasks with verifiable answers; on tasks without correctness structure, they don't reliably improve over base models but always cost more. Plus a pragmatic fourth — anywhere your cache hit rate is high. Reasoning models integrate poorly with prompt caches because reasoning traces are non-deterministic. You lose the cost savings from caching. So the honest answer is: reasoning is a specific tool for structured, verifier-friendly, latency-tolerant, correctness-critical tasks. That's a smaller set than most engineers assume."*

---

*Previous: [← What Reasoning Models Are](../01_what_reasoning_models_are/README.md) · Return to [folder README](../README.md) · Next: [Test-Time Compute Patterns →](../03_test_time_compute_patterns/README.md)*
