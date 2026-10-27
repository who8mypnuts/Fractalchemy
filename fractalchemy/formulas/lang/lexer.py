"""Tokeniser for the formula language (a C subset)."""

from __future__ import annotations

import re
from dataclasses import dataclass


class LexError(ValueError):
    """Unrecognised input."""


@dataclass(frozen=True)
class Token:
    kind: str        # ident | number | string | char | op | ws | eof
    value: str
    pos: int = 0

    def __repr__(self) -> str:
        return f"{self.kind}:{self.value!r}"


_OPERATORS = [
    "<<=", ">>=", "...", "->", "++", "--", "<<", ">>", "<=", ">=", "==", "!=", "&&", "||", "+=", "-=", "*=", "/=",
    "%=", "&=", "|=", "^=", "##", "::",
    "+", "-", "*", "/", "%", "<", ">", "=", "!", "&", "|", "^", "~", "?", ":", ",", ";", ".", "(", ")", "[", "]",
    "{", "}", "#",
]
_TOKEN = re.compile(
    r"(?P<ws>\s+)"
    r"|(?P<number>0[xX][0-9A-Fa-f]+[uUlL]*|(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?(?:i\b|[fFlLuU]*))"
    r"|(?P<ident>[A-Za-z_]\w*)"
    r'|(?P<string>"(?:\\.|[^"\\])*")'
    r"|(?P<char>'(?:\\.|[^'\\])')"
    r"|(?P<op>" + "|".join(re.escape(op) for op in _OPERATORS) + ")"
)


def tokenize(text: str, keep_whitespace: bool = False) -> list[Token]:
    """Split `text` into tokens; raises LexError on anything unexpected."""
    tokens: list[Token] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise LexError(f"unexpected character {text[pos]!r} at offset {pos}")
        kind = m.lastgroup
        if kind != "ws" or keep_whitespace:
            tokens.append(Token(kind, m.group(0), pos))
        pos = m.end()
    if not keep_whitespace:
        tokens.append(Token("eof", "", pos))
    return tokens
