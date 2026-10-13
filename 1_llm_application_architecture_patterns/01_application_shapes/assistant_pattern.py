"""
Assistant Pattern

The Assistant shape — turn-based conversation, thin state, streaming-first, personality-driven

See the section README for the full deep-dive:
  1_llm_application_architecture_patterns/01_application_shapes/README.md
"""


def summary() -> str:
    """One-line summary — the README is the source of truth."""
    return "The Assistant shape — turn-based conversation, thin state, streaming-first, personality-driven"


if __name__ == "__main__":
    print(summary())
