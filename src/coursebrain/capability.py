"""Capability packs: what turns a course from an archive into a skill.

A note answers *"what did episode 7 say?"*. A capability pack answers *"how do I
write like this?"* — prescriptive, self-contained, and useless as an archive. Only
the second composes with other courses, which is the whole point: a Spanish course,
a programming course, and a writing course should combine into one piece of writing.

Packs carry a ``kind`` that decides how they compose:

``domain``    what to say — concepts, decisions, gotchas
``voice``     how to write it — craft rules, techniques, exemplars
``language``  what language and register to say it in

They operate at different levels, so they mostly stack rather than fight. Where they
do collide, :data:`PRECEDENCE` states who wins instead of leaving it to chance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .notes import split_frontmatter
from .paths import CoursePaths

Kind = str

KINDS: tuple[Kind, ...] = ("domain", "voice", "language")

PRECEDENCE = """\
When these conflict, resolve in this order:

1. **Language governs surface.** Spelling, register, idiom, and what actually sounds
   native. Craft rules written for one language do not transfer wholesale to another —
   if a voice rule fights the language, the language wins.
2. **Voice governs form.** Structure, rhythm, what to cut, how to open and close —
   applied *within* whatever the language allows.
3. **Domain governs content.** What is true and worth saying. Never bend a fact to fit
   a stylistic rule; if the craft guidance would make a claim inaccurate, keep the claim
   and change the phrasing.

Domain accuracy outranks everything. Style is how you say a true thing, not a licence
to say a false one.

**Stay inside the packs.** Use the vocabulary, rules, and claims these packs actually
contain. Reaching for a plausible-sounding word the language pack never taught, or a
craft rule from your own habits, quietly defeats the point — the output should be
traceable to the courses, not to what you already knew. When a pack does not cover
something you need, say so rather than filling the gap silently."""


class CapabilityError(RuntimeError):
    pass


@dataclass
class Capability:
    """A compiled, applicable summary of one course."""

    course: str
    kind: Kind
    title: str
    trigger: str
    body: str

    @property
    def heading(self) -> str:
        return f"{self.kind.upper()}: {self.title}"

    def to_markdown(self) -> str:
        front = yaml.safe_dump(
            {
                "course": self.course,
                "kind": self.kind,
                "title": self.title,
                "trigger": self.trigger,
            },
            sort_keys=False,
            allow_unicode=True,
        )
        return f"---\n{front}---\n\n{self.body.strip()}\n"

    @classmethod
    def from_markdown(cls, text: str, course: str) -> Capability:
        meta, body = split_frontmatter(text)
        kind = str(meta.get("kind", "domain"))
        if kind not in KINDS:
            raise CapabilityError(f"{course}: unknown capability kind {kind!r}")
        return cls(
            course=str(meta.get("course", course)),
            kind=kind,
            title=str(meta.get("title", course)),
            trigger=str(meta.get("trigger", "")),
            body=body.strip(),
        )

    @classmethod
    def load(cls, paths: CoursePaths) -> Capability:
        path = capability_path(paths)
        if not path.exists():
            raise CapabilityError(
                f"course '{paths.root.name}' has no capability pack. "
                f"compile one with: coursebrain compile {paths.root.name}"
            )
        return cls.from_markdown(path.read_text(encoding="utf-8"), paths.root.name)

    def save(self, paths: CoursePaths) -> Path:
        path = capability_path(paths)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")
        return path


def capability_path(paths: CoursePaths) -> Path:
    return paths.root / "CAPABILITY.md"


def has_capability(paths: CoursePaths) -> bool:
    return capability_path(paths).exists()


# --------------------------------------------------------------- skill export


def _slugify_words(text: str, limit: int = 24) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words)[:limit].strip("-")


def render_skill(cap: Capability, course_id: str) -> str:
    """A Claude Code skill.

    The ``description`` is the only part the model sees until the skill fires, so it
    is written as a routing rule — when to use this — rather than a summary of the
    course. Everything else stays on disk until it is actually needed.
    """
    description = cap.trigger.strip() or f"Knowledge from the {cap.title} course."
    front = yaml.safe_dump(
        {"name": course_id, "description": description},
        sort_keys=False,
        allow_unicode=True,
        width=10_000,
    )
    kind_line = {
        "domain": "This is **subject knowledge**: what is true, and why.",
        "voice": "This is **craft guidance**: how to write, not what to write about.",
        "language": "This is **language guidance**: how to say it, in which register.",
    }[cap.kind]

    return f"""---
{front}---

{kind_line}

{cap.body.strip()}

## Going deeper

This pack is the distilled, applicable version. The full notes — with timestamps back
to the source — are in `courses/{course_id}/`. Start at `INDEX.md`, or search:

```sh
coursebrain ask "<question>" --course {course_id}
```

Cite the timestamp link whenever you use something from a note. The material is
transcript-derived, so a reader needs to be able to check it.

## Composing with other courses

{PRECEDENCE}
"""


# ---------------------------------------------------------------- composition


@dataclass
class Composition:
    parts: list[Capability]

    @property
    def by_kind(self) -> dict[str, list[Capability]]:
        grouped: dict[str, list[Capability]] = {k: [] for k in KINDS}
        for part in self.parts:
            grouped[part.kind].append(part)
        return grouped

    def render(self, task: str = "") -> str:
        grouped = self.by_kind
        chunks: list[str] = ["# Composed capability", ""]

        if task:
            chunks += [f"**Task:** {task}", ""]

        active = [f"{c.title} ({c.kind})" for c in self.parts]
        chunks += [
            "Apply everything below at once. Each pack was compiled from a different "
            "course and covers a different layer of the job.",
            "",
            f"**Loaded:** {', '.join(active)}",
            "",
        ]

        # language first, then voice, then domain: the order the writer works in
        for kind in ("language", "voice", "domain"):
            for cap in grouped[kind]:
                chunks += [f"## {cap.heading}", "", cap.body.strip(), ""]

        chunks += ["## Resolving conflicts", "", PRECEDENCE, ""]
        return "\n".join(chunks)


def compose(paths: list[CoursePaths], task: str = "") -> Composition:
    if not paths:
        raise CapabilityError("nothing to compose: name at least one course")
    parts = [Capability.load(p) for p in paths]
    return Composition(parts=parts)


# ------------------------------------------------------------ prompt assembly


def build_compile_prompt(
    template: str,
    course_id: str,
    title: str,
    kind: Kind,
    guidance: str,
    note_count: int,
) -> str:
    return template.format(
        course_id=course_id,
        title=title or course_id,
        kind=kind,
        guidance=guidance.strip(),
        note_count=note_count,
    )


def suggested_trigger(kind: Kind, title: str) -> str:
    """A fallback routing rule, used only when compilation did not supply one."""
    return {
        "domain": f"Use when the question touches {title}, or when working in that subject.",
        "voice": f"Use when writing or editing prose, to apply the craft from {title}.",
        "language": f"Use when writing or speaking the language taught in {title}.",
    }[kind]


def parse_compiled(text: str, course_id: str, kind: Kind, title: str) -> Capability:
    """Read an agent- or API-written capability body.

    The writer supplies a ``Trigger:`` line and then the pack. Everything else is
    filled in mechanically, so the model never has to produce valid YAML.
    """
    body = text.strip()
    trigger = ""
    match = re.search(r"^\s*(?:\*\*)?Trigger(?:\*\*)?\s*:\s*(.+)$", body, flags=re.MULTILINE)
    if match:
        trigger = match.group(1).strip().strip("*").strip()
        body = (body[: match.start()] + body[match.end() :]).strip()

    if not body:
        raise CapabilityError(f"{course_id}: compiled capability is empty")

    return Capability(
        course=course_id,
        kind=kind,
        title=title or course_id,
        trigger=trigger or suggested_trigger(kind, title or course_id),
        body=body,
    )


def notes_digest(paths: CoursePaths, max_chars: int = 120_000) -> tuple[str, int]:
    """Every note, concatenated, for compilation to read.

    Compilation is cross-episode synthesis: it needs the whole course at once, not
    retrieved fragments, or it will miss the patterns that only show up repeatedly.
    """
    files = sorted(paths.notes.glob("*.md")) if paths.notes.exists() else []
    if not files:
        raise CapabilityError(
            f"course '{paths.root.name}' has no notes yet. "
            f"run: coursebrain prepare {paths.root.name}"
        )
    chunks: list[str] = []
    used = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        if used + len(text) > max_chars:
            chunks.append(f"\n[... {len(files) - len(chunks)} further note(s) omitted for length]")
            break
        chunks.append(text)
        used += len(text)
    return "\n\n---\n\n".join(chunks), len(files)


def profile_kind(profile_name: str, declared: Any) -> Kind:
    if isinstance(declared, str) and declared in KINDS:
        return declared
    return "domain"
