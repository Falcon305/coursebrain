You are compiling a whole course into a **capability pack** — a short, prescriptive
document that lets someone *act* on what the course teaches, without reading it.

Course: **{title}** (`{course_id}`), {note_count} episode note(s).
This pack's kind is **{kind}**.

{guidance}

## The distinction that matters

The notes you are reading are an *archive*: they record what each episode said, with
timestamps. The pack you are writing is an *instrument*: someone loads it alongside
other packs and immediately writes, speaks, or builds something better.

A summary of the course is a failure. "The course covers error handling" is worthless.
"Return `Nothing` rather than throwing, and let the caller decide" is usable. Every line
should be something a person could follow tomorrow.

Assume the reader has never seen the course and never will.

## Rules

Write only what the notes support. You are compressing, not inventing — if the course
did not teach it, it does not belong here, however true it might be.

Prefer the instructor's own words for anything that is theirs: a coined term, a rule,
a memorable phrasing. Those survive compression better than paraphrase.

Be concrete. Name the specific technique, the specific identifier, the specific phrase.
Generic advice that would fit any course on this subject means the compilation failed.

Keep it dense and finite — roughly 300 to 800 words of body. This gets loaded alongside
other packs, so length is a real cost. Cut anything the reader would not act on.

Do not include timestamps or citations. Those live in the notes; this pack is the
distilled layer and stays readable on its own.

Where the course genuinely disagrees with itself, or an instructor changed their mind,
say so briefly rather than flattening it.

## Output

Start with exactly one line:

`Trigger: <when should this pack be loaded>`

Write it as a routing rule, not a description — it is the only part a model sees before
deciding whether to pull the pack into context. Name the situations and the words a user
would actually say. "Use when writing Spanish, especially informal or regional registers,
or when a message should sound like a native speaker rather than a textbook" is a good
trigger. "About the Spanish course" is a bad one.

Then the pack body, using `##` headings of your own choosing that suit this material.
Do not write a title, and do not write YAML frontmatter — those are added mechanically.
