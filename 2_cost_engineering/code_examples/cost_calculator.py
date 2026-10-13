"""
cost_calculator.py — Cost per successful task calculator.

Given the parameters of an LLM feature, computes the unit economic and
runs a lever analysis showing which single change moves the number most.

Run:
    python cost_calculator.py
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class FeatureCostModel:
    """Parameters for a single LLM feature."""
    name: str
    # Per LLM call (post-caching, post-routing)
    cost_per_call_usd: float
    # Attempts
    calls_per_attempt: int
    retrieval_cost_per_attempt: float = 0.0
    tool_cost_per_attempt: float = 0.0
    # Task-level
    success_rate: float = 1.0  # 0 to 1
    fixed_cost_per_task: float = 0.0
    escalation_cost_per_failure: float = 0.0

    def variable_cost_per_attempt(self) -> float:
        return (
            self.cost_per_call_usd * self.calls_per_attempt
            + self.retrieval_cost_per_attempt
            + self.tool_cost_per_attempt
        )

    def cost_per_success(self) -> float:
        var_cost = self.variable_cost_per_attempt()
        return (
            var_cost / self.success_rate
            + self.escalation_cost_per_failure * (1 - self.success_rate)
            + self.fixed_cost_per_task
        )

    def decompose(self) -> dict:
        cps = self.cost_per_success()
        return {
            "variable_per_attempt": round(self.variable_cost_per_attempt(), 6),
            "amortized_variable": round(self.variable_cost_per_attempt() / self.success_rate, 6),
            "escalation": round(self.escalation_cost_per_failure * (1 - self.success_rate), 6),
            "fixed": round(self.fixed_cost_per_task, 6),
            "total": round(cps, 6),
        }


def lever_analysis(base: FeatureCostModel, delta_pct: float = 0.20) -> list:
    """Compute the impact of moving each lever by delta_pct.

    Returns lever impact ranked by absolute cost reduction.
    """
    baseline = base.cost_per_success()
    results = []

    # Lever: improve success rate
    improved_success = min(1.0, base.success_rate + delta_pct)
    if improved_success != base.success_rate:
        m = FeatureCostModel(**{**base.__dict__, "success_rate": improved_success})
        savings = baseline - m.cost_per_success()
        results.append(("Success rate +20pp", round(savings, 6), round(savings/baseline*100, 1)))

    # Lever: reduce cost per call
    m = FeatureCostModel(**{**base.__dict__, "cost_per_call_usd": base.cost_per_call_usd * (1 - delta_pct)})
    savings = baseline - m.cost_per_success()
    results.append(("LLM cost per call -20%", round(savings, 6), round(savings/baseline*100, 1)))

    # Lever: reduce calls per attempt
    if base.calls_per_attempt > 1:
        m = FeatureCostModel(**{**base.__dict__, "calls_per_attempt": base.calls_per_attempt - 1})
        savings = baseline - m.cost_per_success()
        results.append((f"Calls per attempt {base.calls_per_attempt}→{base.calls_per_attempt-1}", round(savings, 6), round(savings/baseline*100, 1)))

    # Lever: reduce escalation cost
    if base.escalation_cost_per_failure > 0:
        m = FeatureCostModel(**{**base.__dict__, "escalation_cost_per_failure": base.escalation_cost_per_failure * (1 - delta_pct)})
        savings = baseline - m.cost_per_success()
        results.append(("Escalation cost -20%", round(savings, 6), round(savings/baseline*100, 1)))

    # Sort by savings
    results.sort(key=lambda r: r[1], reverse=True)
    return results


def main():
    # Example: customer support copilot
    copilot = FeatureCostModel(
        name="customer_support_copilot",
        cost_per_call_usd=0.00713,   # GPT-4o with 50% input cache
        calls_per_attempt=4,
        retrieval_cost_per_attempt=0.0006,
        tool_cost_per_attempt=0.0,
        success_rate=0.75,
        fixed_cost_per_task=0.002,
        escalation_cost_per_failure=8.00,
    )

    print(f"=== Feature: {copilot.name} ===")
    print()
    decomp = copilot.decompose()
    print(f"  Variable cost per attempt:  ${decomp['variable_per_attempt']:.4f}")
    print(f"  Amortized over success rate:${decomp['amortized_variable']:.4f}")
    print(f"  Escalation cost (25% fail): ${decomp['escalation']:.4f}")
    print(f"  Fixed cost per task:        ${decomp['fixed']:.4f}")
    print(f"  {'─'*45}")
    print(f"  Cost per SUCCESSFUL task:   ${decomp['total']:.4f}")

    print()
    print("=== Lever Analysis (which single change helps most?) ===")
    print()
    for lever, savings, pct in lever_analysis(copilot):
        print(f"  {lever:35s}  saves ${savings:.4f}  ({pct}%)")

    print()
    print("=== Reading This Result ===")
    print()
    print("  The dominant lever is what to focus on.")
    print("  If escalation cost dominates, prompt optimization is noise.")
    print("  If LLM cost dominates, cache stack and routing are wins.")


if __name__ == "__main__":
    main()
