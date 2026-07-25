# coursebrain

**Learn from long-form video, then write from what you learned.**

Point it at a YouTube course. It pulls transcripts, distills each episode into structured
markdown notes with timestamp links back to the source, and builds a hybrid keyword +
semantic index over the result.

Then the part that makes it more than a note-taker: each course **compiles into a skill**.
Feed it a Spanish course, a programming course, and a writing course, and it can write
about the programming — in Spanish, in that register, following that craft guidance. Three
courses, one piece of output, because the packs are built to stack.

**No API key.** Inside Claude Code the agent does the distilling, so there is nothing to
pay for beyond what you are already running.

## Install

As a Claude Code plugin:

```
/plugin marketplace add Falcon305/coursebrain
/plugin install coursebrain
```

Then install the CLI the commands call:

```sh
uv tool install "coursebrain[rag]"
coursebrain doctor
```

`doctor` checks everything and prints the exact fix for anything broken. The `rag` extra
adds semantic search (~100 MB — sqlite-vec plus static embeddings, no PyTorch). Without it
everything still works on keyword search.

## Use

```
/learn https://youtube.com/playlist?list=...
/compose an explainer about monads, in Spanish, using the prose course
```

Or from the shell:

```sh
coursebrain learn <url> --profile programming   # fetch + stage
coursebrain assemble <id>                       # notes
coursebrain index                               # searchable
coursebrain ask "how does revalidation work"    # cited answers

coursebrain compile <id>                        # notes -> capability pack
coursebrain skill <id>                          # pack -> Claude Code skill
coursebrain compose -a monads -v prose -L spanish -t "explain it simply"
```

A single video and a 200-video playlist are the same command.

## How it works

```
video ──▶ transcripts ──▶ notes            deep, cited, searchable
                            │
                            ▼
                       capability pack     applicable, ~500 words
                            │
                            ▼
                       SKILL.md            composes with other courses
```

A **note** answers *"what did episode 7 say?"*. A **capability pack** answers *"how do I
write like this?"* — prescriptive, self-contained, useless as an archive. Only the second
composes, which is the point.

Packs carry a `kind` that decides how they stack:

| kind | from profiles | governs |
|---|---|---|
| `domain` | programming, academic, general | what is true and worth saying |
| `voice` | writing | how the prose moves |
| `language` | language | which language and register |

They work at different layers, so they mostly stack rather than fight. Where they do
collide, `compose` states the precedence — language governs surface, voice governs form,
domain governs content, and accuracy outranks style.

## Retrieval

Keyword (SQLite FTS5, BM25) and semantic (sqlite-vec) search run together, fused with
Reciprocal Rank Fusion. Both indexes live in **one SQLite file**, so there is no second
store to keep in sync.

Semantic search earns its place on vocabulary mismatch: *"how do I deal with stale data"*
finds a section titled **Revalidation** that keyword search misses entirely. That case is a
regression test.

`coursebrain eval <id>` scores retrieval against a question set, so tuning is measured
rather than guessed. Write the questions before you tune.

## Extending it

Sources and profiles are plugins. A profile is a YAML file. A source is a class registered
through an entry point:

```toml
[project.entry-points."coursebrain.sources"]
vimeo = "coursebrain_vimeo:VimeoSource"
```

Implement `matches`, `enumerate`, `fetch`, and `subtitle_path`, using
`src/coursebrain/sources/youtube.py` as the reference. See [CONTRIBUTING.md](CONTRIBUTING.md).

## What it does not do

Notes cover what the speaker **said**. Diagrams, slides, and on-screen code with no
narration are not captured — they are logged as timestamped **visual blind spots** rather
than silently omitted, which doubles as the work list for a later visual pass.

Auto-generated captions mangle identifiers and proper nouns. Notes mark transcript-derived
content as such and flag what could not be recovered. Do not treat a note as authoritative
for exact code; that is what the companion repository is for.

## Layout

```
src/coursebrain/     stages, retrieval, capability, cli
courses/<id>/        config, raw captions, transcripts, notes, CAPABILITY.md
commands/ skills/    the Claude Code plugin
```

Within a course, anything irreplaceable is committed and anything derivable is ignored. Raw
captions are committed on purpose: videos get deleted, and the captions go with them.

## Licence

MIT.
