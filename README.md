# coursebrain

Turns long-form video into a durable knowledge base that coding agents and humans can both read.

Point it at a YouTube video, playlist, or channel. It pulls transcripts, distills them into
structured markdown notes with timestamp links back to the source, and builds a hybrid keyword +
semantic index over the result. Notes live in git, so the knowledge survives the video being taken
down and travels to anyone who clones the repo.

Domain-general by design. A programming series, a university course, a language course and a
writing course each get a note schema that suits them, set by the course's `profile`.

**No API key required.** Inside Claude Code, the agent does the distilling — run `/learn <url>`.
There is an optional unattended path through the Anthropic API for running outside an agent
session, but it is not the default.

## Setup

```sh
uv venv --python 3.12
uv pip install -e ".[dev,rag]"
```

`rag` adds semantic search (~100 MB: sqlite-vec plus static embeddings, no PyTorch). Without it
everything still works on keyword search alone.

## Use

In Claude Code:

```
/learn https://youtube.com/playlist?list=...
```

Or by hand:

```sh
course init <id> <url> --profile programming
course prepare <id>          # stages one task file per episode
# read each .task.md, write the note body to the .body.md path it names
course assemble <id>         # bodies -> notes, frontmatter added mechanically
course index                 # INDEX.md, CONCEPTS.md, BRAIN.md, search index
course verify <id>           # structural check
course ask "how does revalidation work"
```

A single video and a 200-video playlist are the same command.

## Layout

```
pipeline/           stages, retrieval, cli
courses/<id>/       config, raw captions, transcripts, notes, evals
.claude/            the /learn command and the course-knowledge skill
tests/
```

Within a course, anything irreplaceable is committed and anything derivable is ignored. Raw
captions are committed on purpose: videos get deleted, and once the captions are gone they are
gone. Indexes live in `.brain/` and rebuild offline with no API key.

## Retrieval

Keyword (SQLite FTS5, BM25) and semantic (sqlite-vec) search run together and their rankings are
fused with Reciprocal Rank Fusion. Both indexes live in **one SQLite file**, so there is no second
store to keep in sync.

Semantic search earns its place on vocabulary mismatch — "how do I deal with stale data" finds a
section titled *Revalidation* that keyword search misses entirely. That case is a regression test
(`tests/test_vectors.py`).

`course eval <id>` scores retrieval against a question set so changes are measured rather than
guessed. Write the questions before tuning.

## Requirements

Python 3.12+ and `yt-dlp`. An `ANTHROPIC_API_KEY` is needed only for the optional `course build`
path.
