# sum-ai

Turns long-form video into a durable knowledge base that coding agents and humans can both read.

Point it at a YouTube playlist, a channel, or a single three-hour lecture. It pulls transcripts,
distills them into structured markdown notes with timestamp links back to the source, and builds a
hybrid keyword + semantic index over the result. Notes live in git, so the knowledge survives the
video being taken down and travels to anyone who clones the repo.

Domain-general by design. A programming series, a university course, a language course and a
writing course each get a note schema that suits them, set by the course's `profile`. Craft domains
additionally emit a style guide an agent can actually write by, not just a summary.

## Status

Early. The fetch and normalize stages work; distillation and retrieval are in progress.

## Layout

```
pipeline/           stages, retrieval, cli
courses/<id>/       one course: config, raw captions, transcripts, notes, indexes
tests/
```

Within a course, anything irreplaceable is committed and anything derivable is ignored. Raw captions
are committed on purpose: videos get deleted, and once the captions are gone they are gone. Indexes
are rebuildable offline with no API key.

## Setup

```sh
uv venv --python 3.12
uv pip install -e ".[dev]"
```

Optional extras: `rag` for semantic search, `orchestration` for durable resume, `obs` for tracing.

## Usage

```sh
course init <id> <url> --profile programming
course build <id>
course ask "how does revalidation work"
```

## Requirements

Python 3.12+, `yt-dlp`, and an `ANTHROPIC_API_KEY` for the distillation step. Everything else is
optional.
