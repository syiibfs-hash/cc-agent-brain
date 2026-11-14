# Local memory engine

`package/claude/hooks/cc-agent-brain/brain_store.py` uses the Python standard
library (`sqlite3`) only. Nothing in this file imports a third-party package
or opens a network connection.

## Database files

| How you select it | Path | Who writes it |
|-------------------|------|----------------|
| default (hooks and plain CLI) | `.cc-agent-brain/brain.db` under the current working directory | Claude Code hooks and any CLI call without `--global` |
| `--global` | `<global-dir>/brain.db` | CLI and `serve-mcp` you point at that file |
| shared Markdown | `<global-dir>/library.md` | rewritten when the open database is that global file |

`<global-dir>` is `--global-dir`, otherwise the `CC_AGENT_BRAIN_GLOBAL_DIR`
environment variable, otherwise `~/.cc-agent-brain`. An explicit `--db` names
one SQLite file and wins over `--global`. The project file stays
`.cc-agent-brain/brain.db`. It is not the global file.

The default directory is the historical global DB path, so `--global` and the
search fusion below keep one location. `library.md` sits next to `brain.db`.
Moving the directory moves both files. The same directory is what you point
every MCP client at when they should share one library on this machine.

`library.md` is rebuilt from active memories (title, body, writer, source)
and from event and memory counts. Event text is not copied into it.
`sync-md` on a project database still writes `memory/brain-index.generated.md`.
`sync-md --global` writes `library.md`.

`search` always queries the database you opened. It also opens the global path
when that file exists and is not the same file, and fuses the extra lexical
lists with RRF. Hooks never pass `--global`, and the installer does not create
the global directory or retarget the three project MCP entries at it. There
is no daemon and no cross-machine sync. Two local processes can open the same
global SQLite file. Each insert stores a writer (below). That string is not
a detected product name.

## Writer

`events.writer` and `memories.writer` are the identity supplied for that insert.

1. Explicit `--writer`, or the `writer` argument on `brain_add_memory`.
2. Else `CC_AGENT_BRAIN_WRITER`.
3. Else `unspecified`.

Claude Code hooks pass `claude-code` when `CC_AGENT_BRAIN_WRITER` is unset.
That default names the hook code path. It is not a guess about Cursor or
Codex. `source` stays a provenance string (`prompt_capture`, `transcript`,
`mcp`, a wiki path). `search`, `timeline`, and `stats` (`events_by_writer`,
`memories_by_writer`) return the stored value. `_migrate` adds the column
when it is missing. Rows already in the file keep `''`.

## Tables

- `events` — insert-only rows (`kind`: `user` / `assistant` / `tool` / `system`),
  mirrored into `events_fts` (FTS5) at insert time.
- `memories` — rows with status, layer, and validity columns, mirrored into
  `memories_fts` while `active`. A non-active status deletes the FTS row and
  keeps the table row.
- `meta` — `schema_version` (`"2"`), inserted once.

`_migrate` uses `CREATE TABLE IF NOT EXISTS`. It also runs
`ALTER TABLE ... ADD COLUMN writer` when that column is missing. It does not
replace or delete the database file. Legacy `initialize` still advertises
schema id `"2"` in `serverInfo.version`.

## CLI

```bash
BRAIN="python .claude/hooks/cc-agent-brain/brain_store.py"

$BRAIN init
$BRAIN stats
$BRAIN event --kind user --content "..." --writer "claude-code"
$BRAIN memory add --title "..." --body "..." \
    --layer semantic --confidence high --tags "a,b" --source wiki/x.md \
    --writer "claude-code"
$BRAIN --global-dir ~/.cc-agent-brain --global memory add --title "..." --body "..."
$BRAIN memory add ... --supersedes m-xxxx
$BRAIN memory expire m-xxxx
$BRAIN memory list
$BRAIN search "查询词" --k 8 [--layer semantic] [--human]
$BRAIN candidates --days 3
$BRAIN audit
$BRAIN timeline --limit 15
$BRAIN sync-md                                # project DB → memory/brain-index.generated.md
$BRAIN --global sync-md                       # global DB → <global-dir>/library.md
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
