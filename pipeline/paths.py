from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
COURSES_DIR = REPO_ROOT / "courses"


@dataclass
class CourseConfig:
    id: str
    source_url: str
    title: str = ""
    profile: str = "general"
    language: str = "en"
    companion_repo: str | None = None
    glossary: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> CourseConfig:
        data: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
        missing = {"id", "source_url"} - data.keys()
        if missing:
            raise ValueError(f"{path}: missing required key(s): {', '.join(sorted(missing))}")
        return cls(
            id=data["id"],
            source_url=data["source_url"],
            title=data.get("title", ""),
            profile=data.get("profile", "general"),
            language=data.get("language", "en"),
            companion_repo=data.get("companion_repo"),
            glossary=list(data.get("glossary") or []),
        )

    def dump(self, path: Path) -> None:
        payload = {
            "id": self.id,
            "title": self.title,
            "source_url": self.source_url,
            "profile": self.profile,
            "language": self.language,
        }
        if self.companion_repo:
            payload["companion_repo"] = self.companion_repo
        if self.glossary:
            payload["glossary"] = self.glossary
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


@dataclass(frozen=True)
class CoursePaths:
    root: Path

    @classmethod
    def for_course(cls, course_id: str, courses_dir: Path | None = None) -> CoursePaths:
        return cls(root=(courses_dir or COURSES_DIR) / course_id)

    @property
    def config(self) -> Path:
        return self.root / "course.yaml"

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def transcripts(self) -> Path:
        return self.root / "transcripts"

    @property
    def notes(self) -> Path:
        return self.root / "notes"

    @property
    def evals(self) -> Path:
        return self.root / "evals"

    @property
    def manifest(self) -> Path:
        return self.root / "manifest.json"

    @property
    def index_md(self) -> Path:
        return self.root / "INDEX.md"

    @property
    def concepts_md(self) -> Path:
        return self.root / "CONCEPTS.md"

    @property
    def synthesis_md(self) -> Path:
        return self.root / "SYNTHESIS.md"

    @property
    def style_md(self) -> Path:
        return self.root / "STYLE.md"

    @property
    def cache(self) -> Path:
        return self.root / ".cache"

    @property
    def index_db(self) -> Path:
        return self.root / "index.db"

    @property
    def lancedb(self) -> Path:
        return self.root / "lancedb"

    @property
    def checkpoints(self) -> Path:
        return self.root / ".cache" / "checkpoints.db"

    def load_config(self) -> CourseConfig:
        if not self.config.exists():
            raise FileNotFoundError(
                f"no course at {self.root}. create one with: course init <id> <url>"
            )
        return CourseConfig.load(self.config)

    def ensure_dirs(self) -> None:
        for p in (self.raw, self.transcripts, self.notes, self.evals, self.cache):
            p.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        return self.config.exists()


def list_courses(courses_dir: Path | None = None) -> list[str]:
    base = courses_dir or COURSES_DIR
    if not base.exists():
        return []
    return sorted(d.name for d in base.iterdir() if (d / "course.yaml").exists())
