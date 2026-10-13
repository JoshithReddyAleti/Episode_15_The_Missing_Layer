# 🧠 Reasoning Models & Test-Time Compute — The Paradigm Shift Most Engineers Misuse

> *"We upgraded to o3 and now our costs are 40× higher and our chatbot is slower."*
>
> *"What's the chatbot used for?"*
>
> *"Answering FAQs about our shipping policy."*
>
> *🫠*

Reasoning models are the most misunderstood tool in the modern AI stack.

Half the industry avoids them ("too expensive"). The other half slaps them on every task ("smarter is better"). Both are wrong. **Reasoning models are a specific tool for a specific set of problems, and the discipline of when to reach for them is a real skill.**

This folder is that discipline.

---

## 🎯 What Changed

Between 2023 and 2026, model training changed shape.

The **pre-reasoning era** (GPT-3, GPT-4, Claude 2/3, Llama 2/3): models trained to predict the next token, prompted at inference time with "think step by step" to get chain-of-thought reasoning. Reasoning was a *prompting technique*.

The **reasoning-model era** (o1 in late 2024, o3 in 2025, DeepSeek-R1, Claude 3.7 with extended thinking, Gemini 2.5 Flash Thinking, o4/GPT-5-thinking in 2026): models trained via RL on verifiable reasoning tasks. They generate long internal "thinking" traces before their answer. Reasoning became a *model capability*.

**What this means practically:**

- A reasoning model at test-time can use **10-1000× more compute per query** than a base model
- On math, code, and multi-step reasoning, the quality gap is often **massive** (AIME goes from ~13% to ~74%+; Codeforces jumps multiple standard deviations)
- On simple tasks, the gap is **negligible** — sometimes *reversed*
- Cost per response is **5-50× higher** than a comparable base model
- Latency per response is **10-60 seconds** typical, sometimes minutes

**The architectural question shifts from "which model?" to "how much test-time compute is this task worth?"**

That's the real conceptual shift. Model *quality* is no longer a single number — it's a function of how much compute you're willing to spend per query.

---

## 📁 What's In This Folder

| Section | What It Covers | When You Need It |
|---|---|---|
| [`01_what_reasoning_models_are/`](01_what_reasoning_models_are/) | The training paradigm · hidden vs visible thinking · reasoning tokens · what's actually different mechanically | Everyone building with reasoning models — start here |
| [`02_when_reasoning_wins/`](02_when_reasoning_wins/) | Task-by-task where reasoning models crush base models · where they're overkill · where they're actively worse | Every architecture decision involving a reasoning model |
| [`03_test_time_compute_patterns/`](03_test_time_compute_patterns/) | Best-of-N · self-consistency · tree search · iterative refinement · verifier-guided search · scaling laws | Any application willing to trade cost for quality |
| [`04_cost_dynamics/`](04_cost_dynamics/) | The 10-100× multiplier math · latency budgets · real 2026 pricing · break-even vs base + best-of-N | Any cost-conscious deployment considering reasoning |
| [`05_verifier_patterns/`](05_verifier_patterns/) | Formal verifiers · LLM-judge verifiers · task-specific validators · process reward models · why verifier quality caps everything | Any test-time compute system beyond single-shot |

---

## 🧠 The Mental Model Shift

Three ideas that reframe how you think about model choice.

### Idea 1: Compute is a slider, not a switch

Before reasoning models, "which model?" was categorical. GPT-3.5 or GPT-4. Small or large.

Now it's a continuous dial:
- gpt-4o with 400 output tokens → cheap, fast, adequate on easy tasks
- gpt-4o with 4000 output tokens (best-of-8) → 10× more compute, better on hard tasks
- o1 default reasoning → 20-50× more compute, dramatically better on math/code
- o1 with high reasoning effort → 100-200× more compute, incremental quality gains

You're not choosing a model. You're **choosing a point on the quality-cost frontier per query.**

### Idea 2: Verifier quality caps everything

Test-time compute helps only when you have a way to tell good outputs from bad ones. Without a verifier, more samples = more noise, not more quality.

- Math with a symbolic checker → verifier is perfect → best-of-N scales beautifully
- Code with unit tests → verifier is strong → best-of-N works well
- Creative writing → verifier is weak (LLM-judge is noisy) → best-of-N plateaus fast
- Open-ended dialogue → verifier is nearly nonexistent → don't bother

**Whenever you scale test-time compute, ask: what's my verifier signal? If you don't have one, more compute is money for nothing.**

### Idea 3: Reasoning is not always better

Reasoning models have real failure modes:
- **Over-thinking simple queries** ("What's your return policy?" → 4000 tokens of deliberation)
- **Refusing to commit** on ambiguous questions where a base model would just answer
- **Latency** that breaks any interactive UX
- **Worse creative writing** in many measured evals (extended deliberation stifles voice)
- **Format instability** — reasoning traces can leak into output in unpredictable ways
- **Higher hallucination on knowledge tasks** — deliberation without grounding can amplify wrong beliefs

**Reasoning is not "smart mode."** It's a specific tool for problems with structured verification signal.

---

## 📊 The 2026 Reasoning-Model Landscape

Approximate pricing (per million tokens, ballpark 2026):

| Model | Input | Output | Reasoning visible? | Adjustable effort? |
|---|---|---|---|---|
| DeepSeek-R1 (open weights) | $0.55 | $2.19 | Yes | Partial |
| DeepSeek-R1 (self-hosted) | ~$0.20-0.40 blended | ~$0.20-0.40 blended | Yes | Full |
| Gemini 2.5 Flash Thinking | $0.15 | $3.50 (incl. thinking) | Partial | Yes (thinking_budget) |
| Claude 3.7 Sonnet (extended thinking) | $3.00 | $15.00 | Yes | Yes (budget_tokens) |
| Gemini 2.5 Pro Thinking | $1.25 | $10.00 (incl. thinking) | Partial | Yes |
| o1-mini / o3-mini | $1.10-$3.00 | $4.40-$12.00 | No | Yes (reasoning_effort) |
| o1 | $15.00 | $60.00 | No | Yes |
| o3 | $15.00+ | $60.00+ | No | Yes |
| Claude Opus with thinking | $15.00 | $75.00+ | Yes | Yes |

**Base models for comparison (from Folder 2):**
- GPT-4o mini: $0.15 / $0.60 — typical ~500 output tokens
- GPT-4o: $2.50 / $10.00 — typical ~500 output tokens
- Claude Sonnet (no thinking): $3.00 / $15.00 — typical ~500 output tokens

**The critical detail:** reasoning models bill for the reasoning tokens too. A reasoning model that outputs 500 visible tokens might have used 8000 hidden reasoning tokens. **You pay for all of them.**

---

## 💸 The Cost Reality (One Query)

Same task: solve a moderately hard math word problem.

| Approach | Input tokens | Output tokens (incl. reasoning) | Cost | Success rate |
|---|---|---|---|---|
| GPT-4o mini, single shot | 500 | 400 | $0.00033 | ~20% |
| GPT-4o, single shot | 500 | 400 | $0.00525 | ~35% |
| GPT-4o, best-of-8 with verifier | 4000 | 3200 | $0.042 | ~65% |
| Claude 3.7 Sonnet, extended thinking (medium budget) | 500 | 4000 (mostly hidden) | $0.062 | ~78% |
| o3-mini high effort | 500 | 8000 (mostly hidden) | $0.10 | ~85% |
| o3 default | 500 | 12000 (mostly hidden) | $0.72 | ~92% |
| o3 high effort | 500 | 30000+ | $1.80+ | ~95% |

**The pattern:**
- Cheapest option is ~$0.0003. Best option is ~$1.80.
- **6000× cost range** across viable choices for this one task.
- Choose wrong and you either ship low quality or burn the budget on unnecessary reasoning.

---

## 🧭 The Five Questions Before Enabling Reasoning

Every architecture decision involving reasoning starts here.

### 1. Is this task in the "reasoning wins" category?

Reasoning models dominate on:
- **Multi-step math** (word problems, symbolic manipulation, proofs)
- **Competitive coding** (algorithmic, correctness-verifiable)
- **Complex logic** (constraint satisfaction, deduction chains)
- **Multi-step planning** with clear success criteria
- **Multi-hop retrieval-heavy analysis** where deliberation compounds
- **Debugging / root-cause analysis** with structured error signals

Reasoning models tie or lose on:
- **Simple factual QA** ("what's the capital of France?")
- **Creative writing** with voice-driven judgment
- **Format-driven tasks** (extraction, translation, summarization)
- **Real-time conversational UX** (latency kills it)
- **Empathetic dialogue** (over-deliberation reads as robotic)

**If your task isn't in the "wins" list, stop here. Use a base model.**

### 2. Do you have a verifier signal?

For single-shot reasoning: the model's built-in reasoning suffices.

For test-time compute scaling (best-of-N, tree search, iterative refinement): **you need a verifier that's better than random.**

- Formal verifier (unit tests, symbolic check, schema validation) → excellent
- Task-specific validator (code compiles, output parses, structure matches) → strong
- LLM-judge on structured task → moderate
- LLM-judge on subjective task → weak
- No verifier → don't scale compute

### 3. What's your latency budget?

- **< 500ms** → no reasoning model. Period. Base model with prompting is your only option.
- **2-10 seconds** → base model + best-of-3 with verifier, or mini reasoning model (o3-mini low effort, Gemini Flash Thinking)
- **10-60 seconds** → reasoning models in play. Most agent and analysis workflows.
- **Minutes** → full reasoning models with high effort, tree search, multi-verifier ensembles.
- **Hours+** → offline batch. Any compute budget viable.

### 4. What's your cost budget per successful task?

Return to [Folder 2 Unit Economics](../2_cost_engineering/01_unit_economics/README.md).

Cost per successful task with reasoning:
```
Cost = reasoning_cost_per_attempt / success_rate + escalation × (1 - success_rate)
```

Reasoning improves success rate. But it multiplies per-attempt cost by 10-100×.

**Reasoning wins in cost terms when:**
```
reasoning_cost × (1/reasoning_success_rate) < base_cost × (1/base_success_rate) + escalation × (base_fail_rate - reasoning_fail_rate)
```

Not intuitive. Depends heavily on escalation cost. Do the math per feature.

### 5. Do you actually need the answer to be right?

Sounds obvious. Isn't.

- **Financial calculations, medical suggestions, legal analysis** → yes, need right. Reasoning + verifier + human review.
- **Content generation, brainstorming, drafting** → "roughly right" is fine. Base model.
- **Classification, extraction, routing** → determined by acceptance threshold. Usually base model.
- **Agent tool selection** → depends on tool blast radius. Reasoning for high-stakes actions.

**Correctness has a business value. Reasoning is worth it when that value exceeds the cost delta.**

---

## 🏗️ The Reasoning Architecture Diagram

```
                    User query
                        │
                        ▼
              ┌─────────────────┐
              │  Task classifier │ ← "does this need reasoning?"
              └─────────────────┘
                        │
              ┌─────────┼──────────┐
              ▼         ▼          ▼
          Easy task   Medium    Hard task
              │       task         │
              │         │          │
              ▼         ▼          ▼
        [Base model] [Base+BoN] [Reasoning model]
              │         │          │
              ▼         ▼          ▼
              │    ┌──────────┐    │
              │    │ Verifier │    │
              │    └──────────┘    │
              │         │          │
              └─────────┼──────────┘
                        ▼
                  ┌───────────┐
                  │ Response   │
                  └───────────┘
```

**Key architectural moves:**
1. Route by task type first — most queries don't need reasoning
2. Scale compute continuously — best-of-N is the middle ground between base and full reasoning
3. Verifier is not optional whenever compute > single-shot
4. Reasoning model output is *still* worth verifying for high-stakes tasks

---

## 🎯 The Interview Angle

Staff interviews increasingly probe this.

**"When would you use a reasoning model?"**

The wrong answer: "For harder tasks."

The right answer:
*"Three conditions. First, the task is in the 'reasoning wins' category — math, code, multi-step logic, structured planning. If it's factual QA or creative writing, reasoning models tie or lose. Second, I have a verifier signal — either formal like unit tests, or task-specific like schema validation, or at minimum a strong LLM-judge on a structured task. Without a verifier, more compute is money for nothing. Third, the correctness value justifies the cost delta — reasoning models are 10-100× the per-query cost of base models, and the success-rate improvement has to pay for that in cost per successful task. For a math tutor: yes, all three conditions hold. For a customer support chatbot answering shipping questions: no, none hold, use a base model with retrieval."*

**"Explain how o1 differs from GPT-4o."**

The wrong answer: "It's smarter."

The right answer:
*"Different training paradigm. GPT-4o is trained on next-token prediction with RLHF on human preferences. o1 is additionally trained via reinforcement learning on verifiable reasoning tasks — the model produces long internal reasoning traces before its final answer, and the RL signal rewards traces that lead to correct answers. At inference time, o1 generates thousands of hidden reasoning tokens per query, which is why cost is much higher per query. The training has taught the model to explore hypotheses, backtrack, verify, and refine — which is genuinely more capable on math, code, and multi-step reasoning tasks, and roughly the same on factual recall or simple queries. It's not smarter across the board — it's a model with a different tradeoff. More compute per query, better on some tasks, worse on latency-sensitive UX."*

**"Design an AI system that solves complex analytical questions."**

Lean on: task classifier → reasoning tier selection → verifier ensemble → cost tracking. Show that you know reasoning is one tool, not the default.

---

## 🔗 What This Folder Connects To

- **Depends on:** Folder 1 (application shapes — reasoning fits Agent-first and some Assistant, rarely Copilot, never Workflow-first at that latency), Folder 2 (unit economics and cost governance — reasoning changes the math)
- **Bridges to:** Folder 4 (Enterprise Integration — reasoning models often require different compliance treatment for hidden reasoning traces)
- **Anticipates:** Agentic AI Roadmap 2027 — agents often use reasoning models for planning, base models for execution

---

## 📚 How To Read This Folder

**If you have 60 minutes:** read this README + [`02_when_reasoning_wins/`](02_when_reasoning_wins/README.md). That's the 80/20 — knowing when to reach for the tool.

**If you have a weekend:** read all 5 sub-READMEs, run [`code_examples/`](code_examples/), and study the verifier patterns. That's operational fluency.

**If you're prepping for a staff interview:** read [`docs/INTERVIEW_PREP.md`](docs/INTERVIEW_PREP.md) — reasoning questions are showing up in senior AI interviews from mid-2025 onward.

**If you're building this at work:** read [`docs/REASONING_MODEL_SELECTION.md`](docs/REASONING_MODEL_SELECTION.md) — the practical decision tree for choosing a reasoning tier.

---

*Return to [Episode 15 main README](../README.md) · Previous folder: [← Cost Engineering](../2_cost_engineering/) · Next folder: [Enterprise Integration →](../4_enterprise_integration_and_compliance/)*
