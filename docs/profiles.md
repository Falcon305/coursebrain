# Profiles

A profile decides what a note extracts and how the course compiles. It is the reason a
language course and a programming course produce genuinely different notes rather than the
same generic summary with different words in it.

```sh
coursebrain profiles
```

## Shipped profiles

| Profile | For | Note sections | Compiles to |
|---|---|---|---|
| `programming` | Software courses, framework tutorials, system design | Concepts, Code & APIs, Decisions & rationale, Gotchas | `domain` |
| `academic` | Lectures, seminars, research walkthroughs | Key claims, Definitions, Evidence & sources, Frameworks | `domain` |
| `writing` | Craft, rhetoric, editing, copywriting | Principles, Techniques, Exemplars, Anti-patterns | `voice` |
| `language` | Language learning, grammar, immersion | Vocabulary, Grammar points, Usage & idiom, Drills | `language` |
| `general` | Interviews, talks, anything without a better fit | Concepts, Claims & evidence, Practical takeaways | `domain` |

Two sections are appended to every profile:

- **Unclear from audio** — what the transcript could not resolve. Omitted when nothing
  qualifies.
- **Visual blind spots** — timestamped moments where the speaker pointed at something the
  audio cannot convey. An honest gap list, and the work list for a later visual pass.

## Why the sections differ

The `writing` profile insists on **verbatim** exemplars, because style transmits by
specimen — a paraphrased example has destroyed the thing being taught. The `programming`
profile favours *Decisions & rationale*, because source code already shows what was chosen
and only the talk explains why. The `language` profile requires target-language forms with
a gloss after, because a note containing only translations teaches nothing about how to
speak.

Those are not stylistic preferences. They are what makes each profile's output usable for
its domain.

## Adding your own

Profiles are data, not code. Copy `src/coursebrain/profiles/general.yaml`:

```yaml
name: legal
description: Case law lectures, statute walkthroughs, advocacy training.
concept_label: doctrines
capability_kind: domain

capability_guidance: |
  Compile the reasoning, not the holdings alone. What test does this apply, and when
  does it bite? Preserve the distinction between binding authority and persuasive
  commentary.

distill_guidance: |
  Preserve case names and citations exactly as spoken. Auto-captions mangle proper
  nouns badly; flag anything you cannot recover rather than guessing.

sections:
  - heading: TL;DR
    guidance: Two or three sentences. The argument, not the topic.

  - heading: Doctrines
    guidance: >
      Each as its own `###` subheading with a timestamp: the rule, its elements,
      and when it applies.

  - heading: Authorities
    guidance: Cases and statutes cited, with whatever identifying detail was given.
```

Drop it in and it appears in `coursebrain profiles`.

Good profiles are **specific about what belongs in each section** and **honest about which
sections may be omitted**. A section whose guidance is "anything relevant" produces filler,
and filler is worse than a missing section — it looks like coverage.

## Distributing profiles

Register a directory of profile YAML through an entry point so others can install it:

```toml
[project.entry-points."coursebrain.profiles"]
legal = "coursebrain_legal:profiles_dir"
```
