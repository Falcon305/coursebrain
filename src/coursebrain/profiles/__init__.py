from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROFILES_DIR = Path(__file__).resolve().parent

COMMON_SECTIONS = [
    {
        "heading": "Unclear from audio",
        "guidance": (
            "Anything the speaker referred to that the transcript does not resolve. "
            "Omit the section entirely if nothing qualifies."
        ),
    },
    {
        "heading": "Visual blind spots",
        "guidance": (
            "Every moment the speaker points at something on screen that audio alone cannot "
            "capture: 'as you can see here', 'this diagram', 'the code on the right', "
            "'look at this chart'. One bullet each, formatted `- [M:SS] short description of what "
            "was being shown`. This is a work list for a later visual pass, so err toward "
            "including a moment rather than omitting it."
        ),
    },
]


@dataclass
class Section:
    heading: str
    guidance: str


@dataclass
class Profile:
    name: str
    description: str
    sections: list[Section]
    distill_guidance: str = ""
    concept_label: str = "concepts"
    capability_kind: str = "domain"
    capability_guidance: str = ""

    @property
    def headings(self) -> list[str]:
        return [s.heading for s in self.sections]

    def render_schema(self) -> str:
        lines = []
        for section in self.sections:
            lines.append(f"## {section.heading}")
            lines.append(f"  {section.guidance}")
            lines.append("")
        return "\n".join(lines).rstrip()

    @classmethod
    def load(cls, name: str, profiles_dir: Path | None = None) -> Profile:
        path = (profiles_dir or PROFILES_DIR) / f"{name}.yaml"
        if not path.exists():
            available = ", ".join(list_profiles(profiles_dir))
            raise ValueError(f"unknown profile '{name}'. available: {available}")
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        sections = [Section(**s) for s in data.get("sections", [])]
        sections += [Section(**s) for s in COMMON_SECTIONS]
        return cls(
            name=data.get("name", name),
            description=data.get("description", ""),
            sections=sections,
            distill_guidance=data.get("distill_guidance", "").strip(),
            concept_label=data.get("concept_label", "concepts"),
            capability_kind=data.get("capability_kind", "domain"),
            capability_guidance=data.get("capability_guidance", "").strip(),
        )


def list_profiles(profiles_dir: Path | None = None) -> list[str]:
    base = profiles_dir or PROFILES_DIR
    if not base.exists():
        return []
    return sorted(p.stem for p in base.glob("*.yaml"))
