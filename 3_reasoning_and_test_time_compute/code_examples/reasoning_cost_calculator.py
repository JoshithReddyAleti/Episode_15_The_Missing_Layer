"""
reasoning_cost_calculator.py — Cost per successful task calculator for reasoning models.

Given base vs reasoning model parameters, computes break-even and shows when
reasoning wins economically.

Run:
    python reasoning_cost_calculator.py
"""
from dataclasses import dataclass


@dataclass
class ModelTier:
    name: str
    input_cost_per_m: float
    output_cost_per_m: float
    typical_input_tokens: int
    typical_visible_output: int
    typical_reasoning_tokens: int = 0

    def cost_per_call(self) -> float:
        input_cost = self.typical_input_tokens / 1_000_000 * self.input_cost_per_m
        total_output = self.typical_visible_output + self.typical_reasoning_tokens
        output_cost = total_output / 1_000_000 * self.output_cost_per_m
        return input_cost + output_cost


@dataclass
class TaskEconomics:
    name: str
    success_rate: float
    escalation_cost: float
    fixed_cost_per_task: float = 0.0


def cost_per_success(tier: ModelTier, econ: TaskEconomics) -> dict:
    per_call = tier.cost_per_call()
    amortized = per_call / econ.success_rate
    escalation = econ.escalation_cost * (1 - econ.success_rate)
    total = amortized + escalation + econ.fixed_cost_per_task
    return {
        "per_call": per_call,
        "amortized": amortized,
        "escalation": escalation,
        "fixed": econ.fixed_cost_per_task,
        "total": total,
    }


def compare(scenario_name: str, base_tier: ModelTier, reasoning_tier: ModelTier,
            base_econ: TaskEconomics, reasoning_econ: TaskEconomics):
    print(f"\n{'='*60}")
    print(f"Scenario: {scenario_name}")
    print(f"{'='*60}")
    print()

    base_result = cost_per_success(base_tier, base_econ)
    reasoning_result = cost_per_success(reasoning_tier, reasoning_econ)

    print(f"  {'':40s} {base_tier.name:>15s} {reasoning_tier.name:>15s}")
    print(f"  {'─'*72}")
    print(f"  {'Cost per LLM call':40s} {'$' + f'{base_result["per_call"]:.5f}':>15s} {'$' + f'{reasoning_result["per_call"]:.5f}':>15s}")
    print(f"  {'Success rate':40s} {base_econ.success_rate * 100:>13.1f}%   {reasoning_econ.success_rate * 100:>13.1f}%")
    print(f"  {'Escalation cost per failure':40s} {'$' + f'{base_econ.escalation_cost:.2f}':>15s} {'$' + f'{reasoning_econ.escalation_cost:.2f}':>15s}")
    print(f"  {'─'*72}")
    print(f"  {'Amortized LLM cost':40s} {'$' + f'{base_result["amortized"]:.4f}':>15s} {'$' + f'{reasoning_result["amortized"]:.4f}':>15s}")
    print(f"  {'Escalation cost':40s} {'$' + f'{base_result["escalation"]:.4f}':>15s} {'$' + f'{reasoning_result["escalation"]:.4f}':>15s}")
    print(f"  {'─'*72}")
    print(f"  {'COST PER SUCCESSFUL TASK':40s} {'$' + f'{base_result["total"]:.4f}':>15s} {'$' + f'{reasoning_result["total"]:.4f}':>15s}")

    winner = "Reasoning" if reasoning_result["total"] < base_result["total"] else "Base"
    savings = abs(base_result["total"] - reasoning_result["total"])
    pct = savings / max(base_result["total"], reasoning_result["total"]) * 100
    print()
    print(f"  WINNER: {winner} model  (saves ${savings:.4f} per success, {pct:.1f}%)")

    # Cost multiplier at per-query level
    mult = reasoning_result["per_call"] / base_result["per_call"]
    print(f"  Per-query cost multiplier: {mult:.1f}×")


def main():
    print("Reasoning vs Base — Cost Per Successful Task Comparison")
    print()

    # Scenario 1: High-stakes analytical task
    base_1 = ModelTier(
        name="GPT-4o",
        input_cost_per_m=2.50,
        output_cost_per_m=10.00,
        typical_input_tokens=5000,
        typical_visible_output=1200,
    )
    reasoning_1 = ModelTier(
        name="Claude 3.7",
        input_cost_per_m=3.00,
        output_cost_per_m=15.00,
        typical_input_tokens=5000,
        typical_visible_output=1200,
        typical_reasoning_tokens=16000,
    )
    econ_base_1 = TaskEconomics(name="Legal", success_rate=0.68, escalation_cost=50.00)
    econ_reasoning_1 = TaskEconomics(name="Legal", success_rate=0.91, escalation_cost=50.00)
    compare("Legal contract clause identification (high stakes)",
            base_1, reasoning_1, econ_base_1, econ_reasoning_1)

    # Scenario 2: Support FAQ (low stakes)
    base_2 = ModelTier(
        name="GPT-4o-mini",
        input_cost_per_m=0.15,
        output_cost_per_m=0.60,
        typical_input_tokens=3000,
        typical_visible_output=200,
    )
    reasoning_2 = ModelTier(
        name="o3-mini",
        input_cost_per_m=1.10,
        output_cost_per_m=4.40,
        typical_input_tokens=3000,
        typical_visible_output=200,
        typical_reasoning_tokens=4000,
    )
    econ_base_2 = TaskEconomics(name="Support", success_rate=0.91, escalation_cost=1.20)
    econ_reasoning_2 = TaskEconomics(name="Support", success_rate=0.93, escalation_cost=1.20)
    compare("Customer support FAQ (low stakes)",
            base_2, reasoning_2, econ_base_2, econ_reasoning_2)

    # Scenario 3: Autonomous agent planner
    base_3 = ModelTier(
        name="GPT-4o (planner)",
        input_cost_per_m=2.50,
        output_cost_per_m=10.00,
        typical_input_tokens=3000,
        typical_visible_output=800,
    )
    reasoning_3 = ModelTier(
        name="o3 (planner)",
        input_cost_per_m=15.00,
        output_cost_per_m=60.00,
        typical_input_tokens=3000,
        typical_visible_output=800,
        typical_reasoning_tokens=12000,
    )
    econ_base_3 = TaskEconomics(name="Agent", success_rate=0.55, escalation_cost=30.00)
    econ_reasoning_3 = TaskEconomics(name="Agent", success_rate=0.82, escalation_cost=30.00)
    compare("Autonomous agent planner",
            base_3, reasoning_3, econ_base_3, econ_reasoning_3)

    print()
    print("=" * 60)
    print("Reading the Results")
    print("=" * 60)
    print()
    print("Reasoning wins when escalation cost is high AND success rate delta is large.")
    print("Reasoning loses when escalation cost is low OR success rate delta is small.")
    print("Same technology, different economics per task.")


if __name__ == "__main__":
    main()
