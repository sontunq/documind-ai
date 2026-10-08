"""Shared training/inference preprocessing. Preserve words, numbers, punctuation."""
def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())
