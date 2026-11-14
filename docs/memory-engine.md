# Local memory engine

`package/claude/hooks/cc-agent-brain/brain_store.py` uses the Python standard
library (`sqlite3`) only. Nothing in this file imports a third-party package
or opens a network connection.

## Database files

| How you select it | Path | Who writes it |
|-------------------|------|----------------|
| default (hooks and plain CLI) | `.cc-agent-brain/brain.db` under the current working directory | Claude Code hooks and any CLI call without `--global` |
| `--global` | `~/.cc-agent-brain/brain.db` | only commands you point at it |

`search` always queries the database you opened. It also opens the global path
when that file exists and is not the same file, and fuses the extra lexical
lists with RRF. Hooks never pass `--global`, and the installer does not create
the global file. That second file is not a shared multi-agent memory service:
there is no daemon, no agent id, and no cross-process protocol beyond SQLite.

## Tables

- `events` — insert-only rows (`kind`: `user` / `assistant` / `tool` / `system`),
  mirrored into `events_fts` (FTS5) at insert time.
- `memories` — rows with status, layer, and validity columns, mirrored into
  `memories_fts` while `active`. A non-active status deletes the FTS row and
  keeps the table row.
- `meta` — `schema_version` (`"2"`), inserted once.

`_migrate` uses `CREATE TABLE IF NOT EXISTS`. It does not alter columns of a
database created by an older shape of this script.

## CLI

```bash
BRAIN="python .claude/hooks/cc-agent-brain/brain_store.py"

$BRAIN init
$BRAIN stats
$BRAIN event --kind user --content "..."
$BRAIN memory add --title "..." --body "..." \
    --layer semantic --confidence high --tags "a,b" --source wiki/x.md
$BRAIN memory add ... --supersedes m-xxxx
$BRAIN memory expire m-xxxx
$BRAIN memory list
$BRAIN search "查询词" --k 8 [--layer semantic] [--human]
$BRAIN candidates --days 3
$BRAIN audit
$BRAIN timeline --limit 15
$BRAIN sync-md
$BRAIN redact --content "..."
```

Commands print JSON. `search --human` prints plain text for the Claude Code hook. `redact` prints the redacted string.

`search` accepts a query string, `--k`, and `--layer`. It has no timestamp
argument. `timeline --limit` slices the newest rows by `updated_at`.

## Retrieval

1. Free text is tokenized into Latin words (length at least 2) and Chinese
   bigrams. Index writes and `MATCH` queries use that same tokenizer. FTS5
   `unicode61` is not asked to segment CJK.
2. Active memories (`status='active'`, optional layer) and events are each
   ordered by FTS5 `bm25()`.
3. Those lists go through `rrf_fuse` (`k=60` in the fusion formula, `top_n`
   equal to the requested result count). The lists are lexical. `search` never
   builds a vector, never calls an embedding model, and never passes a
   non-FTS ranked list. Vector search is not implemented. The global file,
   when present, contributes two more lexical lists to the same fusion. It is
   not a fallback that runs only when the project lists are empty.
4. Superseded, expired, and archived memories are absent from `memories_fts`,
   so they do not appear in `search`. Their table rows remain readable via
   `memory list` and `timeline`.

## Validity columns and as-of queries

`valid_from` / `valid_to` and `created_at` / `updated_at` are stored.
`search`, `stats`, and `timeline` do not interpret them as a historical
snapshot. There is no as-of query.

## Secret redaction

`add_event` and `add_memory` run `redact()` unless the caller disables it.
Patterns cover common OpenAI, Anthropic, GitHub, AWS, and Google key shapes,
JWTs, Bearer tokens, PEM private keys, and `password=` / `api_key=` style
assignments. Matches become `[REDACTED:kind]`. This is pattern replacement on
the string being written. It does not scan the database later, and it does not
cover every secret.

## Backup

The database is one SQLite file in WAL mode. Copy the file to keep a backup.
Delete it to drop the project store. `installer/uninstall.py` does not remove
it. `installer/install.py` does not replace it when it already exists.
