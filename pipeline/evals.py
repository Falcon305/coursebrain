from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .paths import BrainPaths, CoursePaths
from .retrieval import search


@dataclass
class EvalCase:
    question: str
    episodes: list[int] = field(default_factory=list)
    course: str | None = None


@dataclass
class EvalResult:
    total: int = 0
    hits_at_k: int = 0
    reciprocal_ranks: list[float] = field(default_factory=list)
    misses: list[str] = field(default_factory=list)

    @property
    def recall(self) -> float:
        return self.hits_at_k / self.total if self.total else 0.0

    @property
    def mrr(self) -> float:
        return sum(self.reciprocal_ranks) / self.total if self.total else 0.0

    def line(self, k: int) -> str:
        return (
            f"{self.total} question(s) | recall@{k}: {self.recall:.0%} | MRR: {self.mrr:.2f}"
        )


def load_cases(path: Path) -> list[EvalCase]:
    if not path.exists():
        return []
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    cases: list[EvalCase] = []
    for item in raw:
        if not isinstance(item, dict) or "question" not in item:
            continue
        episodes = item.get("episodes") or ([item["episode"]] if "episode" in item else [])
        cases.append(
            EvalCase(
                question=str(item["question"]),
                episodes=[int(e) for e in episodes],
                course=item.get("course"),
            )
        )
    return cases


def run_eval(
    course_id: str | None = None,
    k: int = 5,
    courses_dir: Path | None = None,
    use_vectors: bool = True,
) -> EvalResult:
    brain = BrainPaths()
    cases: list[EvalCase] = []
    if course_id:
        cases = load_cases(CoursePaths.for_course(course_id, courses_dir).evals / "questions.yaml")
        for case in cases:
            case.course = case.course or course_id
    else:
        from .paths import list_courses

        for cid in list_courses(courses_dir):
            for case in load_cases(
                CoursePaths.for_course(cid, courses_dir).evals / "questions.yaml"
            ):
                case.course = case.course or cid
                cases.append(case)

    result = EvalResult(total=len(cases))
    for case in cases:
        hits = search(
            brain.index_db,
            brain.lancedb,
            case.question,
            k=k,
            course=case.course,
            use_vectors=use_vectors,
        )
        found_at = next(
            (i for i, h in enumerate(hits, start=1) if h.chunk.episode in case.episodes), None
        )
        if found_at is None:
            result.reciprocal_ranks.append(0.0)
            result.misses.append(case.question)
        else:
            result.hits_at_k += 1
            result.reciprocal_ranks.append(1.0 / found_at)
    return result


TEMPLATE = """# Retrieval eval set for this course.
#
# Each entry is a question plus the episode(s) that actually answer it. Write these
# BEFORE tuning retrieval, so chunking, k, and fusion weights get tuned against a
# number instead of a hunch. Aim for ~20, and include questions whose wording does
# NOT appear in the notes — those are the ones keyword search alone will miss.

- question: how does the instructor handle stale cached data
  episodes: [7]

- question: what did they say about naming things
  episodes: [3, 11]
"""


def write_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE, encoding="utf-8")
