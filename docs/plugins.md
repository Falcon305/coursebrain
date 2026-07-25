# Writing a source plugin

A **source** turns a URL into a list of episodes and fetches transcripts for them. YouTube
is the built-in one; anything else — Vimeo, a podcast feed, a Coursera export, local files —
is a plugin that lives in your own package.

## The protocol

```python
from pathlib import Path
from coursebrain.models import Episode
from coursebrain.sources import SourceError, SourceItem


class VimeoSource:
    name = "vimeo"

    def matches(self, url: str) -> bool:
        """True when this source handles the URL."""

    def version(self) -> str:
        """Recorded in the manifest, e.g. "vimeo-dl 1.2.0"."""

    def enumerate(self, url: str, limit: int | None = None) -> list[SourceItem]:
        """List the episodes at the URL, in course order."""

    def fetch(self, item: SourceItem, index: int, raw_dir: Path, language: str) -> Episode:
        """Download metadata and captions into raw_dir, and describe the episode."""

    def subtitle_path(self, video_id: str, raw_dir: Path, language: str) -> Path | None:
        """Where fetch put the subtitles, or None if it found none."""
```

`Source` is a runtime-checkable `Protocol`, so you can assert conformance in your own tests:

```python
from coursebrain.sources import Source


def test_conforms():
    assert isinstance(VimeoSource(), Source)
```

## Registering it

```toml
[project.entry-points."coursebrain.sources"]
vimeo = "coursebrain_vimeo:VimeoSource"
```

Install your package and `coursebrain sources` lists it. `coursebrain learn <url>` will
route to it automatically when `matches()` returns true.

## Rules that matter

**No captions is a skip, not a failure.** Return an `Episode` with
`caption_source="none"` rather than raising. The pipeline reports it and moves on; raising
aborts an episode that was merely quiet.

**Raise `SourceError` with a message a user can act on.** These go straight to the terminal.
*"yt-dlp is not installed. install it with: uv pip install yt-dlp"* is useful;
*"subprocess failed with code 1"* is not.

**`fetch` runs in a thread pool.** Episodes are fetched concurrently, so do not rely on
call order and do not mutate shared state without a lock. Writing distinct files under
`raw_dir` is fine.

**Be honest about timestamps.** The provenance model assumes citations are checkable — a
reader clicks a timestamp and lands at the moment. If your source cannot supply real
timestamps, document it. Emitting uncheckable citations is worse than emitting none.

**A broken plugin fails loudly.** If your entry point raises on import, `load_sources()`
raises `SourceError` naming your plugin rather than silently dropping it.

**You cannot shadow a built-in.** A plugin registered as `youtube` is ignored in favour of
the built-in, so an accidental name clash cannot hijack ingestion.

## Reference implementation

`src/coursebrain/sources/youtube.py` is the one to copy. It shows the subprocess pattern,
the manual-then-auto caption fallback, chapter extraction, and how to resolve a binary that
lives beside the interpreter rather than on `PATH`.
