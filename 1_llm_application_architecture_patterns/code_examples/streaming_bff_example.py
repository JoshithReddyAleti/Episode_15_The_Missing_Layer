"""
streaming_bff_example.py — Reference implementation of an LLM BFF with streaming.

Demonstrates:
- SSE streaming to the client
- Provider abstraction (mock provider that could be swapped)
- Per-user rate limiting (in-memory; use Redis in production)
- Buffered replay for resume
- Observability hooks (trace ID, cost accounting)

Run:
    python streaming_bff_example.py
"""
from __future__ import annotations
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Iterator


# --- Provider abstraction ---

@dataclass
class LLMEvent:
    """A single event in a streaming response."""
    kind: str  # 'token', 'tool_call', 'tool_result', 'citation', 'done'
    data: dict


class MockProvider:
    """Stand-in for OpenAI / Anthropic / Bedrock."""

    def stream(self, messages: list[dict]) -> Iterator[LLMEvent]:
        # Simulate a streamed response with a tool call
        text = "Let me check that. "
        for token in text.split():
            yield LLMEvent("token", {"text": token + " "})
            time.sleep(0.05)
        yield LLMEvent("tool_call", {"name": "check_order", "args": {"id": "12345"}})
        time.sleep(0.3)  # tool executes
        yield LLMEvent("tool_result", {"name": "check_order", "result": {"status": "shipped"}})
        text = "Your order shipped yesterday."
        for token in text.split():
            yield LLMEvent("token", {"text": token + " "})
            time.sleep(0.05)
        yield LLMEvent("citation", {"span": [23, 60], "source": "check_order:12345"})
        yield LLMEvent("done", {"tokens_used": 42, "cost_usd": 0.0008})


# --- Per-user rate limiting (in-memory demo) ---

class RateLimiter:
    def __init__(self, limit_per_minute: int = 30):
        self.limit = limit_per_minute
        self._history: dict[str, deque] = defaultdict(deque)

    def check(self, user_id: str) -> bool:
        now = time.time()
        history = self._history[user_id]
        while history and history[0] < now - 60:
            history.popleft()
        if len(history) >= self.limit:
            return False
        history.append(now)
        return True


# --- Streaming buffer for resume ---

class StreamBuffer:
    """In-memory demo. Redis in production."""

    def __init__(self):
        self._buffers: dict[str, list[LLMEvent]] = {}

    def append(self, stream_id: str, event: LLMEvent) -> None:
        self._buffers.setdefault(stream_id, []).append(event)

    def replay(self, stream_id: str) -> list[LLMEvent]:
        return self._buffers.get(stream_id, [])

    def complete(self, stream_id: str) -> None:
        # After a stream is done, could TTL it or move to persistent store
        pass


# --- The BFF itself ---

@dataclass
class LLMBFF:
    provider: MockProvider = field(default_factory=MockProvider)
    rate_limiter: RateLimiter = field(default_factory=RateLimiter)
    buffer: StreamBuffer = field(default_factory=StreamBuffer)

    def stream_completion(
        self,
        user_id: str,
        messages: list[dict],
        on_event: Callable[[LLMEvent], None],
        stream_id: str | None = None,
    ) -> str:
        """Stream a completion; call on_event for each event.

        Returns the stream_id (useful for resume).
        """
        # 1. Rate limit
        if not self.rate_limiter.check(user_id):
            on_event(LLMEvent("error", {"code": "rate_limited"}))
            return ""

        # 2. New or resumed stream?
        stream_id = stream_id or str(uuid.uuid4())

        # 3. If resumed, replay buffer first
        if self.buffer.replay(stream_id):
            for event in self.buffer.replay(stream_id):
                on_event(event)
            return stream_id  # already complete; just replayed

        # 4. Trace ID for observability
        trace_id = str(uuid.uuid4())
        print(f"[trace={trace_id}] user={user_id} stream={stream_id} started")

        # 5. Stream from provider
        total_cost = 0.0
        for event in self.provider.stream(messages):
            self.buffer.append(stream_id, event)
            on_event(event)
            if event.kind == "done":
                total_cost = event.data.get("cost_usd", 0.0)

        # 6. Emit observability record
        print(f"[trace={trace_id}] completed cost=${total_cost:.4f}")
        self.buffer.complete(stream_id)
        return stream_id


# --- Demo ---

def main():
    bff = LLMBFF()

    def print_event(event: LLMEvent):
        print(f"  [{event.kind}] {event.data}")

    print("=== First request ===")
    stream_id = bff.stream_completion(
        user_id="user_alice",
        messages=[{"role": "user", "content": "Where's my order?"}],
        on_event=print_event,
    )
    print(f"\nStream ID: {stream_id}")

    print("\n=== Resume the same stream ===")
    bff.stream_completion(
        user_id="user_alice",
        messages=[{"role": "user", "content": "Where's my order?"}],
        on_event=print_event,
        stream_id=stream_id,
    )


if __name__ == "__main__":
    main()
