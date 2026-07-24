import pytest

from pipeline.manifest import Manifest
from pipeline.paths import CourseConfig, CoursePaths
from pipeline.stages.verify import verify_course

NOTE = """---
course: demo
episode: 07
profile: programming
video_id: abc123
url: https://youtu.be/abc123
title: "Effects"
duration: 15:30
source: auto
---

# 07 — Effects

## TL;DR

Short summary.

## Concepts

### Cleanup

Detail here. [2:05](https://youtu.be/abc123?t=125)

## Code & APIs

[transcript-derived] `useEffect(fn, deps)`.

## Decisions & rationale

They chose X over Y. [11:00](https://youtu.be/abc123?t=660)
"""


@pytest.fixture
def course(tmp_path):
    paths = CoursePaths.for_course("demo", tmp_path)
    paths.ensure_dirs()
    CourseConfig(id="demo", source_url="https://youtu.be/abc123", profile="programming").dump(
        paths.config
    )
    (paths.notes / "07-effects.md").write_text(NOTE)
    paths.index_md.write_text("# index")
    paths.concepts_md.write_text("# concepts")
    return tmp_path, paths


def write(paths, text):
    (paths.notes / "07-effects.md").write_text(text)


def test_clean_note_passes(course):
    root, _ = course
    report = verify_course("demo", root)
    assert report.ok, report.problems
    assert report.checked == 1


def test_missing_required_section(course):
    root, paths = course
    write(paths, NOTE.split("## Code & APIs")[0])
    report = verify_course("demo", root)
    assert any("Code & APIs" in p for p in report.problems)


def test_timestamp_past_duration(course):
    root, paths = course
    write(paths, NOTE.replace("?t=660", "?t=5940").replace("[11:00]", "[99:00]"))
    report = verify_course("demo", root)
    assert any("past the episode duration" in p for p in report.problems)


def test_timestamp_past_duration_with_quoted_duration(course):
    root, paths = course
    note = NOTE.replace("duration: 15:30", 'duration: "15:30"')
    write(paths, note.replace("?t=660", "?t=5940").replace("[11:00]", "[99:00]"))
    report = verify_course("demo", root)
    assert any("past the episode duration" in p for p in report.problems)


def test_timestamp_pointing_at_another_video(course):
    root, paths = course
    write(paths, NOTE.replace("youtu.be/abc123?t=125", "youtu.be/OTHER?t=125"))
    report = verify_course("demo", root)
    assert any("different video" in p for p in report.problems)


def test_timestamp_label_disagreeing_with_link(course):
    root, paths = course
    write(paths, NOTE.replace("[2:05](https://youtu.be/abc123?t=125)",
                              "[2:05](https://youtu.be/abc123?t=9000)"))
    report = verify_course("demo", root)
    assert any("disagrees" in p for p in report.problems)


def test_broken_relative_link(course):
    root, paths = course
    write(paths, NOTE + "\nSee [the other note](notes/missing.md).\n")
    report = verify_course("demo", root)
    assert any("broken link" in p for p in report.problems)


def test_episode_with_captions_but_no_note(course):
    root, paths = course
    manifest = Manifest.load(paths.manifest, "demo")
    record = manifest.record("zzz999", 8, "Missing episode")
    record.caption_source = "auto"
    manifest.save()
    report = verify_course("demo", root)
    assert any("no note" in p for p in report.problems)


def test_episode_without_captions_is_not_flagged(course):
    root, paths = course
    manifest = Manifest.load(paths.manifest, "demo")
    manifest.record("zzz999", 8, "Silent episode").caption_source = "none"
    manifest.save()
    report = verify_course("demo", root)
    assert report.ok, report.problems


def test_missing_index_is_flagged(course):
    root, paths = course
    paths.index_md.unlink()
    report = verify_course("demo", root)
    assert any("INDEX.md" in p for p in report.problems)
