from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from coursebrain.manifest import Manifest
from coursebrain.models import format_timestamp
from coursebrain.notes import load_notes
from coursebrain.paths import CoursePaths
from coursebrain.profiles import Profile

TIMESTAMP_LINK_RE = re.compile(r"\[(\d+:\d{2}(?::\d{2})?)\]\(https://youtu\.be/([\w-]+)\?t=(\d+)\)")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\((?!https?:)([^)]+)\)")


@dataclass
class VerifyReport:
    checked: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def add(self, note: str, message: str) -> None:
        self.problems.append(f"{note}: {message}")


def verify_course(course_id: str, courses_dir: Path | None = None) -> VerifyReport:
    paths = CoursePaths.for_course(course_id, courses_dir)
    config = paths.load_config()
    profile = Profile.load(config.profile)
    manifest = Manifest.load(paths.manifest, course_id)
    notes = load_notes(paths.notes)
    report = VerifyReport(checked=len(notes))

    by_episode = {n.episode: n for n in notes}
    for record in manifest.episodes.values():
        if record.caption_source == "none":
            continue
        if record.index not in by_episode:
            report.add(f"ep{record.index:02d}", f"no note for '{record.title}'")

    optional = {
        "Unclear from audio",
        "Visual blind spots",
        "Practical takeaways",
        "Gotchas",
        "Exam-relevant points",
        "Drills",
        "Revision moves",
        "Frameworks & models",
        "Pronunciation notes",
    }
    required = [h for h in profile.headings if h not in optional]

    for note in notes:
        name = note.path.name
        present = {c.heading.split(" > ")[0] for c in note.chunks}

        for heading in required:
            if heading not in present:
                report.add(name, f"missing required section '{heading}'")

        for chunk in note.chunks:
            if not chunk.text.strip():
                report.add(name, f"empty section '{chunk.heading}'")

        video_id = str(note.meta.get("video_id", ""))
        if not video_id:
            report.add(name, "frontmatter has no video_id")
        duration = _duration_seconds(note.meta.get("duration"))

        for label, linked_id, seconds in TIMESTAMP_LINK_RE.findall(note.body):
            if linked_id != video_id:
                report.add(name, f"timestamp {label} links to a different video ({linked_id})")
            if duration is not None and int(seconds) > duration + 5:
                report.add(
                    name,
                    f"timestamp {label} ({seconds}s) is past the episode duration "
                    f"({format_timestamp(duration)})",
                )
            if abs(_label_seconds(label) - int(seconds)) > 60:
                report.add(name, f"timestamp {label} disagrees with its t={seconds} link")

        for target in MD_LINK_RE.findall(note.body):
            resolved = (note.path.parent / target.split("#")[0]).resolve()
            if not resolved.exists():
                report.add(name, f"broken link to {target}")

    for path in (paths.index_md, paths.concepts_md):
        if notes and not path.exists():
            report.add(path.name, "missing — run 'coursebrain index'")

    return report


def _duration_seconds(value: object) -> int | None:
    # yaml reads an unquoted "15:30" as sexagesimal (930), so accept both forms
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return _label_seconds(value)
        except ValueError:
            return None
    return None


def _label_seconds(label: str) -> int:
    parts = [int(p) for p in label.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
