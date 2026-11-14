#!/usr/bin/env python3
"""Merge the local cc-agent-brain MCP server into client config files.

Claude Code, Cursor, and Codex each get one stdio server that runs the
project's installed ``brain_store.py serve-mcp``. Only that server entry is
inserted or replaced. Other servers, and the rest of each file, stay.

Shapes follow the client docs (see docs/mcp.md):

- Claude Code ``.mcp.json``: command + args, no ``type`` and no ``url``.
  A missing type means stdio. A url without a type is a configuration error.
- Cursor ``.cursor/mcp.json``: ``type`` ``stdio`` plus command and args.
  The script path uses ``${workspaceFolder}``.
- Codex ``.codex/config.toml``: a ``[mcp_servers.cc-agent-brain]`` table.
  This is the project layer. It overlays ``~/.codex/config.toml`` and does
  not replace the user's other MCP servers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

SERVER_NAME = "cc-agent-brain"
OUR_CODEX_TABLE = "mcp_servers.cc-agent-brain"

_HEADER_RE = re.compile(r"^\s*\[([^\[\]]+)\]\s*(?:#.*)?$")
_ASSIGN_RE = re.compile(r"""^\s*(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9_-]+))\s*=""")


def claude_server_entry(python_command: str, brain_store: Path) -> Dict[str, object]:
    """Stdio entry for a project-root ``.mcp.json``."""
    return {
        "command": python_command,
        "args": [str(brain_store), "serve-mcp"],
    }


def cursor_server_entry(python_command: str) -> Dict[str, object]:
    """Stdio entry for ``.cursor/mcp.json``.

    Cursor's STDIO reference requires ``type``. ``${workspaceFolder}`` is the
    project root that contains ``.cursor/mcp.json``.
    """
    return {
        "type": "stdio",
        "command": python_command,
        "args": [
            "${workspaceFolder}/.claude/hooks/cc-agent-brain/brain_store.py",
            "serve-mcp",
        ],
    }


def write_mcp_configs(target: Path, python_command: str, dry_run: bool) -> Dict[str, Dict[str, str]]:
    """Create or merge all three client configs under ``target``."""
    brain_store = (target / ".claude" / "hooks" / "cc-agent-brain" / "brain_store.py").resolve()
    project = target.resolve()
    return {
        "claude": apply_mcp_json(
            project / ".mcp.json",
            claude_server_entry(python_command, brain_store),
            dry_run,
        ),
        "cursor": apply_mcp_json(
            project / ".cursor" / "mcp.json",
            cursor_server_entry(python_command),
            dry_run,
        ),
        "codex": apply_codex_config(
            project / ".codex" / "config.toml",
            python_command,
            str(brain_store),
            str(project),
            dry_run,
        ),
    }


def apply_mcp_json(path: Path, entry: Dict[str, object], dry_run: bool) -> Dict[str, str]:
    """Merge ``mcpServers.cc-agent-brain``. Leave a file alone when it is not an object."""
    result = {"path": str(path), "status": "created"}
    if path.exists():
        try:
            data = _load_json_config(path.read_text(encoding="utf-8-sig"))
        except ValueError:
            result["status"] = "invalid"
            return result
        servers = data.get("mcpServers")
        if servers is None:
            status = "updated"
        elif not isinstance(servers, dict):
            result["status"] = "invalid"
            return result
        else:
            status = "unchanged" if servers.get(SERVER_NAME) == entry else "updated"
        result["status"] = status
    if dry_run:
        result["status"] = "dry-run"
        return result
    if result["status"] == "unchanged":
        return result
    if path.exists():
        data = _load_json_config(path.read_text(encoding="utf-8-sig"))
    else:
        data = {}
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
        data["mcpServers"] = servers
    servers[SERVER_NAME] = entry
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def apply_codex_config(
    path: Path,
    python_command: str,
    brain_store: str,
    project: str,
    dry_run: bool,
) -> Dict[str, str]:
    """Insert or update ``[mcp_servers.cc-agent-brain]`` and keep every other table."""
    result = {"path": str(path), "status": "created"}
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing is not None and existing.strip() and not _toml_parses(existing):
        result["status"] = "invalid"
        return result
    merged = merge_codex_toml(existing or "", python_command, brain_store, project)
    if not _toml_parses(merged):
        result["status"] = "invalid"
        return result
    if existing is None:
        result["status"] = "created"
    elif existing == merged:
        result["status"] = "unchanged"
    else:
        result["status"] = "updated"
    if dry_run:
        result["status"] = "dry-run"
        return result
    if result["status"] != "unchanged":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(merged, encoding="utf-8")
    return result


def merge_codex_toml(text: str, python_command: str, brain_store: str, project: str) -> str:
    """Return ``text`` with this server's table appended or updated in place."""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    desired = {
        "command": toml_basic_string(python_command),
        "args": toml_string_array([brain_store, "serve-mcp"]),
        "cwd": toml_basic_string(project),
    }
    active = _outside_multiline(lines)
    sections = _find_sections(lines, active)
    by_header = {section[0]: section for section in sections}
    output: List[str] = []
    found = False
    index = 0
    while index < len(lines):
        section = by_header.get(index)
        if section is None:
            output.append(lines[index])
            index += 1
            continue
        header_at, next_at, name = section
        output.append(lines[header_at])
        body = lines[header_at + 1 : next_at]
        body_active = active[header_at + 1 : next_at]
        if name == OUR_CODEX_TABLE:
            found = True
            output.extend(_rewrite_section(body, body_active, replace=desired, drop_keys=set()))
        elif name == "mcp_servers":
            output.extend(_rewrite_section(body, body_active, replace={}, drop_keys={SERVER_NAME}))
        else:
            output.extend(body)
        index = next_at
    if not found:
        if output and output[-1].strip() != "":
            output.append("")
        output.extend(
            [
                "[mcp_servers.cc-agent-brain]",
                f"command = {desired['command']}",
                f"args = {desired['args']}",
                f"cwd = {desired['cwd']}",
            ]
        )
    rendered = newline.join(output)
    if rendered and not rendered.endswith(("\n", "\r\n")):
        rendered += newline
    if not rendered:
        rendered = newline
    return rendered


def toml_basic_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def toml_string_array(items: Sequence[str]) -> str:
    return "[" + ", ".join(toml_basic_string(item) for item in items) + "]"


def _load_json_config(text: str) -> Dict[str, object]:
    if not text.strip():
        return {}
    try:
        data = json.loads(_strip_json_comments(text))
    except json.JSONDecodeError as exc:
        raise ValueError("mcp config is not JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("mcp config is not a JSON object")
    return data


def _strip_json_comments(text: str) -> str:
    """Remove ``//`` and ``/* */`` comments that sit outside JSON strings."""
    out: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            out.append(ch)
            i += 1
            while i < n:
                out.append(text[i])
                if text[i] == "\\":
                    i += 1
                    if i < n:
                        out.append(text[i])
                    i += 1
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            i += 2
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i = min(n, i + 2)
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _toml_parses(text: str) -> bool:
    if not text.strip():
        return True
    try:
        import tomllib
    except ModuleNotFoundError:
        return True
    try:
        tomllib.loads(text)
    except Exception:
        return False
    return True


def _outside_multiline(lines: Sequence[str]) -> List[bool]:
    state: Optional[str] = None
    flags: List[bool] = []
    for line in lines:
        flags.append(state is None)
        state = _scan_multiline(line, state)
    return flags


def _scan_multiline(line: str, state: Optional[str]) -> Optional[str]:
    i = 0
    if state:
        found = line.find(state)
        if found < 0:
            return state
        i = found + len(state)
        state = None
    while i < len(line):
        if line.startswith('"""', i) or line.startswith("'''", i):
            quote = line[i : i + 3]
            found = line.find(quote, i + 3)
            if found < 0:
                return quote
            i = found + 3
            continue
        if line[i] in "\"'":
            nxt = _consume_basic_string(line, i, line[i])
            if nxt > len(line):
                return None
            i = nxt
            continue
        i += 1
    return None


def _find_sections(lines: Sequence[str], active: Sequence[bool]) -> List[tuple]:
    headers: List[int] = []
    for index, line in enumerate(lines):
        if active[index] and _header_name(line) is not None:
            headers.append(index)
    sections = []
    for position, header_at in enumerate(headers):
        next_at = headers[position + 1] if position + 1 < len(headers) else len(lines)
        sections.append((header_at, next_at, _header_name(lines[header_at])))
    return sections


def _header_name(line: str) -> Optional[str]:
    if line.lstrip().startswith("[["):
        return None
    match = _HEADER_RE.match(line)
    if not match:
        return None
    return _normalize_table(match.group(1))


def _normalize_table(body: str) -> str:
    parts: List[str] = []
    i = 0
    text = body.strip()
    while i < len(text):
        while i < len(text) and text[i] in " \t":
            i += 1
        if i >= len(text):
            break
        if text[i] in "\"'":
            quote = text[i]
            end = text.find(quote, i + 1)
            if end < 0:
                parts.append(text[i:])
                break
            parts.append(text[i + 1 : end])
            i = end + 1
        else:
            end = i
            while end < len(text) and text[end] not in ". \t":
                end += 1
            parts.append(text[i:end])
            i = end
        while i < len(text) and text[i] in " \t":
            i += 1
        if i < len(text) and text[i] == ".":
            i += 1
            continue
        break
    return ".".join(parts)


def _rewrite_section(
    body: Sequence[str],
    active: Sequence[bool],
    replace: Dict[str, str],
    drop_keys: Set[str],
) -> List[str]:
    output: List[str] = []
    seen: Set[str] = set()
    index = 0
    while index < len(body):
        key = _assignment_key(body[index]) if active[index] else None
        if key is None:
            output.append(body[index])
            index += 1
            continue
        span_end = _assignment_span_end(body, index)
        chunk = list(body[index:span_end])
        if key in drop_keys:
            index = span_end
            continue
        if key in replace:
            if key not in seen:
                seen.add(key)
                if _value_text(chunk) == replace[key]:
                    output.extend(chunk)
                else:
                    output.append(f"{key} = {replace[key]}")
            index = span_end
            continue
        output.extend(chunk)
        index = span_end
    trailing: List[str] = []
    while output and output[-1].strip() == "":
        trailing.append(output.pop())
    for key in ("command", "args", "cwd"):
        if key in replace and key not in seen:
            output.append(f"{key} = {replace[key]}")
    output.extend(reversed(trailing))
    return output


def _assignment_key(line: str) -> Optional[str]:
    match = _ASSIGN_RE.match(line)
    if not match:
        return None
    return match.group(1) or match.group(2) or match.group(3)


def _assignment_span_end(body: Sequence[str], start: int) -> int:
    joined = body[start]
    end_line = start + 1
    while not _assignment_closed(joined):
        if end_line >= len(body):
            return len(body)
        joined += "\n" + body[end_line]
        end_line += 1
    return end_line


def _assignment_closed(text: str) -> bool:
    eq = text.find("=")
    if eq < 0:
        return True
    return _consume_value(text, eq + 1) <= len(text)


def _value_text(chunk: Sequence[str]) -> str:
    text = "\n".join(chunk)
    eq = text.find("=")
    if eq < 0:
        return ""
    end = _consume_value(text, eq + 1)
    if end > len(text):
        end = len(text)
    return text[eq + 1 : end].strip()


def _consume_value(text: str, i: int) -> int:
    n = len(text)
    while i < n and text[i] in " \t\r\n":
        i += 1
    if i >= n:
        return n + 1
    if text.startswith('"""', i) or text.startswith("'''", i):
        quote = text[i : i + 3]
        found = text.find(quote, i + 3)
        return n + 1 if found < 0 else found + 3
    if text[i] == '"':
        return _consume_basic_string(text, i, '"')
    if text[i] == "'":
        return _consume_basic_string(text, i, "'")
    if text[i] in "[{":
        return _consume_container(text, i)
    while i < n and text[i] not in "\n#":
        i += 1
    return i


def _consume_basic_string(text: str, i: int, quote: str) -> int:
    n = len(text)
    i += 1
    while i < n:
        if quote == '"' and text[i] == "\\":
            i += 2
            continue
        if text[i] == quote:
            return i + 1
        if text[i] == "\n":
            return n + 1
        i += 1
    return n + 1


def _consume_container(text: str, i: int) -> int:
    n = len(text)
    pairs = {"[": "]", "{": "}"}
    stack: List[str] = []
    while i < n:
        if text.startswith('"""', i) or text.startswith("'''", i):
            quote = text[i : i + 3]
            found = text.find(quote, i + 3)
            if found < 0:
                return n + 1
            i = found + 3
            continue
        ch = text[i]
        if ch == '"':
            nxt = _consume_basic_string(text, i, '"')
            if nxt > n:
                return n + 1
            i = nxt
            continue
        if ch == "'":
            nxt = _consume_basic_string(text, i, "'")
            if nxt > n:
                return n + 1
            i = nxt
            continue
        if ch in pairs:
            stack.append(pairs[ch])
            i += 1
            continue
        if ch in "]}":
            if not stack or stack[-1] != ch:
                return n + 1
            stack.pop()
            i += 1
            if not stack:
                return i
            continue
        if ch == "#" and stack:
            nl = text.find("\n", i)
            if nl < 0:
                return n + 1
            i = nl + 1
            continue
        i += 1
    return n + 1
