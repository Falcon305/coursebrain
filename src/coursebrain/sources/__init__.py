"""Ingest sources.

A source turns a URL into a list of episodes and fetches transcripts for them.
Third parties register their own through the ``coursebrain.sources`` entry point
group, so adding Vimeo or a podcast feed needs no change to this package.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import Protocol, runtime_checkable

from coursebrain.models import Episode

ENTRY_POINT_GROUP = "coursebrain.sources"


class SourceError(RuntimeError):
    """Raised when a source cannot enumerate or fetch. Message is user-facing."""


@dataclass(frozen=True)
class SourceItem:
    """One episode as the source sees it, before any transcript is fetched."""

    id: str
    title: str
    duration: float | None = None


@runtime_checkable
class Source(Protocol):
    """What a source must provide.

    Implementations should raise :class:`SourceError` with a message a user can act
    on. If a source cannot supply timestamps, say so in its documentation — the
    provenance model assumes citations are checkable, and emitting uncheckable ones
    is worse than emitting none.
    """

    name: str

    def matches(self, url: str) -> bool:
        """True when this source handles the URL."""
        ...

    def version(self) -> str:
        """Identifier recorded in the manifest, e.g. ``"yt-dlp 2026.7.4"``."""
        ...

    def enumerate(self, url: str, limit: int | None = None) -> list[SourceItem]:
        """List the episodes at the URL, in course order."""
        ...

    def fetch(self, item: SourceItem, index: int, raw_dir: Path, language: str) -> Episode:
        """Download metadata and captions into ``raw_dir`` and describe the episode.

        Set ``caption_source="none"`` rather than raising when captions are simply
        unavailable — that is a skip, not a failure.
        """
        ...

    def subtitle_path(self, video_id: str, raw_dir: Path, language: str) -> Path | None:
        """Where ``fetch`` put the subtitles, or None if it found none."""
        ...


def _builtin_sources() -> list[Source]:
    from coursebrain.sources.youtube import YouTubeSource

    return [YouTubeSource()]


def load_sources() -> list[Source]:
    """Built-in sources first, then any registered by installed packages."""
    sources = _builtin_sources()
    known = {s.name for s in sources}
    for entry in entry_points(group=ENTRY_POINT_GROUP):
        if entry.name in known:
            continue  # a plugin must not silently shadow a built-in
        try:
            source = entry.load()()
        except Exception as e:  # a broken plugin must not take the tool down
            raise SourceError(f"source plugin '{entry.name}' failed to load: {e}") from e
        sources.append(source)
        known.add(entry.name)
    return sources


def source_for(url: str) -> Source:
    for source in load_sources():
        if source.matches(url):
            return source
    names = ", ".join(s.name for s in load_sources())
    raise SourceError(f"no source handles {url!r}. installed sources: {names}")


def source_named(name: str) -> Source:
    for source in load_sources():
        if source.name == name:
            return source
    names = ", ".join(s.name for s in load_sources())
    raise SourceError(f"unknown source {name!r}. installed sources: {names}")
