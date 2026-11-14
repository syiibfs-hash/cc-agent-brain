"""Prove an upgrade refreshes framework files, migrates an existing DB, and merges MCP config.

The install runs against a real temporary project directory. A second run goes
through installer/update.py, which stays a thin wrapper around install.py.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "installer" / "install.py"
UPDATE = ROOT / "installer" / "update.py"
UNINSTALL = ROOT / "installer" / "uninstall.py"
PACKAGE = ROOT / "package"
sys.path.insert(0, str(ROOT / "installer"))

import mcp_config  # noqa: E402
from merge_settings import HOOKS_TO_ADD, merge_settings  # noqa: E402


def run_installer(script: Path, target: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), "--target", str(target), *extra],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def parse_manifest(stdout: str) -> dict:
    marker = "\nCC Agent Brain"
    payload = stdout if marker not in stdout else stdout.split(marker, 1)[0]
    return json.loads(payload)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CodexMergeTests(unittest.TestCase):
    def test_appends_server_and_keeps_other_tables(self) -> None:
        original = textwrap.dedent(
            """\
            # user owns this
            model = "gpt-5"

            [mcp_servers.docs]
            command = "docs-server"
            args = ["--port", "4000"]

            [profiles.ci]
            foo = 1
            """
        )
        merged = mcp_config.merge_codex_toml(
            original,
            "python",
            "/proj/.claude/hooks/cc-agent-brain/brain_store.py",
            "/proj",
        )
        self.assertIn("# user owns this", merged)
        self.assertIn('[profiles.ci]', merged)
        data = tomllib.loads(merged)
        self.assertEqual(data["model"], "gpt-5")
        self.assertEqual(data["mcp_servers"]["docs"]["command"], "docs-server")
        self.assertEqual(data["mcp_servers"]["docs"]["args"], ["--port", "4000"])
        self.assertEqual(data["profiles"]["ci"]["foo"], 1)
        server = data["mcp_servers"]["cc-agent-brain"]
        self.assertEqual(server["command"], "python")
        self.assertEqual(server["args"], ["/proj/.claude/hooks/cc-agent-brain/brain_store.py", "serve-mcp"])
        self.assertEqual(server["cwd"], "/proj")
        again = mcp_config.merge_codex_toml(
            merged,
            "python",
            "/proj/.claude/hooks/cc-agent-brain/brain_store.py",
            "/proj",
        )
        self.assertEqual(again, merged)

    def test_updates_only_this_server_and_keeps_extra_keys(self) -> None:
        original = textwrap.dedent(
            """\
            [mcp_servers.cc-agent-brain]
            command = "python"
            args = [
              "old.py",
              "serve-mcp",
            ]
            cwd = "/old"
            enabled = false

            [mcp_servers.github]
            url = "https://github.example/mcp"
            """
        )
        merged = mcp_config.merge_codex_toml(original, "python3", "/new/brain_store.py", "/work")
        data = tomllib.loads(merged)
        server = data["mcp_servers"]["cc-agent-brain"]
        self.assertEqual(server["command"], "python3")
        self.assertEqual(server["args"], ["/new/brain_store.py", "serve-mcp"])
        self.assertEqual(server["cwd"], "/work")
        self.assertIs(server["enabled"], False)
        self.assertEqual(data["mcp_servers"]["github"]["url"], "https://github.example/mcp")
        self.assertEqual(merged.count("[mcp_servers.cc-agent-brain]"), 1)
        self.assertNotIn("old.py", merged)

    def test_replaces_inline_server_without_dropping_neighbors(self) -> None:
        original = textwrap.dedent(
            """\
            [mcp_servers]
            docs = { command = "docs-server" }
            cc-agent-brain = { command = "old", args = ["old.py"] }
            other = { command = "other" }

            [mcp_servers."quoted"]
            command = "quoted-server"
            """
        )
        merged = mcp_config.merge_codex_toml(original, "python", "/brain.py", "/work")
        data = tomllib.loads(merged)
        self.assertEqual(data["mcp_servers"]["docs"]["command"], "docs-server")
        self.assertEqual(data["mcp_servers"]["other"]["command"], "other")
        self.assertEqual(data["mcp_servers"]["quoted"]["command"], "quoted-server")
        self.assertEqual(data["mcp_servers"]["cc-agent-brain"]["args"], ["/brain.py", "serve-mcp"])
        self.assertNotIn("old.py", merged)

    def test_ignores_a_header_inside_a_multiline_string(self) -> None:
        original = textwrap.dedent(
            '''\
            description = """
            [mcp_servers.fake]
            command = "nope"
            """

            [mcp_servers.docs]
            command = "docs-server"
            '''
        )
        merged = mcp_config.merge_codex_toml(original, "python", "/brain.py", "/work")
        data = tomllib.loads(merged)
        self.assertEqual(data["description"].strip().splitlines()[0], "[mcp_servers.fake]")
        self.assertEqual(data["mcp_servers"]["docs"]["command"], "docs-server")
        self.assertNotIn("fake", data["mcp_servers"])
        self.assertEqual(data["mcp_servers"]["cc-agent-brain"]["cwd"], "/work")

    def test_escapes_quotes_and_backslashes(self) -> None:
        brain = '/tmp/a"b\\c/brain_store.py'
        merged = mcp_config.merge_codex_toml("", "python", brain, "/proj")
        data = tomllib.loads(merged)
        self.assertEqual(data["mcp_servers"]["cc-agent-brain"]["args"][0], brain)

    def test_updates_a_quoted_table_header_in_place(self) -> None:
        original = '[mcp_servers."cc-agent-brain"]\ncommand = "old"\n'
        merged = mcp_config.merge_codex_toml(original, "python", "/brain.py", "/work")
        self.assertEqual(merged.count("cc-agent-brain"), 1)
        data = tomllib.loads(merged)
        self.assertEqual(data["mcp_servers"]["cc-agent-brain"]["command"], "python")
        self.assertEqual(data["mcp_servers"]["cc-agent-brain"]["cwd"], "/work")


class McpJsonMergeTests(unittest.TestCase):
    def test_claude_shape_has_no_type_or_url(self) -> None:
        entry = mcp_config.claude_server_entry("python", Path("/proj/.claude/hooks/cc-agent-brain/brain_store.py"))
        self.assertEqual(
            entry,
            {
                "command": "python",
                "args": ["/proj/.claude/hooks/cc-agent-brain/brain_store.py", "serve-mcp"],
            },
        )

    def test_cursor_shape_requires_stdio_type(self) -> None:
        entry = mcp_config.cursor_server_entry("python")
        self.assertEqual(entry["type"], "stdio")
        self.assertEqual(entry["command"], "python")
        self.assertEqual(
            entry["args"],
            ["${workspaceFolder}/.claude/hooks/cc-agent-brain/brain_store.py", "serve-mcp"],
        )
        self.assertNotIn("url", entry)

    def test_comment_outside_strings_does_not_eat_urls(self) -> None:
        raw = "\n".join(
            [
                "{",
                "  // project servers",
                '  "mcpServers": {',
                '    "remote": {"type": "http", "url": "https://example.com/mcp"}',
                "  }",
                "}",
                "",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mcp.json"
            path.write_text(raw, encoding="utf-8")
            status = mcp_config.apply_mcp_json(path, mcp_config.cursor_server_entry("python"), dry_run=False)
            self.assertEqual(status["status"], "updated")
            data = read_json(path)
            self.assertEqual(data["mcpServers"]["remote"]["url"], "https://example.com/mcp")
            self.assertEqual(data["mcpServers"]["remote"]["type"], "http")
            self.assertEqual(data["mcpServers"]["cc-agent-brain"]["type"], "stdio")


class HookSyncTests(unittest.TestCase):
    def test_settings_patch_matches_hooks_to_add(self) -> None:
        patch = read_json(PACKAGE / "claude" / "settings.patch.json")
        rendered = merge_settings({}, python_command="python")
        self.assertEqual(patch["hooks"], rendered["hooks"])
        self.assertEqual(set(patch["hooks"]), set(HOOKS_TO_ADD))


class InstallUpgradeTests(unittest.TestCase):
    def test_fresh_install_initializes_db_and_writes_three_clients(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "fresh"
            target.mkdir()
            proc = run_installer(INSTALL, target)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            manifest = parse_manifest(proc.stdout)
            self.assertEqual(manifest["engine_state"], "initialized")
            db = target / ".cc-agent-brain" / "brain.db"
            self.assertTrue(db.exists())
            with sqlite3.connect(db) as conn:
                schema = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()[0]
            self.assertEqual(schema, "2")
            self._assert_mcp_shapes(target, "python")
            self.assertEqual(manifest["mcp"]["claude"]["status"], "created")
            self.assertEqual(manifest["mcp"]["cursor"]["status"], "created")
            self.assertEqual(manifest["mcp"]["codex"]["status"], "created")

    def test_upgrade_refreshes_framework_migrates_db_and_merges_mcp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "project"
            target.mkdir()
            self._seed_existing_project(target)
            user_bytes = {
                path: path.read_bytes()
                for path in [
                    target / "memory" / "MEMORY.md",
                    target / "wiki" / "index.md",
                    target / "private" / "secret.md",
                    target / "templates" / "decision-record.md",
                    target / ".claude" / "agents" / "my-agent.md",
                    target / ".claude" / "skills" / "other-skill" / "SKILL.md",
                    target / ".claude" / "hooks" / "cc-agent-brain" / "notes.txt",
                ]
            }
            settings_before = (target / ".claude" / "settings.json").read_text(encoding="utf-8")

            first = run_installer(INSTALL, target)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_manifest = parse_manifest(first.stdout)
            self.assertEqual(first_manifest["engine_state"], "migrated")
            self._assert_user_data_intact(target, user_bytes)
            self._assert_framework_matches_package(target)
            self._assert_schema_and_user_table(target)
            self._assert_mcp_shapes(target, "python")
            self._assert_settings_merged(target)
            for tracked in first_manifest["files_added"]:
                relative = Path(tracked).relative_to(target)
                self.assertNotIn(relative.parts[0], {"memory", "wiki", "private", "templates", ".mcp.json"})
                self.assertFalse(tracked.endswith("brain.db"))
                self.assertFalse(tracked.endswith("mcp.json"))
                self.assertFalse(tracked.endswith("config.toml"))
            self.assertTrue(
                any(path.endswith("brain_store.py") for path in first_manifest["files_updated"]),
                first_manifest["files_updated"],
            )
            for client in ("claude", "cursor", "codex"):
                self.assertEqual(first_manifest["mcp"][client]["status"], "updated")
            backup = (target / ".claude" / "settings.backup.cc-agent-brain.json").read_text(encoding="utf-8")
            self.assertEqual(backup, settings_before)

            brain = target / ".claude" / "hooks" / "cc-agent-brain" / "brain_store.py"
            db = target / ".cc-agent-brain" / "brain.db"
            added = subprocess.run(
                [
                    sys.executable,
                    str(brain),
                    "--db",
                    str(db),
                    "memory",
                    "add",
                    "--title",
                    "Keep me",
                    "--body",
                    "user-fact-survives-upgrade",
                    "--layer",
                    "semantic",
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(added.returncode, 0, added.stderr)
            memory_id = json.loads(added.stdout)["memory"]["id"]

            (target / "memory" / "preferences.md").write_text("USER EDITED PREFERENCES\n", encoding="utf-8")
            brain.write_text("# STALE ENGINE\n", encoding="utf-8")
            skill = target / ".claude" / "skills" / "cc-agent-brain-wiki-search" / "SKILL.md"
            skill.write_text("# STALE SKILL\n", encoding="utf-8")
            agent = target / ".claude" / "agents" / "cc-agent-brain-memory-curator.md"
            agent.write_text("# STALE AGENT\n", encoding="utf-8")
            user_bytes[target / "memory" / "preferences.md"] = b"USER EDITED PREFERENCES\n"

            second = run_installer(UPDATE, target)
            self.assertEqual(second.returncode, 0, second.stderr)
            second_manifest = parse_manifest(second.stdout)
            self.assertEqual(second_manifest["engine_state"], "migrated")
            self._assert_framework_matches_package(target)
            self._assert_user_data_intact(target, user_bytes)
            self._assert_schema_and_user_table(target)
            with sqlite3.connect(db) as conn:
                row = conn.execute("SELECT body FROM memories WHERE id = ?", (memory_id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "user-fact-survives-upgrade")
            self._assert_mcp_shapes(target, "python")
            for client in ("claude", "cursor", "codex"):
                self.assertEqual(second_manifest["mcp"][client]["status"], "unchanged")
            self._assert_settings_not_duplicated(target)
            self.assertEqual(
                (target / ".claude" / "settings.backup.cc-agent-brain.json").read_text(encoding="utf-8"),
                settings_before,
            )
            self.assertIn(str(brain), second_manifest["files_updated"])
            self.assertTrue((target / "templates" / "weekly-review.md").exists())

            removed = run_installer(UNINSTALL, target)
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse(brain.exists())
            self.assertTrue(db.exists())
            self._assert_user_data_intact(target, user_bytes)
            self._assert_schema_and_user_table(target)
            with sqlite3.connect(db) as conn:
                row = conn.execute("SELECT body FROM memories WHERE id = ?", (memory_id,)).fetchone()
            self.assertEqual(row[0], "user-fact-survives-upgrade")
            claude = read_json(target / ".mcp.json")
            self.assertEqual(claude["mcpServers"]["other"]["command"], "other-server")
            self.assertTrue((target / "private" / "secret.md").exists())

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "preview"
            target.mkdir()
            self._seed_existing_project(target)
            before = {
                path: path.read_bytes()
                for path in target.rglob("*")
                if path.is_file()
            }
            proc = run_installer(INSTALL, target, "--dry-run")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            manifest = parse_manifest(proc.stdout)
            self.assertEqual(manifest["engine_state"], "skipped")
            for client in ("claude", "cursor", "codex"):
                self.assertEqual(manifest["mcp"][client]["status"], "dry-run")
            after = {
                path: path.read_bytes()
                for path in target.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)
            self.assertFalse((target / ".cc-agent-brain" / "install-manifest.json").exists())

    def test_invalid_mcp_json_is_left_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "broken"
            target.mkdir()
            broken = target / ".mcp.json"
            broken.write_text("{ this is not json\n", encoding="utf-8")
            proc = run_installer(INSTALL, target)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            manifest = parse_manifest(proc.stdout)
            self.assertEqual(manifest["mcp"]["claude"]["status"], "invalid")
            self.assertEqual(broken.read_text(encoding="utf-8"), "{ this is not json\n")
            self.assertEqual(manifest["mcp"]["cursor"]["status"], "created")
            self.assertEqual(read_json(target / ".cursor" / "mcp.json")["mcpServers"]["cc-agent-brain"]["type"], "stdio")

    def test_python_command_is_written_into_every_client(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "py"
            target.mkdir()
            proc = run_installer(INSTALL, target, "--python-command", "python3")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self._assert_mcp_shapes(target, "python3")
            settings = read_json(target / ".claude" / "settings.json")
            commands = json.dumps(settings)
            self.assertIn("python3 .claude/hooks/cc-agent-brain/session_start.py", commands)
            self.assertNotIn('"command": "python .claude/hooks', commands)

    def _seed_existing_project(self, target: Path) -> None:
        db = target / ".cc-agent-brain" / "brain.db"
        db.parent.mkdir(parents=True)
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE user_notes(id INTEGER PRIMARY KEY, body TEXT)")
            conn.execute("INSERT INTO user_notes(body) VALUES ('keep-me')")
        hook_dir = target / ".claude" / "hooks" / "cc-agent-brain"
        hook_dir.mkdir(parents=True)
        (hook_dir / "brain_store.py").write_text("# STALE ENGINE\n", encoding="utf-8")
        (hook_dir / "notes.txt").write_text("LOCAL NOTE\n", encoding="utf-8")
        skill = target / ".claude" / "skills" / "cc-agent-brain-wiki-search"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# STALE SKILL\n", encoding="utf-8")
        agents = target / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "cc-agent-brain-memory-curator.md").write_text("# STALE AGENT\n", encoding="utf-8")
        (agents / "my-agent.md").write_text("MY AGENT\n", encoding="utf-8")
        other = target / ".claude" / "skills" / "other-skill"
        other.mkdir(parents=True)
        (other / "SKILL.md").write_text("OTHER SKILL\n", encoding="utf-8")
        (target / ".claude" / "settings.json").write_text(
            json.dumps(
                {
                    "customFlag": True,
                    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo keep-me"}]}]},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (target / "memory").mkdir()
        (target / "memory" / "MEMORY.md").write_text("USER MEMORY\n", encoding="utf-8")
        (target / "wiki").mkdir()
        (target / "wiki" / "index.md").write_text("USER WIKI\n", encoding="utf-8")
        (target / "private").mkdir()
        (target / "private" / "secret.md").write_text("SECRET\n", encoding="utf-8")
        (target / "templates").mkdir()
        (target / "templates" / "decision-record.md").write_text("USER TEMPLATE\n", encoding="utf-8")
        (target / ".mcp.json").write_text(
            json.dumps(
                {
                    "theme": "keep",
                    "mcpServers": {
                        "other": {"command": "other-server", "args": ["--stay"]},
                        "cc-agent-brain": {"url": "http://127.0.0.1:9/mcp"},
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        cursor = target / ".cursor"
        cursor.mkdir()
        (cursor / "mcp.json").write_text(
            "\n".join(
                [
                    "{",
                    "  // keep remote",
                    '  "mcpServers": {',
                    '    "remote": {"type": "http", "url": "https://example.com/mcp"},',
                    '    "cc-agent-brain": {"command": "python", "args": ["old.py"]}',
                    "  }",
                    "}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        codex = target / ".codex"
        codex.mkdir()
        (codex / "config.toml").write_text(
            "\n".join(
                [
                    "# user owns this",
                    'model = "gpt-5"',
                    "",
                    "[mcp_servers.docs]",
                    'command = "docs-server"',
                    'args = ["--port", "4000"]',
                    "",
                    "[mcp_servers.cc-agent-brain]",
                    'command = "python"',
                    'args = ["old.py", "serve-mcp"]',
                    'cwd = "/old"',
                    "enabled = false",
                    "",
                    "[profiles.ci]",
                    "foo = 1",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _assert_framework_matches_package(self, target: Path) -> None:
        for relative in (
            Path(".claude/hooks/cc-agent-brain/brain_store.py"),
            Path(".claude/skills/cc-agent-brain-wiki-search/SKILL.md"),
            Path(".claude/agents/cc-agent-brain-memory-curator.md"),
        ):
            installed = (target / relative).read_bytes()
            packaged = (PACKAGE / "claude" / relative.relative_to(".claude")).read_bytes()
            self.assertEqual(installed, packaged, relative)
        self.assertEqual((target / ".claude" / "hooks" / "cc-agent-brain" / "notes.txt").read_text(encoding="utf-8"), "LOCAL NOTE\n")
        self.assertEqual((target / ".claude" / "agents" / "my-agent.md").read_text(encoding="utf-8"), "MY AGENT\n")
        self.assertEqual((target / ".claude" / "skills" / "other-skill" / "SKILL.md").read_text(encoding="utf-8"), "OTHER SKILL\n")

    def _assert_user_data_intact(self, target: Path, user_bytes: dict) -> None:
        for path, payload in user_bytes.items():
            self.assertTrue(path.exists(), path)
            self.assertEqual(path.read_bytes(), payload, path)

    def _assert_schema_and_user_table(self, target: Path) -> None:
        db = target / ".cc-agent-brain" / "brain.db"
        with sqlite3.connect(db) as conn:
            schema = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()[0]
            note = conn.execute("SELECT body FROM user_notes").fetchone()[0]
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertEqual(schema, "2")
        self.assertEqual(note, "keep-me")
        self.assertTrue({"events", "memories", "user_notes"} <= tables)

    def _assert_mcp_shapes(self, target: Path, python_command: str) -> None:
        brain = str((target / ".claude" / "hooks" / "cc-agent-brain" / "brain_store.py").resolve())
        claude = read_json(target / ".mcp.json")
        claude_server = claude["mcpServers"]["cc-agent-brain"]
        if "theme" in claude:
            self.assertEqual(claude["theme"], "keep")
        if "other" in claude["mcpServers"]:
            self.assertEqual(claude["mcpServers"]["other"], {"command": "other-server", "args": ["--stay"]})
        self.assertEqual(set(claude_server), {"command", "args"})
        self.assertEqual(claude_server["command"], python_command)
        self.assertEqual(claude_server["args"], [brain, "serve-mcp"])
        self.assertNotIn("url", claude_server)

        cursor = read_json(target / ".cursor" / "mcp.json")
        cursor_server = cursor["mcpServers"]["cc-agent-brain"]
        self.assertEqual(
            cursor_server,
            {
                "type": "stdio",
                "command": python_command,
                "args": ["${workspaceFolder}/.claude/hooks/cc-agent-brain/brain_store.py", "serve-mcp"],
            },
        )
        if "remote" in cursor["mcpServers"]:
            self.assertEqual(cursor["mcpServers"]["remote"]["type"], "http")
            self.assertEqual(cursor["mcpServers"]["remote"]["url"], "https://example.com/mcp")

        codex_text = (target / ".codex" / "config.toml").read_text(encoding="utf-8")
        self.assertNotIn("mcpServers", codex_text)
        self.assertIn("[mcp_servers.cc-agent-brain]", codex_text)
        codex = tomllib.loads(codex_text)
        server = codex["mcp_servers"]["cc-agent-brain"]
        self.assertEqual(server["command"], python_command)
        self.assertEqual(server["args"], [brain, "serve-mcp"])
        self.assertEqual(server["cwd"], str(target.resolve()))
        if "docs" in codex["mcp_servers"]:
            self.assertEqual(codex["mcp_servers"]["docs"]["command"], "docs-server")
            self.assertEqual(codex["mcp_servers"]["docs"]["args"], ["--port", "4000"])
            self.assertIs(server["enabled"], False)
            self.assertEqual(codex["model"], "gpt-5")
            self.assertEqual(codex["profiles"]["ci"]["foo"], 1)
            self.assertIn("# user owns this", codex_text)

    def _assert_settings_merged(self, target: Path) -> None:
        settings = read_json(target / ".claude" / "settings.json")
        self.assertIs(settings["customFlag"], True)
        commands = [
            hook["command"]
            for entry in settings["hooks"]["Stop"]
            for hook in entry["hooks"]
        ]
        self.assertIn("echo keep-me", commands)
        self.assertTrue(any("cc-agent-brain/transcript_capture.py" in command for command in commands))

    def _assert_settings_not_duplicated(self, target: Path) -> None:
        settings = read_json(target / ".claude" / "settings.json")
        self.assertIs(settings["customFlag"], True)
        rendered = merge_settings(
            {"customFlag": True, "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo keep-me"}]}]}},
            python_command="python",
        )
        self.assertEqual(settings, rendered)


if __name__ == "__main__":
    unittest.main()
