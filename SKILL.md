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
course ask "how does revalidation work"          # hybrid search across every course
course ask "sentence rhythm" --course prose-101  # restrict to one course
course ask "..." -k 10 --chars 800               # more results, longer excerpts
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

**Style and craft courses carry `STYLE.md`.** When a course's profile is `writing` and the user is
writing something in that domain, load it and follow it. It holds extracted, applicable rules —
not a summary.

## Adding a course

```sh
course init <id> <playlist-or-video-url> --profile programming
course build <id>
course index
course verify <id>
```

Profiles: `programming`, `academic`, `writing`, `language`, `general`. Run `course profiles` to
see what each one extracts. The profile determines the note schema, so pick it before building —
changing it later means re-distilling.

## What this is not

Notes cover what the speaker *said*. They do not capture diagrams, slides, or code shown on
screen without narration — those are logged as blind spots for a later visual pass, not silently
omitted. Do not present a note as complete coverage of an episode's visual content.
