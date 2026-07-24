import pytest

from pipeline.notes import Chunk, parse_note, split_frontmatter
from pipeline.retrieval import (
    build_keyword_index,
    fts_query,
    keyword_search,
    reciprocal_rank_fusion,
    search,
)

NOTE = """---
course: react
episode: 07
video_id: abc123
title: "Effects and cleanup"
duration: 15:30
concepts:
  - "Effect cleanup"
  - "Stale closures"
---

# 07 — Effects and cleanup

## TL;DR

Effects run after paint and must clean up after themselves.

## Concepts

### Effect cleanup

Return a function to tear down subscriptions. [2:05](https://youtu.be/abc123?t=125)

### Stale closures

An effect captures the render it was created in. [8:20](https://youtu.be/abc123?t=500)

## Gotchas

Empty dependency arrays freeze the first render's values.
"""


@pytest.fixture
def note(tmp_path):
    path = tmp_path / "07-effects.md"
    path.write_text(NOTE)
    return parse_note(path)


def test_split_frontmatter_parses_yaml():
    meta, body = split_frontmatter(NOTE)
    assert meta["course"] == "react"
    assert meta["video_id"] == "abc123"
    assert body.lstrip().startswith("# 07")


def test_split_frontmatter_without_frontmatter():
    meta, body = split_frontmatter("# just a title\n")
    assert meta == {}
    assert body.startswith("# just")


def test_note_metadata(note):
    assert note.course == "react"
    assert note.episode == 7
    assert note.title == "Effects and cleanup"
    assert note.concepts == ["Effect cleanup", "Stale closures"]


def test_note_summary_comes_from_tldr(note):
    assert note.summary.startswith("Effects run after paint")


def test_chunks_split_on_headings(note):
    headings = [c.heading for c in note.chunks]
    assert "TL;DR" in headings
    assert "Concepts > Effect cleanup" in headings
    assert "Concepts > Stale closures" in headings
    assert "Gotchas" in headings


def test_chunks_capture_first_timestamp(note):
    cleanup = next(c for c in note.chunks if c.heading.endswith("Effect cleanup"))
    assert cleanup.timestamp == 125
    assert cleanup.url == "https://youtu.be/abc123?t=125"


def test_chunk_without_timestamp_falls_back_to_video_url(note):
    gotchas = next(c for c in note.chunks if c.heading == "Gotchas")
    assert gotchas.timestamp is None
    assert gotchas.url == "https://youtu.be/abc123"


def test_fts_query_quotes_terms_and_drops_punctuation():
    assert fts_query("stale cache?") == '"stale" OR "cache"'


def test_fts_query_survives_operators():
    assert '"AND"' in fts_query("foo AND bar") or fts_query("foo AND bar")


def test_fts_query_empty_input():
    assert fts_query("!!! ?") == ""


def test_keyword_index_roundtrip(tmp_path, note):
    db = tmp_path / "index.db"
    assert build_keyword_index(db, note.chunks) == len(note.chunks)
    hits = keyword_search(db, "cleanup subscriptions", k=5)
    assert hits
    assert any("Effect cleanup" in h.heading for h in hits)


def test_keyword_search_filters_by_course(tmp_path, note):
    db = tmp_path / "index.db"
    build_keyword_index(db, note.chunks)
    assert keyword_search(db, "cleanup", k=5, course="react")
    assert keyword_search(db, "cleanup", k=5, course="other") == []


def test_keyword_search_on_missing_db(tmp_path):
    assert keyword_search(tmp_path / "nope.db", "anything", k=5) == []


def test_keyword_search_does_not_crash_on_fts_syntax(tmp_path, note):
    db = tmp_path / "index.db"
    build_keyword_index(db, note.chunks)
    for query in ['"unbalanced', "foo NEAR/", "a AND OR b", "*", "()"]:
        keyword_search(db, query, k=3)


def make_chunk(course, episode, heading):
    return Chunk(
        course=course, episode=episode, video_id="v", note_path="p",
        title="t", heading=heading, text="body",
    )


def test_rrf_rewards_agreement_across_sources():
    a = make_chunk("c", 1, "agreed")
    b = make_chunk("c", 2, "keyword only")
    c = make_chunk("c", 3, "vector only")
    hits = reciprocal_rank_fusion({"keyword": [b, a], "vector": [c, a]}, k=3)
    assert hits[0].chunk.heading == "agreed"
    assert set(hits[0].sources) == {"keyword", "vector"}


def test_rrf_preserves_single_source_order():
    chunks = [make_chunk("c", i, f"h{i}") for i in range(4)]
    hits = reciprocal_rank_fusion({"keyword": chunks}, k=4)
    assert [h.chunk.heading for h in hits] == ["h0", "h1", "h2", "h3"]


def test_rrf_empty():
    assert reciprocal_rank_fusion({"keyword": []}, k=5) == []


def test_search_without_vectors_still_works(tmp_path, note):
    db = tmp_path / "index.db"
    build_keyword_index(db, note.chunks)
    hits = search(db, tmp_path / "lancedb", "stale closures", k=3, use_vectors=False)
    assert hits
    assert hits[0].sources == ("keyword",)
