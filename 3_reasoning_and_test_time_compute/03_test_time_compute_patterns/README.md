# 🌳 Test-Time Compute Patterns — The Slider Between Base and Reasoning

> *Reasoning models give you one point on the compute-quality curve. Test-time compute gives you the full curve.*

You don't have to pick between a $0.005 GPT-4o call and a $0.75 o3 call. Between them lies a spectrum of patterns that let you spend *any amount* of compute per query, using base models plus verifiers, to reach any point on the quality frontier.

This section is that spectrum.

---

## The Fundamental Idea

Given a base model and a verifier, you can trade cost for quality by generating multiple candidates and selecting the best.

**Naive baseline:** one sample, take it. Quality = base model quality.

**Best-of-N:** N samples, pick the best via verifier. Quality improves with N, following a scaling law that plateaus.

**Beyond:** structured search over reasoning space (tree search), iterative refinement, verifier ensembles, hybrid patterns.

**The formal result:** Snell et al. 2024 (approximate — verify citation) showed that on math benchmarks, spending compute at test time via best-of-N or tree search can match or exceed a much larger base model's single-shot performance. **Compute is fungible between training-time and test-time.**

---

## Pattern 1: Best-of-N Sampling

The simplest, and often the best-value.

```python
def best_of_n(query, n=8, verifier):
    candidates = [model.complete(query, temperature=1.0) for _ in range(n)]
    scored = [(c, verifier(query, c)) for c in candidates]
    return max(scored, key=lambda x: x[1])[0]
```

**How quality scales with N (empirical patterns):**
- Diminishing returns. Log-shaped curve.
- Doubling N gives roughly constant absolute improvement (not multiplicative)
- Plateaus around N=8-32 for most tasks
- Beyond N=32, marginal gains are small unless the verifier is very strong

**When it wins:**
- Verifier is strong (unit tests, symbolic checker, structured LLM-judge on structured output)
- Base model has non-trivial per-sample failure rate
- Cost budget allows 8-32× base cost per query

**When it doesn't:**
- Verifier is weak → best-of-N reduces to random selection, no gain
- Base model already at ceiling → no diversity to exploit
- Latency-sensitive → running N samples adds latency (though can parallelize)

**Cost math:**
```
best_of_N_cost = N × base_cost + N × verifier_cost + selection_overhead
```

For N=8 with base cost $0.005 and verifier $0.001 per check: ~$0.048 per query. Comparable to a mid-tier reasoning model, often at higher quality if verifier is good.

---

## Pattern 2: Self-Consistency (Wang et al. 2022)

**The insight:** for tasks with a canonical answer form (a number, a code snippet, a label), sample N reasoning chains, extract the answers, and take the majority vote.

```python
def self_consistency(query, n=8):
    chains = [model.complete(query + "\nLet's think step by step.", temperature=0.7) 
              for _ in range(n)]
    answers = [extract_final_answer(c) for c in chains]
    return most_common(answers)
```

**Why it works:** correct answers are usually reached by multiple reasoning paths; wrong answers tend to be idiosyncratic. Majority voting amplifies the signal.

**When it wins:**
- Answer is discrete/checkable (a number, a code output, a classification)
- No external verifier available (verifier IS the majority)
- Chain-of-thought reasoning is available

**Empirical:** self-consistency with N=40 chains has been shown to match some reasoning-model performance on math benchmarks at a fraction of the cost — with a caveat that reasoning models still win on the very hardest problems.

**When it doesn't:**
- Open-ended output (creative writing, dialogue)
- Answer space is continuous or unstructured
- Base model can't produce diverse-enough chains

---

## Pattern 3: Verifier-Guided Search

**The insight:** don't just sample and pick — use the verifier to guide the search.

Two common shapes:

### Iterative Refinement (Self-Refine, Madaan 2023)

```
1. Generate initial answer
2. Verifier produces critique
3. Model refines answer based on critique
4. Repeat until verifier passes or budget exhausted
```

**Wins when:** critique is informative (verifier can explain what's wrong).

### Tree of Thoughts (Yao et al. 2023)

```
1. Generate multiple next-step candidates from current reasoning state
2. Verifier scores each candidate
3. Expand promising branches (like beam search over reasoning)
4. Backtrack from dead ends
5. Return best complete solution
```

**Wins when:** problem is decomposable into steps, each verifiable individually.

**Cost math:** significantly higher than best-of-N — tree search explores exponentially in worst case. Requires careful budget bounds.

---

## Pattern 4: Process Reward Models (PRMs)

**The idea:** instead of only rewarding final-answer correctness, train a reward model to score *each step* of reasoning.

Introduced formally in Uesato et al. 2022 and Lightman et al. 2023 (approximate — verify citations).

**How it's used at test time:**
- Generate reasoning step by step
- After each step, PRM scores the step
- Prune low-scoring branches; expand high-scoring
- Guarantees you spend compute on promising paths

**When it wins:** math and structured reasoning where step-level correctness is meaningful.

**Deployment reality:** most production teams don't have PRMs. But the pattern is embedded inside the training of modern reasoning models — some of what o1/o3 does at inference is effectively PRM-guided expansion of its own reasoning.

---

## Pattern 5: Ensemble Verifiers

**The insight:** one verifier is noisy. Multiple verifiers, aggregated, give better signal.

```python
def ensemble_verify(query, candidate):
    scores = [
        symbolic_verifier(query, candidate),
        llm_judge_1(query, candidate),
        llm_judge_2(query, candidate),
        format_validator(candidate),
    ]
    return aggregate(scores)  # weighted vote, or product, or worst-case
```

**When it wins:** any test-time compute pattern where verifier quality is the bottleneck.

**Cost consideration:** verifier ensemble multiplies verifier cost by K. For a best-of-N pattern with K verifiers, total cost is `N × base + N × K × verifier`. Structure the ensemble carefully.

---

## Pattern 6: Speculative Decoding + Reasoning

**Not a quality pattern; a cost/latency pattern.**

**The idea:** use a small model to generate reasoning drafts, verify with a large model. If large model agrees, accept; if not, redo.

**Implementation:**
- Small model produces candidate reasoning step
- Large model scores it (via forward pass)
- Accept high-score steps, reject low-score, regenerate

**Wins:** significant cost reduction for reasoning tasks with mostly-correct drafts.

**Downside:** complex; mostly research area today; production tooling limited.

---

## The Test-Time Compute Scaling Law

**Empirical finding (Snell et al. 2024, approximate):**

For math and reasoning benchmarks, the improvement in accuracy scales as:
```
Accuracy(N) ≈ Accuracy(1) + α × log(N)
```

Where α depends on the task and the verifier quality.

**Practical implications:**
- Going from N=1 to N=4 gives 2 log-steps → 2α improvement
- Going from N=4 to N=64 gives 4 log-steps → 4α improvement
- Doubling N gives constant improvement, not doubling

**Cost scales linearly (N×). Quality scales logarithmically (log N).**

**Break-even math:** at some N*, the quality gain no longer justifies the cost. That N* depends on:
- α (task-dependent slope)
- Cost of reasoning model alternative
- Value of quality improvement

For most math tasks, N* is in the range of 8-64.

---

## When Test-Time Compute Beats a Reasoning Model

**Not a rare case.** Common enough that many production teams use base + BoN before ever reaching for a reasoning model.

**Wins when:**
- **You have a strong verifier** — unit tests, symbolic checker, task-specific validator. Reasoning models are less needed when you can verify externally.
- **Cost matters more than latency** — best-of-N runs in parallel; you pay N× cost but not N× latency. Reasoning models have inherent serial latency.
- **You want to control the reasoning trace** — best-of-N with base model produces inspectable, deterministic reasoning. Reasoning models produce hidden or opaque traces.
- **You need to A/B test the verifier** — verifier updates are cheap and fast. Retraining a reasoning model is not.

**Loses to reasoning models when:**
- **Verifier is weak** — reasoning models have implicit verification learned during training.
- **Latency budget allows** — reasoning models are more compute-efficient per accuracy point at high effort.
- **Task is at the frontier of hard reasoning** — o3-level tasks (frontier math, hardest coding) may exceed what best-of-N + base can reach.

---

## Practical Recipe: The Compute Ladder

For a new feature, walk this ladder:

**Rung 1: Base model, single shot.**
Measure success rate. If good enough, stop.

**Rung 2: Base model + prompt engineering + few-shot.**
Measure success rate. If good enough, stop.

**Rung 3: Base model + best-of-4 with cheap verifier.**
4× cost. Measures whether verifier signal helps.

**Rung 4: Base model + best-of-16 with strong verifier.**
16× cost. This is often the sweet spot.

**Rung 5: Base model + best-of-8 + self-consistency + verifier ensemble.**
20-30× cost. Diminishing returns start here.

**Rung 6: Reasoning model, low effort.**
20-40× base cost.

**Rung 7: Reasoning model, medium/high effort.**
50-200× base cost.

**Rung 8: Reasoning model + best-of-4 with verifier.**
200-800× base cost. Ultra-high-quality use cases only.

**Stop climbing when marginal quality gain no longer justifies cost.**

---

## Anti-Patterns

**"Best-of-N without a verifier."**
Random selection from N candidates. Adds noise. Wastes money.

**"Best-of-N with the model as its own verifier."**
The model rates its own outputs. Systematic bias toward flowery/long/confident answers regardless of correctness. Better than nothing on some tasks, but often worse than random on others. Use with caution.

**"Tree search on a task with no clear success signal."**
Exponential compute cost with no way to prune. Kill.

**"Best-of-N in a latency-sensitive UX."**
N samples serially = N× latency. Parallel = N× peak throughput. Neither works for < 2 second UX.

**"Reasoning model + best-of-N high effort by default."**
Rung 8 for everything. Cost bomb.

---

## Files In This Folder

| File | Concept |
|---|---|
| [`best_of_n.py`](best_of_n.py) | Reference implementation with parallel sampling and verifier |
| [`self_consistency.py`](self_consistency.py) | Wang 2022 self-consistency with answer extraction |
| [`iterative_refinement.py`](iterative_refinement.py) | Self-Refine pattern with critique loop |
| [`tree_of_thoughts.py`](tree_of_thoughts.py) | Structured search over reasoning states |
| [`verifier_ensemble.py`](verifier_ensemble.py) | Multi-verifier aggregation with weighting |
| [`compute_ladder.py`](compute_ladder.py) | The 8-rung compute selection framework |

---

## The Staff Interview Question

*"How would you improve LLM accuracy on a task without switching models?"*

**The wrong answer:** "Better prompting."

**The right answer:**
*"Climb the test-time compute ladder. Rung one: baseline single-shot. Rung two: prompt engineering with few-shot. Rung three: best-of-N with a cheap verifier — even N of 4 with a simple validator gives measurable gains. Rung four: best-of-N with a strong verifier — unit tests for code, symbolic checker for math, LLM-judge for structured output. If those aren't enough, move to iterative refinement — generate answer, verifier produces critique, model refines. For math and structured tasks: self-consistency with 8-40 chains and majority vote often beats a reasoning model at fraction of cost. For hardest tasks: switch to a reasoning model. The key insight is that with a good verifier, best-of-N follows a log scaling law — you can trade cost for quality continuously without changing models. Verifier quality is the multiplier; without a strong verifier, none of this works. So the first question is always: what's my verifier?"*

---

*Previous: [← When Reasoning Wins](../02_when_reasoning_wins/README.md) · Return to [folder README](../README.md) · Next: [Cost Dynamics →](../04_cost_dynamics/README.md)*
