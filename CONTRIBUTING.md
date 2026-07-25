# Contributing

Thanks for considering it. This project is small enough that a good issue is as useful as a patch.

## Setup

```sh
git clone https://github.com/Falcon305/coursebrain
cd coursebrain
uv venv --python 3.12
uv pip install -e ".[rag]" --group dev
pre-commit install
```

Then confirm it works:

```sh
pytest
ruff check .
mypy
```

## Before you open a pull request

- `pytest` passes.
- `ruff check .` and `ruff format --check .` are clean. Pre-commit runs both; CI runs them without
  `--fix`, so fix locally.
- `mypy` is clean on `src/coursebrain`.
- New behaviour has a test. Bug fixes get a test that fails before the fix.
- `CHANGELOG.md` has an entry under `## [Unreleased]` if the change is user-visible.

## Where things live

```
src/coursebrain/stages/    fetch -> normalize -> segment -> distill -> index -> verify
src/coursebrain/profiles/  note schemas, one YAML file per domain
src/coursebrain/prompts/   the distillation prompt
tests/
```

Each stage reads and writes disk and skips work already done, so re-running is cheap. Keep it that
way — a stage that is not idempotent breaks resumability for everyone with a 200-episode course.

## Things worth knowing before you change them

**`normalize.py` is the highest-bug-density file in the project.** YouTube auto-captions use a
rolling window that repeats each line across consecutive cues, plus inline `<c>` timing tags.
Changes there need tests against realistic fixtures, not hand-simplified ones — a simplified
fixture will pass while real captions break.

**`manifest.json` deliberately contains no timestamps.** That is what makes the determinism check
possible: re-run the pipeline and get a byte-identical manifest. Do not add a `completed_at`.

**Frontmatter is generated mechanically, never by a model.** Models write note bodies only. Quote
YAML values that would otherwise be misread — an unquoted `15:30` parses as the integer 930, which
silently broke a validation check once already.

**Anything irreplaceable is committed; anything derivable is ignored.** Raw captions are committed
on purpose, because videos get deleted and the captions go with them. Indexes rebuild offline.

## Adding a domain profile

Profiles are data, not code. Copy `src/coursebrain/profiles/general.yaml`, change the sections, and
that is the whole change. Good profiles are specific about what belongs in each section and honest
about which sections may be omitted.

## Adding an ingest source

Sources are discovered through the `coursebrain.sources` entry point group, so they can live in
your own package:

```toml
[project.entry-points."coursebrain.sources"]
vimeo = "coursebrain_vimeo:VimeoSource"
```

Implement the `Source` protocol and use `coursebrain/sources/youtube.py` as the reference. If a
source cannot supply timestamps, say so — the provenance model assumes citations are checkable, and
silently emitting uncheckable ones is worse than emitting none.

## Reporting bugs

Include the course profile, the command you ran, and whether captions were manual or
auto-generated. `coursebrain doctor` output covers most of the environment questions.
