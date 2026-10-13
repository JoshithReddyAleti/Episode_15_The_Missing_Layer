"""
Streaming With Tool Calls

Three patterns: pause-execute-resume, announce-execute-continue, speculative streaming

See the section README for the full deep-dive:
  1_llm_application_architecture_patterns/03_streaming_architecture/README.md
"""


def summary() -> str:
    """One-line summary — the README is the source of truth."""
    return "Three patterns: pause-execute-resume, announce-execute-continue, speculative streaming"


if __name__ == "__main__":
    print(summary())
