"""
verifier_ensemble_demo.py — Multi-verifier aggregation.

Demonstrates:
- Formal verifier (deterministic)
- Task-specific validator (schema check)
- LLM-judge simulation (noisy)
- Ensemble aggregation with hard filters and weighted signals
- Correlated-error mitigation (different judges)

Run:
    python verifier_ensemble_demo.py
"""
import random
from dataclasses import dataclass


@dataclass
class Candidate:
    text: str
    is_correct: bool  # ground truth
    passes_schema: bool
    has_correct_format: bool


def formal_verifier(c: Candidate) -> bool:
    """Runs the test — perfect signal."""
    return c.is_correct


def schema_validator(c: Candidate) -> bool:
    """Cheap deterministic check."""
    return c.passes_schema


def format_check(c: Candidate) -> bool:
    """Another cheap check."""
    return c.has_correct_format


def llm_judge_a(c: Candidate, noise: float = 0.15) -> float:
    """Noisy LLM-judge, family A."""
    base = 0.8 if c.is_correct else 0.3
    return max(0.0, min(1.0, base + random.gauss(0, noise)))


def llm_judge_b(c: Candidate, noise: float = 0.18) -> float:
    """Different LLM-judge family."""
    base = 0.75 if c.is_correct else 0.28
    return max(0.0, min(1.0, base + random.gauss(0, noise)))


def single_judge_verify(candidate: Candidate) -> float:
    """Baseline: one LLM judge."""
    return llm_judge_a(candidate)


def ensemble_verify(candidate: Candidate) -> float:
    """Full ensemble: hard filters + weighted semantic signals."""
    # Hard filters (deterministic pre-check)
    if not schema_validator(candidate):
        return -1.0
    if not format_check(candidate):
        return -1.0

    # Semantic signals
    score_a = llm_judge_a(candidate)
    score_b = llm_judge_b(candidate)

    # Weighted average
    return 0.5 * score_a + 0.5 * score_b


def generate_candidate() -> Candidate:
    """Simulate a base model generating a candidate."""
    is_correct = random.random() < 0.5
    # Schema failure occurs on 20% of correct and 30% of incorrect
    passes_schema = random.random() > (0.30 if not is_correct else 0.20)
    has_correct_format = random.random() > 0.15
    return Candidate("text", is_correct, passes_schema, has_correct_format)


def best_of_n_with_verifier(n: int, verifier) -> Candidate:
    candidates = [generate_candidate() for _ in range(n)]
    scored = [(c, verifier(c)) for c in candidates]
    # Filter out rejects (score < 0)
    scored = [(c, s) for c, s in scored if s >= 0]
    if not scored:
        return candidates[0]  # fallback: return first if all rejected
    return max(scored, key=lambda x: x[1])[0]


def evaluate(name: str, verifier, n_values: list, n_trials: int = 1000):
    print(f"\n=== {name} ===")
    print(f"  N   |  correct_rate  |  ceiling(perfect verifier)")
    print(f"  ────┼───────────────┼───────────────────────────")
    for n in n_values:
        correct_count = 0
        perfect_count = 0
        for _ in range(n_trials):
            # Actual with verifier
            best = best_of_n_with_verifier(n, verifier)
            if best.is_correct:
                correct_count += 1
            # Ceiling: perfect verifier picks best
            candidates = [generate_candidate() for _ in range(n)]
            if any(c.is_correct for c in candidates):
                perfect_count += 1
        actual = correct_count / n_trials
        ceiling = perfect_count / n_trials
        gap = ceiling - actual
        print(f"  {n:3d} |     {actual:.3f}     |         {ceiling:.3f}   (gap: {gap:.3f})")


def main():
    random.seed(42)
    n_values = [1, 2, 4, 8, 16]

    print("Verifier Ensemble Comparison")
    print("Goal: pick correct candidate from N samples")

    evaluate("Single LLM-Judge (baseline)", single_judge_verify, n_values)
    evaluate("Ensemble (schema + format + 2 judges)", ensemble_verify, n_values)

    print()
    print("=" * 60)
    print("Reading the Results")
    print("=" * 60)
    print()
    print("The gap between actual and ceiling shows verifier quality loss.")
    print("Ensemble closes the gap: hard filters remove obvious failures,")
    print("two independent judges reduce correlated-error risk.")
    print()
    print("Best-of-N with a strong verifier approaches ceiling.")
    print("Best-of-N with a weak verifier plateaus below ceiling.")


if __name__ == "__main__":
    main()
