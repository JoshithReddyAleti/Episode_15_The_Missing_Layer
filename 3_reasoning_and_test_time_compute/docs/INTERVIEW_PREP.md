# 🎯 Interview Prep — Reasoning & Test-Time Compute

Reasoning questions have entered staff-level AI interviews from mid-2025 onward. This doc maps common questions to sections.

## The Universal Opener

For any "when should I use a reasoning model" question:

*"Reasoning models are a specific tool for a specific set of problems. Three conditions must hold: the task is in the reasoning-wins category (math, code, multi-step logic, structured analysis), I have a verifier signal or the task is one where reasoning models were trained (verifiable domains), and the correctness value justifies the 10-100× cost delta. If any of those fails, base model with prompt engineering and cache stack wins."*

## Question Bank

### "Explain the difference between o1 and GPT-4o."

**Lean on:** Section 01.

**Key points:**
- Training paradigm: RL on verifiable reasoning vs RLHF for helpfulness
- Reasoning tokens: hidden internal deliberation vs no reasoning tokens
- Cost: 10-100× more per query
- Wins on math/code/logic; ties or loses on factual/creative/latency-sensitive

### "When would you use a reasoning model?"

**Lean on:** Section 02.

**Key points:**
- Three conditions: task fit, verifier available, cost justified
- Task categories that win (math, code, logic, structured analysis)
- Task categories where reasoning is overkill or actively worse

### "When would you NOT use a reasoning model?"

**Lean on:** Section 02.

**Three categories to name:**
- Latency-sensitive UX (< 3s response required)
- Creative or empathetic tasks (deliberation stifles voice)
- Tasks without verifier signal (no way to know if reasoning helped)

### "How would you improve LLM accuracy without switching models?"

**Lean on:** Section 03.

**The compute ladder answer:**
- Prompt engineering
- Best-of-N with cheap verifier
- Best-of-N with strong verifier
- Iterative refinement
- Self-consistency
- Then switch models

### "How do best-of-N and reasoning models compare?"

**Lean on:** Sections 03 and 04.

**Key insight:** with strong verifier, base + BoN can match reasoning model quality at fraction of cost. Reasoning models win when verifier is weak (implicit verification learned in training).

### "How much more expensive are reasoning models?"

**Lean on:** Section 04.

**Structure:**
- Per-query: 10-100× depending on effort and reasoning length
- Per successful task: depends on success rate delta and escalation cost
- Break-even formula: extra reasoning cost vs escalation savings

### "Explain test-time compute scaling laws."

**Lean on:** Section 03.

**Key points:**
- Accuracy ~ log(N) with best-of-N (diminishing returns)
- Cost ~ N (linear)
- Break-even N* depends on task and verifier quality
- Snell et al. 2024 showed test-time and training-time compute are fungible

### "What's a process reward model?"

**Lean on:** Section 05.

**Key points:**
- Trained to score intermediate reasoning steps
- Enables tree search over reasoning
- Rare in production; more common in frontier lab training
- Modern reasoning models have implicit PRMs learned in training

### "How do you evaluate a verifier?"

**Lean on:** Section 05.

**Key points:**
- Golden set of 100-500 labeled (query, candidate) pairs
- Measure ranking accuracy — how often verifier ranks correct above incorrect
- Monitor for drift over time
- Formal verifier > task-specific > LLM-judge

### "Design a code generation system that uses test-time compute."

**Lean on:** all 5 sections.

**Structure:**
- Base model default (base cost, cache-friendly)
- Task classifier routes complex tasks to reasoning tier
- For reasoning tier: unit test verifier as formal signal
- Best-of-4 with test verifier as first escalation
- Reasoning model as second escalation for harder tasks
- Per-user quota on reasoning tier
- Cost accounting per tier
- Verifier accuracy monitoring

## The Framework To Remember

Every reasoning/test-time question maps to:

1. **What reasoning models are** — trained on verifiable reasoning, not just prompted
2. **When reasoning wins** — structured task, verifier, cost justified
3. **Test-time compute patterns** — best-of-N, self-consistency, iterative refinement, tree search
4. **Cost dynamics** — 10-100× per query; break-even depends on success delta and escalation cost
5. **Verifier patterns** — quality caps everything; formal > task-specific > LLM-judge > nothing

Show that you know these five and the interviewer knows you've built with reasoning models, not just heard about them.
