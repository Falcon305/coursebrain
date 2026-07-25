from __future__ import annotations

import html
import re
from pathlib import Path

from coursebrain.models import Segment

TIMING_RE = re.compile(
    r"^(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{1,2}:\d{2}[.,]\d{3})\s*-->\s*"
    r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{1,2}:\d{2}[.,]\d{3})"
)
INLINE_TIME_RE = re.compile(r"<\d{1,2}:\d{2}:\d{2}[.,]\d{3}>")
TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
BLOCK_KEYWORDS = ("WEBVTT", "NOTE", "STYLE", "REGION")


def parse_time(value: str) -> float:
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = "0", parts[0], parts[1]
    else:
        raise ValueError(f"bad timestamp: {value}")
    return int(h) * 3600 + int(m) * 60 + float(s)


def strip_markup(line: str) -> str:
    line = INLINE_TIME_RE.sub("", line)
    line = TAG_RE.sub("", line)
    line = html.unescape(line)
    line = line.replace("\xa0", " ")  # nbsp
    return re.sub(r"\s+", " ", line).strip()


def _cues(text: str) -> list[tuple[float, float, list[str]]]:
    out: list[tuple[float, float, list[str]]] = []
    current: tuple[float, float] | None = None
    lines: list[str] = []

    for raw in text.splitlines():
        stripped = raw.strip()
        match = TIMING_RE.match(stripped)
        if match:
            if current:
                out.append((current[0], current[1], lines))
            current = (parse_time(match.group(1)), parse_time(match.group(2)))
            lines = []
            continue
        if not stripped:
            # a blank line directly after the timing line is padding, not a terminator
            if current and lines:
                out.append((current[0], current[1], lines))
                current, lines = None, []
            continue
        if current is None:
            continue
        if stripped.startswith(BLOCK_KEYWORDS):
            continue
        lines.append(stripped)

    if current:
        out.append((current[0], current[1], lines))
    return out


def parse_vtt(text: str, dedupe_rolling: bool = True) -> list[Segment]:
    segments: list[Segment] = []
    previous: list[str] = []

    for start, end, raw_lines in _cues(text):
        cleaned = [c for c in (strip_markup(line) for line in raw_lines) if c]
        if not cleaned:
            continue

        if not dedupe_rolling:
            segments.append(Segment(start=start, end=max(end, start), text=" ".join(cleaned)))
            continue

        fresh = [line for line in cleaned if line not in previous]
        previous = cleaned
        payload = " ".join(fresh).strip()

        # text still on screen: keep the timing, drop the repeat
        if not payload or (segments and segments[-1].text == payload):
            if segments:
                segments[-1].end = max(segments[-1].end, end)
            continue

        segments.append(Segment(start=start, end=max(end, start), text=payload))

    return segments


def normalize_file(path: Path, caption_source: str = "auto") -> list[Segment]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_vtt(text, dedupe_rolling=caption_source != "manual")


def to_plain_text(segments: list[Segment], width: int = 0) -> str:
    body = " ".join(s.text for s in segments)
    if width <= 0:
        return body
    words, line, lines = body.split(), "", []
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return "\n".join(lines)


def word_count(segments: list[Segment]) -> int:
    return sum(len(s.text.split()) for s in segments)
