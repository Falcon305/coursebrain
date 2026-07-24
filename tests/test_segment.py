from pipeline.models import Chapter, Segment
from pipeline.stages.segment import segment_episode, total_words


def make_segments(n: int, words_each: int = 10, step: float = 5.0) -> list[Segment]:
    return [
        Segment(start=i * step, end=(i + 1) * step, text=" ".join(["word"] * words_each) + ".")
        for i in range(n)
    ]


def test_chapters_drive_segmentation():
    segments = make_segments(30)
    chapters = [
        Chapter(title="Intro", start=0.0, end=50.0),
        Chapter(title="Body", start=50.0, end=100.0),
        Chapter(title="Wrap", start=100.0, end=150.0),
    ]
    sections = segment_episode(segments, chapters)
    assert [s.title for s in sections] == ["Intro", "Body", "Wrap"]
    assert sections[0].start == 0.0
    assert sections[-1].end == 150.0


def test_short_chapter_folds_into_previous():
    segments = make_segments(20)
    chapters = [
        Chapter(title="Long", start=0.0, end=90.0),
        Chapter(title="Blip", start=90.0, end=100.0),
    ]
    sections = segment_episode(segments, chapters)
    assert [s.title for s in sections] == ["Long"]
    assert sections[0].end == 100.0


def test_falls_back_to_windows_without_chapters():
    segments = make_segments(400, words_each=10)
    sections = segment_episode(segments, chapters=None, window_words=500)
    assert len(sections) > 1
    assert all(s.title is None for s in sections)


def test_single_chapter_uses_windows():
    segments = make_segments(200)
    chapters = [Chapter(title="Whole thing", start=0.0, end=1000.0)]
    sections = segment_episode(segments, chapters, window_words=300)
    assert len(sections) > 1


def test_no_words_are_lost():
    segments = make_segments(120, words_each=7)
    expected = sum(len(s.text.split()) for s in segments)
    assert total_words(segment_episode(segments, None, window_words=200)) == expected


def test_empty_input():
    assert segment_episode([], None) == []


def test_chapters_outside_transcript_range_are_dropped():
    segments = make_segments(5)
    chapters = [
        Chapter(title="Real", start=0.0, end=25.0),
        Chapter(title="Ghost", start=900.0, end=1000.0),
    ]
    assert [s.title for s in segment_episode(segments, chapters)] == ["Real"]
