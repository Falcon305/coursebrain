<p align="center">
  <img src="assets/banner.svg" alt="coursebrain — learn from long-form video, then write from what you learned" width="100%">
</p>

<p align="center">
  <a href="https://github.com/Falcon305/coursebrain/actions/workflows/ci.yml"><img src="https://github.com/Falcon305/coursebrain/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.12%20%7C%203.13-blue" alt="Python 3.12 | 3.13">
  <img src="https://img.shields.io/badge/mypy-strict-brightgreen" alt="mypy strict">
  <img src="https://img.shields.io/badge/licence-MIT-blue" alt="MIT">
</p>

---

**Throw a link at it.** A video, a playlist, a whole channel — coursebrain pulls the
transcripts, turns each episode into structured notes with timestamps back to the source,
and makes the lot searchable.

Then the part that makes it more than a note-taker: **courses compile into skills, and
skills compose**. Give it a Spanish course, a programming course, and a writing course, and
it will explain the programming — in Spanish, in that register, following that craft.

> **No API key.** Inside Claude Code the agent does the distilling, so there is nothing to
> pay for beyond what you are already running.

## Install

```sh
uv tool install "coursebrain[rag]"
coursebrain doctor
```

`doctor` checks every dependency and prints the exact command to fix anything broken.

As a Claude Code plugin, for the `/learn` and `/compose` commands:

```
/plugin marketplace add Falcon305/coursebrain
/plugin install coursebrain
```

<details>
<summary>What is the <code>rag</code> extra?</summary>

Semantic search — about 100 MB (sqlite-vec plus static embeddings, **no PyTorch**). Without
it everything still works on keyword search alone, and `doctor` says so rather than failing
mysteriously.
</details>

## Use it

### 1. Point it at something

```sh
coursebrain learn "https://www.youtube.com/playlist?list=PLxxxx" \
    --id react --profile programming
```

One video or two hundred, same command. Pick the profile that fits the material —
`programming`, `academic`, `writing`, `language`, or `general`.

This fetches transcripts in parallel and stages one task file per episode.

### 2. Write the notes

Each staged task holds the instructions, the note schema, and the transcript with `[M:SS]`
markers. Read it, write the note body to the path it names.

In Claude Code this is one command and the agent does all of it:

```
/learn https://www.youtube.com/playlist?list=PLxxxx
```

Then file them:

```sh
coursebrain assemble react
```

### 3. Ask it things

```sh
coursebrain index
coursebrain ask "how do I stop stale data being served"
```

```
╭─ 1. react ep07 · Concepts > Revalidation ──────────────────────╮
│ Serve the cached copy immediately, then refresh in the         │
│ background so the next request is fresh…                       │
╰─ https://youtu.be/VIDEOID?t=289   [keyword+vector]  ───────────╯
```

Keyword and meaning search run together, so a question phrased nothing like the notes still
finds them. Every hit carries a timestamp link straight to the moment.

### 4. Turn a course into a skill

```sh
coursebrain compile react            # notes -> capability pack
coursebrain compile-assemble react
coursebrain skill react              # -> .claude/skills/react/SKILL.md
```

Now Claude Code loads it whenever it is relevant. Do this for several courses and they
combine:

```sh
coursebrain compose --about react --voice prose-craft --lang spanish \
    --task "explain revalidation to a beginner"
```

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
composes, and that distinction is the whole design.

Packs carry a `kind` that decides how they stack:

| kind | from profiles | governs |
| --- | --- | --- |
| `domain` | programming, academic, general | what is true and worth saying |
| `voice` | writing | how the prose moves |
| `language` | language | which language and register |

They work at different layers, so they stack rather than fight. Where they do collide,
`compose` states the precedence: language governs surface, voice governs form, domain
governs content, and accuracy outranks style.

## Commands

| | |
| --- | --- |
| `learn <url>` | Create a course and stage its transcripts |
| `assemble <id>` | Turn written bodies into notes |
| `index` | Rebuild the indexes and `BRAIN.md` |
| `ask <query>` | Hybrid search across every course |
| `compile <id>` | Notes → capability pack |
| `skill <id>` | Pack → Claude Code skill |
| `compose` | Merge several courses into one context pack |
| `verify [id]` | Structural check; non-zero exit on problems |
| `eval [id]` | Score retrieval against a question set |
| `doctor` | Check the setup and name the fix for anything broken |

`--help` on anything. `--json` on every read command, for scripting.

## Extending it

Profiles are YAML. Sources are a four-method protocol registered through an entry point:

```toml
[project.entry-points."coursebrain.sources"]
vimeo = "coursebrain_vimeo:VimeoSource"
```

`src/coursebrain/sources/youtube.py` is the reference implementation.

## Honest limits

Notes cover what the speaker **said**. Diagrams, slides, and silent on-screen code are not
captured — they are logged as timestamped *visual blind spots* rather than quietly dropped,
which doubles as the work list for a later visual pass.

Auto-generated captions mangle identifiers and proper nouns. Notes mark transcript-derived
content as such and flag what could not be recovered.

Your courses stay yours: `courses/` is gitignored, because it holds captions from
third-party videos. This repository ships the tool, not anyone's library.

## Licence

MIT.
