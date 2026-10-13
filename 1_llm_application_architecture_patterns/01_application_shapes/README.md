# 🎭 Application Shapes — The First Architecture Decision

> *Before you pick a model. Before you write a prompt. Before you spin up a vector DB. You pick a shape.*
>
> *Get this wrong and the rest of your architecture is fighting gravity.*

---

## The Four Shapes

Every LLM product I've ever seen fits one of these four shapes. Products that try to be more than one usually fail at all of them.

### 1. Assistant

**The user comes to the AI.** The AI is the surface. The user asks; the AI answers; repeat.

**Interaction model:** turn-based conversation. Each turn is a message pair (user, assistant).

**State:** thin. Conversation history. Optional user memory. Optional retrieved context per turn. That's it.

**Examples:** ChatGPT. Claude.ai. Perplexity. Most consumer chatbots. Most B2C support bots.

**Design implications:**
- **Streaming is critical** — you cannot ship an assistant with 5-second first-token latency
- **Personality matters** — the user talks *to* the AI, not through it
- **Memory matters** — users get frustrated when the AI forgets what they said 10 messages ago
- **Failure mode is "bad response"** — visible immediately, low blast radius

### 2. Copilot

**The user is doing something else.** The AI helps them do it better, inline. The user's actual surface is code, a document, a form, a design canvas. The AI lives *inside* that surface.

**Interaction model:** ambient assistance. Suggestions appear as you work. Sometimes the user requests explicitly (⌘K); sometimes the AI offers unprompted (autocomplete).

**State:** rich. The user's current file. Cursor position. Selected text. Project context. Recent edits. The AI needs to see enough of the workspace to be useful.

**Examples:** GitHub Copilot. Cursor. Notion AI. Grammarly. Figma AI.

**Design implications:**
- **Latency budget is sub-second** — anything > 500ms and the user has typed past your suggestion
- **Suggestions are silent when wrong** — the user just doesn't accept them; you don't get thanked
- **Acceptance rate is the primary metric** — quality is measured by "did the user take it?"
- **Context assembly is 80% of the work** — the model is easy; getting the right slice of the workspace to the model is hard
- **Failure mode is "misleading suggestion"** — accepted then regretted is worse than never accepted

### 3. Agent-first

**The user states a goal.** The AI plans and executes. The user comes back later for the result.

**Interaction model:** goal-oriented. The user's message is not "answer this question" but "accomplish this task."

**State:** rich and structured. Task specification. Plan. Sub-tasks. Tool call history. Intermediate outputs. Retry counts. This state may live for minutes, hours, or days.

**Examples:** Devin. Manus. Deep Research features. Autonomous coding agents. Some sales-outreach agents.

**Design implications:**
- **Latency is minutes to hours** — the user doesn't wait; they get a notification
- **Task success rate is the primary metric** — did the agent actually complete the goal?
- **State persistence is non-negotiable** — you cannot lose an agent's progress if a server crashes
- **Human-in-the-loop is the safety valve** — approvals, checkpoints, escape hatches
- **Failure mode is "wrong outcome"** — high blast radius, sometimes irreversible
- **Evaluation is the hardest problem** — measuring success on open-ended goals is unsolved

### 4. Workflow-first

**The AI is a step in a pipeline.** No user in the loop for most of it. Business process runs on rails, and the LLM handles one specific task at each step.

**Interaction model:** none — usually. The system calls the LLM. The LLM returns structured output. The system continues.

**State:** thin per-invocation, rich in the *pipeline*. The LLM sees only what it needs for its task. The pipeline knows everything.

**Examples:** Invoice classification. Content moderation. Support ticket triage. Document parsing. Fraud flag generation. Sentiment tagging. Log summarization.

**Design implications:**
- **Reliability > cleverness** — the same input should give the same output every time
- **Throughput matters more than latency** — batch processing is fine
- **Structured output is mandatory** — the pipeline consumes JSON/typed data, not prose
- **Cost per unit is the primary metric** — you're often processing millions of invocations
- **Failure mode is "silent bad output"** — the pipeline continues; downstream systems trust the LLM; the mistake compounds
- **Evaluation is deterministic** — you have ground-truth labels or can construct them

---

## The Cross-Cut Reference

| Property | Assistant | Copilot | Agent-first | Workflow-first |
|---|---|---|---|---|
| **User's primary activity** | Talking to AI | Working on something | Waiting on AI | Not present |
| **User in loop** | Every turn | Passive / occasional | Boundaries only | Rarely |
| **State richness** | Thin | Rich (host context) | Rich (task) | Thin per-call |
| **State duration** | Minutes | Session | Minutes to days | Milliseconds |
| **Latency budget (P95)** | 2-5s to first token | < 500ms suggestion | Minutes to hours end-to-end | Batch-tolerable |
| **Streaming importance** | Very high | Very high | Low | None |
| **Personality** | Matters | Doesn't (silent) | Matters at boundaries | Doesn't |
| **Primary metric** | Response quality | Suggestion acceptance rate | Task success rate | Cost × accuracy at throughput |
| **Failure mode** | Bad response (visible) | Misleading suggestion | Wrong outcome (may be silent) | Silent bad output (compounds) |
| **Evaluation difficulty** | Medium (LLM-judge, ratings) | Medium (acceptance) | Very high | Low (labeled sets) |
| **Blast radius per failure** | Low (one turn) | Medium (accepted mistake) | High (irreversible action) | High (compounds) |
| **Cost sensitivity** | Medium | High (called constantly) | High (many tool calls) | Extreme (millions of calls) |

---

## The Decision Framework

Ask three questions in order:

**Q1: Where does the user spend their time?**

- Talking to the AI → **Assistant**
- Doing something the AI can help with → **Copilot**
- Waiting for a result → **Agent-first**
- Nowhere in this loop → **Workflow-first**

**Q2: What defines success?**

- A satisfying response → **Assistant**
- A suggestion the user takes → **Copilot**
- The goal accomplished → **Agent-first**
- A structured output produced reliably → **Workflow-first**

**Q3: What's the blast radius of a failure?**

- The user tries again → **Assistant**
- The user ignores or edits → **Copilot** (still be careful — subtle wrong answers are worst)
- Money spent, data changed, wrong action taken → **Agent-first** (needs approvals, kill switches)
- Downstream systems consume bad output → **Workflow-first** (needs validation, canaries, quality gates)

**If the answers point to different shapes:** the product is under-specified. Go back to product and figure out the real user journey.

---

## The Anti-Patterns

**"Chatbot for everything."**
You built an Assistant. But your users don't want to chat — they want to do their work. A Copilot would have been the right choice. Now you have a beautiful chatbot that nobody uses because it's not on the surface where work happens.

*Real example:* every "AI in your CRM" chatbot that no salesperson opens.

**"Agent from day one."**
You built an Agent-first product because it sounded cool. Users don't trust it enough to hand over goals. They want to see it work step by step. You needed a Copilot with escalation-to-Agent for well-defined tasks, not full autonomy from the start.

*Real example:* early Devin — brilliant demos, cautious adoption, because trust wasn't earned yet.

**"Assistant, but really a workflow."**
Your product looks like a chatbot but it's actually gating a business process. Users hate it because it's not conversational — it's an interrogation. Should have been a form with LLM-in-the-loop, not a chat surface.

*Real example:* every "chatbot" support experience that's actually a decision tree in trench coat.

**"Workflow-first, but the failure mode nobody planned for."**
You built a workflow that classifies documents. Accuracy is 96%. In production. The 4% wrong classifications hit high-value accounts. Money moves. Nobody notices for a month.

*Real example:* most enterprise "AI automation" projects that get quietly killed after an audit.

---

## Files In This Folder

| File | Concept |
|---|---|
| [`assistant_pattern.py`](assistant_pattern.py) | Assistant shape — reference structure, state model, common pitfalls |
| [`copilot_pattern.py`](copilot_pattern.py) | Copilot shape — context assembly, acceptance metrics, inline UX |
| [`agent_first_pattern.py`](agent_first_pattern.py) | Agent-first shape — task state, HITL, checkpoints, blast radius |
| [`workflow_first_pattern.py`](workflow_first_pattern.py) | Workflow-first shape — throughput, reliability, structured I/O |
| [`choosing_the_shape.py`](choosing_the_shape.py) | The decision framework as a runnable questionnaire |

---

## The Staff Interview Question

*"Design a code review assistant."*

**The wrong opener:** "I'd use RAG on the codebase and prompt an LLM to review the code."

**The right opener:**
"Two shapes are viable here. If reviewers come to a chat surface, it's an Assistant — but reviewers live in GitHub PRs, so that's the wrong shape. If it lives inline on the PR — surfacing comments, suggesting fixes — that's a Copilot. Copilot is the correct choice because it meets reviewers where their work happens. That decision changes everything downstream: the primary metric becomes suggestion acceptance rate, not chat satisfaction. Latency budget is sub-second on the PR page. Context assembly needs the diff, the changed files, the PR description, and relevant history. Now let's design the retrieval and prompt layers on top of that Copilot foundation."

**That's the difference.** The candidate who names the shape and defends it has already won half the interview.

---

*Return to [folder README](../README.md) · Next: [Multi-Tenancy →](../02_multi_tenancy/README.md)*
