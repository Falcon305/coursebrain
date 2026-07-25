<p align="center">
  <img src="assets/banner.svg" alt="coursebrain — your agent doesn't search your playlists, it studied them" width="100%">
</p>

<p align="center">
  <a href="https://github.com/Falcon305/coursebrain/actions/workflows/ci.yml"><img src="https://github.com/Falcon305/coursebrain/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://falcon305.github.io/coursebrain/"><img src="https://img.shields.io/badge/docs-live-2dd4bf" alt="Documentation"></a>
  <img src="https://img.shields.io/badge/python-3.12%20|%203.13-blue" alt="Python 3.12 | 3.13">
  <img src="https://img.shields.io/badge/mypy-strict-brightgreen" alt="mypy strict">
  <img src="https://img.shields.io/badge/API%20key-not%20required-2dd4bf" alt="No API key required">
  <img src="https://img.shields.io/badge/licence-MIT-blue" alt="MIT licence">
</p>

<p align="center">
  <b><a href="https://falcon305.github.io/coursebrain/">Docs</a></b> ·
  <a href="https://falcon305.github.io/coursebrain/getting-started/">Getting started</a> ·
  <a href="https://falcon305.github.io/coursebrain/composition/">How composition works</a> ·
  <a href="https://falcon305.github.io/coursebrain/plugins/">Write a plugin</a>
</p>

<h3 align="center">Point it at 20 playlists about one subject.<br>Your agent doesn't search them — it studied them.</h3>

<p align="center">
  <sub>Cited notes with timestamps → compiled into Claude Code skills → applied without being asked.<br>
  No API key. The agent does the studying.</sub>
</p>

---

## The problem

There are hundreds of hours of genuinely good material on your subject sitting on YouTube, and
your agent has watched none of it.

**Retrieval does not fix this.** Ask a RAG system a question and it hands you a passage someone
said once. It cannot tell you which of two contradictory episodes to trust, or that the
instructor spent four minutes explaining why the obvious approach is wrong, or that the step
everybody skips is the one that matters. A quote is not judgement.

Someone who *studied* the material has judgement. They know what's load-bearing, what the traps
are, and what to do differently because of it. That knowledge is integrated — it stopped being
a set of quotes and became a way of working.

## The solution

Two artefacts, and the difference between them is the whole design.

|  | **Note** | **Capability pack** |
| --- | --- | --- |
| Answers | *"What did episode 7 say?"* | *"What does someone who studied this know?"* |
| Shape | Archive, timestamped, searchable | Instrument, prescriptive, ~500 words |
| Produced by | Reading one episode | Reading **every** note at once |
| Good for | Checking a claim, citing a source | Doing the work |
| Loads into your agent | On request | **Automatically, when relevant** |

A pack becomes a Claude Code skill. Your agent holds it, and applies it without being asked —
because that is what skills do.

```
playlists ──▶ transcripts ──▶ cited notes ──▶ capability pack ──▶ SKILL.md
                                  │                                    │
                          search when you                    applied automatically,
                            need a source                     composes with others
```

## Features

<table>
<tr><td width="50%" valign="top">

**📌 Cited by construction**

Every claim carries a video ID and timestamp. What the source didn't say doesn't appear — and
gaps are recorded *as gaps*, not silently omitted.

</td><td width="50%" valign="top">

**🧠 Compiled, not retrieved**

Nothing is fetched at answer time. Expertise is compiled ahead into skills the agent already
carries. Search is the fallback, not the product.

</td></tr>
<tr><td valign="top">

**🧩 Composes across subjects**

Four layers — what's true, how to do it, how it should read, what language. Stack them, with
stated precedence when they conflict.

</td><td valign="top">

**📈 Compounds**

Add a playlist, the skills deepen. Point it at one subject long enough and notes become
competence.

</td></tr>
<tr><td valign="top">

**🔍 Hybrid search**

BM25 and semantic vectors in **one SQLite file**, fused with Reciprocal Rank Fusion. No second
store to keep in sync.

</td><td valign="top">

**🎬 Honest about video**

Diagrams and silent on-screen code become timestamped *visual blind spots* — an explicit work
list, never a pretence of coverage.

</td></tr>
<tr><td valign="top">

**🧪 Measurable**

`verify` catches structural problems; `eval` scores retrieval against a question set, so tuning
is measured rather than guessed.

</td><td valign="top">

**🔌 Extensible**

Profiles are YAML. Ingest sources are a four-method protocol registered by entry point — add
Vimeo or podcasts without touching this repo.

</td></tr>
</table>

## Set it up

**Easiest: hand this page to your agent.** Paste the repository URL into Claude Code and say
*"set this up"*. Everything it needs is below.

<!-- AGENT SETUP: follow these steps verbatim. -->

> ### Instructions for a coding agent
>
> **Step 1 — install the CLI.** `uv` is the only prerequisite; if missing, install it with
> `curl -LsSf https://astral.sh/uv/install.sh | sh`.
>
> ```sh
> uv tool install "coursebrain[rag] @ git+https://github.com/Falcon305/coursebrain"
> coursebrain doctor
> ```
>
> `doctor` prints a checklist and the exact fix for anything broken. Do not continue past a
> failing check — resolve it and re-run.
>
> **Step 2 — install the Claude Code plugin**, which adds `/learn` and `/compose`:
>
> ```
> /plugin marketplace add Falcon305/coursebrain
> /plugin install coursebrain
> ```
>
> **Step 3 — choose where courses live.** Ask the user which they want, then confirm it back:
>
> - **Globally** — one library shared by every project:
>   ```sh
>   echo 'export COURSEBRAIN_HOME="$HOME/.coursebrain"' >> ~/.zshrc   # or ~/.bashrc
>   mkdir -p ~/.coursebrain/courses
>   ```
>   Export skills with `--scope user` so they load everywhere.
>
> - **Locally** — courses belong to this project and are committed with it:
>   ```sh
>   mkdir -p courses
>   ```
>   Nothing else to configure: `coursebrain` walks up from the working directory looking for a
>   `courses/` folder.
>
> **Step 4 — confirm** with `coursebrain doctor` and `coursebrain profiles`, then tell the user
> what to run next.

<details>
<summary><b>Prefer to do it yourself?</b></summary>

<br>

```sh
uv tool install "coursebrain[rag] @ git+https://github.com/Falcon305/coursebrain"
coursebrain doctor
```

`[rag]` adds semantic search — about 100 MB (sqlite-vec plus static embeddings, **no PyTorch**).
Without it everything still works on keyword search, and `doctor` says so rather than failing
mysteriously.

Set `COURSEBRAIN_HOME` for one shared library, or make a `courses/` directory inside a project
for a local one.
</details>

## Study a subject

```sh
coursebrain learn "https://www.youtube.com/playlist?list=PLxxxx" \
    --id quant --profile business
```

One video or two hundred, same command. Transcripts are fetched in parallel and staged as one
task per episode.

In Claude Code, the agent does the whole loop:

```
/learn https://www.youtube.com/playlist?list=PLxxxx
```

Then file the notes and make them searchable:

```sh
coursebrain assemble quant
coursebrain index
coursebrain ask "how do I avoid overfitting a backtest"
```

```
╭─ 1. quant ep06 · Decisions & rationale ─────────────────────────────╮
│ A backtest is a tool to reject a strategy, not to accept one. If it │
│ struggled in the backtest it will almost certainly struggle live…   │
╰─ https://youtu.be/lshC1wmOcjA?t=814   [keyword+vector]  ────────────╯
```

Now compile it into something the agent *applies*:

```sh
coursebrain compile quant          # every note → one capability pack
coursebrain compile-assemble quant
coursebrain skill quant            # → .claude/skills/quant/SKILL.md
```

Add more playlists on the same subject and recompile. The pack deepens.

## Composing several subjects

Real work usually needs more than one kind of knowing at once. Packs carry a `kind` that decides
how they stack:

| kind | from profiles | governs |
| --- | --- | --- |
| `domain` | programming, academic, business, general | what is true and worth saying |
| `method` | craft, method | how to do the work — steps, technique, checks |
| `voice` | writing, design | how the output is shaped |
| `language` | language | which language and register |

```sh
coursebrain compose --about quant --method research-process --voice prose-craft \
    --task "write the strategy section"
```

They work at different layers, so they stack rather than fight. Where they collide, `compose`
states the precedence — language governs surface, voice governs form, method governs process,
domain governs content, and **accuracy outranks style**.

Nine profiles ship, covering software, lectures, business, writing, design, languages, hands-on
skills, and processes. Adding one is a YAML file.

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

## Honest limits

**Notes cover what the speaker said.** Diagrams, slides, and silent on-screen code are not
captured. They are logged as timestamped *visual blind spots* — an explicit work list rather
than a quiet omission.

**Auto-generated captions mangle names and identifiers.** Notes mark transcript-derived content
as such and flag what could not be recovered rather than guessing.

**An episode with no captions is skipped, loudly.** It appears in the manifest as skipped and is
never invented.

**Your courses stay yours.** `courses/` is gitignored, because it holds captions from
third-party videos. This repository ships the tool, not anyone's library.

## Contributing

Profiles are data. Sources are a small protocol. See [CONTRIBUTING.md](CONTRIBUTING.md) and the
[plugin guide](https://falcon305.github.io/coursebrain/plugins/).

```sh
git clone https://github.com/Falcon305/coursebrain && cd coursebrain
uv venv --python 3.12 && uv pip install -e ".[rag]" --group dev
pytest && ruff check . && mypy
```

## Licence

MIT — see [LICENSE](LICENSE).
