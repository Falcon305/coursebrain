from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ..models import Chapter, Episode
from ..paths import CoursePaths

YTDLP = "yt-dlp"


class FetchError(RuntimeError):
    pass


def ytdlp_version() -> str:
    try:
        out = subprocess.run(
            [YTDLP, "--version"], capture_output=True, text=True, timeout=30, check=True
        )
        return f"yt-dlp {out.stdout.strip()}"
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        raise FetchError(f"yt-dlp unavailable: {e}") from e


def _run(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [YTDLP, "--no-warnings", "--ignore-config", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def enumerate_source(url: str, limit: int | None = None) -> list[tuple[str, str]]:
    args = ["--flat-playlist", "--dump-json", url]
    if limit:
        args = ["--playlist-end", str(limit), *args]
    proc = _run(args, timeout=300)
    if proc.returncode != 0:
        raise FetchError(proc.stderr.strip().splitlines()[-1] if proc.stderr else "enumerate failed")

    out: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        vid = entry.get("id")
        if vid and entry.get("_type") != "playlist":
            out.append((vid, entry.get("title") or vid))
    if not out:
        raise FetchError(f"no videos found at {url}")
    return out


def _info_path(paths: CoursePaths, video_id: str) -> Path:
    return paths.raw / f"{video_id}.info.json"


def _subtitle_path(paths: CoursePaths, video_id: str, lang: str) -> Path | None:
    for candidate in sorted(paths.raw.glob(f"{video_id}.*.vtt")):
        if candidate.stem.endswith(f".{lang}") or f".{lang}-" in candidate.name:
            return candidate
    matches = sorted(paths.raw.glob(f"{video_id}.*.vtt"))
    return matches[0] if matches else None


def _download_info(paths: CoursePaths, video_id: str) -> dict:
    target = _info_path(paths, video_id)
    if not target.exists():
        proc = _run(
            [
                "--skip-download",
                "--write-info-json",
                "-o",
                str(paths.raw / "%(id)s.%(ext)s"),
                f"https://www.youtube.com/watch?v={video_id}",
            ]
        )
        if not target.exists():
            raise FetchError(proc.stderr.strip().splitlines()[-1] if proc.stderr else "no info.json")
    return json.loads(target.read_text(encoding="utf-8"))


def _download_subtitles(paths: CoursePaths, video_id: str, info: dict, lang: str) -> str:
    existing = _subtitle_path(paths, video_id, lang)
    if existing:
        return "manual" if _has_manual(info, lang) else "auto"

    manual = _has_manual(info, lang)
    args = [
        "--skip-download",
        "--sub-format",
        "vtt/best",
        "--sub-langs",
        f"{lang}.*,{lang}",
        "-o",
        str(paths.raw / "%(id)s.%(ext)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    args.insert(0, "--write-subs" if manual else "--write-auto-subs")
    _run(args)

    if _subtitle_path(paths, video_id, lang):
        return "manual" if manual else "auto"

    if manual:
        _run(["--write-auto-subs", *args[1:]])
        if _subtitle_path(paths, video_id, lang):
            return "auto"
    return "none"


def _has_manual(info: dict, lang: str) -> bool:
    subs = info.get("subtitles") or {}
    return any(k == lang or k.startswith(f"{lang}-") for k in subs)


def _chapters(info: dict, duration: float) -> list[Chapter]:
    raw = info.get("chapters") or []
    out: list[Chapter] = []
    for i, ch in enumerate(raw):
        start = float(ch.get("start_time") or 0.0)
        end = ch.get("end_time")
        if end is None:
            end = raw[i + 1]["start_time"] if i + 1 < len(raw) else duration
        out.append(Chapter(title=ch.get("title") or f"Chapter {i + 1}", start=start, end=float(end)))
    return out


def fetch_episode(paths: CoursePaths, video_id: str, index: int, lang: str) -> Episode:
    info = _download_info(paths, video_id)
    duration = float(info.get("duration") or 0.0)
    source = _download_subtitles(paths, video_id, info, lang)
    return Episode(
        video_id=video_id,
        index=index,
        title=info.get("title") or video_id,
        duration=duration,
        caption_source=source,
        caption_lang=lang,
        upload_date=info.get("upload_date"),
        description=(info.get("description") or "")[:4000],
        chapters=_chapters(info, duration),
    )
