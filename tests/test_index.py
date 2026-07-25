import pytest

from coursebrain.notes import parse_note
from coursebrain.paths import CourseConfig, CoursePaths
from coursebrain.stages.index import (
    index_all,
    index_course,
    render_brain,
    render_concepts,
    render_course_index,
)

NOTE = """---
course: demo
episode: {n:02d}
video_id: vid{n}
url: https://youtu.be/vid{n}
title: "Episode {n}"
duration: "10:00"
concepts:
  - "Concept {n}"
  - "Shared concept"
---

# {n:02d} — Episode {n}

## TL;DR

Summary of episode {n}.

## Concepts

### Concept {n}

Detail. [1:00](https://youtu.be/vid{n}?t=60)

### Shared concept

Also covered here.
"""


@pytest.fixture
def course(tmp_path):
    paths = CoursePaths.for_course("demo", tmp_path / "courses")
    paths.ensure_dirs()
    CourseConfig(
        id="demo", source_url="https://x", profile="programming", title="Demo Course"
    ).dump(paths.config)
    for n in (1, 2):
        (paths.notes / f"{n:02d}-episode.md").write_text(NOTE.format(n=n))
    return tmp_path, paths


def notes_of(paths):
    return [parse_note(p) for p in sorted(paths.notes.glob("*.md"))]


def test_course_index_lists_every_episode(course):
    _, paths = course
    out = render_course_index("demo", "Demo Course", notes_of(paths))
    assert "# Demo Course" in out
    assert "01. Episode 1" in out
    assert "02. Episode 2" in out
    assert "Summary of episode 1." in out


def test_course_index_links_are_relative_to_the_course(course):
    _, paths = course
    out = render_course_index("demo", "Demo Course", notes_of(paths))
    assert "(notes/01-episode.md)" in out


def test_course_index_falls_back_to_the_id_without_a_title(course):
    _, paths = course
    assert render_course_index("demo", "", notes_of(paths)).startswith("# demo")


def test_concepts_group_episodes_under_a_shared_concept(course):
    _, paths = course
    out = render_concepts(notes_of(paths))
    line = next(li for li in out.splitlines() if "Shared concept" in li)
    assert "ep01" in line and "ep02" in line


def test_concepts_handles_no_notes():
    assert "No concepts" in render_concepts([])


def test_brain_lists_courses():
    out = render_brain([("demo", "Demo Course", "programming", 2)])
    assert "Demo Course" in out
    assert "(courses/demo/INDEX.md)" in out
    assert "programming, 2 episode(s)" in out


def test_brain_handles_empty_workspace():
    assert "No courses indexed" in render_brain([])


def test_index_course_writes_both_files_and_returns_chunks(course):
    root, paths = course
    chunks, count = index_course("demo", root / "courses")
    assert count == 2
    assert chunks
    assert paths.index_md.exists()
    assert paths.concepts_md.exists()


def test_index_all_writes_brain_and_builds_the_index(course, monkeypatch):
    root, _ = course
    monkeypatch.chdir(root)
    indexed = index_all(root / "courses", use_vectors=False, log=lambda *a: None)
    assert indexed > 0
    assert (root / "BRAIN.md").exists()
    assert (root / ".brain" / "index.db").exists()


def test_index_all_on_an_empty_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert index_all(tmp_path / "courses", use_vectors=False, log=lambda *a: None) == 0
    assert "No courses indexed" in (tmp_path / "BRAIN.md").read_text()
