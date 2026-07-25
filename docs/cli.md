# CLI reference

Every command supports `--help`. Read commands support `--json` for scripting.

## Ingest

| Command | What it does |
|---|---|
| `learn <url>` | Create a course and stage its transcripts, in one step |
| `init <id> <url>` | Create a course without fetching |
| `prepare <id>` | Fetch transcripts and stage episodes |
| `pending [id]` | List staged episodes awaiting a note |
| `assemble <id>` | Turn written bodies into finished notes |
| `build <id>` | Unattended end-to-end run through the Anthropic API |

Useful flags: `--limit N` (first N episodes), `--only N` (just episode N), `--workers/-j`
(parallel fetches, default 8), `--force` (redo work already done).

## Capability and composition

| Command | What it does |
|---|---|
| `compile <id>` | Stage a compilation over all the notes |
| `compile-assemble <id>` | Write `CAPABILITY.md` from the compiled body |
| `skill <id>` | Export as a Claude Code skill (`--scope project\|user`) |
| `compose` | Merge packs into one context pack |

```sh
coursebrain compose -a <domain> -v <voice> -L <language> -t "<task>" [-o out.md]
```

## Query

| Command | What it does |
|---|---|
| `index` | Rebuild `INDEX.md`, `CONCEPTS.md`, `BRAIN.md`, and the search index |
| `ask <query>` | Hybrid search across every course |
| `list` | Courses in this workspace |
| `profiles` | Available note schemas |
| `sources` | Installed ingest sources, including plugins |

`ask` takes `-k` (results), `--course/-c` (restrict), `--chars` (excerpt length), and
`--no-vectors` (keyword only).

## Integrity

| Command | What it does |
|---|---|
| `verify [id]` | Structural check; exits non-zero on problems |
| `eval [id]` | Score retrieval against a question set |
| `doctor` | Check the environment and name the fix for anything broken |

`eval <id> --init` writes a starter question set. Write the questions *before* tuning
retrieval, so changes are measured rather than guessed — and use around twenty spanning
several episodes, because a handful cannot discriminate.

## Environment

| Variable | Effect |
|---|---|
| `COURSEBRAIN_HOME` | Workspace location. Otherwise resolved from the working directory. |
| `ANTHROPIC_API_KEY` | Only needed for `build`. |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Optional tracing; no-ops when absent. |
