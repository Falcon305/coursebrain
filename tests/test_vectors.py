import pytest

from pipeline.notes import Chunk
from pipeline.retrieval import build_index, search, vector_search, vectors_available

pytestmark = pytest.mark.skipif(
    not vectors_available(), reason="semantic search needs the 'rag' extra"
)


def chunk(course, episode, heading, text):
    return Chunk(
        course=course, episode=episode, video_id="v", note_path="p",
        title="t", heading=heading, text=text,
    )


CHUNKS = [
    chunk("c", 1, "Revalidation", "Serve the cached copy, then refresh it in the background."),
    chunk("c", 2, "Routing", "Each folder under app maps to a URL segment."),
    chunk("c", 3, "Fonts", "Self-host typefaces to avoid a layout shift on first paint."),
    chunk("other", 4, "Revalidation", "A different course also covers cache refreshing."),
]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "index.db"
    indexed, embedded = build_index(path, CHUNKS)
    assert indexed == len(CHUNKS)
    assert embedded == len(CHUNKS)
    return path


def test_vector_search_finds_paraphrase(db):
    # none of these words appear in the chunk — this is the case keyword search misses
    hits = vector_search(db, "how do I deal with stale data", k=2)
    assert hits
    assert hits[0].heading == "Revalidation"


def test_vector_search_respects_course_filter(db):
    hits = vector_search(db, "stale data", k=4, course="other")
    assert hits
    assert all(h.course == "other" for h in hits)


def test_hybrid_beats_keyword_alone_on_vocabulary_mismatch(db):
    from pipeline.retrieval import keyword_search

    query = "how do I deal with stale data"
    keyword_only = keyword_search(db, query, k=3)
    hybrid = search(db, query, k=3)
    assert not any(c.heading == "Revalidation" for c in keyword_only)
    assert any(h.chunk.heading == "Revalidation" for h in hybrid)


def test_index_is_a_single_file(db):
    assert db.is_file()
    assert not (db.parent / "lancedb").exists()


def test_rebuild_replaces_rather_than_appends(tmp_path):
    path = tmp_path / "index.db"
    build_index(path, CHUNKS)
    indexed, embedded = build_index(path, CHUNKS[:2])
    assert indexed == 2 and embedded == 2
    assert len(vector_search(path, "anything at all", k=10)) <= 2
