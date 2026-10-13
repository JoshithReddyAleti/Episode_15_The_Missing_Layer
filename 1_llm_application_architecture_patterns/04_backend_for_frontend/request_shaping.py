"""
Request Shaping

Client request → provider request → client response transformations

See the section README for the full deep-dive:
  1_llm_application_architecture_patterns/04_backend_for_frontend/README.md
"""


def summary() -> str:
    """One-line summary — the README is the source of truth."""
    return "Client request → provider request → client response transformations"


if __name__ == "__main__":
    print(summary())
