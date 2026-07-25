from __future__ import annotations

from coursebrain.models import Chapter, Section, Segment

DEFAULT_WINDOW_WORDS = 1500
MIN_CHAPTER_WORDS = 40


def _join(segments: list[Segment]) -> str:
    return " ".join(s.text for s in segments).strip()


def _by_chapters(segments: list[Segment], chapters: list[Chapter]) -> list[Section]:
    sections: list[Section] = []
    for chapter in chapters:
        inside = [s for s in segments if chapter.start <= s.start < chapter.end]
        text = _join(inside)
        if not text:
            continue
        sections.append(
            Section(
                start=inside[0].start,
                end=inside[-1].end,
                text=text,
                title=chapter.title,
            )
        )

    # a chapter too short to stand alone folds into its neighbour
    merged: list[Section] = []
    for section in sections:
        if merged and len(section.text.split()) < MIN_CHAPTER_WORDS:
            merged[-1].text = f"{merged[-1].text} {section.text}"
            merged[-1].end = section.end
        else:
            merged.append(section)
    return merged


def _by_window(segments: list[Segment], window_words: int) -> list[Section]:
    sections: list[Section] = []
    bucket: list[Segment] = []
    count = 0

    for segment in segments:
        bucket.append(segment)
        count += len(segment.text.split())
        if count >= window_words and segment.text.rstrip().endswith((".", "?", "!")):
            sections.append(Section(start=bucket[0].start, end=bucket[-1].end, text=_join(bucket)))
            bucket, count = [], 0

    if bucket:
        text = _join(bucket)
        if sections and count < MIN_CHAPTER_WORDS:
            sections[-1].text = f"{sections[-1].text} {text}"
            sections[-1].end = bucket[-1].end
        else:
            sections.append(Section(start=bucket[0].start, end=bucket[-1].end, text=text))
    return sections


def segment_episode(
    segments: list[Segment],
    chapters: list[Chapter] | None = None,
    window_words: int = DEFAULT_WINDOW_WORDS,
) -> list[Section]:
    if not segments:
        return []
    if chapters and len(chapters) > 1:
        sections = _by_chapters(segments, chapters)
        if sections:
            return sections
    return _by_window(segments, window_words)


def total_words(sections: list[Section]) -> int:
    return sum(len(s.text.split()) for s in sections)
