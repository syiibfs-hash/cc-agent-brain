"""Stdio proof that serve-mcp speaks both MCP eras.

Legacy clients still complete initialize (protocolVersion 2024-11-05).
A 2026-07-28 client completes server/discover and tools/list. An unsupported
modern protocolVersion returns JSON-RPC -32022 with data.supported and
data.requested, and the process does not fall back to initialize.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAIN = ROOT / "package" / "claude" / "hooks" / "cc-agent-brain" / "brain_store.py"
sys.path.insert(0, str(BRAIN.parent))

import brain_store  # noqa: E402

PROTOCOL_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
CLIENT_CAPABILITIES_KEY = "io.modelcontextprotocol/clientCapabilities"
SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"
TOOL_NAMES = (
    "brain_search",
    "brain_add_memory",
    "brain_forget",
    "brain_timeline",
    "brain_stats",
)


def modern_request(method: str, req_id, protocol: str = "2026-07-28", **params):
    body = {
        "_meta": {
            PROTOCOL_VERSION_KEY: protocol,
            CLIENT_CAPABILITIES_KEY: {},
            "io.modelcontextprotocol/clientInfo": {
                "name": "dual-era-test",
                "version": "1.0.0",
            },
        }
    }
    body.update(params)
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": body}


def legacy_initialize(req_id=1):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "legacy-test", "version": "1.0.0"},
        },
    }


def run_session(messages):
    payload = "".join(json.dumps(message, ensure_ascii=False) + "\n" for message in messages)
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "brain.db")
        proc = subprocess.run(
            [sys.executable, str(BRAIN), "--db", db, "serve-mcp"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    if proc.returncode != 0:
        raise AssertionError(f"serve-mcp exited {proc.returncode}\nstderr:\n{proc.stderr}")
    responses = []
    for line in proc.stdout.splitlines():
        if line.strip():
            responses.append(json.loads(line))
    return responses, proc.stderr


def server_info(result):
    return result["_meta"][SERVER_INFO_KEY]


class LegacyHandshakeTest(unittest.TestCase):
    def test_initialize_tools_and_ping(self):
        responses, _stderr = run_session(
            [
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                legacy_initialize(1),
                {"jsonrpc": "2.0", "id": 2, "method": "ping"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "brain_stats", "arguments": {}},
                },
            ]
        )
        self.assertEqual(len(responses), 4)
        self.assertEqual([item["id"] for item in responses], [1, 2, 3, 4])

        initialized = responses[0]["result"]
        self.assertEqual(initialized["protocolVersion"], "2024-11-05")
        self.assertEqual(initialized["capabilities"], {"tools": {}})
        self.assertEqual(initialized["serverInfo"]["name"], "cc-agent-brain")
        self.assertIn("version", initialized["serverInfo"])
        self.assertNotIn("resultType", initialized)

        self.assertEqual(responses[1]["result"], {})

        listed = responses[2]["result"]
        self.assertEqual([tool["name"] for tool in listed["tools"]], list(TOOL_NAMES))
        self.assertNotIn("resultType", listed)

        called = responses[3]["result"]
        self.assertEqual(called["isError"], False)
        self.assertEqual(called["content"][0]["type"], "text")
        self.assertNotIn("resultType", called)


class ModernHandshakeTest(unittest.TestCase):
    def test_discover_and_tools_list(self):
        responses, _stderr = run_session(
            [
                modern_request("server/discover", "discover-1"),
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                modern_request("tools/list", 2),
                modern_request("tools/call", 3, name="brain_stats", arguments={}),
            ]
        )
        self.assertEqual(len(responses), 3)
        self.assertEqual([item["id"] for item in responses], ["discover-1", 2, 3])

        discovered = responses[0]["result"]
        self.assertEqual(discovered["resultType"], "complete")
        self.assertEqual(discovered["supportedVersions"], ["2026-07-28", "2024-11-05"])
        self.assertEqual(discovered["capabilities"], {"tools": {}})
        self.assertEqual(discovered["cacheScope"], "public")
        self.assertIsInstance(discovered["ttlMs"], int)
        self.assertGreaterEqual(discovered["ttlMs"], 0)
        info = server_info(discovered)
        self.assertEqual(info["name"], "cc-agent-brain")
        self.assertEqual(info["version"], "0.2.0")
        self.assertNotEqual(info["version"], brain_store.SCHEMA_VERSION)

        listed = responses[1]["result"]
        self.assertEqual(listed["resultType"], "complete")
        self.assertEqual([tool["name"] for tool in listed["tools"]], list(TOOL_NAMES))
        self.assertEqual(
            [tool["name"] for tool in listed["tools"]],
            [tool["name"] for tool in brain_store.MCP_TOOLS],
        )
        self.assertEqual(listed["cacheScope"], "public")
        self.assertIsInstance(listed["ttlMs"], int)
        self.assertGreaterEqual(listed["ttlMs"], 0)
        self.assertNotIn("nextCursor", listed)
        listed_info = server_info(listed)
        self.assertEqual(listed_info, {"name": "cc-agent-brain", "version": "0.2.0"})

        called = responses[2]["result"]
        self.assertEqual(called["resultType"], "complete")
        self.assertEqual(called["isError"], False)
        self.assertEqual(called["content"][0]["type"], "text")
        self.assertEqual(server_info(called)["version"], "0.2.0")
        self.assertNotIn("ttlMs", called)
        self.assertNotIn("cacheScope", called)

    def test_modern_path_does_not_depend_on_ping(self):
        responses, _stderr = run_session([modern_request("ping", 1)])
        self.assertEqual(responses[0]["error"]["code"], -32601)
        self.assertNotIn("result", responses[0])

    def test_enveloped_initialize_is_not_the_legacy_handshake(self):
        responses, _stderr = run_session([modern_request("initialize", 1)])
        self.assertEqual(responses[0]["error"]["code"], -32601)
        self.assertNotIn("result", responses[0])


class UnsupportedProtocolVersionTest(unittest.TestCase):
    def test_unknown_version_returns_32022_and_blocks_initialize(self):
        responses, _stderr = run_session(
            [
                modern_request("server/discover", 7, protocol="1900-01-01"),
                legacy_initialize(8),
            ]
        )
        self.assertEqual(len(responses), 2)
        error = responses[0]["error"]
        self.assertEqual(error["code"], -32022)
        self.assertEqual(error["data"]["requested"], "1900-01-01")
        self.assertEqual(error["data"]["supported"], ["2026-07-28", "2024-11-05"])
        self.assertNotIn("result", responses[0])

        fallback = responses[1]
        self.assertEqual(fallback["error"]["code"], -32022)
        self.assertEqual(fallback["error"]["data"]["supported"], ["2026-07-28", "2024-11-05"])
        self.assertEqual(fallback["error"]["data"]["requested"], "2024-11-05")
        self.assertNotIn("result", fallback)

    def test_legacy_version_inside_modern_meta_is_not_initialize(self):
        responses, _stderr = run_session(
            [modern_request("tools/list", 1, protocol="2024-11-05")]
        )
        error = responses[0]["error"]
        self.assertEqual(error["code"], -32022)
        self.assertEqual(error["data"]["requested"], "2024-11-05")
        self.assertIn("2026-07-28", error["data"]["supported"])
        self.assertNotIn("result", responses[0])

    def test_successful_discover_does_not_fall_back_to_initialize(self):
        responses, _stderr = run_session(
            [
                modern_request("server/discover", 1),
                modern_request("tools/list", 2),
                legacy_initialize(3),
            ]
        )
        self.assertEqual(responses[0]["result"]["resultType"], "complete")
        self.assertEqual(responses[1]["result"]["resultType"], "complete")
        self.assertEqual(responses[2]["error"]["code"], -32022)
        self.assertNotIn("protocolVersion", responses[2].get("result", {}))


class EraDetectionTest(unittest.TestCase):
    def test_partial_meta_stays_on_the_legacy_path(self):
        responses, _stderr = run_session(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {
                        "_meta": {
                            PROTOCOL_VERSION_KEY: "2026-07-28",
                        }
                    },
                }
            ]
        )
        listed = responses[0]["result"]
        self.assertIn("tools", listed)
        self.assertNotIn("resultType", listed)

    def test_wrong_meta_types_are_not_served_as_initialize(self):
        responses, _stderr = run_session(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "_meta": {
                            PROTOCOL_VERSION_KEY: 2026,
                            CLIENT_CAPABILITIES_KEY: [],
                        },
                    },
                }
            ]
        )
        self.assertEqual(responses[0]["error"]["code"], -32602)
        self.assertNotIn("result", responses[0])


if __name__ == "__main__":
    unittest.main()
