# Getting started

## Install

=== "Claude Code plugin"

    ```
    /plugin marketplace add Falcon305/coursebrain
    /plugin install coursebrain
    ```

    Then install the CLI the commands call:

    ```sh
    uv tool install "coursebrain[rag]"
    ```

=== "CLI only"

    ```sh
    uv tool install "coursebrain[rag]"
    ```

Check it:

```sh
coursebrain doctor
```

`doctor` reports every dependency and prints the exact command to fix anything broken. It is
the first thing to run when something misbehaves.

!!! note "The `rag` extra"
    `[rag]` adds semantic search — about 100 MB (sqlite-vec plus static embeddings, no
    PyTorch). Without it everything still works on keyword search alone, and `doctor` will
    tell you it is missing.

## Learn a course

```sh
coursebrain learn https://www.youtube.com/playlist?list=PLxxxx \
    --id react --profile programming
```

A single video, a playlist, and a channel are the same command. Pick the
[profile](profiles.md) that fits the material — it decides what the notes extract, so
changing it later means re-distilling.

`learn` fetches transcripts in parallel and stages one task file per episode. Each task
contains the instructions, the note schema, and the transcript with `[M:SS]` markers.

## Write the notes

Read each staged task and write the note body to the path it names. Inside Claude Code,
`/learn <url>` does this whole loop for you.

```sh
coursebrain pending             # what is still waiting
coursebrain assemble react     # bodies -> notes, frontmatter added mechanically
```

## Make it searchable

```sh
coursebrain index
coursebrain ask "how do I stop it crashing on bad input"
```

`ask` searches keywords and meaning together, so a question phrased differently from the
notes still finds them. Every hit carries a timestamp link back to the source.

```sh
coursebrain verify react       # structural check; exits non-zero on problems
```

## Make it composable

```sh
coursebrain compile react          # notes -> capability pack
coursebrain compile-assemble react
coursebrain skill react            # pack -> Claude Code skill
```

Now see [Composition](composition.md) for the part where several courses act together.

## Where things live

The workspace is resolved at call time: `COURSEBRAIN_HOME` if set, otherwise the nearest
parent directory containing `courses/` or `.coursebrain/`, otherwise the current directory.

```
courses/<id>/
    course.yaml       source url, profile, language
    raw/              captions, committed on purpose
    transcripts/      normalized
    notes/            the product
    CAPABILITY.md     the compiled pack
.brain/index.db       search index, rebuildable offline
BRAIN.md              one line per course
```

Anything irreplaceable is committed; anything derivable is ignored. Raw captions are
committed because videos get deleted and the captions go with them.
