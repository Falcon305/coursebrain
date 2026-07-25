# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`method` capability kind** — a fourth compositional layer for courses that teach *how to
  do the work* rather than what is true, how to write, or in which language. Precedence is
  stated: style never overrides a procedure that exists for a reason.
- Four profiles: `craft` (hands-on skills, `method`), `method` (processes and systems,
  `method`), `design` (visual and interaction design, `voice`), and `business` (`domain`).
  Nine ship in total.
- `coursebrain compose --method/-m` for the new layer.
- Agent-followable setup instructions in the README, so pasting the repository URL into a
  coding agent is enough to get installed and configured.
- `scripts/bootstrap.sh` installs from GitHub and works without a clone.
- Documentation site at <https://falcon305.github.io/coursebrain/>, built with mkdocs-material
  and deployed from CI. Builds run on pull requests too, so a broken link fails review.

### Changed
- Course libraries (`courses/`, `BRAIN.md`, generated skills) are no longer tracked. They
  contain captions from third-party videos; the repository ships the tool, not a library.
- The ASR regression fixture reproduces real YouTube caption structure byte for byte with
  substituted words, so no third-party transcript is redistributed.

## [0.1.0] - 2026-07-25

First release. Ingests a YouTube video, playlist, or channel; distills each episode into a
structured markdown note with timestamp links back to the source; searches across every course
with hybrid retrieval; and compiles courses into skills that compose with one another.

### Composition

- **Capability packs.** `coursebrain compile` turns a course's notes into a short, prescriptive
  pack — what a reader needs in order to *act*, rather than an archive of what was said. Packs
  carry a `kind` (`domain`, `voice`, `language`) that decides how they stack.
- **`coursebrain skill`** exports a course as a Claude Code skill, with the frontmatter
  `description` written as a routing rule so the model can decide when to load it.
- **`coursebrain compose`** merges several packs into one context pack and states the precedence
  for conflicts: language governs surface, voice governs form, domain governs content, and
  accuracy outranks style.

### Ingest and retrieval

- Domain profiles (`programming`, `academic`, `writing`, `language`, `general`), each with its
  own note schema and compilation guidance.
- Distillation runs inside Claude Code with no API key, or unattended through the Anthropic API.
- Keyword (FTS5/BM25) and semantic (sqlite-vec) search in a single SQLite file, fused with
  Reciprocal Rank Fusion.
- Parallel episode fetching.
- Source plugins via the `coursebrain.sources` entry point group, with YouTube as the built-in
  reference implementation.
- `verify` for structural checks and `eval` for scoring retrieval against a question set.
- Raw captions are committed alongside notes, so a course survives its videos being taken down.

### Interface

- Typer + Rich CLI: progress during fetch, `--json` on read commands, shell completion, and
  errors that name their fix.
- `coursebrain doctor` checks the environment and prints the exact command for anything broken.
- `coursebrain learn` collapses create-and-stage into one step.
- Claude Code plugin with `/learn` and `/compose`, a bundled knowledge skill, and a
  SessionStart check for a missing CLI.

### Notes on design

- The Python package is `coursebrain`, in a `src/` layout. An earlier top-level `pipeline`
  package would have collided with unrelated installs.
- Workspace resolution: `COURSEBRAIN_HOME`, else the nearest ancestor containing `courses/` or
  `.coursebrain/`, else the working directory. An installed tool never writes into its own
  package directory.
- `manifest.json` carries no wall-clock timestamps, so a re-run produces a byte-identical file
  and determinism is checkable.
