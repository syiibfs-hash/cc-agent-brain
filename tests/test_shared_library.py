"""Shared global library path and writer identity.

Two MCP clients can write one on-disk SQLite library and both read the rows
back. Writer is whatever the caller passed, not a guess about the product.
The shared Markdown file is rebuilt from memories and from event counts.
Project brain.db stays a different file; search still fuses the global file
when that file exists.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
BRAIN = ROOT / "package" / "claude" / "hooks" / "cc-agent-brain" / "brain_store.py"
HOOKS = BRAIN.parent
sys.path.insert(0, str(HOOKS))

import brain_store  # noqa: E402
import _utils  # noqa: E402

RAW_UTTERANCE = "raw-utterance-7f3a9c"


def _tree_sig(path: Path):
    if not path.exists():
        return None
    files = []
    for item in sorted(path.rglob("*")):
        if item.is_file():
            st = item.stat()
            files.append((str(item.relative_to(path)), st.st_mtime_ns, st.st_size))
    return tuple(files)


def _tool_call(name: str, arguments: dict, req_id: int) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


def _tool_payload(response: dict):
    result = response["result"]
    if result.get("isError"):
        raise AssertionError(result)
    return json.loads(result["content"][0]["text"])


class SharedLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.global_dir = self.root / "global-library"
        self._saved_env = {
            brain_store.GLOBAL_DIR_ENV: os.environ.get(brain_store.GLOBAL_DIR_ENV),
            brain_store.WRITER_ENV: os.environ.get(brain_store.WRITER_ENV),
        }
        self._saved_override = brain_store._global_dir_override
        brain_store.set_global_library_dir(None)
        os.environ[brain_store.GLOBAL_DIR_ENV] = str(self.global_dir)
        os.environ.pop(brain_store.WRITER_ENV, None)
        self._home_before = _tree_sig(Path.home() / ".cc-agent-brain")

    def tearDown(self) -> None:
        brain_store.set_global_library_dir(None)
        brain_store._global_dir_override = self._saved_override
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()
        self.assertEqual(_tree_sig(Path.home() / ".cc-agent-brain"), self._home_before)

    def env_for(self, writer: Optional[str] = None) -> dict:
        env = os.environ.copy()
        env[brain_store.GLOBAL_DIR_ENV] = str(self.global_dir)
        if writer is None:
            env.pop(brain_store.WRITER_ENV, None)
        else:
            env[brain_store.WRITER_ENV] = writer
        return env

    def run_json(self, args: list, env: Optional[dict] = None, cwd: Optional[Path] = None):
        proc = subprocess.run(
            [sys.executable, str(BRAIN), *args],
            capture_output=True,
            text=True,
            env=env or self.env_for(),
            cwd=str(cwd or self.root),
            timeout=20,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"{args}\nexit {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
        text = proc.stdout.strip()
        if not text:
            return None
        return json.loads(text)

    def mcp(self, messages: list, env: dict) -> list:
        payload = "".join(json.dumps(message) + "\n" for message in messages)
        proc = subprocess.run(
            [sys.executable, str(BRAIN), "--global", "serve-mcp"],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(self.root),
            timeout=20,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"serve-mcp exit {proc.returncode}\nstderr:\n{proc.stderr}")
        return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]

    def test_default_global_dir_is_under_home(self) -> None:
        os.environ.pop(brain_store.GLOBAL_DIR_ENV, None)
        brain_store.set_global_library_dir(None)
        self.assertEqual(
            brain_store.global_library_dir(),
            (Path.home() / ".cc-agent-brain").resolve(),
        )
        self.assertEqual(brain_store.global_db_path().name, "brain.db")
        self.assertEqual(brain_store.global_markdown_path().name, "library.md")
        self.assertEqual(brain_store.global_db_path().parent, brain_store.global_markdown_path().parent)

    def test_two_mcp_clients_share_rows_and_writer(self) -> None:
        claude = self.mcp(
            [
                _tool_call(
                    "brain_add_memory",
                    {
                        "title": "Claude window",
                        "body": "deploy window is blue",
                        "writer": "claude-code",
                        "source": "mcp",
                    },
                    1,
                )
            ],
            self.env_for("env-must-not-override"),
        )
        first = _tool_payload(claude[0])
        self.assertEqual(first["writer"], "claude-code")
        self.assertEqual(first["source"], "mcp")

        cursor = self.mcp(
            [
                _tool_call(
                    "brain_add_memory",
                    {"title": "Cursor window", "body": "deploy window is blue too"},
                    2,
                )
            ],
            self.env_for("cursor"),
        )
        second = _tool_payload(cursor[0])
        self.assertEqual(second["writer"], "cursor")

        self.run_json(
            ["--global", "event", "--kind", "user", "--content", f"{RAW_UTTERANCE} from claude", "--writer", "claude-code"]
        )
        self.run_json(
            [
                "--global",
                "event",
                "--kind",
                "assistant",
                "--content",
                f"{RAW_UTTERANCE} from cursor",
                "--writer",
                "cursor",
            ]
        )

        found = self.mcp(
            [_tool_call("brain_search", {"query": "deploy window", "k": 8}, 3)],
            self.env_for(),
        )
        hits = _tool_payload(found[0])
        by_title = {hit["title"]: hit["writer"] for hit in hits if hit.get("_type") == "memory"}
        self.assertEqual(by_title["Claude window"], "claude-code")
        self.assertEqual(by_title["Cursor window"], "cursor")

        events = self.mcp(
            [_tool_call("brain_search", {"query": RAW_UTTERANCE, "k": 8}, 4)],
            self.env_for(),
        )
        event_hits = _tool_payload(events[0])
        event_writers = sorted(hit["writer"] for hit in event_hits if hit.get("_type") == "event")
        self.assertEqual(event_writers, ["claude-code", "cursor"])

        timeline = _tool_payload(
            self.mcp([_tool_call("brain_timeline", {"limit": 10}, 5)], self.env_for())[0]
        )
        timeline_writers = {row["title"]: row["writer"] for row in timeline}
        self.assertEqual(timeline_writers["Claude window"], "claude-code")
        self.assertEqual(timeline_writers["Cursor window"], "cursor")

        stats = _tool_payload(self.mcp([_tool_call("brain_stats", {}, 6)], self.env_for())[0])
        self.assertGreaterEqual(stats["memories_by_writer"].get("claude-code", 0), 1)
        self.assertGreaterEqual(stats["memories_by_writer"].get("cursor", 0), 1)
        self.assertGreaterEqual(stats["events_by_writer"].get("claude-code", 0), 1)
        self.assertGreaterEqual(stats["events_by_writer"].get("cursor", 0), 1)
        self.assertEqual(stats["db"], str(self.global_dir / "brain.db"))

    def test_writer_precedence_and_source_stay_distinct(self) -> None:
        omitted = self.run_json(
            ["--global", "memory", "add", "--title", "No writer", "--body", "uses the documented default"]
        )
        self.assertEqual(omitted["memory"]["writer"], "unspecified")

        from_env = self.run_json(
            ["--global", "memory", "add", "--title", "Env writer", "--body", "label comes from the environment"],
            env=self.env_for("codex"),
        )
        self.assertEqual(from_env["memory"]["writer"], "codex")

        explicit = self.run_json(
            [
                "--global",
                "memory",
                "add",
                "--title",
                "Explicit writer",
                "--body",
                "flag wins",
                "--writer",
                "claude-code",
                "--source",
                "wiki/decisions/window.md",
            ],
            env=self.env_for("codex"),
        )
        self.assertEqual(explicit["memory"]["writer"], "claude-code")
        self.assertEqual(explicit["memory"]["source"], "wiki/decisions/window.md")

    def test_shared_markdown_updates_without_raw_utterances(self) -> None:
        self.run_json(
            [
                "--global",
                "memory",
                "add",
                "--title",
                "Shared decision",
                "--body",
                "use the blue deploy window",
                "--writer",
                "claude-code",
            ]
        )
        self.run_json(
            ["--global", "event", "--kind", "user", "--content", f"please remember {RAW_UTTERANCE}", "--writer", "cursor"]
        )
        library = self.global_dir / "library.md"
        text = library.read_text(encoding="utf-8")
        self.assertIn("Shared decision", text)
        self.assertIn("use the blue deploy window", text)
        self.assertIn("writer: claude-code", text)
        self.assertIn("events by writer: cursor 1", text)
        self.assertNotIn(RAW_UTTERANCE, text)
        self.assertNotIn("please remember", text)

        self.run_json(
            [
                "--global",
                "memory",
                "add",
                "--title",
                "Second shared fact",
                "--body",
                "keep the rollback note",
                "--writer",
                "codex",
            ]
        )
        updated = library.read_text(encoding="utf-8")
        self.assertIn("Second shared fact", updated)
        self.assertIn("keep the rollback note", updated)
        self.assertNotIn(RAW_UTTERANCE, updated)
        self.assertNotEqual(text, updated)

        synced = self.run_json(["--global", "sync-md"])
        self.assertEqual(Path(synced["written"]), library.resolve())
        resynced = library.read_text(encoding="utf-8")
        self.assertIn("Second shared fact", resynced)
        self.assertNotIn(RAW_UTTERANCE, resynced)

    def test_project_db_stays_isolated_except_search_fallback(self) -> None:
        project = self.root / "proj"
        project.mkdir()
        project_db = project / ".cc-agent-brain" / "brain.db"
        self.run_json(
            [
                "--global",
                "memory",
                "add",
                "--title",
                "GlobalOnlyToken",
                "--body",
                "shared across clients",
                "--writer",
                "cursor",
            ]
        )
        self.run_json(
            [
                "--db",
                str(project_db),
                "memory",
                "add",
                "--title",
                "ProjectLocalToken",
                "--body",
                "only this project",
                "--writer",
                "claude-code",
            ],
            cwd=project,
        )

        with sqlite3.connect(project_db) as conn:
            project_titles = [row[0] for row in conn.execute("SELECT title FROM memories")]
        with sqlite3.connect(self.global_dir / "brain.db") as conn:
            global_titles = [row[0] for row in conn.execute("SELECT title FROM memories")]
        self.assertEqual(project_titles, ["ProjectLocalToken"])
        self.assertIn("GlobalOnlyToken", global_titles)
        self.assertNotIn("ProjectLocalToken", global_titles)

        self.assertEqual(self.run_json(["--global", "search", "ProjectLocalToken"]), [])
        library = (self.global_dir / "library.md").read_text(encoding="utf-8")
        self.assertIn("GlobalOnlyToken", library)
        self.assertNotIn("ProjectLocalToken", library)

        project_store = brain_store.BrainStore(project_db)
        global_store = brain_store.BrainStore(self.global_dir / "brain.db")
        try:
            fused = project_store.search("GlobalOnlyToken")
            self.assertTrue(any(hit.get("title") == "GlobalOnlyToken" for hit in fused))
            alone = project_store.search("GlobalOnlyToken", include_global=False)
            self.assertEqual(alone, [])
            own = project_store.search("ProjectLocalToken", include_global=False)
            self.assertTrue(any(hit.get("title") == "ProjectLocalToken" for hit in own))
            self.assertEqual(global_store.search("ProjectLocalToken"), [])
        finally:
            project_store.close()
            global_store.close()

        synced = self.run_json(["--db", str(project_db), "sync-md"], cwd=project)
        index = project / "memory" / "brain-index.generated.md"
        self.assertEqual(Path(synced["written"]), index.resolve())
        projected = index.read_text(encoding="utf-8")
        self.assertIn("ProjectLocalToken", projected)
        self.assertNotIn("GlobalOnlyToken", projected)
        self.assertNotIn(RAW_UTTERANCE, projected)

    def test_global_dir_flag_overrides_env(self) -> None:
        custom = self.root / "custom-lib"
        env = os.environ.copy()
        env[brain_store.GLOBAL_DIR_ENV] = str(self.global_dir)
        env.pop(brain_store.WRITER_ENV, None)
        written = self.run_json(
            [
                "--global-dir",
                str(custom),
                "--global",
                "memory",
                "add",
                "--title",
                "CustomDirFact",
                "--body",
                "lives next to the flag",
                "--writer",
                "codex",
            ],
            env=env,
        )
        self.assertEqual(written["memory"]["writer"], "codex")
        self.assertTrue((custom / "brain.db").is_file())
        self.assertIn("CustomDirFact", (custom / "library.md").read_text(encoding="utf-8"))
        self.assertFalse((self.global_dir / "brain.db").exists())

    def test_existing_database_gains_writer_column(self) -> None:
        db = self.root / "legacy.db"
        conn = sqlite3.connect(db)
        conn.executescript(
            """
            CREATE TABLE events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts TEXT NOT NULL,
              kind TEXT NOT NULL,
              content TEXT NOT NULL,
              tags TEXT DEFAULT '[]',
              source TEXT DEFAULT '',
              dedup_hash TEXT UNIQUE,
              created_at TEXT NOT NULL
            );
            CREATE TABLE memories(
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
              updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO events(ts, kind, content, tags, source, dedup_hash, created_at) VALUES(?,?,?,?,?,?,?)",
            ("2020-01-01T00:00:00", "user", "legacy event", "[]", "prompt_capture", "legacyhash", "2020-01-01T00:00:00"),
        )
        conn.execute(
            """INSERT INTO memories(id, layer, scope, title, body, tags, confidence, status,
               valid_from, source, created_at, updated_at)
               VALUES('m-legacy', 'semantic', 'project', 'Legacy fact', 'already stored', '[]',
                      'medium', 'active', '2020-01-01T00:00:00', 'wiki/old.md',
                      '2020-01-01T00:00:00', '2020-01-01T00:00:00')"""
        )
        conn.commit()
        conn.close()

        store = brain_store.BrainStore(db)
        try:
            event_cols = {row["name"] for row in store.conn.execute("PRAGMA table_info(events)")}
            memory_cols = {row["name"] for row in store.conn.execute("PRAGMA table_info(memories)")}
            self.assertIn("writer", event_cols)
            self.assertIn("writer", memory_cols)
            self.assertEqual(store.conn.execute("SELECT writer FROM events").fetchone()["writer"], "")
            self.assertEqual(store.conn.execute("SELECT writer FROM memories WHERE id='m-legacy'").fetchone()["writer"], "")
            created = store.add_memory(title="After migrate", body="new row", writer="cursor")
            self.assertEqual(created["writer"], "cursor")
            self.assertEqual(store.get_memory("m-legacy")["title"], "Legacy fact")
        finally:
            store.close()

    def test_hook_writer_is_explicit_and_recorded(self) -> None:
        os.environ.pop(brain_store.WRITER_ENV, None)
        self.assertEqual(_utils.hook_writer(), "claude-code")
        os.environ[brain_store.WRITER_ENV] = "custom-hook"
        self.assertEqual(_utils.hook_writer(), "custom-hook")
        self.assertEqual(_utils.hook_writer("explicit-hook"), "explicit-hook")

        captured = {}

        def fake_cli(args, stdin_text=None, timeout=8.0):
            captured["args"] = list(args)
            return {"ok": True}

        original = _utils.brain_cli
        _utils.brain_cli = fake_cli
        try:
            _utils.brain_event("user", "hello from the hook", tags=["user_prompt"], source="prompt_capture")
        finally:
            _utils.brain_cli = original
        args = captured["args"]
        self.assertEqual(args[args.index("--writer") + 1], "custom-hook")
        self.assertEqual(args[args.index("--source") + 1], "prompt_capture")

        os.environ.pop(brain_store.WRITER_ENV, None)
        project = self.root / "hook-proj"
        project.mkdir()
        prompt = subprocess.run(
            [sys.executable, str(HOOKS / "prompt_capture.py")],
            input=json.dumps({"prompt": "hook prompt token stays in the project db"}),
            capture_output=True,
            text=True,
            env=self.env_for(),
            cwd=str(project),
            timeout=20,
            check=False,
        )
        self.assertEqual(prompt.returncode, 0, prompt.stderr)
        transcript = self.root / "transcript.jsonl"
        transcript.write_text(
            json.dumps(
                {
                    "uuid": "u1",
                    "message": {"role": "assistant", "content": [{"type": "text", "text": "hook assistant token"}]},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        stopped = subprocess.run(
            [sys.executable, str(HOOKS / "transcript_capture.py")],
            input=json.dumps({"transcript_path": str(transcript)}),
            capture_output=True,
            text=True,
            env=self.env_for(),
            cwd=str(project),
            timeout=20,
            check=False,
        )
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        with sqlite3.connect(project / ".cc-agent-brain" / "brain.db") as conn:
            rows = conn.execute("SELECT kind, source, writer, content FROM events").fetchall()
        by_source = {row[1]: row for row in rows}
        self.assertEqual(by_source["prompt_capture"][2], "claude-code")
        self.assertIn("hook prompt token", by_source["prompt_capture"][3])
        self.assertEqual(by_source["transcript"][2], "claude-code")
        self.assertIn("hook assistant token", by_source["transcript"][3])
        self.assertFalse((self.global_dir / "brain.db").exists())


if __name__ == "__main__":
    unittest.main()
