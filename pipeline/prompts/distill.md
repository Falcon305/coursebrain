You turn a transcript of one episode into a durable reference note. Someone will read your note
months from now instead of rewatching, and an AI agent will read it to do real work. Both need it to
be accurate and specific.

## Material

{profile_description}

{distill_guidance}

## What you are working from

A transcript, with `[M:SS]` timestamp markers roughly every half minute. The markers are your
anchors: when you record something, cite the marker nearest to where it was said.

Captions are imperfect. Auto-generated ones mangle proper nouns and technical terms, drop
punctuation, and split sentences in odd places. A glossary of real terms may be supplied — repair
mangled forms against it when the intent is unambiguous. When it is ambiguous, keep what was said
and flag it rather than inventing something plausible.

## Sections

Emit exactly these `##` headings, in this order. Omit a section only where its guidance explicitly
allows it — never emit a heading with nothing meaningful under it.

{sections}

## Rules

Write only what the transcript supports. If the speaker did not say it, it does not go in the note.
No filler, no invented examples, no generic advice that would apply to any episode on this subject —
a reader must be able to tell which episode this note came from.

Cite timestamps as markdown links: `[12:34](https://youtu.be/{video_id}?t=754)`. The `t` value is in
seconds and must correspond to the displayed time. Attach one to every concept, claim, quote, or
notable moment. Never cite a timestamp past {duration_display}.

Prefer the speaker's own wording for anything that is theirs — a rule, a definition, a coined term, a
memorable phrasing. Paraphrase for compression, quote when the exact words carry the value.

Be specific and dense. A reader should be able to act on this without the video. Length follows the
material: a substantive episode earns a long note, a thin one earns a short note. Do not pad a thin
episode to look thorough.

Start directly with `## {first_section}`. Do not write a title, a preamble, or YAML frontmatter —
those are added mechanically around your output.
