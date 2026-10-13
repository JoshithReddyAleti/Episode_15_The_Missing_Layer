# 📖 Cost Engineering Glossary

**Actual cost** — LLM call cost after all caching and routing discounts applied.

**Allocated cost** — variable cost plus share of fixed infrastructure and headcount.

**Anomaly detection** — automated monitoring of cost signals for outlier events triggering alerts or throttling.

**Batch API** — provider offering with delayed SLA in exchange for ~50% cost discount.

**Break-even utilization** — the sustained throughput at which self-hosting matches provider API cost.

**Budget hard cap** — spend level triggering automated degradation (route to smaller model).

**Budget kill switch** — spend level triggering complete block of further LLM calls.

**Budget soft alert** — spend level triggering notification without automated action.

**Cache hit rate** — fraction of requests served from cache instead of a fresh LLM call.

**Cascade router** — routing pattern that starts with cheap model, escalates only when confidence is low.

**Classifier router** — routing pattern using a small LLM to categorize the query and select the appropriate model.

**Contribution margin** — revenue per unit minus variable cost per unit.

**Cost observability** — telemetry that makes cost debuggable in the same way traces make latency debuggable.

**Cost per active user (CPU)** — total variable cost divided by active users in a period.

**Cost per successful task** — the actual unit economic; total variable cost to produce one successful business outcome.

**End-of-month projection** — forecast of monthly spend based on current burn rate and trend.

**Exact response cache** — cache layer that returns previous answers for byte-identical requests.

**Fixed cost per task** — cost that applies regardless of number of LLM call attempts (logging, audit, notifications).

**Hybrid deployment** — architecture using provider APIs for majority of traffic and self-hosted for specific workloads.

**KV cache** — internal transformer state cached across a conversation session to avoid recomputing prior tokens.

**Learned router** — routing pattern using a fine-tuned classifier trained on labeled query-to-route data.

**Marginal cost** — the additional cost of serving one more task.

**Model routing** — architectural pattern of choosing the smallest capable model for each request.

**Multi-provider fallback** — reliability pattern of using multiple LLM providers with automatic failover.

**On-demand pricing** — cloud GPU pricing with no commitment; most expensive per hour, most flexible.

**Ops overhead** — the human and infrastructure cost of running self-hosted GPU inference in production.

**Prompt cache** — provider-side cache of prompt prefix computations, discounted on repeat.

**Reserved instances** — cloud GPU pricing with 1-3 year commitment; 30-70% discount over on-demand.

**Runaway** — cost anomaly caused by unbounded LLM usage; typical causes are infinite loops, max_tokens misconfigurations, or abusive input.

**Semantic cache** — cache layer that returns previous answers for semantically similar (not identical) queries.

**Spot instances** — cloud GPU pricing with 60-90% discount but interruptible; suitable for batch workloads.

**Success rate** — fraction of task attempts that complete successfully without escalation.

**Sustained load** — average throughput required to justify self-hosted infrastructure economics.

**Throughput** — output tokens per second, aggregate across all concurrent requests.

**Total cost of ownership (TCO)** — full cost of self-hosting including hardware, ops, on-call, and reliability engineering.

**Unit economics** — the profitability math per unit of business outcome (customer, task, user).

**Utilization** — fraction of self-hosted capacity actually being used at a given time.
