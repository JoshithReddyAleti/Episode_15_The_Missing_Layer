# 🎯 Reasoning Model Selection Guide

A practical decision tree for picking the right reasoning tier for a given feature.

## Question 1: Do you need reasoning at all?

Task categories:
- **Reasoning wins:** math, code, logic, multi-step analysis, root-cause debugging → continue
- **Reasoning ties:** simple classification, extraction, format tasks → **use base model, stop**
- **Reasoning loses:** creative writing, empathetic dialogue, interactive chat → **use base model, stop**

## Question 2: What's your latency budget?

| Latency budget | Options |
|---|---|
| < 3s | Base + BoN parallel, mini reasoning at low effort |
| 3-15s | Mini reasoning (o1-mini, o3-mini, Gemini Flash Thinking) |
| 15-60s | Standard reasoning (Claude 3.7 extended, DeepSeek-R1) |
| 60s+ | Full reasoning at medium/high effort (o1, o3) |
| Minutes+ | Any reasoning with BoN and verifier ensemble |

## Question 3: What's your cost budget per successful task?

| Budget per success | Options |
|---|---|
| < $0.01 | Base model with cache stack; skip reasoning |
| $0.01 - $0.10 | Base + BoN, mini reasoning at low effort |
| $0.10 - $1.00 | Standard reasoning, mini reasoning at high effort |
| $1.00+ | Full reasoning at medium/high effort |
| $10.00+ | Reasoning + BoN + verifier ensemble |

## Question 4: What's your compliance context?

| Context | Implications |
|---|---|
| Standard B2B SaaS | Any provider works |
| Healthcare / HIPAA | Prefer BAA-covered providers (OpenAI enterprise, Anthropic, Bedrock) |
| Financial services | Prefer providers with SOC 2 + specific certifications |
| Government / defense | Bedrock GovCloud, Azure Government, or on-prem/self-hosted DeepSeek-R1 |
| Auditability required | Prefer visible-reasoning models (Claude, Gemini, DeepSeek); hidden reasoning limits audit |
| Data residency | Provider region constraints; consider self-hosted DeepSeek-R1 |

## Question 5: Which provider tier fits?

**For lowest cost:**
- DeepSeek-R1 API or self-hosted (dramatic cost advantage)
- Gemini 2.5 Flash Thinking (cheap tier from Google)

**For balanced quality/cost:**
- Claude 3.7 Sonnet extended thinking (with configurable budget)
- o3-mini or o1-mini
- Gemini 2.5 Pro Thinking

**For maximum quality:**
- o3 or o4 at high effort
- Claude Opus with thinking (when available)

**For enterprise compliance:**
- Anthropic (strong contract terms)
- Bedrock (AWS ecosystem, region control)
- Azure OpenAI (Microsoft compliance)

**For inspectable reasoning:**
- Claude 3.7 (visible extended thinking)
- DeepSeek-R1 (full trace)
- Gemini Thinking (partial visibility)

## The Decision Tree Summary

```
Task fits reasoning? ─── No ──► Base model with cache stack
       │
       Yes
       │
Verifier available? ─── No ──► Reasoning model, single shot
       │
       Yes
       │
Latency budget?
   < 5s ────────► Base + BoN parallel OR mini reasoning low effort
   5-30s ───────► Mini reasoning medium/high, or standard reasoning
   30s+ ────────► Full reasoning or reasoning + BoN
       │
       │
Compliance? ──► Filter providers accordingly
       │
       │
Cost budget? ──► Filter tiers accordingly
       │
       ▼
   Chosen tier
```

## Real Selections

**Legal contract analyzer:** Claude 3.7 Sonnet extended thinking (16K budget) — visible reasoning for auditability, strong reasoning capability, Anthropic enterprise contract.

**Autonomous coding agent (planner):** o3 default — best-in-class planning, hidden reasoning acceptable, OpenAI enterprise contract.

**Math tutor:** DeepSeek-R1 API — cheapest reasoning tier, visible reasoning for pedagogy, math is directly in training distribution.

**Financial analyst research tool:** Claude 3.7 extended thinking + best-of-4 with LLM-judge — high stakes justify verifier ensemble; extended thinking gives inspectable reasoning for compliance.

**Consumer chatbot with reasoning fallback:** GPT-4o default, escalate to o3-mini on low-confidence — most traffic stays cheap, escalation for complex queries.
