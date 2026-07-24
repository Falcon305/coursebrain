from pipeline.stages.normalize import parse_time, parse_vtt, strip_markup, to_plain_text

AUTO_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.030 --> 00:00:02.669 align:start position:0%

hello<00:00:00.719><c> everyone</c><00:00:01.020><c> welcome</c>

00:00:02.669 --> 00:00:02.679 align:start position:0%
hello everyone welcome


00:00:02.679 --> 00:00:05.190 align:start position:0%
hello everyone welcome
to<00:00:03.360><c> the</c><00:00:03.720><c> course</c>

00:00:05.190 --> 00:00:05.200 align:start position:0%
to the course


00:00:05.200 --> 00:00:08.000 align:start position:0%
to the course
today<00:00:06.100><c> we</c><00:00:06.400><c> cover</c><00:00:06.900><c> hooks</c>
"""

MANUAL_VTT = """WEBVTT

1
00:00:01.000 --> 00:00:03.000
Welcome to the course.

2
00:00:03.000 --> 00:00:06.000
Today we cover hooks.
"""


def test_auto_captions_dedupe_rolling_window():
    segments = parse_vtt(AUTO_VTT)
    assert [s.text for s in segments] == [
        "hello everyone welcome",
        "to the course",
        "today we cover hooks",
    ]


def test_auto_captions_preserve_timing():
    segments = parse_vtt(AUTO_VTT)
    assert segments[0].start == 0.03
    assert segments[1].start == 2.679
    assert segments[2].start == 5.2
    assert all(s.end >= s.start for s in segments)


def test_manual_captions_pass_through():
    segments = parse_vtt(MANUAL_VTT, dedupe_rolling=False)
    assert [s.text for s in segments] == ["Welcome to the course.", "Today we cover hooks."]


def test_manual_captions_keep_legitimate_repeats():
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nNo.\n\n00:00:02.000 --> 00:00:03.000\nNo.\n"
    assert len(parse_vtt(vtt, dedupe_rolling=False)) == 2


def test_strip_markup_removes_inline_timings_and_entities():
    raw = 'a<00:00:01.500><c.colorE5E5E5> b</c>&amp;<i>c</i>'
    assert strip_markup(raw) == "a b&c"


def test_parse_time_handles_both_forms():
    assert parse_time("00:01:30.500") == 90.5
    assert parse_time("01:30.500") == 90.5
    assert parse_time("00:00:02,669") == 2.669


def test_empty_and_header_only_input():
    assert parse_vtt("WEBVTT\n\n") == []
    assert parse_vtt("") == []


def test_note_blocks_ignored():
    vtt = "WEBVTT\n\nNOTE this is a comment\n\n00:00:01.000 --> 00:00:02.000\nreal text\n"
    assert [s.text for s in parse_vtt(vtt)] == ["real text"]


def test_consecutive_identical_cues_merge():
    vtt = (
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:02.000\nsame\n\n"
        "00:00:02.000 --> 00:00:04.000\nsame\n"
    )
    segments = parse_vtt(vtt)
    assert len(segments) == 1
    assert segments[0].end == 4.0


def test_to_plain_text_joins_segments():
    assert to_plain_text(parse_vtt(AUTO_VTT)) == (
        "hello everyone welcome to the course today we cover hooks"
    )
