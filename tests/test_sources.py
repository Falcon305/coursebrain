from pathlib import Path

import pytest

from coursebrain.models import Episode
from coursebrain.sources import (
    Source,
    SourceError,
    SourceItem,
    load_sources,
    source_for,
    source_named,
)
from coursebrain.sources.youtube import YouTubeSource


class FakeSource:
    """A minimal third-party source, as a plugin author would write one."""

    name = "fake"

    def matches(self, url: str) -> bool:
        return url.startswith("fake://")

    def version(self) -> str:
        return "fake 1.0"

    def enumerate(self, url: str, limit: int | None = None) -> list[SourceItem]:
        items = [SourceItem(id=f"f{i}", title=f"Fake {i}") for i in range(1, 4)]
        return items[:limit] if limit else items

    def fetch(self, item: SourceItem, index: int, raw_dir: Path, language: str) -> Episode:
        return Episode(video_id=item.id, index=index, title=item.title, duration=60.0)

    def subtitle_path(self, video_id: str, raw_dir: Path, language: str) -> Path | None:
        return None


def test_fake_source_satisfies_the_protocol():
    assert isinstance(FakeSource(), Source)


def test_youtube_source_satisfies_the_protocol():
    assert isinstance(YouTubeSource(), Source)


@pytest.mark.parametrize(
    "url",
    [
        "https://youtube.com/watch?v=abc",
        "https://www.youtube.com/playlist?list=PL123",
        "https://youtu.be/abc123",
        "HTTPS://YouTube.com/watch?v=abc",
        "ytsearch3:some query",
        "ytsearchdate1:another",
    ],
)
def test_youtube_matches_its_urls(url):
    assert YouTubeSource().matches(url)


@pytest.mark.parametrize(
    "url",
    ["https://vimeo.com/123", "https://example.com/video.mp4", "fake://thing", "not a url"],
)
def test_youtube_declines_other_urls(url):
    assert not YouTubeSource().matches(url)


def test_youtube_is_registered_by_default():
    assert any(s.name == "youtube" for s in load_sources())


def test_source_for_picks_youtube():
    assert source_for("https://youtu.be/abc").name == "youtube"


def test_source_for_unknown_url_names_the_installed_sources():
    with pytest.raises(SourceError) as exc:
        source_for("gopher://nope")
    assert "youtube" in str(exc.value)


def test_source_named_lookup():
    assert source_named("youtube").name == "youtube"


def test_source_named_unknown_is_actionable():
    with pytest.raises(SourceError) as exc:
        source_named("vimeo")
    assert "installed sources" in str(exc.value)


def test_plugins_cannot_shadow_a_builtin(monkeypatch):
    class Impostor(FakeSource):
        name = "youtube"

    class Entry:
        name = "youtube"

        @staticmethod
        def load():
            return Impostor

    monkeypatch.setattr("coursebrain.sources.entry_points", lambda group: [Entry()])
    youtubes = [s for s in load_sources() if s.name == "youtube"]
    assert len(youtubes) == 1
    assert isinstance(youtubes[0], YouTubeSource)


def test_registered_plugin_is_discovered(monkeypatch):
    class Entry:
        name = "fake"

        @staticmethod
        def load():
            return FakeSource

    monkeypatch.setattr("coursebrain.sources.entry_points", lambda group: [Entry()])
    assert source_for("fake://anything").name == "fake"


def test_a_broken_plugin_fails_loudly(monkeypatch):
    class Entry:
        name = "broken"

        @staticmethod
        def load():
            raise ImportError("missing dependency")

    monkeypatch.setattr("coursebrain.sources.entry_points", lambda group: [Entry()])
    with pytest.raises(SourceError) as exc:
        load_sources()
    assert "broken" in str(exc.value)


def test_enumerate_respects_limit():
    assert len(FakeSource().enumerate("fake://x", limit=2)) == 2


def test_missing_ytdlp_binary_gives_an_install_hint():
    source = YouTubeSource(binary="/nonexistent/yt-dlp")
    with pytest.raises(SourceError) as exc:
        source.version()
    assert "install" in str(exc.value).lower()


def test_subtitle_path_prefers_the_requested_language(tmp_path):
    for name in ("v1.en.vtt", "v1.es.vtt", "v1.fr.vtt"):
        (tmp_path / name).write_text("WEBVTT")
    found = YouTubeSource().subtitle_path("v1", tmp_path, "es")
    assert found is not None and found.name == "v1.es.vtt"


def test_subtitle_path_accepts_regional_variants(tmp_path):
    (tmp_path / "v1.en-GB.vtt").write_text("WEBVTT")
    found = YouTubeSource().subtitle_path("v1", tmp_path, "en")
    assert found is not None and found.name == "v1.en-GB.vtt"


def test_subtitle_path_falls_back_to_any_language(tmp_path):
    (tmp_path / "v1.de.vtt").write_text("WEBVTT")
    assert YouTubeSource().subtitle_path("v1", tmp_path, "en") is not None


def test_subtitle_path_when_nothing_downloaded(tmp_path):
    assert YouTubeSource().subtitle_path("v1", tmp_path, "en") is None
    assert YouTubeSource().subtitle_path("v1", tmp_path / "missing", "en") is None
