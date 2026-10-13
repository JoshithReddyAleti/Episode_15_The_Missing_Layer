"""
session_continuation_demo.py — Session state across devices with pinning.

Demonstrates:
- Three-level state model (session / conversation / continuous)
- Conversation model-and-prompt pinning
- Multi-device conversation resume
- Draft preservation for partial state recovery

Run:
    python session_continuation_demo.py
"""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


# --- State model ---

@dataclass
class Message:
    role: str
    content: str
    ts: float = field(default_factory=time.time)


@dataclass
class Conversation:
    """Persistent conversation state. Postgres-backed in production."""
    id: str
    user_id: str
    tenant_id: str
    messages: list[Message] = field(default_factory=list)
    # Pinned at conversation start — never changes
    pinned_model: str = "gpt-4o"
    pinned_prompt_version: str = "v3"
    pinned_tools: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class Session:
    """Ephemeral session state. Redis-backed in production."""
    id: str
    user_id: str
    conversation_id: str
    device_fingerprint: str
    active_stream_id: Optional[str] = None
    draft_text: str = ""
    last_activity: float = field(default_factory=time.time)


@dataclass
class ContinuousState:
    """User memory across all conversations. Structured DB + vectors in production."""
    user_id: str
    tenant_id: str
    preferences: dict[str, str] = field(default_factory=dict)
    entity_memory: dict[str, str] = field(default_factory=dict)


# --- The state store ---

class StateStore:
    def __init__(self):
        self.sessions: dict[str, Session] = {}
        self.conversations: dict[str, Conversation] = {}
        self.continuous: dict[str, ContinuousState] = {}

    def create_conversation(self, user_id: str, tenant_id: str,
                            current_model: str, current_prompt_version: str) -> Conversation:
        """New conversations pin to current model/prompt."""
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            pinned_model=current_model,
            pinned_prompt_version=current_prompt_version,
        )
        self.conversations[conv.id] = conv
        return conv

    def start_session(self, user_id: str, conversation_id: str,
                      device_fingerprint: str) -> Session:
        """User opens a device. Attach a session to an existing conversation."""
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            conversation_id=conversation_id,
            device_fingerprint=device_fingerprint,
        )
        self.sessions[session.id] = session
        return session

    def save_draft(self, session_id: str, text: str) -> None:
        """Auto-called every few seconds while user types."""
        if session_id in self.sessions:
            self.sessions[session_id].draft_text = text
            self.sessions[session_id].last_activity = time.time()

    def get_conversation_for_resume(self, conversation_id: str) -> Optional[Conversation]:
        """When a device reconnects, load the conversation."""
        return self.conversations.get(conversation_id)


# --- Demo ---

def main():
    store = StateStore()

    # Set up continuous state (user memory)
    store.continuous["user_alice"] = ContinuousState(
        user_id="user_alice",
        tenant_id="acme_corp",
        preferences={"tone": "casual", "language": "en"},
        entity_memory={"current_project": "Q4 roadmap"},
    )

    # --- Day 1: user on phone ---
    print("=== Day 1: Alice on phone ===")
    conv = store.create_conversation(
        user_id="user_alice",
        tenant_id="acme_corp",
        current_model="gpt-4o",
        current_prompt_version="v3",
    )
    print(f"  New conversation: {conv.id[:8]}...")
    print(f"  Pinned: model={conv.pinned_model} prompt={conv.pinned_prompt_version}")

    session_phone = store.start_session(
        user_id="user_alice",
        conversation_id=conv.id,
        device_fingerprint="phone_ios",
    )
    conv.messages.append(Message("user", "Help me draft the Q4 update"))
    conv.messages.append(Message("assistant", "Sure! What are the key wins to highlight?"))
    print(f"  Messages: {len(conv.messages)}")

    # User starts typing but doesn't send
    store.save_draft(session_phone.id, "The main win was")
    print(f"  Draft saved: '{session_phone.draft_text}'")

    # --- Day 2: platform upgraded to gpt-5 with prompt v4 ---
    print("\n=== Day 2: platform now defaults to gpt-5 + v4 prompt ===")
    print(f"  Alice's conversation still pinned to: {conv.pinned_model} / {conv.pinned_prompt_version}")

    # --- Day 2: Alice opens laptop ---
    print("\n=== Day 2: Alice opens laptop ===")
    session_laptop = store.start_session(
        user_id="user_alice",
        conversation_id=conv.id,
        device_fingerprint="laptop_mac",
    )
    resumed = store.get_conversation_for_resume(conv.id)
    print(f"  Resumed conversation with {len(resumed.messages)} messages")
    print(f"  Still using pinned {resumed.pinned_model} + {resumed.pinned_prompt_version}")
    print(f"  Draft from phone available: '{session_phone.draft_text}'")

    # Continuous state (user memory) is available across both devices
    memory = store.continuous["user_alice"]
    print(f"  User memory intact: {memory.preferences}")


if __name__ == "__main__":
    main()
