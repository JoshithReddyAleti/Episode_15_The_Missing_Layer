"""
cache_stack_demo.py — Three-layer cache stack with hit rate simulation.

Demonstrates:
- Exact response cache (Layer 1)
- Semantic cache (Layer 2, threshold-based)
- Prompt cache savings (Layer 3, provider-side)

Simulates a workload and reports combined cost reduction.

Run:
    python cache_stack_demo.py
"""
import hashlib
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Request:
    tenant_id: str
    user_message: str
    retrieved_context_hash: str
    prompt_version: str = "v3"
    model: str = "gpt-4o"


@dataclass
class Response:
    text: str
    tokens_used: int
    cache_source: str  # 'exact', 'semantic', 'prompt_cache_hit', 'full'


class ExactResponseCache:
    """Layer 1: byte-identical request cache."""

    def __init__(self):
        self._cache: dict[str, Response] = {}
        self.hits = 0
        self.misses = 0

    def key(self, req: Request) -> str:
        h = hashlib.sha256()
        for field in [req.tenant_id, req.user_message, req.retrieved_context_hash,
                      req.prompt_version, req.model]:
            h.update(field.encode())
            h.update(b":")
        return h.hexdigest()

    def get(self, req: Request) -> Optional[Response]:
        k = self.key(req)
        if k in self._cache:
            self.hits += 1
            return self._cache[k]
        self.misses += 1
        return None

    def put(self, req: Request, resp: Response):
        self._cache[self.key(req)] = resp


class SemanticCache:
    """Layer 2: similarity-based cache (simulated with prefix matching for demo)."""

    def __init__(self, threshold: float = 0.95):
        self.threshold = threshold
        # (tenant_id, prompt_version) -> list of (message_prefix, response)
        self._cache: dict[tuple, list] = {}
        self.hits = 0
        self.misses = 0

    def _similarity(self, a: str, b: str) -> float:
        """Simulated similarity — real impl would use embeddings."""
        if a == b:
            return 1.0
        # Simulate: 12-character prefix match ~0.96
        common = 0
        for ca, cb in zip(a.lower(), b.lower()):
            if ca == cb:
                common += 1
            else:
                break
        max_len = max(len(a), len(b))
        return common / max_len if max_len else 0.0

    def get(self, req: Request) -> Optional[Response]:
        key = (req.tenant_id, req.prompt_version)
        entries = self._cache.get(key, [])
        for prev_msg, prev_resp in entries:
            sim = self._similarity(req.user_message, prev_msg)
            if sim >= self.threshold:
                self.hits += 1
                return prev_resp
        self.misses += 1
        return None

    def put(self, req: Request, resp: Response):
        key = (req.tenant_id, req.prompt_version)
        self._cache.setdefault(key, []).append((req.user_message, resp))


@dataclass
class PromptCacheState:
    """Layer 3: provider-side prompt cache tracking (Anthropic-style ~90% discount)."""
    cache_read_savings: float = 0.90
    prefix_cached_fraction: float = 0.65  # portion of tokens that are cached prefix
    seen_prompt_versions: set = field(default_factory=set)

    def cost_multiplier(self, prompt_version: str) -> float:
        """Return the fraction of full cost to pay."""
        if prompt_version in self.seen_prompt_versions:
            # Cached
            return (1 - self.prefix_cached_fraction) + \
                   (self.prefix_cached_fraction * (1 - self.cache_read_savings))
        else:
            self.seen_prompt_versions.add(prompt_version)
            # First hit: cache write premium
            return 1.25


class CostModel:
    """GPT-4o pricing (approximate 2026)."""

    INPUT_COST_PER_M = 2.50
    OUTPUT_COST_PER_M = 10.00

    def cost(self, input_tokens: int, output_tokens: int, cost_multiplier: float = 1.0) -> float:
        input_cost = input_tokens / 1_000_000 * self.INPUT_COST_PER_M * cost_multiplier
        output_cost = output_tokens / 1_000_000 * self.OUTPUT_COST_PER_M
        return input_cost + output_cost


def simulate_workload(n_requests: int = 1000):
    exact = ExactResponseCache()
    semantic = SemanticCache(threshold=0.95)
    prompt_cache = PromptCacheState()
    costs = CostModel()

    # Generate a workload with realistic hit patterns
    TENANTS = ["tenant_a", "tenant_b", "tenant_c"]
    FAQ_QUERIES = [
        "What are your business hours",
        "How do I return an item",
        "What is your shipping policy",
        "How do I reset my password",
        "Where is my order",
    ]

    total_full_cost = 0.0    # if no caching
    total_actual_cost = 0.0  # with caching

    for i in range(n_requests):
        tenant = random.choice(TENANTS)
        # 40% of queries are FAQ-style (cacheable)
        if random.random() < 0.4:
            base_msg = random.choice(FAQ_QUERIES)
            # Sometimes exact, sometimes minor variation
            if random.random() < 0.5:
                msg = base_msg  # exact match
            else:
                msg = base_msg + "?" if not base_msg.endswith("?") else base_msg[:-1]
        else:
            msg = f"Unique query {i} with random content {random.randint(1, 10000)}"

        req = Request(
            tenant_id=tenant,
            user_message=msg,
            retrieved_context_hash=f"ctx_{i // 100}",  # context changes every 100 requests
        )

        # Baseline: full cost with no caching
        input_tokens = len(msg) + 3000  # simulated system + context tokens
        output_tokens = 400
        full_cost = costs.cost(input_tokens, output_tokens, cost_multiplier=1.0)
        total_full_cost += full_cost

        # Check exact cache
        resp = exact.get(req)
        if resp:
            # 100% savings
            continue

        # Check semantic cache
        resp = semantic.get(req)
        if resp:
            # 100% savings
            continue

        # Cache miss — pay for LLM with prompt cache benefit
        mult = prompt_cache.cost_multiplier(req.prompt_version)
        actual = costs.cost(input_tokens, output_tokens, cost_multiplier=mult)
        total_actual_cost += actual

        # Store in caches
        new_resp = Response(
            text=f"[response to '{msg[:30]}']",
            tokens_used=input_tokens + output_tokens,
            cache_source="full" if mult > 1 else "prompt_cache_hit",
        )
        exact.put(req, new_resp)
        semantic.put(req, new_resp)

    return {
        "total_requests": n_requests,
        "exact_hits": exact.hits,
        "exact_hit_rate": exact.hits / n_requests * 100,
        "semantic_hits": semantic.hits,
        "semantic_hit_rate": semantic.hits / max(1, n_requests - exact.hits) * 100,
        "cost_no_caching": total_full_cost,
        "cost_with_caching": total_actual_cost,
        "savings_pct": (1 - total_actual_cost / total_full_cost) * 100,
    }


def main():
    random.seed(42)
    result = simulate_workload(n_requests=1000)

    print("=== 3-Layer Cache Stack Simulation ===")
    print(f"  Total requests: {result['total_requests']}")
    print()
    print(f"  Layer 1 (Exact) hits:    {result['exact_hits']:4d}  ({result['exact_hit_rate']:.1f}%)")
    print(f"  Layer 2 (Semantic) hits: {result['semantic_hits']:4d}  ({result['semantic_hit_rate']:.1f}% of remaining)")
    print(f"  Layer 3 (Prompt cache):   built in on all cache misses")
    print()
    print(f"  Cost with NO caching:    ${result['cost_no_caching']:.2f}")
    print(f"  Cost WITH cache stack:   ${result['cost_with_caching']:.2f}")
    print(f"  {'─' * 45}")
    print(f"  Savings:                 {result['savings_pct']:.1f}%")


if __name__ == "__main__":
    main()
