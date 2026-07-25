import pytest

from coursebrain.paths import ENV_HOME, BrainPaths, CoursePaths, courses_dir, find_workspace


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_HOME, raising=False)


def test_env_var_wins(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_HOME, str(tmp_path / "elsewhere"))
    assert find_workspace() == (tmp_path / "elsewhere").resolve()


def test_env_var_expands_user(monkeypatch):
    monkeypatch.setenv(ENV_HOME, "~/somewhere")
    assert "~" not in str(find_workspace())


def test_finds_nearest_ancestor_with_courses(tmp_path):
    (tmp_path / "courses").mkdir()
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert find_workspace(deep) == tmp_path.resolve()


def test_dot_coursebrain_also_marks_a_workspace(tmp_path):
    (tmp_path / ".coursebrain").mkdir()
    nested = tmp_path / "nested"
    nested.mkdir()
    assert find_workspace(nested) == tmp_path.resolve()


def test_falls_back_to_the_starting_directory(tmp_path):
    nowhere = tmp_path / "nothing" / "here"
    nowhere.mkdir(parents=True)
    assert find_workspace(nowhere) == nowhere.resolve()


def test_nearest_marker_wins_over_a_further_one(tmp_path):
    (tmp_path / "courses").mkdir()
    inner = tmp_path / "inner"
    (inner / "courses").mkdir(parents=True)
    assert find_workspace(inner) == inner.resolve()


def test_courses_dir_hangs_off_the_workspace(tmp_path):
    assert courses_dir(tmp_path) == tmp_path / "courses"


def test_brain_paths_are_workspace_relative(tmp_path):
    brain = BrainPaths.for_workspace(tmp_path)
    assert brain.root == tmp_path / ".brain"
    assert brain.index_db == tmp_path / ".brain" / "index.db"
    assert brain.brain_md == tmp_path / "BRAIN.md"


def test_course_paths_accept_an_explicit_root(tmp_path):
    paths = CoursePaths.for_course("demo", tmp_path)
    assert paths.root == tmp_path / "demo"
    assert paths.config == tmp_path / "demo" / "course.yaml"


def test_workspace_is_resolved_at_call_time_not_import_time(tmp_path, monkeypatch):
    # an installed tool must never store data inside its own package directory
    monkeypatch.chdir(tmp_path)
    first = find_workspace()
    (tmp_path / "courses").mkdir()
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    assert find_workspace() == tmp_path.resolve()
    assert first == tmp_path.resolve()
