---
description: Write something using several courses at once — subject, style, and language together
argument-hint: <what to write> [using <course> <course> ...]
allowed-tools: Bash(coursebrain:*), Read, Glob
---

Produce: **$ARGUMENTS**

You are going to write this using the courses in this workspace, combined. Not one course
at a time — all of them at once, each supplying a different layer.

## 1. Pick the courses

```sh
coursebrain list
```

If the user named courses, use those. Otherwise choose by what the task needs, and say
which you picked and why:

- **domain** — a subject course. What is actually true and worth saying.
- **voice** — a writing-craft course. How the prose should be shaped.
- **language** — a language course. Which language and register to write in.

You do not need all three. One is fine; three is where this gets interesting.

Each course needs a compiled capability pack. If `coursebrain compose` reports one
missing, compile it first:

```sh
coursebrain compile <course>     # stages a task file
# read the task, write the body it names
coursebrain compile-assemble <course>
```

## 2. Load the composition

```sh
coursebrain compose -a <domain> -v <voice> -L <language> -t "<the task>"
```

Read all of it before writing anything. It ends with a precedence section that tells you
how to resolve conflicts between the packs — language governs surface, voice governs form,
domain governs content, and accuracy outranks style.

## 3. Write

Follow every pack at once. That is the whole point: the subject course decides what is
true, the craft course decides how the sentences move, the language course decides how it
sounds.

**Stay inside the packs.** Use the vocabulary and rules they actually contain. Reaching for
a plausible word the language pack never taught, or a craft habit of your own, quietly
defeats the exercise — the output should be traceable to these courses. Where a pack does
not cover something you need, say so rather than filling the gap silently.

If you need a specific fact, search rather than guess:

```sh
coursebrain ask "<question>" --course <domain>
```

## 4. Report

Deliver the writing, then say in one or two lines which pack shaped what — so the user can
tell whether the composition worked or whether one dimension went missing. If a pack
barely showed up in the output, say that plainly; it usually means the pack needs
recompiling rather than that the idea failed.
