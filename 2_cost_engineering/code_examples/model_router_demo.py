"""
model_router_demo.py — Cascade router with confidence-based escalation.

Demonstrates:
- Cascade pattern: cheap model first, escalate to expensive on low confidence
- Cost tracking across the routing decision
- Quality metric preservation on a golden eval set

Run:
    python model_router_demo.py
"""
import random
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ModelInfo:
    name: str
    input_cost_per_m: float
    output_cost_per_m: float
    quality_baseline: float  # 0-1, on some domain metric

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens / 1_000_000 * self.input_cost_per_m
                + output_tokens / 1_000_000 * self.output_cost_per_m)


# Approximate 2026 pricing
CHEAP_MODEL = ModelInfo("gpt-4o-mini", 0.15, 0.60, quality_baseline=0.82)
EXPENSIVE_MODEL = ModelInfo("gpt-4o", 2.50, 10.00, quality_baseline=0.94)


@dataclass
class Query:
    text: str
    complexity: float  # 0-1, hidden ground truth
    expected_tokens_in: int = 2500
    expected_tokens_out: int = 400


@dataclass
class RoutingResult:
    query: Query
    model_used: str
    escalated: bool
    total_cost: float
    quality_score: float


def simulate_cheap_model_response(query: Query) -> tuple[float, float]:
    """Returns (quality_score, confidence). Cheap model is worse on complex queries."""
    # Quality degrades linearly with complexity for cheap model
    quality = CHEAP_MODEL.quality_baseline - 0.35 * query.complexity + random.uniform(-0.05, 0.05)
    quality = max(0.0, min(1.0, quality))
    # Confidence is imperfectly correlated with actual quality
    confidence = quality + random.uniform(-0.15, 0.15)
    confidence = max(0.0, min(1.0, confidence))
    return quality, confidence


def simulate_expensive_model_response(query: Query) -> float:
    """Returns quality_score. Expensive model handles complexity better."""
    quality = EXPENSIVE_MODEL.quality_baseline - 0.10 * query.complexity + random.uniform(-0.03, 0.03)
    return max(0.0, min(1.0, quality))


class CascadeRouter:
    def __init__(self, confidence_threshold: float = 0.75):
        self.confidence_threshold = confidence_threshold

    def route(self, query: Query) -> RoutingResult:
        # Try cheap model first
        cheap_cost = CHEAP_MODEL.cost(query.expected_tokens_in, query.expected_tokens_out)
        cheap_quality, cheap_confidence = simulate_cheap_model_response(query)

        if cheap_confidence >= self.confidence_threshold:
            return RoutingResult(
                query=query,
                model_used=CHEAP_MODEL.name,
                escalated=False,
                total_cost=cheap_cost,
                quality_score=cheap_quality,
            )

        # Escalate — pay for BOTH calls
        expensive_cost = EXPENSIVE_MODEL.cost(query.expected_tokens_in, query.expected_tokens_out)
        expensive_quality = simulate_expensive_model_response(query)
        return RoutingResult(
            query=query,
            model_used=EXPENSIVE_MODEL.name,
            escalated=True,
            total_cost=cheap_cost + expensive_cost,
            quality_score=expensive_quality,
        )


class AlwaysExpensiveRouter:
    def route(self, query: Query) -> RoutingResult:
        cost = EXPENSIVE_MODEL.cost(query.expected_tokens_in, query.expected_tokens_out)
        quality = simulate_expensive_model_response(query)
        return RoutingResult(
            query=query,
            model_used=EXPENSIVE_MODEL.name,
            escalated=False,
            total_cost=cost,
            quality_score=quality,
        )


def build_workload(n: int = 500):
    """Realistic query mix: 60% simple, 30% medium, 10% complex."""
    workload = []
    for _ in range(n):
        r = random.random()
        if r < 0.60:
            complexity = random.uniform(0.0, 0.3)
        elif r < 0.90:
            complexity = random.uniform(0.3, 0.7)
        else:
            complexity = random.uniform(0.7, 1.0)
        workload.append(Query(
            text=f"query complexity={complexity:.2f}",
            complexity=complexity,
        ))
    return workload


def evaluate(router, workload) -> dict:
    results = [router.route(q) for q in workload]
    total_cost = sum(r.total_cost for r in results)
    avg_quality = sum(r.quality_score for r in results) / len(results)
    escalations = sum(1 for r in results if r.escalated)
    cheap_used = sum(1 for r in results if r.model_used == CHEAP_MODEL.name)
    return {
        "total_cost": total_cost,
        "avg_quality": avg_quality,
        "escalation_rate": escalations / len(results) * 100,
        "cheap_used_pct": cheap_used / len(results) * 100,
    }


def main():
    random.seed(0)
    workload = build_workload(n=500)

    print("=== Cascade Router vs Always-Expensive ===")
    print()

    baseline = AlwaysExpensiveRouter()
    b_result = evaluate(baseline, workload)
    print(f"Baseline (always expensive):")
    print(f"  Total cost:        ${b_result['total_cost']:.4f}")
    print(f"  Average quality:   {b_result['avg_quality']:.3f}")
    print()

    # Try different confidence thresholds
    for threshold in [0.65, 0.75, 0.85]:
        random.seed(0)  # same workload
        _ = build_workload(500)
        random.seed(1000)  # different noise realizations for router
        router = CascadeRouter(confidence_threshold=threshold)
        r = evaluate(router, workload)
        print(f"Cascade (threshold={threshold}):")
        print(f"  Total cost:        ${r['total_cost']:.4f}")
        print(f"  Average quality:   {r['avg_quality']:.3f}")
        print(f"  Escalation rate:   {r['escalation_rate']:.1f}%")
        print(f"  Cheap used:        {r['cheap_used_pct']:.1f}%")
        savings = (b_result['total_cost'] - r['total_cost']) / b_result['total_cost'] * 100
        quality_delta = r['avg_quality'] - b_result['avg_quality']
        print(f"  vs baseline:       {savings:.1f}% savings, {quality_delta:+.3f} quality delta")
        print()


if __name__ == "__main__":
    main()
