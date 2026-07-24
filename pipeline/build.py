from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .cache import Cache, content_hash
from .manifest import Manifest, StageRecord
from .models import Episode, Segment
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
    distill_episode,
    render_note,
)


@dataclass
class BuildReport:
    fetched: int = 0
    distilled: int = 0
    cached: int = 0
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def line(self) -> str:
        parts = [f"{self.fetched} fetched", f"{self.distilled} distilled", f"{self.cached} cached"]
        if self.skipped:
            parts.append(f"{len(self.skipped)} skipped")
        if self.failed:
            parts.append(f"{len(self.failed)} failed")
        return " | ".join(parts)


def _transcript_path(paths: CoursePaths, episode: Episode) -> Path:
    return paths.transcripts / f"{episode.slug}.jsonl"


def _write_transcript(path: Path, segments: list[Segment]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(s.to_dict(), ensure_ascii=False) for s in segments) + "\n",
        encoding="utf-8",
    )


def _read_transcript(path: Path) -> list[Segment]:
    return [
        Segment.from_dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_course(
    course_id: str,
    courses_dir: Path | None = None,
    limit: int | None = None,
    only: int | None = None,
    model: str = DEFAULT_MODEL,
    force: bool = False,
    fetch_only: bool = False,
    log=print,
) -> BuildReport:
    paths = CoursePaths.for_course(course_id, courses_dir)
    config = paths.load_config()
    profile = Profile.load(config.profile)
    paths.ensure_dirs()

    obs = Observability()
    cache = Cache(paths.cache)
    manifest = Manifest.load(paths.manifest, course_id)
    report = BuildReport()

    log(f"course: {course_id} | profile: {profile.name} | {obs.status}")

    tool = fetch.ytdlp_version()
    entries = fetch.enumerate_source(config.source_url, limit=limit)
    log(f"source: {len(entries)} video(s)")

    prompt = obs.get_prompt("distill", PROMPT_FILE)

    for index, (video_id, raw_title) in enumerate(entries, start=1):
        if only is not None and index != only:
            continue
        label = f"[{index:02d}] {raw_title[:60]}"
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
            log(f"{label} — no captions available, skipped")
            report.skipped.append(video_id)
            record.stages["fetch"] = StageRecord(
                input_hash=video_id, output_hash="", tool=tool, notes="no captions"
            )
            continue

        vtt = fetch._subtitle_path(paths, video_id, config.language)
        segments = normalize.normalize_file(vtt, episode.caption_source)
        transcript_path = _transcript_path(paths, episode)
        _write_transcript(transcript_path, segments)
        transcript_hash = content_hash([s.to_dict() for s in segments])
        record.stages["fetch"] = StageRecord(
            input_hash=video_id, output_hash=transcript_hash, tool=tool
        )

        if fetch_only:
            log(f"{label} — {normalize.word_count(segments)} words")
            continue

        sections = segment.segment_episode(segments, episode.chapters)
        note_path = paths.notes / f"{episode.slug}.md"
        key = cache.key(
            "distill",
            prompt.version,
            {
                "transcript": transcript_hash,
                "profile": profile.name,
                "model": model,
                "glossary": sorted(config.glossary),
                "title": episode.title,
            },
        )

        cached = None if force else cache.get(key)
        if cached is not None and note_path.exists():
            report.cached += 1
            record.stages["distill"] = StageRecord(
                input_hash=transcript_hash,
                output_hash=content_hash(cached["body"]),
                tool=f"{cached['model']} @ {cached['prompt_version']}",
            )
            log(f"{label} — cached")
            continue

        try:
            result = (
                Distillation(**cached)
                if cached is not None
                else distill_episode(
                    episode, sections, profile, config.glossary, model=model, obs=obs
                )
            )
        except Refusal as e:
            log(f"{label} — declined ({e.category}); skipped")
            report.failed.append(video_id)
            continue
        except DistillError as e:
            log(f"{label} — distill failed: {e}")
            report.failed.append(video_id)
            continue

        cache.put(key, {"body": result.body, "model": result.model,
                        "prompt_version": result.prompt_version, "trace_id": result.trace_id})
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(render_note(episode, course_id, profile, result), encoding="utf-8")

        record.stages["distill"] = StageRecord(
            input_hash=transcript_hash,
            output_hash=content_hash(result.body),
            tool=f"{result.model} @ {result.prompt_version}",
            trace_id=result.trace_id,
        )
        report.distilled += 1
        log(f"{label} — {len(result.body.split())} words")

    manifest.save()
    obs.flush()
    log(f"{report.line()} | {cache.stats}")
    return report
