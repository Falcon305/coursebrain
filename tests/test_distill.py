import pytest

from coursebrain.models import Chapter, Episode, Section
from coursebrain.profiles import Profile
from coursebrain.stages.distill import (
    Distillation,
    DistillError,
    Refusal,
    _chunk,
    _merge,
    build_system,
    build_user,
    distill_episode,
    render_note,
    render_transcript,
)


@pytest.fixture
def episode():
    return Episode(
        video_id="abc123",
        index=7,
        title='Hooks: "useEffect" deep dive',
        duration=930.0,
        caption_source="auto",
        upload_date="20260101",
        chapters=[Chapter(title="Intro", start=0.0, end=60.0)],
    )


@pytest.fixture
def profile():
    return Profile.load("programming")


def make_sections(n=3, words=100):
    return [
        Section(
            start=i * 60.0,
            end=(i + 1) * 60.0,
            text=" ".join(f"w{j}" for j in range(words)),
            title=f"Part {i}",
        )
        for i in range(n)
    ]


class FakeMessage:
    def __init__(self, text, stop_reason="end_turn", details=None):
        self.content = [type("B", (), {"type": "text", "text": text})()]
        self.stop_reason = stop_reason
        self.stop_details = details


class FakeClient:
    def __init__(self, *messages):
        self.messages_out = list(messages)
        self.calls = []
        self.beta = self

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        message = self.messages_out.pop(0)

        class Ctx:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def get_final_message(self_inner):
                return message

        return Ctx()

    @property
    def messages(self):
        return self


def test_render_transcript_emits_timestamp_markers():
    out = render_transcript(make_sections(1, words=120))
    assert "[0:00]" in out
    assert "### Part 0" in out
    assert out.count("[") >= 2


def test_render_transcript_timestamps_stay_within_section():
    sections = [Section(start=100.0, end=160.0, text=" ".join(["x"] * 60))]
    out = render_transcript(sections)
    assert "[1:40]" in out
    assert "[0:00]" not in out


def test_chunk_splits_only_when_over_limit():
    assert len(_chunk(make_sections(3, words=100), limit=12000)) == 1
    assert len(_chunk(make_sections(6, words=5000), limit=12000)) > 1


def test_chunk_preserves_every_section():
    sections = make_sections(10, words=3000)
    assert sum(len(c) for c in _chunk(sections, limit=5000)) == 10


def test_build_system_fills_every_placeholder(profile, episode):
    from coursebrain.observability import Prompt
    from coursebrain.stages.distill import PROMPT_FILE

    prompt = Prompt(text=PROMPT_FILE.read_text(), version="test")
    system = build_system(profile, prompt, episode)
    assert "{" not in system.replace("{c}", "")
    assert "abc123" in system
    assert "15:30" in system
    assert "## Visual blind spots" in system


def test_build_user_includes_glossary_and_metadata(profile, episode):
    user = build_user(episode, make_sections(1), ["useEffect", "useMemo"])
    assert "useEffect" in user
    assert "https://youtu.be/abc123" in user
    assert "auto-generated" in user


def test_build_user_marks_multipart(episode):
    user = build_user(episode, make_sections(1), [], part=(2, 3))
    assert "part 2 of 3" in user


def test_merge_regroups_sections_across_parts(profile):
    a = "## TL;DR\n\nfirst half.\n\n## Gotchas\n\n- a"
    b = "## TL;DR\n\nsecond half.\n\n## Gotchas\n\n- b"
    merged = _merge([a, b], profile)
    assert merged.count("## TL;DR") == 1
    assert "first half." in merged and "second half." in merged
    assert "- a" in merged and "- b" in merged


def test_merge_single_part_is_identity(profile):
    body = "## TL;DR\n\nonly.\n"
    assert _merge([body], profile) == body


def test_merge_drops_empty_headings(profile):
    merged = _merge(["## TL;DR\n\nkept.\n", "## Gotchas\n\n"], profile)
    assert "## Gotchas" not in merged


def test_render_note_frontmatter_and_concepts(episode, profile):
    d = Distillation(
        body="## TL;DR\n\nx\n\n## Concepts\n\n### Effect cleanup\n\ndetail",
        model="claude-opus-5",
        prompt_version="v1",
    )
    note = render_note(episode, "react-course", profile, d)
    assert note.startswith("---\n")
    assert "episode: 07" in note
    assert 'title: "Hooks: \\"useEffect\\" deep dive"' in note
    assert "concepts:" in note
    assert '  - "Effect cleanup"' in note
    assert "# 07 — Hooks:" in note


def test_distill_refusal_raises(episode, profile):
    details = type("D", (), {"category": "cyber", "explanation": "nope"})()
    client = FakeClient(FakeMessage("", stop_reason="refusal", details=details))
    with pytest.raises(Refusal) as exc:
        distill_episode(episode, make_sections(1), profile, client=client)
    assert exc.value.category == "cyber"


def test_distill_empty_response_raises(episode, profile):
    client = FakeClient(FakeMessage("   "))
    with pytest.raises(DistillError):
        distill_episode(episode, make_sections(1), profile, client=client)


def test_distill_no_sections_raises(episode, profile):
    with pytest.raises(DistillError):
        distill_episode(episode, [], profile, client=FakeClient())


def test_distill_caches_system_prompt(episode, profile):
    client = FakeClient(FakeMessage("## TL;DR\n\nfine"))
    distill_episode(episode, make_sections(1), profile, client=client)
    system = client.calls[0]["system"]
    assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_distill_returns_body_and_metadata(episode, profile):
    client = FakeClient(FakeMessage("## TL;DR\n\nfine"))
    result = distill_episode(episode, make_sections(1), profile, client=client)
    assert result.body.startswith("## TL;DR")
    assert result.model == "claude-opus-5"
    assert result.prompt_version.startswith("local")
