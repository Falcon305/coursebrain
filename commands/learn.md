---
description: Turn a YouTube video, playlist, or channel into searchable course notes
argument-hint: <url> [--profile programming|academic|writing|language|general] [--limit N]
allowed-tools: Bash(coursebrain:*), Read, Write, Glob
---

Learn the material at: **$ARGUMENTS**

You are going to distill this yourself. There is no API key and none is needed — you are the
model. Work through the loop below.

## 1. Create the course

Pick a short kebab-case id from the source title, and a profile that fits the material:
`programming`, `academic`, `writing`, `language`, or `general` (run `coursebrain profiles` if unsure).
Honour a `--profile` or `--limit` in the arguments if the user gave one.

```sh
coursebrain learn "<url>" --id <id> --profile <profile> --title "<Real Title>"
```

A single video and a 200-video playlist are the same command — the pipeline treats a lone video
as a one-episode course.

## 2. Stage the transcripts

`learn` already did this. To restage, or to add episodes later:

```sh
coursebrain prepare <id>
```

This downloads captions and writes one task file per episode. It prints the pending list; you can
re-read it any time with `coursebrain pending <id>`. Episodes without captions are skipped and reported
— mention them at the end rather than pretending they were covered.

## 3. Write a note per episode

For each pending episode:

1. **Read** the `.task.md` file. It contains the full instructions, the note schema for this
   course's profile, the episode metadata, and the transcript with `[M:SS]` markers.
2. **Follow those instructions exactly.** They are the specification — do not substitute your own
   note format.
3. **Write** the note body to the `.body.md` path the task file names. Body only: start at the
   first `##` heading. No frontmatter, no title, no preamble — those are added mechanically.

Do episodes one at a time and actually read each transcript. Never write a note from the title
alone; a fabricated note is worse than a missing one.

The task files are large. If a transcript is long, read the task file in chunks rather than
skipping content — coverage of the whole episode is the point.

## 4. Assemble, index, verify

```sh
coursebrain assemble <id>   # wraps your bodies in frontmatter, files them as notes
coursebrain index           # rebuilds INDEX.md, CONCEPTS.md, BRAIN.md, and the search index
coursebrain verify <id>     # structural check — must pass
```

If `verify` reports problems, fix the notes it names and re-run `assemble` and `index`. Do not
report success while verify is failing.

## 5. Report back

Tell the user: how many episodes were distilled, any that were skipped and why, and two or three
concrete things the course actually covers — drawn from the notes you wrote, not guessed from the
title. Then show them one query they can run:

```sh
coursebrain ask "<something the course genuinely covers>"
```

## 6. Optional: make it composable

A course becomes a *skill* — loadable alongside other courses — once it is compiled into a
capability pack:

```sh
coursebrain compile <id>          # stages a compilation task over all the notes
# read the task file, write the body it names
coursebrain compile-assemble <id>
coursebrain skill <id>            # exports .claude/skills/<id>/SKILL.md
```

That is what lets a language course, a subject course, and a writing course act together.
Suggest it once a course has several notes — it is the difference between an archive you
search and a skill you write from.
