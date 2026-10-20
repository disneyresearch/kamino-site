"""Render the Basic Usage snippet into index.html with semantic syntax highlighting.

Names are classified by importing the snippet's imports and resolving dotted
attribute chains through introspection, so modules, classes and types,
functions and methods, and constants are colored by what they actually are.
Brackets are colored by nesting depth.

Run from the site root with an environment that has Newton installed, e.g.:

    uv run --project ../../src/newton-alt python tools/render_snippet.py

Pass ``--check`` to only verify that index.html is up to date.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import enum
import html
import importlib
import inspect
import io
import keyword
import re
import sys
import tokenize
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
SNIPPET_PATH = SITE_ROOT / "snippets" / "basic_usage.py"
HTML_PATH = SITE_ROOT / "index.html"
TARGET_RE = re.compile(r'(<pre id="usage-code"><code class="language-python">)(.*?)(</code></pre>)', re.S)

BRACKET_COLORS = 3
OPEN_BRACKETS = "([{"
CLOSE_BRACKETS = ")]}"
STRING_TYPES = {tokenize.STRING} | {
    getattr(tokenize, name) for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END") if hasattr(tokenize, name)
}
SKIPPED_TYPES = {tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
UNKNOWN = object()


def collect_names(source: str) -> tuple[dict[str, object], set[str]]:
    """Return the objects bound by import statements and the names assigned in the snippet."""
    imported: dict[str, object] = {}
    assigned: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = importlib.import_module(alias.name)
                if alias.asname:
                    imported[alias.asname] = module
                else:
                    root = alias.name.split(".")[0]
                    imported[root] = importlib.import_module(root)
        elif isinstance(node, ast.ImportFrom):
            module = importlib.import_module(node.module)
            for alias in node.names:
                imported[alias.asname or alias.name] = getattr(module, alias.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            assigned.add(node.id)
    return imported, assigned


def classify_object(obj: object) -> str | None:
    if inspect.ismodule(obj) or inspect.isclass(obj):
        return "type"
    if isinstance(obj, enum.Enum):
        return "constant"
    if isinstance(obj, property):
        return None
    if callable(obj):
        return "function"
    return "constant"


def classify_unknown(name: str, next_token: tokenize.TokenInfo | None) -> str | None:
    if next_token is not None and next_token.string == "(":
        return "function"
    if name.isupper():
        return "constant"
    return None


def classify_tokens(tokens: list[tokenize.TokenInfo], imported: dict[str, object], assigned: set[str]) -> list[str | None]:
    """Return the highlighting class of each token, or ``None`` for plain text."""
    classes: list[str | None] = [None] * len(tokens)
    resolved: dict[int, object] = {}
    significant = [i for i, tok in enumerate(tokens) if tok.type not in SKIPPED_TYPES]
    depth = 0

    for i, tok in enumerate(tokens):
        if tok.type == tokenize.COMMENT:
            classes[i] = "comment"

    for k, i in enumerate(significant):
        tok = tokens[i]
        prev = tokens[significant[k - 1]] if k > 0 else None
        prev2 = tokens[significant[k - 2]] if k > 1 else None
        next_token = tokens[significant[k + 1]] if k + 1 < len(significant) else None

        if tok.type in STRING_TYPES:
            classes[i] = "string"
        elif tok.type == tokenize.NUMBER:
            classes[i] = "number"
        elif tok.type == tokenize.OP and tok.string in OPEN_BRACKETS:
            classes[i] = f"bracket-{depth % BRACKET_COLORS}"
            depth += 1
        elif tok.type == tokenize.OP and tok.string in CLOSE_BRACKETS:
            depth = max(depth - 1, 0)
            classes[i] = f"bracket-{depth % BRACKET_COLORS}"
        elif tok.type == tokenize.NAME:
            name = tok.string
            if keyword.iskeyword(name):
                classes[i] = "keyword"
                continue
            if prev is not None and prev.string == "def":
                classes[i] = "function"
                continue
            if prev is not None and prev.string == "class":
                classes[i] = "type"
                continue
            if depth > 0 and next_token is not None and next_token.string == "=":
                continue  # Keyword argument name

            if prev is not None and prev.string == ".":
                base = resolved.get(significant[k - 2], UNKNOWN) if prev2 is not None else UNKNOWN
                obj = UNKNOWN if base is UNKNOWN else getattr(base, name, UNKNOWN)
            elif name in assigned:
                obj = UNKNOWN
            else:
                obj = imported.get(name, getattr(builtins, name, UNKNOWN))

            resolved[i] = obj
            classes[i] = classify_unknown(name, next_token) if obj is UNKNOWN else classify_object(obj)

    return classes


def render(source: str) -> str:
    """Return the snippet as HTML with each highlighted token wrapped in a ``tok-*`` span."""
    imported, assigned = collect_names(source)
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    classes = classify_tokens(tokens, imported, assigned)

    line_offsets = [0]
    for line in source.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(line))

    def offset(position: tuple[int, int]) -> int:
        row, col = position
        return line_offsets[row - 1] + col

    parts: list[str] = []
    cursor = 0
    for tok, css_class in zip(tokens, classes):
        start, end = offset(tok.start), offset(tok.end)
        if start < cursor:
            continue
        parts.append(html.escape(source[cursor:start], quote=False))
        text = html.escape(source[start:end], quote=False)
        parts.append(f'<span class="tok-{css_class}">{text}</span>' if css_class and text else text)
        cursor = end
    parts.append(html.escape(source[cursor:], quote=False))
    return "".join(parts).rstrip("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Only check that index.html is up to date.")
    args = parser.parse_args()

    page = HTML_PATH.read_text()
    if TARGET_RE.search(page) is None:
        print(f"Could not find the usage code block in {HTML_PATH}", file=sys.stderr)
        return 1

    rendered = render(SNIPPET_PATH.read_text())
    updated = TARGET_RE.sub(lambda m: m.group(1) + rendered + m.group(3), page, count=1)

    if args.check:
        if updated != page:
            print(f"{HTML_PATH.name} is out of date; re-run {Path(__file__).name}", file=sys.stderr)
            return 1
        return 0

    HTML_PATH.write_text(updated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
