from __future__ import annotations

import argparse
import sys

from . import work
from .build import assemble_course, build_course, prepare_course
from .evals import run_eval, write_template
from .manifest import Manifest
from .models import slugify
from .paths import BrainPaths, CourseConfig, CoursePaths, list_courses
from .profiles import Profile, list_profiles
from .retrieval import search
from .stages.distill import DEFAULT_MODEL, api_key_present
from .stages.index import index_all
from .stages.verify import verify_course


def cmd_init(args: argparse.Namespace) -> int:
    course_id = args.id or slugify(args.title or "course")
    paths = CoursePaths.for_course(course_id)
    if paths.exists() and not args.force:
        print(f"course '{course_id}' already exists at {paths.root}", file=sys.stderr)
        return 1
    if args.profile not in list_profiles():
        print(
            f"unknown profile '{args.profile}'. available: {', '.join(list_profiles())}",
            file=sys.stderr,
        )
        return 1

    paths.ensure_dirs()
    CourseConfig(
        id=course_id,
        source_url=args.url,
        title=args.title or "",
        profile=args.profile,
        language=args.language,
        companion_repo=args.repo,
    ).dump(paths.config)
    print(f"created {paths.config}")
    print(f"next: course build {course_id}")
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    report = prepare_course(args.id, limit=args.limit, only=args.only, force=args.force)
    paths = CoursePaths.for_course(args.id)
    todo = work.pending(paths)
    if todo:
        print(f"\n{len(todo)} episode(s) waiting to be distilled:")
        for item in todo:
            print(f"  read  {item.task}")
            print(f"  write {item.body}")
        print("\nthen run: course assemble " + args.id)
    return 1 if report.failed else 0


def cmd_pending(args: argparse.Namespace) -> int:
    targets = [args.id] if args.id else list_courses()
    total = 0
    for course_id in targets:
        todo = work.pending(CoursePaths.for_course(course_id))
        total += len(todo)
        for item in todo:
            print(f"{course_id}\t{item.episode:02d}\t{item.task}\t{item.body}")
    if not total:
        print("nothing pending", file=sys.stderr)
    return 0


def cmd_assemble(args: argparse.Namespace) -> int:
    report = assemble_course(args.id)
    return 1 if report.failed else 0


def cmd_build(args: argparse.Namespace) -> int:
    if not args.fetch_only and not api_key_present():
        print(
            "no ANTHROPIC_API_KEY set.\n"
            "  'course build' calls the API directly. Inside Claude Code you don't need it —\n"
            "  use 'course prepare' / 'course assemble' instead, or add --fetch-only here.",
            file=sys.stderr,
        )
        return 1
    report = build_course(
        args.id,
        limit=args.limit,
        only=args.only,
        model=args.model,
        force=args.force,
        fetch_only=args.fetch_only,
    )
    return 1 if report.failed else 0


def cmd_list(args: argparse.Namespace) -> int:
    courses = list_courses()
    if not courses:
        print("no courses yet. create one with: course init <id> <url>")
        return 0
    for course_id in courses:
        paths = CoursePaths.for_course(course_id)
        config = paths.load_config()
        manifest = Manifest.load(paths.manifest, course_id)
        notes = len(list(paths.notes.glob("*.md"))) if paths.notes.exists() else 0
        print(f"{course_id:<28} {config.profile:<12} {notes:>3} notes   {manifest.summary()}")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    index_all(use_vectors=not args.no_vectors)
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    brain = BrainPaths.for_workspace()
    if not brain.index_db.exists():
        print("no index yet — run: course index", file=sys.stderr)
        return 1
    hits = search(
        brain.index_db,
        args.query,
        k=args.k,
        course=args.course,
        use_vectors=not args.no_vectors,
    )
    if not hits:
        print("no matches")
        return 0
    for i, hit in enumerate(hits, start=1):
        print(f"\n{i}. {hit.chunk.label}")
        print(f"   {hit.chunk.url}   [{'+'.join(hit.sources)}]")
        body = " ".join(hit.chunk.text.split())
        print(f"   {body[: args.chars]}{'…' if len(body) > args.chars else ''}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    targets = [args.id] if args.id else list_courses()
    failed = False
    for course_id in targets:
        report = verify_course(course_id)
        if report.ok:
            print(f"{course_id}: ok ({report.checked} note(s))")
        else:
            failed = True
            print(f"{course_id}: {len(report.problems)} problem(s) in {report.checked} note(s)")
            for problem in report.problems:
                print(f"  - {problem}")
    return 1 if failed else 0


def cmd_eval(args: argparse.Namespace) -> int:
    if args.init:
        path = CoursePaths.for_course(args.id).evals / "questions.yaml"
        if path.exists() and not args.force:
            print(f"{path} already exists", file=sys.stderr)
            return 1
        write_template(path)
        print(f"wrote {path} — fill it in, then run: course eval {args.id}")
        return 0

    result = run_eval(args.id, k=args.k, use_vectors=not args.no_vectors)
    if not result.total:
        print("no eval questions found — create some with: course eval <id> --init")
        return 0
    print(result.line(args.k))
    for miss in result.misses:
        print(f"  missed: {miss}")
    return 0


def cmd_profiles(args: argparse.Namespace) -> int:
    for name in list_profiles():
        profile = Profile.load(name)
        print(f"{name:<14} {profile.description}")
        print(f"{'':<14} sections: {', '.join(profile.headings)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="course", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create a new course")
    p.add_argument("id", nargs="?", help="course id (slug)")
    p.add_argument("url", help="playlist, channel, or single video URL")
    p.add_argument("--title", default="")
    p.add_argument("--profile", default="general", help=f"one of: {', '.join(list_profiles())}")
    p.add_argument("--language", default="en")
    p.add_argument("--repo", default=None, help="companion source repository")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("prepare", help="fetch transcripts and stage episodes for distilling")
    p.add_argument("id")
    p.add_argument("--limit", type=int, default=None, help="only the first N videos")
    p.add_argument("--only", type=int, default=None, help="only episode N")
    p.add_argument("--force", action="store_true", help="restage episodes that already have notes")
    p.set_defaults(func=cmd_prepare)

    p = sub.add_parser("pending", help="list staged episodes awaiting a note (tab-separated)")
    p.add_argument("id", nargs="?")
    p.set_defaults(func=cmd_pending)

    p = sub.add_parser("assemble", help="turn written bodies into finished notes")
    p.add_argument("id")
    p.set_defaults(func=cmd_assemble)

    p = sub.add_parser("build", help="unattended end-to-end build (needs ANTHROPIC_API_KEY)")
    p.add_argument("id")
    p.add_argument("--limit", type=int, default=None, help="only the first N videos")
    p.add_argument("--only", type=int, default=None, help="only episode N")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--force", action="store_true", help="ignore cached distillations")
    p.add_argument("--fetch-only", action="store_true", help="stop after transcripts")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser(
        "index", help="rebuild INDEX.md, CONCEPTS.md, BRAIN.md, and the search index"
    )
    p.add_argument("--no-vectors", action="store_true", help="keyword index only")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("ask", help="hybrid search across every course")
    p.add_argument("query")
    p.add_argument("-k", type=int, default=5, help="results to return")
    p.add_argument("--course", default=None, help="restrict to one course")
    p.add_argument("--chars", type=int, default=400, help="excerpt length")
    p.add_argument("--no-vectors", action="store_true")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("verify", help="check notes for structural problems")
    p.add_argument("id", nargs="?", help="course id (default: all)")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("eval", help="score retrieval against a question set")
    p.add_argument("id", nargs="?", help="course id (default: all)")
    p.add_argument("-k", type=int, default=5)
    p.add_argument("--init", action="store_true", help="write a starter question set")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-vectors", action="store_true")
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("list", help="list courses")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("profiles", help="list domain profiles")
    p.set_defaults(func=cmd_profiles)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
