# 🔬 What Reasoning Models Actually Are — The Training Paradigm Shift

> *"Reasoning models are just GPT-4 with chain-of-thought baked in."*
>
> *No. That framing misses what actually changed.*

Chain-of-thought prompting has existed since Wei et al. 2022. Reasoning models are a different animal, trained differently, priced differently, and useful for different reasons. This section is what actually happens under the hood — and why it matters for the architectural choices in the rest of this folder.

---

## The Two Eras

### Era 1: Prompted Reasoning (2022-2024)

Base models trained on next-token prediction with RLHF for helpfulness and harmlessness.

Reasoning was elicited at inference time via prompting:
- *"Let's think step by step."* (Wei 2022 — Chain of Thought Prompting)
- *"Take a deep breath and work on this problem."*
- Few-shot with worked examples showing intermediate reasoning
- Self-consistency: sample N chains, take majority vote (Wang 2023)

**What the model learned:** to produce reasoning-shaped text if prompted to.

**What the model didn't learn:** whether that reasoning was actually *good*. RLHF rewarded final-answer helpfulness, not the quality of intermediate steps. Models could produce fluent-looking reasoning that led nowhere.

**Effective, but capped.** Chain of thought gave measurable gains on math and reasoning — but performance plateaued because the model had no training signal for *what makes reasoning better*.

### Era 2: Trained Reasoning (2024+)

The insight (formalized in OpenAI's o1 blog post, September 2024, and DeepSeek's R1 paper, January 2025):

**Train the model to be rewarded for reasoning traces that lead to verifiably correct answers.**

The training recipe (simplified):
1. Start from a strong base model (post-trained on human data)
2. Generate large numbers of reasoning traces on tasks with **verifiable** answers (math, code, logic)
3. Use RL to reward traces whose *final answer* is correct
4. The model learns to generate long, exploratory reasoning traces that improve final-answer accuracy
5. Optionally, use process reward models (PRMs) to reward intermediate reasoning quality, not just final answer (Uesato 2022, Lightman 2023)

**What emerges:**
- The model produces much longer internal reasoning ("thinking tokens")
- Reasoning explores hypotheses, backtracks, verifies, refines
- Final-answer accuracy on trained-domain tasks jumps dramatically
- Generalization to untrained-but-related reasoning tasks emerges

**This is the paradigm shift.** Not "chain of thought at inference." Chain of thought trained *into* the model with verifiable RL signal.

*Note: specific paper citations should be verified — Claude may hallucinate exact author/year combinations. The general lineage is accurate.*

---

## What "Reasoning Tokens" Actually Are

When a reasoning model responds to a query, its output has two parts:

**Thinking tokens** (also called reasoning tokens, hidden reasoning, internal deliberation):
- The model's exploratory work
- May include hypotheses tried and rejected
- May include self-verification steps
- May include backtracking
- Not necessarily coherent to the user
- May be truncated, hidden, or summarized before user sees them

**Answer tokens:**
- The final response the user sees
- Written in the model's normal answer style
- Sometimes with a summary of the reasoning ("I checked X, then Y...")
- Formatted for the actual task

**Key architectural facts:**
- **You pay for both.** OpenAI, Anthropic, Google all bill reasoning tokens as output tokens.
- **The ratio is typically 5:1 to 20:1** reasoning tokens to answer tokens.
- **A 500-token answer might have 5000-20000 reasoning tokens behind it.**
- **Reasoning tokens don't fit in context.** Once the response completes, they may or may not be preserved for future turns.

---

## Hidden vs Visible Thinking

Providers made different design choices about reasoning visibility.

### Hidden Reasoning (OpenAI o1, o3)

**Design:** the reasoning trace is generated but not shown to the user. Only the final answer is streamed. Sometimes a summary of reasoning is shown.

**Rationale (per OpenAI):**
- Protect model IP — reasoning traces reveal training approach
- Prevent users from "learning to hack" the reasoning
- Simpler UX — users see conclusions, not deliberations
- Ability to update reasoning training without breaking user experience

**Implications for engineers:**
- You can't inspect why the model answered the way it did
- Debugging is harder — no reasoning trace to review
- Auditing for compliance is harder — reasoning is opaque
- Cost is still charged for reasoning you can't see

### Visible Reasoning (DeepSeek-R1, Claude 3.7 Sonnet, Gemini 2.5 Thinking)

**Design:** the reasoning trace is streamed alongside the answer. Users see the deliberation in real time.

**Rationale:**
- Transparency — users understand *why* the model answered
- Better debugging — reasoning is inspectable
- Educational — users see how to reason
- Competitive differentiation — openness as feature

**Implications for engineers:**
- You can inspect reasoning quality
- You can build UX that shows deliberation ("thinking...")
- You can save/analyze reasoning traces for eval
- You may need to filter reasoning from user-facing output for compliance reasons

**Neither is objectively better.** Different tradeoffs. Hidden reasoning is more common in enterprise/compliance-heavy deployments; visible is more common in developer tools and consumer chat.

---

## Adjustable Reasoning Effort

Modern reasoning models expose a **compute dial**.

### OpenAI's `reasoning_effort` parameter (o1, o3)

Values: `low`, `medium`, `high`

- **Low:** fewer reasoning tokens, faster, cheaper, lower quality on hard tasks
- **Medium:** balanced default
- **High:** many more reasoning tokens, slower, expensive, higher quality on hard tasks

Empirically: high effort can be 3-5× more expensive than low, with ~5-15% absolute accuracy improvement on hard benchmarks.

### Anthropic's `budget_tokens` (Claude 3.7 extended thinking)

Values: integer, e.g., 1024, 4096, 16000, 64000

- Explicit cap on how many thinking tokens the model can use before it must answer
- Model manages within budget; may end early if confident
- Predictable cost ceiling
- 1024: light deliberation. 16000: heavy. 64000: extreme.

### Google's `thinking_budget` (Gemini 2.5)

Similar to Anthropic — explicit thinking token budget.

### DeepSeek-R1 (open weights)

Effort is controlled implicitly via prompt engineering and generation parameters. Full control if you self-host.

**The design consequence:**

*You now have two independent axes for each request:*
1. **Which model?** (base vs reasoning; small vs large)
2. **How much reasoning effort?** (low/medium/high or budget tokens)

**Both are cost levers. Both affect quality.**

---

## What's Happening Mechanically

Not fully understood publicly, but the following are broadly accepted:

**1. Long-context self-attention over reasoning.** The model attends over its own reasoning tokens as it generates. Later tokens can refer back to earlier hypotheses, verifications, corrections.

**2. Structured deliberation patterns.** Training instills patterns like "let me try X. That gives Y. Wait, that's wrong because Z. Let me try..." The model has learned to produce and consume these patterns.

**3. Self-verification.** Some reasoning training explicitly rewards traces that check their own work. The model may re-derive an answer via a different method and cross-verify.

**4. Backtracking.** Reasoning models can commit to a line of thought, discover it's wrong, and explicitly abandon it. Base models rarely do this — they tend to press forward.

**5. Exploration budget.** The model has effectively learned to spend more compute on harder problems and less on easier ones — often signaled by trained cues in the input or by internal "problem hardness" estimation.

**What this does NOT mean:**
- The model is not doing "true" symbolic reasoning
- The model is not "conscious" of its thinking
- The reasoning traces are not necessarily faithful to the actual computation
- Reasoning tokens are still generated via forward passes over a transformer

**Practically:** reasoning models exhibit behaviors that look like structured problem-solving because they've been trained on structured problem-solving. Treat the capability as real without over-interpreting the mechanism.

---

## Reasoning Isn't Magic — Where the Training Doesn't Transfer

Reasoning models are trained on tasks with verifiable answers: math, code, logic puzzles, structured multi-step problems.

**They generalize surprisingly well to:**
- Related structured tasks (SQL generation, structured extraction, multi-step planning)
- Analytical tasks with clear correctness signal (root-cause debugging, error diagnosis)
- Long-context research/analysis where reasoning compounds

**They generalize poorly (or negatively) to:**
- Creative writing (deliberation stifles voice)
- Open-ended dialogue (reasoning slows response, users prefer immediate answers)
- Empathetic response (reasoning reads as robotic)
- Simple factual retrieval (no room for reasoning to help)
- Format-driven tasks (deliberation without clear correctness signal doesn't add value)

**This is not a bug.** It's a consequence of *what* they were trained to reason about. If you're not solving a task like the ones in the RL training distribution, expect no reasoning benefit and often a regression.

---

## Files In This Folder

| File | Concept |
|---|---|
| [`training_paradigm_shift.py`](training_paradigm_shift.py) | The two eras and what changed technically |
| [`reasoning_tokens_and_billing.py`](reasoning_tokens_and_billing.py) | Reasoning vs answer tokens; how billing works |
| [`hidden_vs_visible_thinking.py`](hidden_vs_visible_thinking.py) | Design tradeoffs and implications per provider |
| [`adjustable_effort_patterns.py`](adjustable_effort_patterns.py) | Using reasoning_effort and budget_tokens |
| [`what_reasoning_isnt.py`](what_reasoning_isnt.py) | Common misconceptions and failure modes |

---

## The Staff Interview Question

*"Explain what makes o1 different from GPT-4o at the training level."*

**The wrong answer:** "It uses chain of thought."

**The right answer:**
*"Different training objective. GPT-4o is next-token prediction plus RLHF for helpfulness. o1 is additionally trained with reinforcement learning on verifiable reasoning tasks — math, code, logic — where the reward signal is whether the final answer is correct. The model generates long internal reasoning traces during training, and RL updates favor traces that lead to correct answers. Over time, the model learns to produce exploratory reasoning, backtrack, verify its own work, and refine — behaviors that increase accuracy on the trained-domain tasks. At inference time, this manifests as long hidden reasoning tokens the model generates before its final answer, which is why cost per query is much higher and latency is much higher. The tradeoff: much stronger on tasks like the training distribution, roughly neutral or worse on factual/creative/format tasks that don't benefit from deliberation. It's not 'smarter' — it's a different point on the training-objective curve, with a corresponding shift in cost and latency profile."*

---

*Return to [folder README](../README.md) · Next: [When Reasoning Wins →](../02_when_reasoning_wins/README.md)*
