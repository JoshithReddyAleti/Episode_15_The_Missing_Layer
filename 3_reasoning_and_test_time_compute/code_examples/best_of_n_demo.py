"""
best_of_n_demo.py — Best-of-N sampling with verifier.

Demonstrates:
- Parallel candidate generation (simulated)
- Formal verifier (deterministic check)
- LLM-judge verifier (simulated)
- Scaling behavior with N (log-scaling law)
- Cost tracking

Run:
    python best_of_n_demo.py
"""
import math
import random
from dataclasses import dataclass


@dataclass
class Candidate:
    text: str
    quality: float  # 0-1 hidden ground truth
    tokens_out: int


def simulate_base_model(query: str, temperature: float = 1.0) -> Candidate:
    """Simulate a base model with variable output quality."""
    # Quality has some baseline + noise (higher temp = more noise, more diversity)
    baseline = 0.62
    noise = random.gauss(0, temperature * 0.25)
    quality = max(0.0, min(1.0, baseline + noise))
    return Candidate(
        text=f"candidate q={quality:.2f}",
        quality=quality,
        tokens_out=400,
    )


def formal_verifier(candidate: Candidate) -> float:
    """Perfect verifier — returns the true quality."""
    return candidate.quality


def llm_judge_verifier(candidate: Candidate, noise: float = 0.15) -> float:
    """Noisy LLM-judge with configurable noise level."""
    return max(0.0, min(1.0, candidate.quality + random.gauss(0, noise)))


def weak_verifier(candidate: Candidate) -> float:
    """Weak verifier — barely correlated with quality."""
    return max(0.0, min(1.0, candidate.quality * 0.3 + random.random() * 0.7))


def best_of_n(query: str, n: int, verifier) -> Candidate:
    """Standard best-of-N pattern."""
    candidates = [simulate_base_model(query) for _ in range(n)]
    scored = [(c, verifier(c)) for c in candidates]
    return max(scored, key=lambda x: x[1])[0]


def cost_of_run(n: int, verifier_cost_per_call: float = 0.0) -> float:
    """Compute cost: N base calls + N verifier calls."""
    base_cost = 0.005  # ~GPT-4o per call
    return n * base_cost + n * verifier_cost_per_call


def evaluate(n_values: list, verifier, verifier_name: str, verifier_cost: float, n_trials: int = 500):
    """Measure best-of-N quality across trials."""
    print(f"\n=== Verifier: {verifier_name} ===")
    print(f"  N   |  avg_quality  |  cost/query  |  quality gain over N=1")
    print(f"  ────┼──────────────┼──────────────┼───────────────────────")
    baseline = None
    for n in n_values:
        qualities = []
        for _ in range(n_trials):
            best = best_of_n("dummy", n, verifier)
            qualities.append(best.quality)
        avg = sum(qualities) / len(qualities)
        cost = cost_of_run(n, verifier_cost)
        if baseline is None:
            baseline = avg
        gain = avg - baseline
        print(f"  {n:3d} |    {avg:.4f}    |   ${cost:.4f}   |    +{gain:.4f}")


def main():
    random.seed(42)
    n_values = [1, 2, 4, 8, 16, 32]

    print("=" * 60)
    print("Best-of-N Scaling Behavior")
    print("=" * 60)
    print()
    print("Task: base model produces candidates with ~62% baseline quality.")
    print("Verifier picks the best from N samples.")

    # Perfect verifier — best case
    evaluate(n_values, formal_verifier, "Formal (perfect)", verifier_cost=0.0)

    # LLM-judge — realistic case
    evaluate(n_values, llm_judge_verifier, "LLM-Judge (0.15 noise)", verifier_cost=0.002)

    # Weak verifier — near-random
    evaluate(n_values, weak_verifier, "Weak (barely correlated)", verifier_cost=0.002)

    print("\n=== Key Insight ===")
    print()
    print("With a FORMAL verifier: best-of-N approaches perfect quality (log scaling).")
    print("With an LLM-JUDGE: quality improves but plateaus below the ceiling.")
    print("With a WEAK verifier: best-of-N is mostly noise. Wasted money.")
    print()
    print("The verifier quality caps everything.")


if __name__ == "__main__":
    main()
