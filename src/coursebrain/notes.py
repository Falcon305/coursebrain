from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

TIMESTAMP_RE = re.compile(r"\?t=(\d+)")
HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$")


@dataclass
class Chunk:
    course: str
    episode: int
    video_id: str
    note_path: str
    title: str
    heading: str
    text: str
    timestamp: int | None = None
    layer: str = "note"

    @property
    def url(self) -> str:
        base = f"https://youtu.be/{self.video_id}"
        return f"{base}?t={self.timestamp}" if self.timestamp is not None else base

    @property
    def label(self) -> str:
        return f"{self.course} ep{self.episode:02d} · {self.heading}"


@dataclass
class Note:
    path: Path
    meta: dict[str, Any]
    body: str
    chunks: list[Chunk] = field(default_factory=list)

    @property
    def course(self) -> str:
        return str(self.meta.get("course", ""))

    @property
    def episode(self) -> int:
        try:
            return int(self.meta.get("episode", 0))
        except (TypeError, ValueError):
            return 0

    @property
    def title(self) -> str:
        return str(self.meta.get("title", self.path.stem))

    @property
    def concepts(self) -> list[str]:
        for key in ("concepts", "principles", "grammar points"):
            value = self.meta.get(key)
            if isinstance(value, list):
                return [str(v) for v in value]
        return []

    @property
    def summary(self) -> str:
        for chunk in self.chunks:
            if chunk.heading.startswith("TL;DR"):
                return " ".join(chunk.text.split())
        return ""


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    # split on the *first* closing delimiter only: a body may legitimately contain
    # a `---` horizontal rule, and splitting on all of them truncates the note
    raw, sep, body = text[3:].partition("\n---")
    if not sep:
        return {}, text
    body = body.lstrip("\n")
    try:
        meta = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        meta = {}
    return (meta if isinstance(meta, dict) else {}), body


def _first_timestamp(text: str) -> int | None:
    match = TIMESTAMP_RE.search(text)
    return int(match.group(1)) if match else None


def parse_note(path: Path) -> Note:
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    note = Note(path=path, meta=meta, body=body)

    section = ""
    heading = ""
    buffer: list[str] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if not text or not heading:
            return
        note.chunks.append(
            Chunk(
                course=note.course,
                episode=note.episode,
                video_id=str(meta.get("video_id", "")),
                note_path=str(path),
                title=note.title,
                heading=heading,
                text=text,
                timestamp=_first_timestamp(text),
            )
        )

    for line in body.splitlines():
        match = HEADING_RE.match(line)
        if match:
            flush()
            buffer = []
            level, name = len(match.group(1)), match.group(2)
            if level == 2:
                section, heading = name, name
            else:
                heading = f"{section} > {name}" if section else name
            continue
        buffer.append(line)
    flush()
    return note


def load_notes(notes_dir: Path) -> list[Note]:
    if not notes_dir.exists():
        return []
    return [parse_note(p) for p in sorted(notes_dir.glob("*.md"))]
