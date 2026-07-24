from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import Episode
from .paths import CoursePaths


@dataclass
class WorkItem:
    """One episode staged for an agent to distill.

    The agent reads `task` (instructions plus transcript) and writes prose to `body`.
    Frontmatter is added mechanically at assemble time, so the agent never writes YAML.
    """

    episode: int
    slug: str
    task: Path
    body: Path
    meta: Path
    note: Path

    @property
    def done(self) -> bool:
        return self.body.exists() and bool(self.body.read_text(encoding="utf-8").strip())


def work_dir(paths: CoursePaths) -> Path:
    return paths.root / ".work"


def item_for(paths: CoursePaths, episode: int, slug: str) -> WorkItem:
    d = work_dir(paths)
    return WorkItem(
        episode=episode,
        slug=slug,
        task=d / f"{slug}.task.md",
        body=d / f"{slug}.body.md",
        meta=d / f"{slug}.meta.json",
        note=paths.notes / f"{slug}.md",
    )


def write_task(item: WorkItem, episode: Episode, transcript_hash: str, system: str, user: str) -> None:
    item.task.parent.mkdir(parents=True, exist_ok=True)
    item.meta.write_text(
        json.dumps(
            {"episode": episode.to_dict(), "transcript_hash": transcript_hash},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    header = (
        f"<!-- Episode {episode.index:02d} of this course. Follow the instructions below and "
        f"write ONLY the note body to:\n     {item.body}\n"
        "     Do not write frontmatter or a title — those are added mechanically. -->\n\n"
        f"# Instructions\n\n"
    )
    item.task.write_text(f"{header}{system}\n\n# Episode\n\n{user}\n", encoding="utf-8")


def read_meta(item: WorkItem) -> tuple[Episode, str]:
    data = json.loads(item.meta.read_text(encoding="utf-8"))
    return Episode.from_dict(data["episode"]), data["transcript_hash"]


def list_items(paths: CoursePaths) -> list[WorkItem]:
    d = work_dir(paths)
    if not d.exists():
        return []
    items: list[WorkItem] = []
    for meta in sorted(d.glob("*.meta.json")):
        slug = meta.name[: -len(".meta.json")]
        try:
            episode = int(slug.split("-", 1)[0])
        except ValueError:
            continue
        items.append(item_for(paths, episode, slug))
    return items


def pending(paths: CoursePaths) -> list[WorkItem]:
    return [i for i in list_items(paths) if not i.done]


def clear(item: WorkItem) -> None:
    for path in (item.task, item.body, item.meta):
        path.unlink(missing_ok=True)


def strip_preamble(text: str) -> str:
    """Agents sometimes open with a title or a sentence of narration. Drop anything
    before the first `##` so the note starts where the schema says it should."""
    lines = text.strip().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("## "):
            return "\n".join(lines[i:]).strip()
    return text.strip()
