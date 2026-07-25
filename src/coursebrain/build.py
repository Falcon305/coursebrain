from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import work
from .cache import Cache, content_hash
from .manifest import Manifest, StageRecord
from .models import Segment
from .observability import Observability
from .paths import CoursePaths
from .profiles import Profile
from .stages import fetch, normalize, segment
from .stages.distill import (
    DEFAULT_MODEL,
    PROMPT_FILE,
    Distillation,
    DistillError,
    Refusal,
    build_system,
    build_user,
    distill_episode,
    render_note,
)

Logger = Callable[[str], None]


@dataclass
class BuildReport:
    fetched: int = 0
    prepared: int = 0
    distilled: int = 0
    assembled: int = 0
    cached: int = 0
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def line(self) -> str:
        parts = []
        for label, n in (
            ("fetched", self.fetched),
            ("prepared", self.prepared),
            ("distilled", self.distilled),
            ("assembled", self.assembled),
            ("cached", self.cached),
        ):
            if n:
                parts.append(f"{n} {label}")
        if self.skipped:
            parts.append(f"{len(self.skipped)} skipped")
        if self.failed:
            parts.append(f"{len(self.failed)} failed")
        return " | ".join(parts) or "nothing to do"


def _write_transcript(path: Path, segments: list[Segment]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(s.to_dict(), ensure_ascii=False) for s in segments) + "\n",
        encoding="utf-8",
    )


def _distill_cache_key(
    cache: Cache,
    version: str,
    transcript_hash: str,
    profile: Profile,
    model: str,
    glossary: list[str],
    title: str,
) -> str:
    return cache.key(
        "distill",
        version,
        {
            "transcript": transcript_hash,
            "profile": profile.name,
            "model": model,
            "glossary": sorted(glossary),
            "title": title,
        },
    )


def prepare_course(
    course_id: str,
    courses_dir: Path | None = None,
    limit: int | None = None,
    only: int | None = None,
    force: bool = False,
    log: Logger = print,
) -> BuildReport:
    """Fetch, normalize, segment, and stage each episode for distillation.

    Stops short of distilling — an agent (or `distill_pending`) does that next.
    """
    paths = CoursePaths.for_course(course_id, courses_dir)
    config = paths.load_config()
    profile = Profile.load(config.profile)
    paths.ensure_dirs()

    obs = Observability()
    manifest = Manifest.load(paths.manifest, course_id)
    report = BuildReport()

    tool = fetch.ytdlp_version()
    entries = fetch.enumerate_source(config.source_url, limit=limit)
    log(f"{course_id}: {len(entries)} video(s) at source, profile '{profile.name}'")

    prompt = obs.get_prompt("distill", PROMPT_FILE)

    for index, (video_id, raw_title) in enumerate(entries, start=1):
        if only is not None and index != only:
            continue
        label = f"[{index:02d}] {raw_title[:56]}"
        try:
            episode = fetch.fetch_episode(paths, video_id, index, config.language)
        except fetch.FetchError as e:
            log(f"{label} — fetch failed: {e}")
            report.failed.append(video_id)
            continue

        record = manifest.record(video_id, index, episode.title)
        record.caption_source = episode.caption_source
        report.fetched += 1

        if episode.needs_transcription:
            log(f"{label} — no captions, skipped")
            report.skipped.append(video_id)
            record.stages["fetch"] = StageRecord(
                input_hash=video_id, output_hash="", tool=tool, notes="no captions"
            )
            continue

        vtt = fetch.subtitle_path(paths, video_id, config.language)
        if vtt is None:
            # the fetch stage reported captions but the file is gone: a partial
            # download or a hand-edited raw/ directory. Fail this episode loudly
            # rather than crashing the whole run on an attribute error.
            log(f"{label} — caption file missing from raw/, skipped")
            report.failed.append(video_id)
            continue
        segments = normalize.normalize_file(vtt, episode.caption_source)
        _write_transcript(paths.transcripts / f"{episode.slug}.jsonl", segments)
        transcript_hash = content_hash([s.to_dict() for s in segments])
        record.stages["fetch"] = StageRecord(
            input_hash=video_id, output_hash=transcript_hash, tool=tool
        )

        item = work.item_for(paths, index, episode.slug)
        if item.note.exists() and not force:
            log(f"{label} — note exists")
            continue

        sections = segment.segment_episode(segments, episode.chapters)
        work.write_task(
            item,
            episode,
            transcript_hash,
            build_system(profile, prompt, episode),
            build_user(episode, sections, config.glossary),
        )
        report.prepared += 1
        log(f"{label} — staged ({normalize.word_count(segments)} words)")

    manifest.save()
    log(report.line())
    return report


def assemble_course(
    course_id: str, courses_dir: Path | None = None, log: Logger = print
) -> BuildReport:
    """Wrap agent-written bodies in mechanical frontmatter and file them as notes."""
    paths = CoursePaths.for_course(course_id, courses_dir)
    config = paths.load_config()
    profile = Profile.load(config.profile)
    manifest = Manifest.load(paths.manifest, course_id)
    report = BuildReport()

    for item in work.list_items(paths):
        if not item.done:
            continue
        episode, transcript_hash = work.read_meta(item)
        body = work.strip_preamble(item.body.read_text(encoding="utf-8"))
        if not body:
            log(f"[{item.episode:02d}] empty body, left in place")
            report.failed.append(episode.video_id)
            continue

        d = Distillation(body=body, model="claude-code", prompt_version="agent")
        item.note.parent.mkdir(parents=True, exist_ok=True)
        item.note.write_text(render_note(episode, course_id, profile, d), encoding="utf-8")

        record = manifest.record(episode.video_id, episode.index, episode.title)
        record.caption_source = episode.caption_source
        record.stages["distill"] = StageRecord(
            input_hash=transcript_hash,
            output_hash=content_hash(body),
            tool="claude-code @ agent",
        )
        work.clear(item)
        report.assembled += 1
        log(f"[{item.episode:02d}] {item.note.name}")

    manifest.save()
    log(report.line())
    return report


def distill_pending(
    course_id: str,
    courses_dir: Path | None = None,
    model: str = DEFAULT_MODEL,
    force: bool = False,
    log: Logger = print,
) -> BuildReport:
    """Distill staged episodes through the Anthropic API instead of an agent."""
    paths = CoursePaths.for_course(course_id, courses_dir)
    config = paths.load_config()
    profile = Profile.load(config.profile)
    obs = Observability()
    cache = Cache(paths.cache)
    prompt = obs.get_prompt("distill", PROMPT_FILE)
    report = BuildReport()

    for item in work.list_items(paths):
        if item.done and not force:
            continue
        episode, transcript_hash = work.read_meta(item)
        label = f"[{episode.index:02d}] {episode.title[:56]}"
        key = _distill_cache_key(
            cache, prompt.version, transcript_hash, profile, model, config.glossary, episode.title
        )
        cached = None if force else cache.get(key)
        if cached is not None:
            item.body.write_text(cached["body"], encoding="utf-8")
            report.cached += 1
            log(f"{label} — cached")
            continue

        segments = [
            Segment.from_dict(json.loads(line))
            for line in (paths.transcripts / f"{episode.slug}.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        sections = segment.segment_episode(segments, episode.chapters)
        try:
            result = distill_episode(
                episode, sections, profile, config.glossary, model=model, obs=obs
            )
        except Refusal as e:
            log(f"{label} — declined ({e.category})")
            report.failed.append(episode.video_id)
            continue
        except DistillError as e:
            log(f"{label} — failed: {e}")
            report.failed.append(episode.video_id)
            continue

        cache.put(
            key,
            {
                "body": result.body,
                "model": result.model,
                "prompt_version": result.prompt_version,
                "trace_id": result.trace_id,
            },
        )
        item.body.write_text(result.body, encoding="utf-8")
        report.distilled += 1
        log(f"{label} — {len(result.body.split())} words")

    obs.flush()
    log(f"{report.line()} | {cache.stats}")
    return report


def build_course(
    course_id: str,
    courses_dir: Path | None = None,
    limit: int | None = None,
    only: int | None = None,
    model: str = DEFAULT_MODEL,
    force: bool = False,
    fetch_only: bool = False,
    log: Logger = print,
) -> BuildReport:
    """Full unattended build through the API. Agent mode uses prepare + assemble."""
    report = prepare_course(course_id, courses_dir, limit, only, force, log)
    if fetch_only:
        return report
    distilled = distill_pending(course_id, courses_dir, model, force, log)
    assembled = assemble_course(course_id, courses_dir, log)
    report.distilled = distilled.distilled
    report.cached = distilled.cached
    report.assembled = assembled.assembled
    report.failed += distilled.failed + assembled.failed
    return report
