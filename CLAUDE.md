# sum-ai

Distills long-form video into markdown notes an agent can search and cite. See `SKILL.md` for how
to query the knowledge; `BRAIN.md` lists every course.

## Working on the pipeline

```sh
uv pip install -e ".[dev]"      # core; add [rag] for semantic search
.venv/bin/python -m pytest      # must stay green
```

Stages live in `pipeline/stages/` and run in order: fetch → normalize → segment → distill → index
→ verify. Each reads and writes disk and skips work already done, so re-running is cheap.

**Distillation has two paths.** Agent mode (`prepare` → agent writes bodies → `assemble`) is the
default and needs no API key — inside Claude Code the agent *is* the model. `build` is the
unattended API path for running outside an agent session. Both converge on the same
`render_note()`, so notes are identical whichever produced them.

## Conventions that matter

**Anything irreplaceable is committed; anything derivable is ignored.** Raw captions under
`courses/*/raw/` are committed on purpose — videos get deleted, and once the captions are gone they
are gone. Indexes under `.brain/` are ignored and must stay rebuildable offline with no API key.

**`manifest.json` contains no wall-clock timestamps.** That is deliberate: it makes the determinism
check possible (re-run the pipeline, get a byte-identical manifest). Langfuse holds timing. Don't
add a `completed_at`.

**Note schemas come from `pipeline/profiles/*.yaml`, not code.** Adding a domain is a YAML file.
Changing a profile's sections invalidates nothing automatically — existing notes keep their old
shape until re-distilled.

**The distill prompt version is part of the cache key.** Editing `pipeline/prompts/distill.md`
invalidates distillations and nothing else. Fetching and normalizing stay cached.

**`normalize.py` is the highest-bug-density file.** YouTube auto-captions use a rolling window that
repeats each line across consecutive cues, plus inline `<c>` timing tags. Changes there need tests
against realistic fixtures, not hand-simplified ones.

**Frontmatter is generated mechanically, never by the model.** The model writes the body only. Quote
values that YAML would misread — an unquoted `15:30` parses as the integer 930.

**Keyword and vector indexes share one SQLite file.** That was a deliberate move away from a
separate vector store: one file means no sync problem and nothing to corrupt independently.
Embeddings are static (model2vec, no PyTorch), so `course index` runs offline in seconds.

## Cost

Distillation is the only paid step. Roughly $10–15 for a 30-episode course, cached afterwards.
Embeddings run locally and are free. Use `--fetch-only` to build transcripts without spending.
