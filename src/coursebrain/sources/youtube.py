"""YouTube ingest via yt-dlp. The reference implementation of :class:`Source`.

yt-dlp's CLI is the stable contract, not its Python API, so this shells out. That
also means yt-dlp breakage is the single most likely failure mode in the project:
YouTube changes, yt-dlp ships a fix, and an old pin stops working. Keep it current.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from coursebrain.models import CaptionSource, Chapter, Episode
from coursebrain.sources import SourceError, SourceItem

URL_RE = re.compile(r"(youtube\.com|youtu\.be)/", re.IGNORECASE)
SEARCH_RE = re.compile(r"^yt(search|searchdate)\d*:", re.IGNORECASE)


def resolve_ytdlp() -> str:
    """Prefer the yt-dlp installed alongside the running interpreter.

    A subprocess does not inherit the virtualenv's bin directory on PATH, so
    looking beside sys.executable is what makes this work from an installed CLI.
    """
    local = Path(sys.executable).parent / "yt-dlp"
    if local.exists():
        return str(local)
    return shutil.which("yt-dlp") or "yt-dlp"


class YouTubeSource:
    name = "youtube"

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or resolve_ytdlp()

    # --- Source protocol -------------------------------------------------

    def matches(self, url: str) -> bool:
        return bool(URL_RE.search(url) or SEARCH_RE.match(url))

    def version(self) -> str:
        try:
            out = subprocess.run(
                [self.binary, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
        except FileNotFoundError as e:
            raise SourceError(
                "yt-dlp is not installed. install it with: uv pip install yt-dlp"
            ) from e
        except subprocess.SubprocessError as e:
            raise SourceError(f"yt-dlp is installed but not runnable: {e}") from e
        return f"yt-dlp {out.stdout.strip()}"

    def enumerate(self, url: str, limit: int | None = None) -> list[SourceItem]:
        args = ["--flat-playlist", "--dump-json", url]
        if limit:
            args = ["--playlist-end", str(limit), *args]
        proc = self._run(args, timeout=300)
        if proc.returncode != 0:
            raise SourceError(self._last_error(proc) or f"could not read {url}")

        out: list[SourceItem] = []
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            vid = entry.get("id")
            if vid and entry.get("_type") != "playlist":
                out.append(
                    SourceItem(
                        id=vid,
                        title=entry.get("title") or vid,
                        duration=float(entry["duration"]) if entry.get("duration") else None,
                    )
                )
        if not out:
            raise SourceError(f"no videos found at {url}")
        return out

    def fetch(self, item: SourceItem, index: int, raw_dir: Path, language: str) -> Episode:
        info = self._download_info(item.id, raw_dir)
        duration = float(info.get("duration") or 0.0)
        caption_source = self._download_subtitles(item.id, raw_dir, info, language)
        return Episode(
            video_id=item.id,
            index=index,
            title=info.get("title") or item.title,
            duration=duration,
            caption_source=caption_source,
            caption_lang=language,
            upload_date=info.get("upload_date"),
            description=(info.get("description") or "")[:4000],
            chapters=self._chapters(info, duration),
        )

    def subtitle_path(self, video_id: str, raw_dir: Path, language: str) -> Path | None:
        if not raw_dir.exists():
            return None
        candidates = sorted(raw_dir.glob(f"{video_id}.*.vtt"))
        for candidate in candidates:
            if candidate.stem.endswith(f".{language}") or f".{language}-" in candidate.name:
                return candidate
        return candidates[0] if candidates else None

    # --- internals -------------------------------------------------------

    def _run(self, args: list[str], timeout: int = 600) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.binary, "--no-warnings", "--ignore-config", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    @staticmethod
    def _last_error(proc: subprocess.CompletedProcess[str]) -> str:
        lines = [ln for ln in (proc.stderr or "").splitlines() if ln.strip()]
        return lines[-1] if lines else ""

    @staticmethod
    def _watch_url(video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"

    def _download_info(self, video_id: str, raw_dir: Path) -> dict[str, Any]:
        target = raw_dir / f"{video_id}.info.json"
        if not target.exists():
            raw_dir.mkdir(parents=True, exist_ok=True)
            proc = self._run(
                [
                    "--skip-download",
                    "--write-info-json",
                    "-o",
                    str(raw_dir / "%(id)s.%(ext)s"),
                    self._watch_url(video_id),
                ]
            )
            if not target.exists():
                raise SourceError(self._last_error(proc) or f"no metadata for {video_id}")
        info: dict[str, Any] = json.loads(target.read_text(encoding="utf-8"))
        return info

    def _download_subtitles(
        self, video_id: str, raw_dir: Path, info: dict[str, Any], language: str
    ) -> CaptionSource:
        manual = self._has_manual(info, language)
        if self.subtitle_path(video_id, raw_dir, language):
            return "manual" if manual else "auto"

        args = [
            "--skip-download",
            "--sub-format",
            "vtt/best",
            "--sub-langs",
            f"{language}.*,{language}",
            "-o",
            str(raw_dir / "%(id)s.%(ext)s"),
            self._watch_url(video_id),
        ]
        self._run(["--write-subs" if manual else "--write-auto-subs", *args])
        if self.subtitle_path(video_id, raw_dir, language):
            return "manual" if manual else "auto"

        # a video can advertise manual subs that fail to download; auto is the fallback
        if manual:
            self._run(["--write-auto-subs", *args])
            if self.subtitle_path(video_id, raw_dir, language):
                return "auto"
        return "none"

    @staticmethod
    def _has_manual(info: dict[str, Any], language: str) -> bool:
        subs = info.get("subtitles") or {}
        return any(k == language or k.startswith(f"{language}-") for k in subs)

    @staticmethod
    def _chapters(info: dict[str, Any], duration: float) -> list[Chapter]:
        raw = info.get("chapters") or []
        out: list[Chapter] = []
        for i, ch in enumerate(raw):
            start = float(ch.get("start_time") or 0.0)
            end = ch.get("end_time")
            if end is None:
                end = raw[i + 1]["start_time"] if i + 1 < len(raw) else duration
            out.append(
                Chapter(title=ch.get("title") or f"Chapter {i + 1}", start=start, end=float(end))
            )
        return out
