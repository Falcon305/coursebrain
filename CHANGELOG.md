# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Workspace resolution: `COURSEBRAIN_HOME`, else the nearest ancestor containing `courses/` or
  `.coursebrain/`, else the working directory. An installed tool no longer writes into its own
  package directory.
- `coursebrain.sources` entry point group so third parties can add ingest sources.
- MIT licence, changelog, contributing guide, and PyPI-grade project metadata.

### Changed
- **Breaking:** the Python package is now `coursebrain`, not `pipeline`. `import pipeline` was
  far too generic for a published library and would collide with unrelated packages.
- Project layout moved to `src/`, so tests run against the installed package rather than the
  working tree.
- The CLI is `coursebrain`, with `brain` as a shorter alias.

### Removed
- Dead path helpers left behind by the move to sqlite-vec (`lancedb`, `checkpoints`) and the
  unbuilt synthesis/style outputs, which capability packs replace.

## [0.1.0] - unreleased

First release. Ingests a YouTube video, playlist, or channel; distills each episode into a
structured markdown note with timestamp links back to the source; and searches across every course
with hybrid keyword and semantic retrieval.

- Domain profiles (`programming`, `academic`, `writing`, `language`, `general`) that each set their
  own note schema.
- Distillation runs inside Claude Code with no API key, or unattended through the Anthropic API.
- Keyword (FTS5/BM25) and semantic (sqlite-vec) search in a single SQLite file, fused with
  Reciprocal Rank Fusion.
- `verify` for structural checks and `eval` for scoring retrieval against a question set.
- Raw captions are committed alongside notes, so a course survives its videos being taken down.
