from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ENV_HOME = "COURSEBRAIN_HOME"
MARKERS = ("courses", ".coursebrain")


def find_workspace(start: Path | None = None) -> Path:
    """Where this machine keeps its courses.

    An installed tool must not store data inside its own package directory, so the
    workspace is resolved at call time: an explicit COURSEBRAIN_HOME wins, otherwise
    the nearest ancestor of the working directory that already looks like a
    workspace, otherwise the working directory itself.
    """
    override = os.environ.get(ENV_HOME)
    if override:
        return Path(override).expanduser().resolve()

    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in MARKERS):
            return candidate
    return current


def courses_dir(workspace: Path | None = None) -> Path:
    return (workspace or find_workspace()) / "courses"


@dataclass(frozen=True)
class BrainPaths:
    """Cross-course index. Derivable from the notes, so never committed."""

    root: Path

    @classmethod
    def for_workspace(cls, workspace: Path | None = None) -> BrainPaths:
        return cls(root=(workspace or find_workspace()) / ".brain")

    @property
    def index_db(self) -> Path:
        """Keyword and vector indexes share one file — nothing to keep in sync."""
        return self.root / "index.db"

    @property
    def brain_md(self) -> Path:
        return self.root.parent / "BRAIN.md"

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)


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
        payload: dict[str, Any] = {
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
    def for_course(cls, course_id: str, root: Path | None = None) -> CoursePaths:
        return cls(root=(root or courses_dir()) / course_id)

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
    def cache(self) -> Path:
        return self.root / ".cache"

    def load_config(self) -> CourseConfig:
        if not self.config.exists():
            raise FileNotFoundError(
                f"no course at {self.root}. create one with: coursebrain init <id> <url>"
            )
        return CourseConfig.load(self.config)

    def ensure_dirs(self) -> None:
        for p in (self.raw, self.transcripts, self.notes, self.evals, self.cache):
            p.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        return self.config.exists()


def list_courses(root: Path | None = None) -> list[str]:
    base = root or courses_dir()
    if not base.exists():
        return []
    return sorted(d.name for d in base.iterdir() if (d / "course.yaml").exists())
