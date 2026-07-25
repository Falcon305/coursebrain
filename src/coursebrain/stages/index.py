from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from coursebrain.notes import Chunk, Note, load_notes
from coursebrain.paths import BrainPaths, CoursePaths, list_courses
from coursebrain.retrieval import build_index, vectors_available

Logger = Callable[[str], None]


def render_course_index(course_id: str, title: str, notes: list[Note]) -> str:
    lines = [f"# {title or course_id}", ""]
    lines.append(
        f"{len(notes)} episode note(s). Read this index first, then open only the notes you need."
    )
    lines.append("")
    for note in sorted(notes, key=lambda n: n.episode):
        rel = f"notes/{note.path.name}"
        summary = note.summary
        lines.append(
            f"- **[{note.episode:02d}. {note.title}]({rel})** — {summary}"
            if summary
            else f"- **[{note.episode:02d}. {note.title}]({rel})**"
        )
        if note.concepts:
            lines.append(f"  - {', '.join(note.concepts[:12])}")
    lines.append("")
    return "\n".join(lines)


def render_concepts(notes: list[Note]) -> str:
    index: dict[str, list[Note]] = defaultdict(list)
    for note in notes:
        for concept in note.concepts:
            index[concept].append(note)
    lines = ["# Concepts", ""]
    if not index:
        lines.append("_No concepts extracted yet._")
        return "\n".join(lines) + "\n"
    for concept in sorted(index, key=str.lower):
        refs = ", ".join(
            f"[ep{n.episode:02d}](notes/{n.path.name})"
            for n in sorted(index[concept], key=lambda n: n.episode)
        )
        lines.append(f"- **{concept}** — {refs}")
    lines.append("")
    return "\n".join(lines)


def render_brain(summaries: list[tuple[str, str, str, int]]) -> str:
    lines = [
        "# Brain",
        "",
        "Everything this repository has learned, one line per course.",
        'Open a course\'s `INDEX.md` to go deeper, or run `course ask "<question>"`.',
        "",
    ]
    if not summaries:
        lines.append("_No courses indexed yet._")
        return "\n".join(lines) + "\n"
    for course_id, title, profile, count in sorted(summaries):
        label = title or course_id
        lines.append(
            f"- **[{label}](courses/{course_id}/INDEX.md)** — {profile}, {count} episode(s)"
        )
    lines.append("")
    return "\n".join(lines)


def index_course(course_id: str, courses_dir: Path | None = None) -> tuple[list[Chunk], int]:
    paths = CoursePaths.for_course(course_id, courses_dir)
    config = paths.load_config()
    notes = load_notes(paths.notes)

    paths.index_md.write_text(render_course_index(course_id, config.title, notes), encoding="utf-8")
    paths.concepts_md.write_text(render_concepts(notes), encoding="utf-8")

    chunks = [c for note in notes for c in note.chunks]
    return chunks, len(notes)


def index_all(
    courses_dir: Path | None = None, use_vectors: bool = True, log: Logger = print
) -> int:
    brain = BrainPaths.for_workspace()
    brain.ensure()

    all_chunks: list[Chunk] = []
    summaries: list[tuple[str, str, str, int]] = []

    for course_id in list_courses(courses_dir):
        paths = CoursePaths.for_course(course_id, courses_dir)
        config = paths.load_config()
        chunks, count = index_course(course_id, courses_dir)
        all_chunks.extend(chunks)
        summaries.append((course_id, config.title, config.profile, count))
        log(f"{course_id}: {count} note(s), {len(chunks)} chunk(s)")

    brain.brain_md.write_text(render_brain(summaries), encoding="utf-8")
    indexed, embedded = build_index(brain.index_db, all_chunks, use_vectors=use_vectors)

    if use_vectors and not vectors_available():
        log("semantic search unavailable (install the 'rag' extra) — keyword only")
    elif embedded:
        log(f"embedded {embedded} chunk(s)")

    log(f"indexed {indexed} chunk(s) across {len(summaries)} course(s)")
    return indexed
