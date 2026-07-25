import pytest

from coursebrain import work
from coursebrain.build import assemble_course
from coursebrain.models import Episode
from coursebrain.paths import CourseConfig, CoursePaths

BODY = """## TL;DR

A summary.

## Concepts

### A thing

Detail. [1:00](https://youtu.be/vid123?t=60)

## Code & APIs

[transcript-derived] `f(x)`.

## Decisions & rationale

They chose X.
"""


@pytest.fixture
def staged(tmp_path):
    paths = CoursePaths.for_course("demo", tmp_path)
    paths.ensure_dirs()
    CourseConfig(id="demo", source_url="https://youtu.be/vid123", profile="programming").dump(
        paths.config
    )
    episode = Episode(
        video_id="vid123",
        index=1,
        title="First episode",
        duration=600.0,
        caption_source="auto",
    )
    item = work.item_for(paths, 1, episode.slug)
    work.write_task(item, episode, "hash123", "SYSTEM TEXT", "USER TEXT")
    return tmp_path, paths, item


def test_task_file_names_the_body_path(staged):
    _, _, item = staged
    text = item.task.read_text()
    assert str(item.body) in text
    assert "SYSTEM TEXT" in text
    assert "USER TEXT" in text
    assert "Do not write frontmatter" in text


def test_item_is_pending_until_body_written(staged):
    _, paths, item = staged
    assert work.pending(paths) == [item]
    item.body.write_text(BODY)
    assert work.pending(paths) == []


def test_whitespace_only_body_stays_pending(staged):
    _, paths, item = staged
    item.body.write_text("   \n\n")
    assert work.pending(paths) == [item]


def test_meta_roundtrip(staged):
    _, _, item = staged
    episode, transcript_hash = work.read_meta(item)
    assert episode.video_id == "vid123"
    assert episode.index == 1
    assert transcript_hash == "hash123"


def test_assemble_produces_a_note_with_frontmatter(staged):
    root, _paths, item = staged
    item.body.write_text(BODY)
    report = assemble_course("demo", root, log=lambda *a: None)
    assert report.assembled == 1
    note = item.note.read_text()
    assert note.startswith("---\n")
    assert "course: demo" in note
    assert "episode: 01" in note
    assert 'duration: "10:00"' in note
    assert "# 01 — First episode" in note
    assert "## TL;DR" in note


def test_assemble_clears_the_work_queue(staged):
    root, paths, item = staged
    item.body.write_text(BODY)
    assemble_course("demo", root, log=lambda *a: None)
    assert not item.task.exists()
    assert not item.body.exists()
    assert not item.meta.exists()
    assert work.pending(paths) == []


def test_assemble_records_the_manifest(staged):
    root, paths, item = staged
    item.body.write_text(BODY)
    assemble_course("demo", root, log=lambda *a: None)
    from coursebrain.manifest import Manifest

    manifest = Manifest.load(paths.manifest, "demo")
    record = manifest.episodes["vid123"]
    assert "distill" in record.stages
    assert record.stages["distill"].tool == "claude-code @ agent"


def test_assemble_skips_unwritten_bodies(staged):
    root, _paths, item = staged
    report = assemble_course("demo", root, log=lambda *a: None)
    assert report.assembled == 0
    assert item.task.exists()


@pytest.mark.parametrize(
    "preamble",
    [
        "Here is the note:\n\n",
        "# 01 — First episode\n\n",
        "I've read the transcript. Note follows.\n\n",
    ],
)
def test_strip_preamble_drops_anything_before_the_first_heading(preamble):
    assert work.strip_preamble(preamble + BODY).startswith("## TL;DR")


def test_strip_preamble_leaves_a_clean_body_alone():
    assert work.strip_preamble(BODY) == BODY.strip()


def test_manifest_survives_an_episode_with_no_captions(tmp_path):
    """A skipped episode has an empty output_hash. Stripping it on write made the
    manifest unloadable, which only showed up on a real playlist."""
    from coursebrain.manifest import Manifest, StageRecord

    path = tmp_path / "manifest.json"
    manifest = Manifest(path, "demo")
    record = manifest.record("silent", 2, "No captions here")
    record.caption_source = "none"
    record.stages["fetch"] = StageRecord(
        input_hash="silent", output_hash="", tool="yt-dlp 1.0", notes="no captions"
    )
    manifest.save()

    reloaded = Manifest.load(path, "demo")
    stage = reloaded.episodes["silent"].stages["fetch"]
    assert stage.output_hash == ""
    assert stage.notes == "no captions"


def test_manifest_omits_optional_fields_when_empty(tmp_path):
    from coursebrain.manifest import Manifest, StageRecord

    path = tmp_path / "manifest.json"
    manifest = Manifest(path, "demo")
    manifest.record("v", 1, "T").stages["fetch"] = StageRecord(
        input_hash="a", output_hash="b", tool="t"
    )
    manifest.save()
    written = path.read_text()
    assert "trace_id" not in written
    assert "notes" not in written
    assert '"output_hash": "b"' in written


def test_manifest_loads_records_written_by_an_older_version(tmp_path):
    """Manifests written before the fix omit empty required fields entirely."""
    import json

    from coursebrain.manifest import Manifest

    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "course": "demo",
                "pipeline_version": "1",
                "episodes": [
                    {
                        "video_id": "old",
                        "index": 1,
                        "title": "Legacy",
                        "caption_source": "none",
                        "stages": {"fetch": {"input_hash": "x", "tool": "yt-dlp"}},
                    }
                ],
            }
        )
    )
    stage = Manifest.load(path, "demo").episodes["old"].stages["fetch"]
    assert stage.output_hash == ""
    assert stage.tool == "yt-dlp"
