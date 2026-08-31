"""Small, dependency-free reader for the Claude frontmatter fields ctxfire models."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

_KEY = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$")


@dataclass(frozen=True)
class Frontmatter:
    """Parsed top-level scalars/lists plus the Markdown body."""

    fields: dict[str, str | tuple[str, ...]]
    body: str
    present: bool
    warning: str | None = None

    def scalar(self, key: str) -> str | None:
        value = self.fields.get(key)
        return value if isinstance(value, str) else None

    def items(self, key: str) -> tuple[str, ...] | None:
        value = self.fields.get(key)
        if value is None:
            return None
        return value if isinstance(value, tuple) else (value,)


def _unquote(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] == '"':
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return stripped[1:-1]
        return parsed if isinstance(parsed, str) else stripped
    if len(stripped) >= 2 and stripped[0] == stripped[-1] == "'":
        return stripped[1:-1].replace("''", "'")
    return stripped


def _strip_plain_comment(value: str) -> str:
    """Strip a YAML-style trailing comment without touching quoted hashes."""

    single_quoted = False
    double_quoted = False
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if character == "\\" and double_quoted:
            escaped = True
            continue
        if character == "'" and not double_quoted:
            single_quoted = not single_quoted
            continue
        if character == '"' and not single_quoted:
            double_quoted = not double_quoted
            continue
        if (
            character == "#"
            and not single_quoted
            and not double_quoted
            and (index == 0 or value[index - 1].isspace())
        ):
            return value[:index].rstrip()
    return value.strip()


def _inline_list(value: str) -> tuple[str, ...] | None:
    stripped = value.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return None
    reader = csv.reader(io.StringIO(stripped[1:-1]), skipinitialspace=True)
    try:
        row = next(reader)
    except (csv.Error, StopIteration):
        return ()
    return tuple(_unquote(item) for item in row if item.strip())


def parse_frontmatter_bytes(content: bytes) -> Frontmatter:
    """Parse the small top-level YAML subset used by Claude rules/agents/skills.

    Unknown fields and nested mappings are ignored. The supported field shapes
    are scalar values, inline arrays, indented dash arrays, and literal/folded
    scalar blocks. This intentionally avoids adding a YAML runtime dependency.
    """

    text = content.decode("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return Frontmatter({}, text, False)
    closing = next(
        (index for index, line in enumerate(lines[1:], 1) if line.strip() in {"---", "..."}),
        None,
    )
    if closing is None:
        return Frontmatter({}, text, True, "opening frontmatter delimiter has no closing delimiter")

    header = [line.rstrip("\r\n") for line in lines[1:closing]]
    fields: dict[str, str | tuple[str, ...]] = {}
    index = 0
    while index < len(header):
        line = header[index]
        if not line.strip() or line.lstrip().startswith("#") or line[:1].isspace():
            index += 1
            continue
        match = _KEY.fullmatch(line)
        if match is None:
            index += 1
            continue
        key, raw = match.group(1), _strip_plain_comment(match.group(2) or "")
        inline = _inline_list(raw)
        if inline is not None:
            fields[key] = inline
            index += 1
            continue
        if raw in {"|", ">", "|-", ">-", "|+", ">+"}:
            block: list[str] = []
            index += 1
            while index < len(header) and (not header[index] or header[index][:1].isspace()):
                block.append(header[index].lstrip())
                index += 1
            separator = " " if raw.startswith(">") else "\n"
            fields[key] = separator.join(block).strip()
            continue
        if raw:
            fields[key] = _unquote(raw)
            index += 1
            continue
        items: list[str] = []
        index += 1
        while index < len(header) and (not header[index] or header[index][:1].isspace()):
            item = header[index].strip()
            if item.startswith("-"):
                value = _strip_plain_comment(item[1:].strip())
                if value:
                    items.append(_unquote(value))
            index += 1
        fields[key] = tuple(items)

    return Frontmatter(fields, "".join(lines[closing + 1 :]), True)


def read_frontmatter(path: Path) -> Frontmatter:
    return parse_frontmatter_bytes(path.read_bytes())


def yaml_boolean(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.casefold()
    if normalized in {"true", "yes", "on", "1"}:
        return True
    if normalized in {"false", "no", "off", "0"}:
        return False
    return default


def first_markdown_paragraph(body: str) -> str:
    paragraphs = re.split(r"\n\s*\n", body.strip())
    for paragraph in paragraphs:
        flattened = " ".join(line.strip() for line in paragraph.splitlines()).strip()
        if flattened:
            return flattened
    return ""
