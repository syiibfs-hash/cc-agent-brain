#!/usr/bin/env python3
"""CC Agent Brain — local memory engine (zero third-party dependencies).

Storage:
  events    append-only episodic stream (user / assistant / tool / system)
  memories  versioned long-term memory with bi-temporal validity and status

Retrieval:
  SQLite FTS5 (BM25) over events and memories. Search reads the database it
  opened, and also fuses the global library when that file exists and is a
  different file. A pure RRF fusion helper is provided so an optional vector
  channel can be plugged in later without changing call sites.

Shared library (one machine, many MCP clients):
  ~/.cc-agent-brain/brain.db and ~/.cc-agent-brain/library.md, unless
  CC_AGENT_BRAIN_GLOBAL_DIR or --global-dir names another directory.
  Project .cc-agent-brain/brain.db stays the project store. Writes store a
  caller-supplied writer (else CC_AGENT_BRAIN_WRITER, else "unspecified").
  library.md is rebuilt from active memories and from event counts. Event
  text is not copied into that file.

Also exposes a minimal, dependency-free MCP (JSON-RPC over stdio) server:
  python brain_store.py serve-mcp

The server is dual-era. A legacy client opens with initialize (protocol
2024-11-05). A request whose params._meta carries both
io.modelcontextprotocol/protocolVersion and
io.modelcontextprotocol/clientCapabilities is served statelessly as
2026-07-28 (server/discover, resultType). The memory engine underneath
is unchanged.

CLI commands emit JSON by default so hooks and skills can consume them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCHEMA_VERSION = "2"
# Software version advertised in modern serverInfo. Distinct from the DB schema.
PRODUCT_VERSION = "0.2.0"
MCP_SERVER_NAME = "cc-agent-brain"
MCP_LEGACY_PROTOCOL_VERSION = "2024-11-05"
MCP_MODERN_PROTOCOL_VERSION = "2026-07-28"
# Newest first. Legacy 2024-11-05 is reached via initialize, not via _meta.
MCP_SUPPORTED_PROTOCOL_VERSIONS = (
    MCP_MODERN_PROTOCOL_VERSION,
    MCP_LEGACY_PROTOCOL_VERSION,
)
_MCP_PROTOCOL_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
_MCP_CLIENT_CAPABILITIES_KEY = "io.modelcontextprotocol/clientCapabilities"
_MCP_SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"
_MCP_UNSUPPORTED_PROTOCOL_VERSION = -32022
# Freshness hint for the static tool catalog and discovery document.
_MCP_TTL_MS = 3_600_000
_MCP_CACHE_SCOPE = "public"
MEMORY_LAYERS = ("working", "episodic", "semantic", "procedural")
MEMORY_STATUSES = ("active", "superseded", "expired", "archived")
CONFIDENCE_LEVELS = ("high", "medium", "low")
EVENT_KINDS = ("user", "assistant", "tool", "system")
# Directory of the shared on-disk library. The project DB is not this path.
GLOBAL_DIR_ENV = "CC_AGENT_BRAIN_GLOBAL_DIR"
# Identity recorded on a write when the caller does not pass one.
WRITER_ENV = "CC_AGENT_BRAIN_WRITER"
DEFAULT_WRITER = "unspecified"
GLOBAL_DB_NAME = "brain.db"
GLOBAL_MARKDOWN_NAME = "library.md"
# Set by --global-dir for this process. Environment is the cross-process knob.
_global_dir_override: Optional[Path] = None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def set_global_library_dir(path: Optional[str]) -> None:
    """Select the shared library directory for this process.

    ``None`` clears the flag override. The environment variable still applies.
    """
    global _global_dir_override
    if path and str(path).strip():
        _global_dir_override = Path(str(path).strip()).expanduser().resolve()
    else:
        _global_dir_override = None


def global_library_dir() -> Path:
    """Directory that holds the shared SQLite file and library.md.

    Precedence: ``--global-dir``, then ``CC_AGENT_BRAIN_GLOBAL_DIR``, then
    ``~/.cc-agent-brain``. The default stays next to the historical global DB
    so existing ``--global`` files and search fusion keep one location.
    """
    if _global_dir_override is not None:
        return _global_dir_override
    raw = os.environ.get(GLOBAL_DIR_ENV, "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".cc-agent-brain").resolve()


def project_db_path() -> Path:
    return Path.cwd() / ".cc-agent-brain" / "brain.db"


def global_db_path() -> Path:
    return global_library_dir() / GLOBAL_DB_NAME


def global_markdown_path() -> Path:
    return global_library_dir() / GLOBAL_MARKDOWN_NAME


def resolve_db_path(global_db: bool = False, explicit: Optional[str] = None) -> Path:
    """Pick the SQLite file for this command.

    An explicit ``--db`` wins, including over ``--global``. ``--global`` opens
    the shared library. Otherwise the project file under the working directory
    is used.
    """
    if explicit:
        return Path(explicit).expanduser().resolve()
    if global_db:
        return global_db_path()
    return project_db_path()


def same_file(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def resolve_writer(explicit: Optional[str] = None) -> str:
    """Writer recorded on a row.

    An explicit caller value wins, then ``CC_AGENT_BRAIN_WRITER``, then
    ``unspecified``. Nothing here inspects which product launched the process.
    """
    chosen = ""
    if explicit is not None and str(explicit).strip():
        chosen = str(explicit).strip()
    else:
        chosen = os.environ.get(WRITER_ENV, "").strip()
    if not chosen:
        chosen = DEFAULT_WRITER
    return " ".join(chosen.split())


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Secret redaction (privacy left-shift: redact at capture time)
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: Sequence[Tuple[str, re.Pattern]] = [
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}\b")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("aws-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("google-api", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}\b")),
    ("bearer", re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._\-]{16,}")),
    ("pem", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")),
    ("kv-secret", re.compile(r"(?i)\b((?:password|passwd|pwd|token|secret|api[_-]?key|access[_-]?key)\s*[=:]\s*)\S{6,}")),
]


def redact(text: str) -> str:
    """Replace common credential shapes with [REDACTED:kind]. Best-effort."""
    if not text:
        return text
    out = text
    for kind, pattern in _SECRET_PATTERNS:
        if kind in ("bearer", "kv-secret"):
            out = pattern.sub(lambda m, k=kind: m.group(1) + f"[REDACTED:{k}]", out)
        else:
            out = pattern.sub(f"[REDACTED:{kind}]", out)
    return out


# ---------------------------------------------------------------------------
# FTS tokenization. unicode61 has no CJK tokenizer: a run of Han characters is
# stored as one opaque token, which makes per-character search miss. We therefore
# index AND query through the same CJK-bigram + latin-word tokenizer so both
# sides align; BM25 then ranks documents hitting more bigrams higher.
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*|[\u4e00-\u9fff]+")
_HAN = re.compile(r"[\u4e00-\u9fff]")


def _cjk_bigrams(run: str) -> List[str]:
    if len(run) == 1:
        return [run]
    return [run[i : i + 2] for i in range(len(run) - 1)]


def fts_tokens(text: str) -> List[str]:
    tokens: List[str] = []
    for match in _TOKEN_RE.finditer(text or ""):
        piece = match.group(0)
        if _HAN.match(piece):
            tokens.extend(_cjk_bigrams(piece))
        elif len(piece) >= 2:
            tokens.append(piece.lower())
    return tokens


def fts_index_text(text: str) -> str:
    """Normalized text written into FTS virtual tables."""
    return " ".join(fts_tokens(text or ""))


def build_fts_match(query: str) -> str:
    """Turn free text into a safe FTS5 MATCH expression (OR of quoted tokens)."""
    seen = set()
    quoted = []
    for token in fts_tokens(query):
        item = '"' + token.replace('"', '""') + '"'
        if item not in seen:
            seen.add(item)
            quoted.append(item)
    return " OR ".join(quoted)


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion (pure function; vector channel can be added later)
# ---------------------------------------------------------------------------


def rrf_fuse(ranked_lists: Sequence[Sequence[Dict[str, Any]]], k: int = 60, top_n: int = 10, id_key: str = "_rid") -> List[Dict[str, Any]]:
    scores: Dict[str, float] = {}
    picked: Dict[str, Dict[str, Any]] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            rid = str(item.get(id_key))
            scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
            picked.setdefault(rid, item)
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    result = []
    for rid, score in ordered[:top_n]:
        item = dict(picked[rid])
        item["rrf_score"] = round(score, 5)
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class BrainStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    def _migrate(self) -> None:
        c = self.conn
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts TEXT NOT NULL,
              kind TEXT NOT NULL,
              content TEXT NOT NULL,
              tags TEXT DEFAULT '[]',
              source TEXT DEFAULT '',
              dedup_hash TEXT UNIQUE,
              created_at TEXT NOT NULL,
              writer TEXT NOT NULL DEFAULT ''
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(content, tags, kind);
            CREATE TABLE IF NOT EXISTS memories(
              seq INTEGER PRIMARY KEY AUTOINCREMENT,
              id TEXT UNIQUE NOT NULL,
              layer TEXT NOT NULL,
              scope TEXT NOT NULL DEFAULT 'project',
              title TEXT NOT NULL,
              body TEXT NOT NULL,
              tags TEXT DEFAULT '[]',
              confidence TEXT DEFAULT 'medium',
              status TEXT NOT NULL DEFAULT 'active',
              valid_from TEXT NOT NULL,
              valid_to TEXT,
              source TEXT DEFAULT '',
              supersedes TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              writer TEXT NOT NULL DEFAULT ''
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(title, body, tags);
            CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status, layer);
            CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
            """
        )
        c.execute("INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)", (SCHEMA_VERSION,))
        # Additive column. SCHEMA_VERSION stays "2" because legacy initialize
        # advertises that id in serverInfo.version. Existing rows keep ''.
        self._ensure_column("events", "writer", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("memories", "writer", "TEXT NOT NULL DEFAULT ''")
        c.commit()

    def _ensure_column(self, table: str, name: str, declaration: str) -> None:
        rows = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        have = {row["name"] for row in rows}
        if name not in have:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")

    # ----- events ----------------------------------------------------------

    @staticmethod
    def _dedup_hash(kind: str, content: str, ts: str) -> str:
        return hashlib.sha1(f"{kind}|{ts}|{content}".encode("utf-8")).hexdigest()[:16]

    def add_event(
        self,
        kind: str,
        content: str,
        tags: Optional[Sequence[str]] = None,
        source: str = "",
        redact_secrets: bool = True,
        writer: Optional[str] = None,
    ) -> int:
        if kind not in EVENT_KINDS:
            raise ValueError(f"unknown event kind: {kind}")
        if redact_secrets:
            content = redact(content)
        content = content.strip()
        if not content:
            return -1
        ts = now_iso()
        tags_json = json.dumps(list(tags or []), ensure_ascii=False)
        dedup = self._dedup_hash(kind, content, ts)
        who = resolve_writer(writer)
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO events(ts, kind, content, tags, source, dedup_hash, created_at, writer) VALUES(?,?,?,?,?,?,?,?)",
            (ts, kind, content, tags_json, source, dedup, ts, who),
        )
        if cur.lastrowid:
            self.conn.execute(
                "INSERT INTO events_fts(rowid, content, tags, kind) VALUES(?,?,?,?)",
                (cur.lastrowid, fts_index_text(content), fts_index_text(" ".join(tags or [])), kind),
            )
            self.conn.commit()
            self.maintain_shared_markdown()
            return int(cur.lastrowid)
        return -1

    # ----- memories --------------------------------------------------------

    @staticmethod
    def new_memory_id(title: str, body: str) -> str:
        return "m-" + hashlib.sha1(f"{title}|{body}|{now_iso()}".encode("utf-8")).hexdigest()[:10]

    def add_memory(
        self,
        title: str,
        body: str,
        layer: str = "semantic",
        confidence: str = "medium",
        tags: Optional[Sequence[str]] = None,
        source: str = "",
        scope: str = "project",
        supersedes: Optional[str] = None,
        redact_secrets: bool = True,
        writer: Optional[str] = None,
    ) -> Dict[str, Any]:
        if layer not in MEMORY_LAYERS:
            raise ValueError(f"layer must be one of {MEMORY_LAYERS}")
        if confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"confidence must be one of {CONFIDENCE_LEVELS}")
        if redact_secrets:
            title, body = redact(title), redact(body)
        mid = self.new_memory_id(title, body)
        ts = now_iso()
        tags_json = json.dumps(list(tags or []), ensure_ascii=False)
        who = resolve_writer(writer)
        cur = self.conn.execute(
            """INSERT INTO memories(id, layer, scope, title, body, tags, confidence, status,
               valid_from, valid_to, source, supersedes, created_at, updated_at, writer)
               VALUES(?,?,?,?,?,?,?, 'active', ?, NULL, ?, ?, ?, ?, ?)""",
            (mid, layer, scope, title, body, tags_json, confidence, ts, source, supersedes, ts, ts, who),
        )
        seq = cur.lastrowid
        self.conn.execute(
            "INSERT INTO memories_fts(rowid, title, body, tags) VALUES(?,?,?,?)",
            (seq, fts_index_text(title), fts_index_text(body), fts_index_text(" ".join(tags or []))),
        )
        if supersedes:
            self._set_status(supersedes, "superseded", valid_to=ts)
        self.conn.commit()
        self.maintain_shared_markdown()
        return self.get_memory(mid)

    def _set_status(self, mid: str, status: str, valid_to: Optional[str] = None) -> bool:
        row = self.conn.execute("SELECT seq FROM memories WHERE id=?", (mid,)).fetchone()
        if not row:
            return False
        if valid_to is None and status in ("superseded", "expired", "archived"):
            valid_to = now_iso()
        self.conn.execute(
            "UPDATE memories SET status=?, valid_to=COALESCE(?, valid_to), updated_at=? WHERE id=?",
            (status, valid_to, now_iso(), mid),
        )
        # Non-active memories must leave the active FTS index.
        self.conn.execute("DELETE FROM memories_fts WHERE rowid=?", (row["seq"],))
        self.conn.commit()
        self.maintain_shared_markdown()
        return True

    def expire_memory(self, mid: str) -> bool:
        return self._set_status(mid, "expired")

    def supersede_memory(self, old_id: str, new: Dict[str, Any]) -> Dict[str, Any]:
        new["supersedes"] = old_id
        return self.add_memory(**new)

    def get_memory(self, mid: str) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM memories WHERE id=?", (mid,)).fetchone()
        return dict(row) if row else {}

    def list_memories(self, status: Optional[str] = None, layer: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM memories WHERE 1=1"
        args: List[Any] = []
        if status:
            sql += " AND status=?"
            args.append(status)
        if layer:
            sql += " AND layer=?"
            args.append(layer)
        sql += " ORDER BY updated_at DESC"
        return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    # ----- search ----------------------------------------------------------

    def _search_memories(self, match: str, limit: int, layer: Optional[str]) -> List[Dict[str, Any]]:
        if not match:
            return []
        sql = (
            "SELECT m.*, bm25(memories_fts) AS rank_score "
            "FROM memories_fts f JOIN memories m ON m.seq=f.rowid "
            "WHERE memories_fts MATCH ? AND m.status='active'"
        )
        args: List[Any] = [match]
        if layer:
            sql += " AND m.layer=?"
            args.append(layer)
        sql += " ORDER BY rank_score LIMIT ?"
        args.append(limit)
        rows = [dict(r) for r in self.conn.execute(sql, args).fetchall()]
        for r in rows:
            r["_rid"] = "mem:" + r["id"]
            r["_type"] = "memory"
        return rows

    def _search_events(self, match: str, limit: int) -> List[Dict[str, Any]]:
        if not match:
            return []
        rows = [
            dict(r)
            for r in self.conn.execute(
                "SELECT e.*, bm25(events_fts) AS rank_score FROM events_fts f "
                "JOIN events e ON e.id=f.rowid WHERE events_fts MATCH ? "
                "ORDER BY rank_score LIMIT ?",
                (match, limit),
            ).fetchall()
        ]
        for r in rows:
            r["_rid"] = "evt:" + str(r["id"])
            r["_type"] = "event"
        return rows

    def search(self, query: str, k: int = 8, layer: Optional[str] = None, include_global: bool = True) -> List[Dict[str, Any]]:
        match = build_fts_match(query)
        if not match:
            return []
        mem_hits = self._search_memories(match, k * 2, layer)
        evt_hits = self._search_events(match, k * 2)
        lists = [mem_hits, evt_hits]
        if include_global:
            gpath = global_db_path()
            if gpath.exists() and not same_file(gpath, self.db_path):
                g = BrainStore(gpath)
                try:
                    lists.append(g._search_memories(match, k * 2, layer))
                    lists.append(g._search_events(match, k * 2))
                finally:
                    g.close()
        return rrf_fuse(lists, top_n=k)

    # ----- consolidation candidates ---------------------------------------

    def consolidation_candidates(self, days: int = 3, limit: int = 20) -> List[Dict[str, Any]]:
        since = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        rows = self.conn.execute(
            "SELECT kind, COUNT(*) AS n FROM events WHERE ts >= ? GROUP BY kind ORDER BY n DESC",
            (since,),
        ).fetchall()
        recent = [dict(r) for r in rows]
        samples = [
            dict(r)
            for r in self.conn.execute(
                "SELECT id, ts, kind, substr(content,1,200) AS preview FROM events WHERE ts>=? ORDER BY id DESC LIMIT ?",
                (since, limit),
            ).fetchall()
        ]
        return {"window_days": days, "counts_by_kind": recent, "recent_events": samples}

    # ----- audit -----------------------------------------------------------

    def audit(self) -> Dict[str, Any]:
        issues: List[Dict[str, str]] = []
        # 1. Same layer + title with several active copies (potential conflict).
        for r in self.conn.execute(
            "SELECT layer, title, COUNT(*) n FROM memories WHERE status='active' GROUP BY layer, title HAVING n>1"
        ):
            issues.append({"level": "warn", "code": "duplicate_active", "message": f"{r['layer']}: {r['title']} has {r['n']} active copies"})
        # 2. Broken supersedes chain.
        for r in self.conn.execute(
            "SELECT m.id, m.supersedes FROM memories m LEFT JOIN memories p ON p.id=m.supersedes "
            "WHERE m.supersedes IS NOT NULL AND p.id IS NULL"
        ):
            issues.append({"level": "warn", "code": "broken_supersede_chain", "message": f"{r['id']} points to missing {r['supersedes']}"})
        # 3. Stale active semantic memories (older than 90 days, never updated).
        threshold = (datetime.now() - timedelta(days=90)).isoformat(timespec="seconds")
        for r in self.conn.execute(
            "SELECT id, title FROM memories WHERE status='active' AND layer IN('semantic','working') AND updated_at < ?",
            (threshold,),
        ):
            issues.append({"level": "info", "code": "stale_candidate", "message": f"{r['id']} {r['title']} not updated in 90+ days"})
        # 4. Low-confidence active memories.
        n_low = self.conn.execute("SELECT COUNT(*) c FROM memories WHERE status='active' AND confidence='low'").fetchone()["c"]
        if n_low:
            issues.append({"level": "info", "code": "low_confidence", "message": f"{n_low} active memories have low confidence"})
        # 5. Event backlog not reflected in any memory.
        n_evt = self.conn.execute("SELECT COUNT(*) c FROM events").fetchone()["c"]
        n_mem = self.conn.execute("SELECT COUNT(*) c FROM memories WHERE status='active'").fetchone()["c"]
        if n_evt >= 30 and n_mem == 0:
            issues.append({"level": "warn", "code": "never_distilled", "message": f"{n_evt} events captured but 0 memories — run memory-distill"})
        stats = self.stats()
        return {"issues": issues, "stats": stats}

    # ----- stats / timeline ------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        def group(table: str, col: str) -> Dict[str, int]:
            return {r[col]: r["n"] for r in self.conn.execute(f"SELECT {col}, COUNT(*) n FROM {table} GROUP BY {col}")}

        bounds = self.conn.execute("SELECT MIN(ts) a, MAX(ts) b FROM events").fetchone()
        return {
            "db": str(self.db_path),
            "events_total": self.conn.execute("SELECT COUNT(*) c FROM events").fetchone()["c"],
            "memories_total": self.conn.execute("SELECT COUNT(*) c FROM memories").fetchone()["c"],
            "memories_active": self.conn.execute("SELECT COUNT(*) c FROM memories WHERE status='active'").fetchone()["c"],
            "events_by_kind": group("events", "kind"),
            "memories_by_layer": group("memories", "layer"),
            "memories_by_status": group("memories", "status"),
            "events_by_writer": group("events", "writer"),
            "memories_by_writer": group("memories", "writer"),
            "events_span": {"first": bounds["a"], "last": bounds["b"]},
        }

    def timeline(self, limit: int = 15) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, layer, title, status, confidence, valid_from, valid_to, supersedes, source, writer, updated_at "
            "FROM memories ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ----- markdown projection --------------------------------------------

    def export_markdown(self) -> str:
        lines = [
            "<!-- AUTO-GENERATED by brain_store.py sync-md. Do not edit by hand. -->",
            f"<!-- generated: {now_iso()} -->",
            "# Brain Index (generated)",
            "",
            "Active long-term memories indexed by the local engine.",
            "",
        ]
        for layer in MEMORY_LAYERS:
            rows = self.list_memories(status="active", layer=layer)
            if not rows:
                continue
            lines.append(f"## {layer}")
            lines.append("")
            for r in rows:
                tags = json.loads(r["tags"]) if r["tags"] else []
                tag_text = f" [{', '.join(tags)}]" if tags else ""
                lines.append(f"### {r['title']}{tag_text}")
                lines.append(
                    f"- id: {r['id']} · confidence: {r['confidence']} · from: {r['valid_from']} · "
                    f"source: {r['source'] or 'n/a'} · writer: {r.get('writer') or 'n/a'}"
                )
                lines.append("")
                lines.append(r["body"])
                lines.append("")
        return "\n".join(lines)

    def is_global_library(self) -> bool:
        return same_file(self.db_path, global_db_path())

    def export_library_markdown(self) -> str:
        """Living shared document. Active memories are included. Event text is not."""
        stats = self.stats()
        lines = [
            "<!-- AUTO-GENERATED by brain_store.py from the shared global library. Do not edit by hand. -->",
            f"<!-- generated: {now_iso()} -->",
            "# Shared library",
            "",
            "Maintained from the global memory store on this machine.",
            "Active memories are included. Event text is not copied into this document.",
            "",
            "## Active memories",
            "",
        ]
        any_memory = False
        for layer in MEMORY_LAYERS:
            rows = self.list_memories(status="active", layer=layer)
            if not rows:
                continue
            any_memory = True
            lines.append(f"### {layer}")
            lines.append("")
            for r in rows:
                tags = json.loads(r["tags"]) if r["tags"] else []
                tag_text = f" [{', '.join(tags)}]" if tags else ""
                lines.append(f"#### {r['title']}{tag_text}")
                lines.append(
                    f"- id: {r['id']} · confidence: {r['confidence']} · from: {r['valid_from']} · "
                    f"source: {r['source'] or 'n/a'} · writer: {r.get('writer') or 'n/a'}"
                )
                lines.append("")
                lines.append(r["body"])
                lines.append("")
        if not any_memory:
            lines.append("No active memories.")
            lines.append("")
        lines.append("## Activity")
        lines.append("")
        lines.append("Counts only. Raw event text stays in SQLite.")
        lines.append("")
        lines.append(f"- events: {stats['events_total']}")
        lines.append(f"- events by kind: {_format_counts(stats['events_by_kind'])}")
        lines.append(f"- events by writer: {_format_counts(stats['events_by_writer'])}")
        lines.append(f"- memories: {stats['memories_total']} ({stats['memories_active']} active)")
        lines.append(f"- memories by writer: {_format_counts(stats['memories_by_writer'])}")
        lines.append("")
        return "\n".join(lines)

    def maintain_shared_markdown(self) -> Optional[Path]:
        """Rewrite library.md when this connection is the shared global DB."""
        if not self.is_global_library():
            return None
        target = global_markdown_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.export_library_markdown(), encoding="utf-8")
        return target


def _format_counts(counts: Dict[str, int]) -> str:
    if not counts:
        return "none"
    parts = []
    for key in sorted(counts, key=lambda item: (item is None, str(item))):
        label = key if key else "(none)"
        parts.append(f"{label} {counts[key]}")
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Minimal MCP server (JSON-RPC 2.0 newline-delimited over stdio)
# ---------------------------------------------------------------------------

MCP_TOOLS = [
    {
        "name": "brain_search",
        "description": "Search local CC Agent Brain memories and event stream by keyword (FTS5/BM25).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "default": 8},
                "layer": {"type": "string", "enum": list(MEMORY_LAYERS)},
            },
            "required": ["query"],
        },
    },
    {
        "name": "brain_add_memory",
        "description": "Persist a stable, compressed long-term memory with layer/confidence/tags. writer is the caller-supplied identity stored on the row.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "layer": {"type": "string", "enum": list(MEMORY_LAYERS), "default": "semantic"},
                "confidence": {"type": "string", "enum": list(CONFIDENCE_LEVELS), "default": "medium"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source": {"type": "string"},
                "writer": {"type": "string"},
            },
            "required": ["title", "body"],
        },
    },
    {
        "name": "brain_forget",
        "description": "Mark a memory expired (kept for audit, removed from active retrieval).",
        "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    },
    {
        "name": "brain_timeline",
        "description": "Show recent memory changes including superseded/expired history.",
        "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 15}}},
    },
    {
        "name": "brain_stats",
        "description": "Summarize local brain size, layers and event coverage.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


class _McpEra:
    """Per-stdio-process era. Modern confirmation is sticky.

    A valid modern `_meta` envelope confirms the 2026-07-28 era. After that,
    `initialize` is not served: the spec treats a modern result or
    UnsupportedProtocolVersionError as proof the peer stays modern, and this
    server must not fall back to the legacy handshake.
    """

    def __init__(self) -> None:
        self.modern_confirmed = False


def _mcp_server_info() -> Dict[str, str]:
    return {"name": MCP_SERVER_NAME, "version": PRODUCT_VERSION}


def _modern_result_meta() -> Dict[str, Any]:
    return {_MCP_SERVER_INFO_KEY: _mcp_server_info()}


def _mcp_params(msg: Dict[str, Any]) -> Dict[str, Any]:
    params = msg.get("params")
    if isinstance(params, dict):
        return params
    return {}


def _classify_mcp_meta(meta: Any) -> str:
    """Return 'modern', 'invalid', or 'legacy'.

    Modern requires both envelope keys with the types from the 2026-07-28
    schema (protocolVersion string, clientCapabilities object). A partial
    envelope is legacy traffic: 2024-11-05 clients also use `_meta`, but not
    these keys. Both keys present with the wrong types is an attempted modern
    envelope and is rejected rather than reinterpreted as `initialize`.
    """
    if not isinstance(meta, dict):
        return "legacy"
    has_version = _MCP_PROTOCOL_VERSION_KEY in meta
    has_caps = _MCP_CLIENT_CAPABILITIES_KEY in meta
    if not has_version or not has_caps:
        return "legacy"
    version = meta[_MCP_PROTOCOL_VERSION_KEY]
    caps = meta[_MCP_CLIENT_CAPABILITIES_KEY]
    if isinstance(version, str) and isinstance(caps, dict):
        return "modern"
    return "invalid"


def _jsonrpc_result(mid: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _jsonrpc_error(mid: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    error: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": mid, "error": error}


def _unsupported_protocol_version(mid: Any, requested: str) -> Dict[str, Any]:
    return _jsonrpc_error(
        mid,
        _MCP_UNSUPPORTED_PROTOCOL_VERSION,
        "Unsupported protocol version",
        {
            "supported": list(MCP_SUPPORTED_PROTOCOL_VERSIONS),
            "requested": requested,
        },
    )


def _legacy_initialize_result() -> Dict[str, Any]:
    # Keep the historical serverInfo.version (schema id "2") so existing
    # 2024-11-05 clients see the same initialize payload. Modern `_meta`
    # uses PRODUCT_VERSION instead.
    return {
        "protocolVersion": MCP_LEGACY_PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": MCP_SERVER_NAME, "version": SCHEMA_VERSION},
    }


def _discover_result() -> Dict[str, Any]:
    return {
        "resultType": "complete",
        "supportedVersions": list(MCP_SUPPORTED_PROTOCOL_VERSIONS),
        "capabilities": {"tools": {}},
        "_meta": _modern_result_meta(),
        "instructions": (
            "Local CC Agent Brain memory stored in SQLite. "
            "Use the brain_* tools to search, add, expire, and review memories."
        ),
        "ttlMs": _MCP_TTL_MS,
        "cacheScope": _MCP_CACHE_SCOPE,
    }


def _modern_tools_list() -> Dict[str, Any]:
    # MCP_TOOLS is a fixed literal; that order is the stable tools/list order.
    return {
        "resultType": "complete",
        "tools": MCP_TOOLS,
        "_meta": _modern_result_meta(),
        "ttlMs": _MCP_TTL_MS,
        "cacheScope": _MCP_CACHE_SCOPE,
    }


def _modernize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(result)
    out["resultType"] = "complete"
    meta = dict(out.get("_meta") or {})
    meta.update(_modern_result_meta())
    out["_meta"] = meta
    return out


def dispatch_mcp(store: "BrainStore", msg: Dict[str, Any], era: _McpEra) -> Optional[Dict[str, Any]]:
    """Handle one JSON-RPC message. Notifications return None."""
    if "id" not in msg:
        return None
    mid = msg["id"]
    method = msg.get("method")
    params = _mcp_params(msg)
    meta = params.get("_meta") if params else None
    # params may be {} when the message omitted params; meta then stays absent.
    if "params" in msg and not isinstance(msg.get("params"), dict):
        meta = None
    status = _classify_mcp_meta(meta)

    if status == "invalid":
        return _jsonrpc_error(
            mid,
            -32602,
            "invalid _meta: io.modelcontextprotocol/protocolVersion must be a string "
            "and io.modelcontextprotocol/clientCapabilities must be an object",
        )

    if status == "modern":
        era.modern_confirmed = True
        if not isinstance(meta, dict):
            return _jsonrpc_error(mid, -32602, "invalid _meta envelope")
        requested = meta[_MCP_PROTOCOL_VERSION_KEY]
        if requested != MCP_MODERN_PROTOCOL_VERSION:
            return _unsupported_protocol_version(mid, requested)
        try:
            if method == "server/discover":
                result = _discover_result()
            elif method == "tools/list":
                result = _modern_tools_list()
            elif method == "tools/call":
                result = _modernize_result(_handle_mcp_call(store, params))
            else:
                # initialize and ping were removed in 2026-07-28. Do not answer
                # them with the legacy payloads once this request is modern.
                return _jsonrpc_error(mid, -32601, f"method not found: {method}")
            return _jsonrpc_result(mid, result)
        except Exception as exc:  # never kill the transport on a bad call
            return _jsonrpc_error(mid, -32000, str(exc))

    if method == "initialize":
        if era.modern_confirmed:
            requested = params.get("protocolVersion")
            if not isinstance(requested, str):
                requested = ""
            return _unsupported_protocol_version(mid, requested)
        return _jsonrpc_result(mid, _legacy_initialize_result())

    try:
        if method == "ping":
            result: Dict[str, Any] = {}
        elif method == "tools/list":
            result = {"tools": MCP_TOOLS}
        elif method == "tools/call":
            result = _handle_mcp_call(store, params)
        else:
            return _jsonrpc_error(mid, -32601, f"method not found: {method}")
        return _jsonrpc_result(mid, result)
    except Exception as exc:  # never kill the transport on a bad call
        return _jsonrpc_error(mid, -32000, str(exc))


def serve_mcp(db_path: Path) -> int:
    store = BrainStore(db_path)
    out = sys.stdout
    era = _McpEra()

    def send(obj: Dict[str, Any]) -> None:
        out.write(json.dumps(obj, ensure_ascii=False) + "\n")
        out.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(msg, dict):
            continue
        response = dispatch_mcp(store, msg, era)
        if response is not None:
            send(response)
    store.close()
    return 0


def _handle_mcp_call(store: BrainStore, params: Dict[str, Any]) -> Dict[str, Any]:
    name = params.get("name")
    args = params.get("arguments") or {}

    def text(payload: Any) -> Dict[str, Any]:
        return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}], "isError": False}

    if name == "brain_search":
        payload = store.search(args["query"], k=int(args.get("k", 8)), layer=args.get("layer"))
    elif name == "brain_add_memory":
        payload = store.add_memory(
            title=args["title"],
            body=args["body"],
            layer=args.get("layer", "semantic"),
            confidence=args.get("confidence", "medium"),
            tags=args.get("tags") or [],
            source=args.get("source", "mcp"),
            writer=args.get("writer"),
        )
    elif name == "brain_forget":
        payload = {"id": args["id"], "expired": store.expire_memory(args["id"])}
    elif name == "brain_timeline":
        payload = store.timeline(limit=int(args.get("limit", 15)))
    elif name == "brain_stats":
        payload = store.stats()
    else:
        return {"content": [{"type": "text", "text": f"unknown tool {name}"}], "isError": True}
    return text(payload)


# ---------------------------------------------------------------------------
# Human-readable rendering for hooks
# ---------------------------------------------------------------------------


def render_human(hits: Sequence[Dict[str, Any]]) -> str:
    if not hits:
        return ""
    lines = ["CC Agent Brain recall (local engine):"]
    for i, h in enumerate(hits, 1):
        who = h.get("writer") or ""
        who_bit = f" · writer {who}" if who else ""
        if h.get("_type") == "memory":
            snippet = (h.get("body") or "").strip().replace("\n", " ")
            if len(snippet) > 160:
                snippet = snippet[:160] + "…"
            lines.append(f"{i}. [memory/{h.get('layer')}] {h.get('title')} — {snippet} (id {h.get('id')}{who_bit})")
        else:
            snippet = (h.get("content") or "").strip().replace("\n", " ")
            if len(snippet) > 140:
                snippet = snippet[:140] + "…"
            lines.append(f"{i}. [event/{h.get('kind')} {h.get('ts')}] {snippet}{who_bit}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _read_content(args: argparse.Namespace) -> str:
    if getattr(args, "content", None):
        return args.content
    raw = sys.stdin.read()
    return raw.strip()


def _tags(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [t.strip() for t in re.split(r"[,，]", value) if t.strip()]


def _print(obj: Any) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CC Agent Brain local memory engine")
    p.add_argument("--db", help="Explicit SQLite path (default: ./.cc-agent-brain/brain.db). Wins over --global.")
    p.add_argument("--global", dest="use_global", action="store_true", help="Use the shared global library (brain.db beside library.md)")
    p.add_argument(
        "--global-dir",
        help="Shared library directory for this process (brain.db and library.md). Overrides CC_AGENT_BRAIN_GLOBAL_DIR.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")
    sub.add_parser("stats")

    pe = sub.add_parser("event")
    pe.add_argument("--kind", required=True, choices=EVENT_KINDS)
    pe.add_argument("--content")
    pe.add_argument("--tags")
    pe.add_argument("--source", default="")
    pe.add_argument("--writer", default=None, help="Caller identity. Default: CC_AGENT_BRAIN_WRITER or unspecified")

    pm = sub.add_parser("memory")
    msub = pm.add_subparsers(dest="mem_cmd", required=True)
    ma = msub.add_parser("add")
    ma.add_argument("--title", required=True)
    ma.add_argument("--body", required=True)
    ma.add_argument("--layer", default="semantic", choices=MEMORY_LAYERS)
    ma.add_argument("--confidence", default="medium", choices=CONFIDENCE_LEVELS)
    ma.add_argument("--tags")
    ma.add_argument("--source", default="")
    ma.add_argument("--writer", default=None, help="Caller identity. Default: CC_AGENT_BRAIN_WRITER or unspecified")
    ma.add_argument("--scope", default="project", choices=("project", "global"))
    ma.add_argument("--supersedes")
    msub.add_parser("list")
    me = msub.add_parser("expire")
    me.add_argument("id")

    ps = sub.add_parser("search")
    ps.add_argument("query")
    ps.add_argument("--k", type=int, default=8)
    ps.add_argument("--layer")
    ps.add_argument("--human", action="store_true")

    pc = sub.add_parser("candidates")
    pc.add_argument("--days", type=int, default=3)

    sub.add_parser("audit")
    pt = sub.add_parser("timeline")
    pt.add_argument("--limit", type=int, default=15)
    sub.add_parser("sync-md")
    sub.add_parser("serve-mcp")
    pr = sub.add_parser("redact")
    pr.add_argument("--content")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
    args = build_parser().parse_args(argv)
    set_global_library_dir(getattr(args, "global_dir", None))
    db_path = resolve_db_path(global_db=args.use_global, explicit=args.db)

    if args.cmd == "serve-mcp":
        return serve_mcp(db_path)
    if args.cmd == "redact":
        sys.stdout.write(redact(_read_content(args)))
        return 0

    store = BrainStore(db_path)
    try:
        if args.cmd == "init":
            library_md = store.maintain_shared_markdown()
            _print({"ok": True, "db": str(db_path), "schema": SCHEMA_VERSION, "library_md": str(library_md) if library_md else None})
        elif args.cmd == "stats":
            _print(store.stats())
        elif args.cmd == "event":
            eid = store.add_event(
                args.kind,
                _read_content(args),
                tags=_tags(args.tags),
                source=args.source,
                writer=args.writer,
            )
            _print({"ok": eid >= 0, "event_id": eid})
        elif args.cmd == "memory":
            if args.mem_cmd == "add":
                mem = store.add_memory(
                    title=args.title,
                    body=args.body,
                    layer=args.layer,
                    confidence=args.confidence,
                    tags=_tags(args.tags),
                    source=args.source,
                    scope=args.scope,
                    supersedes=args.supersedes,
                    writer=args.writer,
                )
                _print({"ok": True, "memory": mem})
            elif args.mem_cmd == "list":
                _print(store.list_memories())
            elif args.mem_cmd == "expire":
                _print({"ok": store.expire_memory(args.id), "id": args.id})
        elif args.cmd == "search":
            hits = store.search(args.query, k=args.k, layer=args.layer)
            if args.human:
                sys.stdout.write(render_human(hits) + ("\n" if hits else ""))
            else:
                _print(hits)
        elif args.cmd == "candidates":
            _print(store.consolidation_candidates(days=args.days))
        elif args.cmd == "audit":
            _print(store.audit())
        elif args.cmd == "timeline":
            _print(store.timeline(limit=args.limit))
        elif args.cmd == "sync-md":
            if store.is_global_library():
                target = global_markdown_path()
                text = store.export_library_markdown()
            else:
                target = Path.cwd() / "memory" / "brain-index.generated.md"
                text = store.export_markdown()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            _print({"ok": True, "written": str(target)})
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
