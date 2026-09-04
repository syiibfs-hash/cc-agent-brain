#!/usr/bin/env python3
"""UserPromptSubmit hook: real local retrieval instead of keyword matching.

Runs an FTS5/BM25 search over compressed memories and the event stream.
When relevant local context exists, it is printed as additional context for
Claude Code. Silent when the engine is unavailable or nothing matches —
hard-coded keyword lists are intentionally gone.
"""

from __future__ import annotations

import sys

from _utils import brain_search_human, read_stdin_json

data = read_stdin_json()
prompt = str(data.get("prompt") or data.get("raw_stdin") or "").strip()
if not prompt or len(prompt) < 2:
    sys.exit(0)

hint = brain_search_human(prompt, k=6)
if hint:
    print(hint)
