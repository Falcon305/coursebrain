# Composition

## The problem

Someone who has studied a subject properly does not answer you by quoting a source. They
answer from judgement — they know which claim to trust, which advice is obsolete, what the
instructor spent four minutes warning against, and what to actually do. That knowledge is
*integrated*. It has stopped being a set of quotes and become a way of working.

Retrieval never gets there. A search over your notes returns the passage most similar to your
question. It cannot tell you that two episodes contradict each other and which one is right,
or that the technique in episode 3 is the one everybody skips. Those are properties of the
course as a whole, not of any passage in it.

**Compilation is how a course stops being an archive and becomes competence.** Reading every
note at once and asking "what does someone who has done this actually know?" produces a
different artefact from any amount of searching — one that fits in context, applies without
being asked, and can be held alongside others.

## Why several at once

Expertise is rarely one layer. Doing real work usually needs several kinds of knowing at the
same time: what is true, how to carry out the procedure, how the output should read, and what
language it should be in.

A person who has studied all four applies them together without noticing. Four separate
searches cannot, because the layers have to be resolved against each other — and when they
conflict, something has to decide.

## Notes versus capability packs

The distinction is load-bearing, and getting it wrong is the main way this feature fails.

| | Note | Capability pack |
|---|---|---|
| Answers | *"What did episode 7 say?"* | *"How do I write like this?"* |
| Shape | Archive, with timestamps | Instrument, prescriptive |
| Length | However long the episode was | ~300–800 words |
| Good for | Checking a fact, citing a source | Producing something |
| Composes | No | **Yes** |

A pack that reads like a course description has failed. *"The course covers error
handling"* is worthless. *"Return `Nothing` rather than throwing, and let the caller
decide"* is usable.

Compile one with:

```sh
coursebrain compile <course>          # stages a task over all the notes
# read the task file, write the body it names
coursebrain compile-assemble <course> # -> courses/<course>/CAPABILITY.md
```

## Kinds decide how packs stack

Every pack carries a `kind`, set by the course's [profile](profiles.md):

| kind | from | governs |
|---|---|---|
| `domain` | programming, academic, general | what is true and worth saying |
| `voice` | writing | how the prose moves |
| `language` | language | which language and register |

They operate at different layers, so they mostly stack rather than fight. A domain pack has
nothing to say about sentence rhythm; a language pack has no opinion about monads.

## Resolving conflicts

Where packs *do* collide, the precedence is stated rather than left to chance:

1. **Language governs surface.** Spelling, register, idiom, what sounds native. Craft rules
   written for one language do not transfer wholesale to another — if a voice rule fights
   the language, the language wins.
2. **Voice governs form.** Structure, rhythm, what to cut — applied *within* what the
   language allows.
3. **Domain governs content.** Never bend a fact to fit a stylistic rule.

**Domain accuracy outranks everything.** Style is how you say a true thing, not a licence to
say a false one.

!!! warning "Stay inside the packs"
    Use the vocabulary and rules the packs actually contain. Reaching for a plausible word
    the language pack never taught, or a craft habit of your own, quietly defeats the point
    — the output should be traceable to the courses.

    This rule exists because testing found exactly that leak: an output used a Spanish word
    no pack had taught, and a filter-word construction the voice pack explicitly says to
    cut. Both looked fine until checked against the packs.

## Using it

From Claude Code:

```
/compose an explainer about revalidation, in Spanish, using the prose course
```

From the shell:

```sh
coursebrain compose \
    --about react \
    --voice prose-craft \
    --lang spanish \
    --task "explain revalidation to a beginner"
```

That prints a single context pack: every loaded capability, ordered language → voice →
domain, ending with the precedence rules. Pipe it into whatever you like.

## Or let skills do it

`coursebrain skill <course>` exports a pack as a Claude Code skill:

```sh
coursebrain skill spanish            # ./.claude/skills/spanish/SKILL.md
coursebrain skill spanish --scope user   # ~/.claude/skills/, available everywhere
```

Claude Code loads roughly 100 tokens of frontmatter per skill at startup and pulls the body
only when relevant, so a shelf of exported courses costs almost nothing until used — and
several can be active at once. That is why the frontmatter `description` is written as a
**routing rule**, not a summary: it is the only part the model sees before deciding.

Compiled triggers look like this:

> Use when writing or speaking Mexican Spanish, especially informal or friendly registers —
> messages to friends, casual dialogue, anything that should sound like a Mexican speaker
> rather than a textbook.

Not *"about the Spanish course"*.

## Judging whether it worked

A pack that quietly contributes nothing looks identical to one that worked, until you read
the output. After composing, check each dimension separately:

- Did the **domain** pack's actual judgements appear, or just its topic?
- Did the **voice** pack change the sentences, or is the prose your default?
- Did the **language** pack's register show up, or is it generic?

If one dimension is missing, recompile that pack — the usual cause is a pack that
summarised its course instead of instructing.
