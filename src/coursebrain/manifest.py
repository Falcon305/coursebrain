from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StageRecord:
    input_hash: str
    output_hash: str
    tool: str
    trace_id: str | None = None
    notes: str = ""

    # dropping an empty *required* field makes the record unreadable on reload —
    # an episode with no captions legitimately has an empty output_hash
    OPTIONAL = ("trace_id", "notes")

    def to_dict(self) -> dict[str, Any]:
        return {
            k: v
            for k, v in asdict(self).items()
            if k not in StageRecord.OPTIONAL or v not in (None, "")
        }


@dataclass
class EpisodeRecord:
    video_id: str
    index: int
    title: str
    caption_source: str = "none"
    stages: dict[str, StageRecord] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "index": self.index,
            "title": self.title,
            "caption_source": self.caption_source,
            "stages": {k: v.to_dict() for k, v in sorted(self.stages.items())},
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EpisodeRecord:
        return cls(
            video_id=d["video_id"],
            index=int(d["index"]),
            title=d["title"],
            caption_source=d.get("caption_source", "none"),
            stages={
                k: StageRecord(
                    input_hash=v.get("input_hash", ""),
                    output_hash=v.get("output_hash", ""),
                    tool=v.get("tool", ""),
                    trace_id=v.get("trace_id"),
                    notes=v.get("notes", ""),
                )
                # tolerate manifests written before empty required fields were kept
                for k, v in (d.get("stages") or {}).items()
            },
        )


class Manifest:
    def __init__(self, path: Path, course_id: str = "") -> None:
        self.path = path
        self.course_id = course_id
        self.episodes: dict[str, EpisodeRecord] = {}
        self.pipeline_version = "1"

    @classmethod
    def load(cls, path: Path, course_id: str = "") -> Manifest:
        m = cls(path, course_id)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            m.course_id = data.get("course", course_id)
            m.pipeline_version = data.get("pipeline_version", "1")
            m.episodes = {
                e["video_id"]: EpisodeRecord.from_dict(e) for e in data.get("episodes", [])
            }
        return m

    def record(self, video_id: str, index: int, title: str) -> EpisodeRecord:
        rec = self.episodes.get(video_id)
        if rec is None:
            rec = EpisodeRecord(video_id=video_id, index=index, title=title)
            self.episodes[video_id] = rec
        else:
            rec.index, rec.title = index, title
        return rec

    def stage_done(self, video_id: str, stage: str, input_hash: str) -> bool:
        rec = self.episodes.get(video_id)
        return bool(rec and stage in rec.stages and rec.stages[stage].input_hash == input_hash)

    def save(self) -> None:
        payload = {
            "course": self.course_id,
            "pipeline_version": self.pipeline_version,
            "episodes": [
                e.to_dict() for e in sorted(self.episodes.values(), key=lambda e: e.index)
            ],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def summary(self) -> str:
        by_stage: dict[str, int] = {}
        for rec in self.episodes.values():
            for stage in rec.stages:
                by_stage[stage] = by_stage.get(stage, 0) + 1
        parts = [f"{n} {stage}" for stage, n in sorted(by_stage.items())]
        untranscribed = sum(1 for r in self.episodes.values() if r.caption_source == "none")
        line = f"{len(self.episodes)} episodes | " + ", ".join(parts)
        if untranscribed:
            line += f" | {untranscribed} without captions"
        return line
