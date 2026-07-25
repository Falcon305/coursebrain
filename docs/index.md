# coursebrain

**Point it at 20 playlists about one subject. Your agent doesn't search them — it studied them.**

Every episode becomes a cited note with timestamps back to the source. Those notes then
**compile into Claude Code skills** your agent carries and applies, the way someone who took
the course would.

The distinction that matters: retrieval hands you a passage someone said once. Someone who
studied the material has judgement — they know which episode to trust, what the traps are, and
what to do differently. Compilation is how you get the second thing.

!!! tip "No API key"
    Inside Claude Code the agent does the distilling. There is nothing to pay for beyond
    what you are already running. The Anthropic API path exists for unattended runs and is
    entirely optional.

## The problem

There are hundreds of hours of genuinely good material on your subject sitting on YouTube, and
your agent has watched none of it.

Retrieval does not fix it. A RAG system hands you a passage someone said once; it cannot tell
you which of two contradictory episodes to trust, or that the step everybody skips is the one
that matters. **A quote is not judgement.**

## The solution

```
playlists ──▶ transcripts ──▶ cited notes ──▶ capability pack ──▶ SKILL.md
                                   │                                  │
                           search when you                  applied automatically,
                             need a source                   composes with others
```

|  | **Note** | **Capability pack** |
| --- | --- | --- |
| Answers | *"What did episode 7 say?"* | *"What does someone who studied this know?"* |
| Produced by | Reading one episode | Reading **every** note at once |
| Loads | On request | **Automatically, when relevant** |
| Composes | No | **Yes** |

That distinction is the whole design, and it is covered in [Composition](composition.md).

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
