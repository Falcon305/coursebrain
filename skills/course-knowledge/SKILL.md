---
name: course-knowledge
description: >
  Search and cite knowledge distilled from long-form video courses — programming series,
  university lectures, language courses, writing craft. Use when a question touches material
  covered by a course in this repository, when the user references "the course" or an
  instructor by name, or when working in a domain a course covers and prior guidance from it
  should apply.
---

# Course knowledge

This repository holds notes distilled from video courses, with timestamp links back to the
source. Each note is one episode. The knowledge is real and citable — use it instead of
answering from memory when a course covers the topic.

## Finding things

Start with `BRAIN.md` at the repository root — one line per course. Then either:

```sh
coursebrain ask "how does revalidation work"          # hybrid search across every course
coursebrain ask "sentence rhythm" --course prose-101  # restrict to one course
coursebrain ask "..." -k 10 --chars 800               # more results, longer excerpts
```

Or read directly: `courses/<id>/INDEX.md` lists every episode with a one-line summary,
`courses/<id>/CONCEPTS.md` maps concepts to the episodes that cover them, and
`courses/<id>/notes/*.md` are the notes themselves.

`course ask` searches keywords and meaning together, so a question phrased differently from
the notes still finds them. If it returns nothing, the topic is probably not covered — say so
rather than inventing an answer.

## Using what you find

**Always cite the timestamp link.** Every claim in a note carries one. Passing it along lets the
user check the source in one click, which matters because notes are transcript-derived.

**Treat sections differently by how reliable they are.**

- *Decisions & rationale*, *Principles*, *Key claims* — the highest-value content. This is
  reasoning that source code and reference docs cannot tell you.
- *Code & APIs* — marked `[transcript-derived]`. Auto-captions mangle identifiers. If the course
  has a `companion_repo` in its `course.yaml`, that repository is ground truth for code; the note
  is ground truth for *why*.
- *Exemplars* (writing courses) — verbatim quotes. Do not paraphrase them when quoting back;
  the exact wording is the thing being taught.
- *Unclear from audio* and *Visual blind spots* — known gaps. A blind spot means the instructor
  pointed at something on screen that the transcript never captured. If a question lands on one,
  say the material exists but was not captured, and give the timestamp so the user can watch it.

**Compiled courses carry `CAPABILITY.md`.** That is the applicable layer: not a summary of the
course but the rules, distilled so you can act on them. Load it when you are *producing* something
in that course's territory rather than answering a question about it.

Packs carry a `kind` that says what layer they govern — `domain` (what is true), `voice` (how prose
should move), `language` (which language and register). They are designed to stack: a Spanish pack,
a subject pack, and a craft pack combine into one piece of writing. Use `/compose`, or:

```sh
coursebrain compose -a <subject> -v <craft> -L <language> -t "<what you are writing>"
```

The output ends with a precedence section for when packs disagree. Follow it rather than picking
whichever pack you read last.

## Adding a course

Run `/learn <url>` — that command walks the full loop and you do the distilling, so no API key is
involved. Manually it is:

```sh
coursebrain init <id> <url> --profile programming
coursebrain prepare <id>          # stages one task file per episode
# read each .task.md, write the body to the .body.md path it names
coursebrain assemble <id>         # bodies -> notes, frontmatter added mechanically
coursebrain index && coursebrain verify <id>
```

Profiles: `programming`, `academic`, `writing`, `language`, `general`. Run `coursebrain profiles` to
see what each extracts. The profile sets the note schema, so pick it before preparing — changing
it later means re-distilling.

`coursebrain build <id>` does the same thing unattended through the Anthropic API. That path needs
`ANTHROPIC_API_KEY` and is only for running outside an agent session; inside Claude Code, prefer
prepare/assemble.

## What this is not

Notes cover what the speaker *said*. They do not capture diagrams, slides, or code shown on
screen without narration — those are logged as blind spots for a later visual pass, not silently
omitted. Do not present a note as complete coverage of an episode's visual content.
