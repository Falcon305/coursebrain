from __future__ import annotations

import argparse
import sys

from .build import build_course
from .manifest import Manifest
from .models import slugify
from .paths import CourseConfig, CoursePaths, list_courses
from .profiles import Profile, list_profiles
from .stages.distill import DEFAULT_MODEL, api_key_present


def cmd_init(args: argparse.Namespace) -> int:
    course_id = args.id or slugify(args.title or "course")
    paths = CoursePaths.for_course(course_id)
    if paths.exists() and not args.force:
        print(f"course '{course_id}' already exists at {paths.root}", file=sys.stderr)
        return 1
    if args.profile not in list_profiles():
        print(f"unknown profile '{args.profile}'. available: {', '.join(list_profiles())}",
              file=sys.stderr)
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


def cmd_build(args: argparse.Namespace) -> int:
    if not args.fetch_only and not api_key_present():
        print("no ANTHROPIC_API_KEY set — run with --fetch-only, or export a key", file=sys.stderr)
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

    p = sub.add_parser("build", help="fetch, normalize, and distill a course")
    p.add_argument("id")
    p.add_argument("--limit", type=int, default=None, help="only the first N videos")
    p.add_argument("--only", type=int, default=None, help="only episode N")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--force", action="store_true", help="ignore cached distillations")
    p.add_argument("--fetch-only", action="store_true", help="stop after transcripts")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("list", help="list courses")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("profiles", help="list domain profiles")
    p.set_defaults(func=cmd_profiles)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
