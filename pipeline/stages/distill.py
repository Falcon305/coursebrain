from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import Episode, Section, format_timestamp
from ..observability import Observability, Prompt
from ..profiles import Profile

DEFAULT_MODEL = "claude-opus-5"
MAX_TOKENS = 32000
MARKER_INTERVAL = 30.0
CHUNK_WORDS = 12000

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "distill.md"


class DistillError(RuntimeError):
    pass


class Refusal(DistillError):
    def __init__(self, category: str | None, explanation: str = "") -> None:
        super().__init__(f"model declined to process this episode ({category or 'unspecified'})")
        self.category = category
        self.explanation = explanation


@dataclass
class Distillation:
    body: str
    model: str
    prompt_version: str
    trace_id: str | None = None


def render_transcript(sections: list[Section], interval: float = MARKER_INTERVAL) -> str:
    out: list[str] = []
    for section in sections:
        if section.title:
            out.append(f"\n### {section.title}  [{format_timestamp(section.start)}]\n")
        words = section.text.split()
        if not words:
            continue
        span = max(section.end - section.start, 1.0)
        per_word = span / len(words)
        marks = max(1, int(span // interval))
        stride = max(1, len(words) // marks)
        for i in range(0, len(words), stride):
            at = section.start + i * per_word
            out.append(f"[{format_timestamp(at)}] {' '.join(words[i : i + stride])}")
    return "\n".join(out).strip()


def _chunk(sections: list[Section], limit: int = CHUNK_WORDS) -> list[list[Section]]:
    chunks: list[list[Section]] = []
    current: list[Section] = []
    count = 0
    for section in sections:
        words = len(section.text.split())
        if current and count + words > limit:
            chunks.append(current)
            current, count = [], 0
        current.append(section)
        count += words
    if current:
        chunks.append(current)
    return chunks


def build_system(profile: Profile, prompt: Prompt, episode: Episode) -> str:
    return prompt.text.format(
        profile_description=profile.description,
        distill_guidance=profile.distill_guidance or "",
        sections=profile.render_schema(),
        video_id=episode.video_id,
        duration_display=format_timestamp(episode.duration),
        first_section=profile.headings[0],
    )


def build_user(
    episode: Episode,
    sections: list[Section],
    glossary: list[str],
    part: tuple[int, int] | None = None,
) -> str:
    lines = [
        f"Title: {episode.title}",
        f"Video: {episode.url}",
        f"Duration: {format_timestamp(episode.duration)}",
        f"Captions: {episode.caption_source}-generated",
    ]
    if episode.upload_date:
        lines.append(f"Published: {episode.upload_date}")
    if episode.chapters:
        chapter_list = ", ".join(
            f"{c.title} [{format_timestamp(c.start)}]" for c in episode.chapters[:40]
        )
        lines.append(f"Chapters: {chapter_list}")
    if glossary:
        lines.append("")
        lines.append(
            "Glossary of real terms used in this material — repair mangled caption forms "
            "against these when the intent is clear:"
        )
        lines.append(", ".join(sorted(set(glossary))[:300]))
    if part:
        lines.append("")
        lines.append(
            f"This is part {part[0]} of {part[1]} of a long episode. Cover only what appears "
            "below; the parts are merged afterward."
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(render_transcript(sections))
    return "\n".join(lines)


def _client() -> Any:
    try:
        import anthropic
    except ImportError as e:
        raise DistillError("anthropic sdk not installed") from e
    return anthropic.Anthropic()


def _call(client: Any, system: str, user: str, model: str) -> Any:
    with client.beta.messages.stream(
        model=model,
        max_tokens=MAX_TOKENS,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    ) as stream:
        return stream.get_final_message()


def _text_of(message: Any) -> str:
    return "".join(b.text for b in message.content if b.type == "text").strip()


def _merge(parts: list[str], profile: Profile) -> str:
    if len(parts) == 1:
        return parts[0]
    buckets: dict[str, list[str]] = {h: [] for h in profile.headings}
    for part in parts:
        current: str | None = None
        for line in part.splitlines():
            match = re.match(r"^##\s+(.+?)\s*$", line)
            if match and match.group(1) in buckets:
                current = match.group(1)
                continue
            if current:
                buckets[current].append(line)
    out: list[str] = []
    for heading in profile.headings:
        body = "\n".join(buckets[heading]).strip()
        if body:
            out.append(f"## {heading}\n\n{body}")
    return "\n\n".join(out)


def distill_episode(
    episode: Episode,
    sections: list[Section],
    profile: Profile,
    glossary: list[str] | None = None,
    model: str = DEFAULT_MODEL,
    obs: Observability | None = None,
    client: Any = None,
) -> Distillation:
    if not sections:
        raise DistillError(f"episode {episode.index} has no transcript to distill")

    obs = obs or Observability()
    prompt = obs.get_prompt("distill", PROMPT_FILE)
    client = client or _client()
    system = build_system(profile, prompt, episode)
    chunks = _chunk(sections)

    parts: list[str] = []
    trace_id: str | None = None
    for i, chunk in enumerate(chunks, start=1):
        part = (i, len(chunks)) if len(chunks) > 1 else None
        user = build_user(episode, chunk, glossary or [], part)
        with obs.span(
            "distill",
            episode=episode.index,
            video_id=episode.video_id,
            profile=profile.name,
            model=model,
            prompt_version=prompt.version,
            part=i,
        ) as span:
            message = _call(client, system, user, model)
            trace_id = trace_id or getattr(span, "trace_id", None)
            if message.stop_reason == "refusal":
                details = getattr(message, "stop_details", None)
                raise Refusal(
                    getattr(details, "category", None),
                    getattr(details, "explanation", "") or "",
                )
            body = _text_of(message)
            if not body:
                raise DistillError(f"empty distillation for episode {episode.index}")
            parts.append(body)

    return Distillation(
        body=_merge(parts, profile),
        model=model,
        prompt_version=prompt.version,
        trace_id=trace_id,
    )


def render_note(episode: Episode, course_id: str, profile: Profile, d: Distillation) -> str:
    concepts = re.findall(r"^###\s+(.+?)\s*$", d.body, flags=re.MULTILINE)
    front = [
        "---",
        f"course: {course_id}",
        f"episode: {episode.index:02d}",
        f"profile: {profile.name}",
        f"video_id: {episode.video_id}",
        f"url: {episode.url}",
        f"title: {_yaml_str(episode.title)}",
        f"duration: {_yaml_str(format_timestamp(episode.duration))}",
        f"source: {episode.caption_source}",
        f"distilled_with: {d.model} @ {d.prompt_version}",
    ]
    if episode.upload_date:
        front.append(f"published: {episode.upload_date}")
    if concepts:
        front.append(f"{profile.concept_label}:")
        front += [f"  - {_yaml_str(c)}" for c in concepts[:40]]
    front.append("---")
    return "\n".join(front) + f"\n\n# {episode.index:02d} — {episode.title}\n\n{d.body}\n"


def _yaml_str(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def api_key_present() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
