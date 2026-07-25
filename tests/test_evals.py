import pytest

from coursebrain.evals import EvalResult, load_cases, run_eval, write_template
from coursebrain.notes import Chunk
from coursebrain.paths import BrainPaths, CourseConfig, CoursePaths
from coursebrain.retrieval import build_index

QUESTIONS = """
- question: how do you avoid crashing on bad input
  episodes: [1]
- question: what is never covered anywhere
  episodes: [9]
"""


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = CoursePaths.for_course("demo", tmp_path / "courses")
    paths.ensure_dirs()
    CourseConfig(id="demo", source_url="https://x", profile="programming").dump(paths.config)
    (paths.evals / "questions.yaml").write_text(QUESTIONS)

    chunks = [
        Chunk(
            course="demo",
            episode=1,
            video_id="v1",
            note_path="p",
            title="t",
            heading="Safe division",
            text="Guard against dividing by zero so the program never crashes on bad input.",
        ),
        Chunk(
            course="demo",
            episode=2,
            video_id="v2",
            note_path="p",
            title="t",
            heading="Routing",
            text="Folders map to url segments.",
        ),
    ]
    build_index(BrainPaths.for_workspace(tmp_path).index_db, chunks, use_vectors=False)
    return tmp_path


def test_load_cases_parses_questions(tmp_path):
    path = tmp_path / "questions.yaml"
    path.write_text(QUESTIONS)
    cases = load_cases(path)
    assert len(cases) == 2
    assert cases[0].episodes == [1]


def test_load_cases_accepts_singular_episode(tmp_path):
    path = tmp_path / "q.yaml"
    path.write_text("- question: single\n  episode: 4\n")
    assert load_cases(path)[0].episodes == [4]


def test_load_cases_skips_malformed_entries(tmp_path):
    path = tmp_path / "q.yaml"
    path.write_text("- notaquestion: x\n- question: fine\n  episodes: [1]\n")
    assert len(load_cases(path)) == 1


def test_load_cases_missing_file_is_empty(tmp_path):
    assert load_cases(tmp_path / "nope.yaml") == []


def test_run_eval_scores_hits_and_misses(workspace):
    result = run_eval("demo", k=5, courses_dir=workspace / "courses", use_vectors=False)
    assert result.total == 2
    assert result.hits_at_k == 1
    assert result.misses == ["what is never covered anywhere"]


def test_run_eval_reports_recall_and_mrr(workspace):
    result = run_eval("demo", k=5, courses_dir=workspace / "courses", use_vectors=False)
    assert result.recall == 0.5
    assert 0 < result.mrr <= 1.0
    assert "recall@5" in result.line(5)


def test_run_eval_with_no_questions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = CoursePaths.for_course("empty", tmp_path / "courses")
    paths.ensure_dirs()
    CourseConfig(id="empty", source_url="https://x").dump(paths.config)
    result = run_eval("empty", courses_dir=tmp_path / "courses", use_vectors=False)
    assert result.total == 0
    assert result.recall == 0.0
    assert result.mrr == 0.0


def test_empty_result_does_not_divide_by_zero():
    result = EvalResult()
    assert result.recall == 0.0
    assert result.mrr == 0.0


def test_write_template_creates_a_usable_starter(tmp_path):
    path = tmp_path / "evals" / "questions.yaml"
    write_template(path)
    assert path.exists()
    cases = load_cases(path)
    assert cases and all(c.episodes for c in cases)
