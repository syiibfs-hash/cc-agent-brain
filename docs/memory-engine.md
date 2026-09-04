# Local Memory Engine

`package/claude/hooks/cc-agent-brain/brain_store.py` is the engine. It uses only
the Python standard library (sqlite3) — no pip install, no network.

## Database locations

| Scope | Path | Used for |
|-------|------|----------|
| project (default) | `.cc-agent-brain/brain.db` | this project's events and memories |
| global (`--global`) | `~/.cc-agent-brain/brain.db` | identity and preferences shared across projects |

Search always queries the project DB first and merges the global DB when present.

## Tables

- `events` — append-only episodic stream (kind: user/assistant/tool/system),
  mirrored into `events_fts` (FTS5).
- `memories` — versioned long-term records, mirrored into `memories_fts`.
  Non-active memories are removed from the FTS index but kept in the table.
- `meta` — schema version.

## CLI

```bash
BRAIN="python .claude/hooks/cc-agent-brain/brain_store.py"

$BRAIN init                                   # create / migrate the DB
$BRAIN stats                                  # counts by kind/layer/status
$BRAIN event --kind user --content "..."      # append an event (auto-redacted)
$BRAIN memory add --title "..." --body "..." \
    --layer semantic --confidence high --tags "a,b" --source wiki/x.md
$BRAIN memory add ... --supersedes m-xxxx     # replace an old memory
$BRAIN memory expire m-xxxx                   # invalidate, keep history
$BRAIN memory list
$BRAIN search "查询词" --k 8 [--layer semantic] [--human]
$BRAIN candidates --days 3                    # consolidation backlog
$BRAIN audit                                   # duplicates / chains / stale
$BRAIN timeline --limit 15
$BRAIN sync-md                                # regenerate memory/brain-index.generated.md
$BRAIN redact --content "..."                 # standalone secret redaction
```

All commands emit JSON except `search --human`, which prints hook-ready text.

## Retrieval details

1. Free text is tokenized into latin words + Chinese bigrams (FTS5's unicode61
   has no CJK segmenter; indexing and querying use the identical tokenizer).
2. Active memories and events are ranked by FTS5 `bm25()`.
3. Project and global result lists are fused with Reciprocal Rank Fusion
   (`rrf_fuse`, k=60). The same fusion point accepts a future vector channel
   without changing call sites.
4. Superseded / expired / archived memories never appear in active recall.

## Secret redaction

Applied at capture time to both events and memories. Recognized shapes include
OpenAI/Anthropic/GitHub/AWS/Google keys, JWTs, Bearer tokens, PEM blocks and
`password=/api_key=` style assignments. They are replaced by `[REDACTED:kind]`.
Redaction is best-effort and never a replacement for not storing secrets.

## Backup

The DB is a single ordinary SQLite file (WAL mode). Copy it to back up; delete
it to reset. Uninstall never removes it.
