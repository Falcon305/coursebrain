import pytest

from coursebrain.capability import (
    PRECEDENCE,
    Capability,
    CapabilityError,
    Composition,
    capability_path,
    compose,
    notes_digest,
    parse_compiled,
    profile_kind,
    render_skill,
    suggested_trigger,
)
from coursebrain.paths import CourseConfig, CoursePaths

NOTE = """---
course: demo
episode: 01
title: "One"
---

## TL;DR

Something.
"""


def make_course(root, course_id, profile="programming", notes=1):
    paths = CoursePaths.for_course(course_id, root / "courses")
    paths.ensure_dirs()
    CourseConfig(id=course_id, source_url="https://x", profile=profile, title=course_id).dump(
        paths.config
    )
    for n in range(1, notes + 1):
        (paths.notes / f"{n:02d}-note.md").write_text(NOTE)
    return paths


def cap(kind="domain", course="demo"):
    return Capability(
        course=course,
        kind=kind,
        title=course.title(),
        trigger=f"Use when {kind} matters.",
        body=f"## Rules\n\nDo the {kind} thing.",
    )


# --- round trip -----------------------------------------------------------


def test_capability_roundtrips_through_markdown():
    original = cap("language", "spanish")
    restored = Capability.from_markdown(original.to_markdown(), "spanish")
    assert restored.kind == "language"
    assert restored.trigger == original.trigger
    assert restored.body == original.body


def test_save_and_load(tmp_path):
    paths = make_course(tmp_path, "demo")
    cap().save(paths)
    assert capability_path(paths).exists()
    assert Capability.load(paths).kind == "domain"


def test_loading_a_missing_pack_says_how_to_make_one(tmp_path):
    paths = make_course(tmp_path, "demo")
    with pytest.raises(CapabilityError) as exc:
        Capability.load(paths)
    assert "coursebrain compile" in str(exc.value)


def test_unknown_kind_is_rejected():
    text = "---\ncourse: x\nkind: nonsense\ntitle: X\n---\n\nbody"
    with pytest.raises(CapabilityError):
        Capability.from_markdown(text, "x")


# --- parsing what a writer produced ---------------------------------------


def test_parse_extracts_the_trigger_line():
    result = parse_compiled(
        "Trigger: Use when writing Spanish.\n\n## Rules\n\nSay it well.",
        course_id="es",
        kind="language",
        title="Spanish",
    )
    assert result.trigger == "Use when writing Spanish."
    assert "Trigger:" not in result.body
    assert result.body.startswith("## Rules")


def test_parse_accepts_a_bolded_trigger():
    result = parse_compiled(
        "**Trigger**: Use when editing prose.\n\n## Rules\n\nCut filters.",
        course_id="p",
        kind="voice",
        title="Prose",
    )
    assert result.trigger == "Use when editing prose."


def test_parse_falls_back_to_a_generated_trigger():
    result = parse_compiled("## Rules\n\nNo trigger line here.", "x", "domain", "Thing")
    assert result.trigger == suggested_trigger("domain", "Thing")


def test_parse_rejects_an_empty_body():
    with pytest.raises(CapabilityError):
        parse_compiled("Trigger: only a trigger\n", "x", "domain", "Thing")


# --- skill export ---------------------------------------------------------


def test_skill_description_is_the_trigger_not_a_summary():
    skill = render_skill(cap("language", "spanish"), "spanish")
    assert "description: Use when language matters." in skill
    assert skill.startswith("---\n")
    assert "name: spanish" in skill


def test_skill_states_which_kind_it_is():
    assert "craft guidance" in render_skill(cap("voice"), "prose")
    assert "subject knowledge" in render_skill(cap("domain"), "monads")
    assert "language guidance" in render_skill(cap("language"), "es")
    assert "method guidance" in render_skill(cap("method"), "cooking")


def test_every_kind_renders_a_skill():
    from coursebrain.capability import KINDS

    for kind in KINDS:
        assert render_skill(cap(kind), "x").startswith("---")


def test_skill_points_back_at_the_notes_for_depth():
    skill = render_skill(cap(), "monads")
    assert "coursebrain ask" in skill
    assert "courses/monads/" in skill


def test_skill_carries_the_conflict_rules():
    assert "Language governs surface" in render_skill(cap(), "x")


# --- composition ----------------------------------------------------------


def test_compose_orders_by_layer():
    composition = Composition(
        parts=[cap("domain", "d"), cap("voice", "v"), cap("language", "l"), cap("method", "m")]
    )
    text = composition.render()
    assert (
        text.index("LANGUAGE") < text.index("VOICE") < text.index("METHOD") < text.index("DOMAIN")
    )


def test_method_is_a_supported_kind():
    assert "METHOD" in Composition(parts=[cap("method", "m")]).render()


def test_precedence_covers_every_kind():
    from coursebrain.capability import KINDS

    for kind in KINDS:
        assert kind.capitalize() in PRECEDENCE or kind in PRECEDENCE.lower()


def test_method_never_loses_a_step_to_style():
    assert "keep the step" in PRECEDENCE


def test_compose_lists_what_is_loaded():
    text = Composition(parts=[cap("domain", "d"), cap("language", "l")]).render()
    assert "D (domain)" in text
    assert "L (language)" in text


def test_compose_includes_the_task():
    text = Composition(parts=[cap()]).render(task="write a tutorial")
    assert "write a tutorial" in text


def test_compose_always_states_precedence():
    assert "Resolving conflicts" in Composition(parts=[cap()]).render()
    assert "Domain accuracy outranks everything" in PRECEDENCE


def test_precedence_forbids_going_outside_the_packs():
    # testing found the model reaching for vocabulary no pack taught
    assert "Stay inside the packs" in PRECEDENCE


def test_compose_from_disk(tmp_path):
    a = make_course(tmp_path, "monads", "programming")
    b = make_course(tmp_path, "prose", "writing")
    cap("domain", "monads").save(a)
    cap("voice", "prose").save(b)
    composition = compose([a, b])
    assert {p.kind for p in composition.parts} == {"domain", "voice"}


def test_compose_with_no_courses_is_an_error():
    with pytest.raises(CapabilityError):
        compose([])


def test_compose_reports_a_course_without_a_pack(tmp_path):
    paths = make_course(tmp_path, "demo")
    with pytest.raises(CapabilityError) as exc:
        compose([paths])
    assert "no capability pack" in str(exc.value)


# --- inputs ---------------------------------------------------------------


def test_notes_digest_reads_every_note(tmp_path):
    paths = make_course(tmp_path, "demo", notes=3)
    digest, count = notes_digest(paths)
    assert count == 3
    assert digest.count("## TL;DR") == 3


def test_notes_digest_truncates_and_says_so(tmp_path):
    paths = make_course(tmp_path, "demo", notes=5)
    digest, count = notes_digest(paths, max_chars=120)
    assert count == 5
    assert "omitted for length" in digest


def test_notes_digest_without_notes_says_what_to_run(tmp_path):
    paths = make_course(tmp_path, "empty", notes=0)
    with pytest.raises(CapabilityError) as exc:
        notes_digest(paths)
    assert "coursebrain prepare" in str(exc.value)


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        ("programming", "domain"),
        ("academic", "domain"),
        ("business", "domain"),
        ("writing", "voice"),
        ("design", "voice"),
        ("language", "language"),
        ("craft", "method"),
        ("method", "method"),
        ("general", "domain"),
    ],
)
def test_profiles_declare_their_kind(profile, expected):
    from coursebrain.profiles import Profile

    assert profile_kind(profile, Profile.load(profile).capability_kind) == expected


def test_unknown_kind_falls_back_to_domain():
    assert profile_kind("whatever", "nonsense") == "domain"
    assert profile_kind("whatever", None) == "domain"
