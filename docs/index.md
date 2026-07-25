# coursebrain

**Learn from long-form video, then write from what you learned.**

Point it at a YouTube course. It pulls transcripts, distills each episode into structured
markdown notes with timestamp links back to the source, and builds a hybrid keyword +
semantic index over the result.

Then the part that makes it more than a note-taker: each course **compiles into a skill**.
Feed it a Spanish course, a programming course, and a writing course, and it can write about
the programming — in Spanish, in that register, following that craft guidance. Three courses,
one piece of output.

!!! tip "No API key"
    Inside Claude Code the agent does the distilling. There is nothing to pay for beyond
    what you are already running. The Anthropic API path exists for unattended runs and is
    entirely optional.

## The idea in one diagram

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
write like this?"* — prescriptive, self-contained, and useless as an archive.

Only the second composes. That distinction is the whole design, and it is covered in
[Composition](composition.md).

## Where to go next

<div class="grid cards" markdown>

- **[Getting started](getting-started.md)** — install, learn your first course, ask it a
  question.
- **[Composition](composition.md)** — the part you came for. How three courses combine
  into one piece of writing.
- **[Profiles](profiles.md)** — why a language course and a programming course produce
  different notes, and how to add your own domain.
- **[Source plugins](plugins.md)** — ingest something other than YouTube.

</div>

## What it deliberately does not do

Notes cover what the speaker **said**. Diagrams, slides, and on-screen code with no
narration are not captured — they are logged as timestamped *visual blind spots* rather
than silently omitted, which doubles as the work list for a later visual pass.

Auto-generated captions mangle identifiers and proper nouns. Notes mark transcript-derived
content as such and flag what could not be recovered. Do not treat a note as authoritative
for exact code; the companion repository is for that.
