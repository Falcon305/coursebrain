import json

import pytest
from typer.testing import CliRunner

from coursebrain.cli import app
from coursebrain.notes import Chunk
from coursebrain.paths import BrainPaths, CourseConfig, CoursePaths
from coursebrain.retrieval import build_index, vectors_available

runner = CliRunner()

NOTE = """---
course: demo
episode: 01
profile: programming
video_id: vid1
url: https://youtu.be/vid1
title: "Effects"
duration: "10:00"
source: auto
concepts:
  - "Cleanup"
---

# 01 — Effects

## TL;DR

Effects tear down what they set up.

## Concepts

### Cleanup

Return a teardown function. [1:00](https://youtu.be/vid1?t=60)

## Code & APIs

[transcript-derived] `useEffect(fn, deps)`.

## Decisions & rationale

Explicit dependencies over auto-tracking.
"""


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSEBRAIN_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    paths = CoursePaths.for_course("demo", tmp_path / "courses")
    paths.ensure_dirs()
    CourseConfig(
        id="demo", source_url="https://youtu.be/vid1", profile="programming", title="Demo"
    ).dump(paths.config)
    (paths.notes / "01-effects.md").write_text(NOTE)
    return tmp_path


@pytest.fixture
def indexed(workspace):
    chunk = Chunk(
        course="demo",
        episode=1,
        video_id="vid1",
        note_path="p",
        title="Effects",
        heading="Concepts > Cleanup",
        text="Return a teardown function to cancel subscriptions.",
        timestamp=60,
    )
    build_index(BrainPaths.for_workspace(workspace).index_db, [chunk], use_vectors=False)
    return workspace


def invoke(*args):
    return runner.invoke(app, list(args))


# --- basics ---------------------------------------------------------------


def test_help_lists_the_main_commands():
    result = invoke("--help")
    assert result.exit_code == 0
    for command in ("learn", "prepare", "assemble", "ask", "doctor", "verify"):
        assert command in result.output


def test_version_flag():
    result = invoke("--version")
    assert result.exit_code == 0
    assert "coursebrain" in result.output


def test_no_args_shows_help_rather_than_a_traceback():
    assert invoke().exit_code != 0


# --- discovery ------------------------------------------------------------


def test_profiles_lists_every_schema():
    result = invoke("profiles")
    assert result.exit_code == 0
    for name in ("programming", "writing", "language", "academic", "general"):
        assert name in result.output


def test_profiles_json_is_parseable():
    result = invoke("profiles", "--json")
    rows = json.loads(result.output)
    assert {r["name"] for r in rows} >= {"programming", "writing"}
    assert all(r["sections"] for r in rows)


def test_sources_lists_youtube():
    assert "youtube" in invoke("sources").output


def test_list_on_an_empty_workspace_suggests_learn(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSEBRAIN_HOME", str(tmp_path))
    result = invoke("list")
    assert result.exit_code == 0
    assert "learn" in result.output


def test_list_shows_the_course(workspace):
    result = invoke("list")
    assert "demo" in result.output
    assert "programming" in result.output


def test_list_json(workspace):
    rows = json.loads(invoke("list", "--json").output)
    assert rows[0]["id"] == "demo"
    assert rows[0]["notes"] == 1


# --- errors name their fix -------------------------------------------------


def test_unknown_course_is_actionable(workspace):
    result = invoke("assemble", "nope")
    assert result.exit_code == 1
    assert "no course named" in result.output


def test_unknown_profile_lists_the_valid_ones(workspace):
    result = invoke("init", "x", "https://youtu.be/a", "--profile", "nonsense")
    assert result.exit_code == 1
    assert "programming" in result.output


def test_unsupported_url_is_reported(workspace):
    result = invoke("learn", "gopher://nope.example")
    assert result.exit_code == 1
    assert "no source handles" in result.output


def test_ask_without_an_index_says_what_to_run(workspace):
    result = invoke("ask", "anything")
    assert result.exit_code == 1
    assert "coursebrain index" in result.output


def test_build_without_a_key_points_at_prepare(workspace, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    result = invoke("build", "demo")
    assert result.exit_code == 1
    assert "prepare" in result.output


# --- init / lifecycle -----------------------------------------------------


def test_init_creates_a_course(workspace):
    result = invoke("init", "fresh", "https://youtu.be/abc", "--profile", "writing")
    assert result.exit_code == 0
    config = (workspace / "courses" / "fresh" / "course.yaml").read_text()
    assert "profile: writing" in config


def test_init_refuses_to_clobber(workspace):
    result = invoke("init", "demo", "https://youtu.be/abc")
    assert result.exit_code == 1
    assert "--force" in result.output


def test_init_force_overwrites(workspace):
    assert invoke("init", "demo", "https://youtu.be/abc", "--force").exit_code == 0


# --- search ---------------------------------------------------------------


def test_ask_returns_a_hit_with_its_source_link(indexed):
    result = invoke("ask", "teardown subscriptions", "-k", "1")
    assert result.exit_code == 0
    assert "Cleanup" in result.output
    assert "youtu.be/vid1" in result.output


def test_ask_json_carries_url_and_score(indexed):
    rows = json.loads(invoke("ask", "teardown", "--json").output)
    assert rows
    assert rows[0]["url"].endswith("?t=60")
    assert "score" in rows[0]


def test_ask_with_no_matches_is_not_an_error(indexed):
    result = invoke("ask", "zzzquux", "--json")
    assert result.exit_code == 0
    assert json.loads(result.output) == []


def test_ask_can_filter_by_course(indexed):
    assert json.loads(invoke("ask", "teardown", "-c", "other", "--json").output) == []


# --- integrity ------------------------------------------------------------


def test_verify_passes_on_a_good_note(workspace):
    invoke("index", "--no-vectors")  # verify requires INDEX.md/CONCEPTS.md
    result = invoke("verify", "demo")
    assert result.exit_code == 0
    assert "✓" in result.output


def test_verify_fails_and_names_the_problem(workspace):
    invoke("index", "--no-vectors")
    note = workspace / "courses" / "demo" / "notes" / "01-effects.md"
    note.write_text(NOTE.split("## Code & APIs")[0])
    result = invoke("verify", "demo")
    assert result.exit_code == 1
    assert "Code & APIs" in result.output


def test_verify_json_exit_code_still_signals_failure(workspace):
    invoke("index", "--no-vectors")
    note = workspace / "courses" / "demo" / "notes" / "01-effects.md"
    note.write_text(NOTE.split("## Code & APIs")[0])
    result = invoke("verify", "demo", "--json")
    assert result.exit_code == 1
    assert json.loads(result.output)[0]["problems"]


def test_index_builds_the_search_index(workspace):
    result = invoke("index", "--no-vectors")
    assert result.exit_code == 0
    assert (workspace / ".brain" / "index.db").exists()
    assert (workspace / "BRAIN.md").exists()


def test_eval_init_writes_a_template(workspace):
    result = invoke("eval", "demo", "--init")
    assert result.exit_code == 0
    assert (workspace / "courses" / "demo" / "evals" / "questions.yaml").exists()


def test_eval_init_needs_a_course(workspace):
    assert invoke("eval", "--init").exit_code == 1


def test_eval_warns_that_a_tiny_question_set_proves_nothing(indexed):
    evals = indexed / "courses" / "demo" / "evals"
    evals.mkdir(parents=True, exist_ok=True)
    (evals / "questions.yaml").write_text("- question: teardown\n  episodes: [1]\n")
    result = invoke("eval", "demo", "--no-vectors")
    assert result.exit_code == 0
    assert "discriminate" in result.output


def test_pending_is_empty_when_nothing_staged(workspace):
    assert json.loads(invoke("pending", "--json").output) == []


# --- doctor ---------------------------------------------------------------


def test_doctor_reports_every_check(workspace):
    result = invoke("doctor", "--json")
    names = {c["check"] for c in json.loads(result.output)}
    assert {"python", "workspace", "yt-dlp", "semantic search", "courses"} <= names


def test_doctor_flags_a_missing_index_with_the_fix(workspace):
    checks = {c["check"]: c for c in json.loads(invoke("doctor", "--json").output)}
    assert checks["search index"]["ok"] is False
    assert "coursebrain index" in checks["search index"]["fix"]


def test_doctor_exits_nonzero_when_something_is_broken(workspace):
    assert invoke("doctor").exit_code == 1  # no search index yet


@pytest.mark.skipif(not vectors_available(), reason="doctor rightly flags the missing 'rag' extra")
def test_doctor_passes_once_the_index_exists(indexed):
    assert invoke("doctor").exit_code == 0


def test_doctor_still_reports_the_index_once_built(indexed):
    # holds with or without the rag extra, unlike the exit code
    checks = {c["check"]: c for c in json.loads(invoke("doctor", "--json").output)}
    assert checks["search index"]["ok"] is True
