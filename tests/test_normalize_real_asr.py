"""Dedup tested against real YouTube ASR structure, not a hand-simplified fixture.

`tests/fixtures/youtube_asr.en.vtt` reproduces exactly what YouTube serves — cue
timings, tags and layout taken byte for byte from a real auto-captioned video, with
only the words swapped for filler so no third-party transcript ships here. It has: a rolling window that repeats each line across consecutive cues,
inline `<00:00:00.240><c>word</c>` timing tags, 10ms transition cues, and a
leading space-only line inside each cue. Every one of those has broken this
parser at some point, and a simplified fixture passes while real captions fail.
"""

from collections import Counter
from itertools import pairwise
from pathlib import Path

import pytest

from coursebrain.stages.normalize import parse_vtt, to_plain_text, word_count

FIXTURE = Path(__file__).parent / "fixtures" / "youtube_asr.en.vtt"


@pytest.fixture(scope="module")
def raw() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def segments(raw):
    return parse_vtt(raw, dedupe_rolling=True)


def test_the_fixture_is_genuinely_asr(raw):
    # guards against someone "tidying" the fixture into uselessness
    assert "<c>" in raw
    assert raw.count("-->") >= 10
    assert "align:start position:0%" in raw


def test_produces_segments(segments):
    assert len(segments) >= 4


def test_no_inline_markup_survives(segments):
    for segment in segments:
        assert "<c>" not in segment.text
        assert "</c>" not in segment.text
        assert "00:00:" not in segment.text


def test_no_adjacent_duplicates(segments):
    texts = [s.text for s in segments]
    assert all(a != b for a, b in pairwise(texts))


def test_the_rolling_window_is_actually_collapsed(raw, segments):
    """The whole point: real ASR repeats ~2/3 of its words across cues."""
    raw_words = sum(
        len(line.split())
        for line in raw.splitlines()
        if line.strip()
        and "-->" not in line
        and not line.startswith(("WEBVTT", "Kind:", "Language:"))
    )
    assert word_count(segments) < raw_words * 0.7


def test_first_line_of_the_first_cue_is_not_lost(segments):
    # a space-only line follows the timing line; treating it as a terminator
    # silently dropped the opening words of every cue
    assert segments[0].text.startswith("the quick brown fox")


def test_timestamps_are_monotonic_and_sane(segments):
    assert all(a.start <= b.start for a, b in pairwise(segments))
    assert all(s.end >= s.start for s in segments)
    assert segments[0].start < 1.0


def test_text_reads_as_continuous_prose(segments):
    text = to_plain_text(segments)
    assert "quick brown fox" in text
    # a phrase repeated by the rolling window must appear once, not three times
    assert text.count("the quick brown fox") == 1


def test_no_word_is_tripled(segments):
    """The characteristic failure: naive parsers emit each line three times."""
    text = to_plain_text(segments).lower()
    for phrase in Counter(
        " ".join(w) for w in zip(text.split(), text.split()[1:], text.split()[2:], strict=False)
    ).most_common(3):
        assert phrase[1] <= 2, f"{phrase[0]!r} appears {phrase[1]} times"


def test_manual_mode_would_not_collapse_this(raw, segments):
    """Sanity check that dedup is doing the work, not the cue structure."""
    undeduped = parse_vtt(raw, dedupe_rolling=False)
    assert len(undeduped) > len(segments)
    assert word_count(undeduped) > word_count(segments)
