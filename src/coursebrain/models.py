from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

CaptionSource = Literal["manual", "auto", "whisper", "none"]


def slugify(text: str, max_len: int = 60) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text[:max_len].rstrip("-") or "untitled"


def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


@dataclass
class Chapter:
    title: str
    start: float
    end: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Chapter:
        return cls(title=d["title"], start=float(d["start"]), end=float(d["end"]))


@dataclass
class Episode:
    video_id: str
    index: int
    title: str
    duration: float
    caption_source: CaptionSource = "none"
    caption_lang: str = "en"
    upload_date: str | None = None
    description: str = ""
    chapters: list[Chapter] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"https://youtu.be/{self.video_id}"

    def url_at(self, seconds: float) -> str:
        return f"{self.url}?t={int(seconds)}"

    @property
    def slug(self) -> str:
        return f"{self.index:02d}-{slugify(self.title)}"

    @property
    def needs_transcription(self) -> bool:
        return self.caption_source == "none"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["chapters"] = [c.to_dict() for c in self.chapters]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Episode:
        return cls(
            video_id=d["video_id"],
            index=int(d["index"]),
            title=d["title"],
            duration=float(d["duration"]),
            caption_source=d.get("caption_source", "none"),
            caption_lang=d.get("caption_lang", "en"),
            upload_date=d.get("upload_date"),
            description=d.get("description", ""),
            chapters=[Chapter.from_dict(c) for c in d.get("chapters", [])],
        )


@dataclass
class Segment:
    start: float
    end: float
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"start": round(self.start, 2), "end": round(self.end, 2), "text": self.text}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Segment:
        return cls(start=float(d["start"]), end=float(d["end"]), text=d["text"])


@dataclass
class Section:
    start: float
    end: float
    text: str
    title: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Section:
        return cls(
            start=float(d["start"]),
            end=float(d["end"]),
            text=d["text"],
            title=d.get("title"),
        )
