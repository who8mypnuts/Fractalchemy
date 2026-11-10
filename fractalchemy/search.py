"""Fuzzy matching for the command palette (Qt-free): how well a typed query matches a text, or not at all.

`fuzzy_score(query, text)` is None when the query's characters do not all appear in the text in order (case-insensitive),
else a score — higher is better: a contiguous match beats a scattered one, a match at the start of the text or of a word
beats one inside a word, and shorter texts win ties.
"""

from __future__ import annotations

WORD_BREAKS = " _-▸/.:(…"


def fuzzy_score(query: str, text: str) -> float | None:
    """How well `query` matches `text` (None: it does not)."""
    q = query.lower().strip()
    t = text.lower()
    if not q:
        return 0.0
    at = t.find(q)
    if at >= 0:
        word_start = at == 0 or t[at - 1] in WORD_BREAKS
        return 1000.0 + (300.0 if at == 0 else 150.0 if word_start else 0.0) - at - len(t) * 0.1
    score, position, previous = 0.0, 0, -2
    for ch in q:
        if ch == " ":
            continue
        found = t.find(ch, position)
        if found < 0:
            return None
        score += 10.0
        if found == previous + 1:
            score += 15.0                                  # consecutive characters
        if found == 0 or t[found - 1] in WORD_BREAKS:
            score += 20.0                                  # the start of a word
        score -= (found - position) * 0.5                  # gaps cost a little
        previous, position = found, found + 1
    return score - len(t) * 0.1


def best_matches(query: str, texts: list[str], limit: int | None = None) -> list[tuple[float, int]]:
    """(score, index) of the texts that match, best first."""
    scored = [(s, i) for i, s in ((i, fuzzy_score(query, text)) for i, text in enumerate(texts)) if s is not None]
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return scored[:limit] if limit else scored


__all__ = ["fuzzy_score", "best_matches"]
