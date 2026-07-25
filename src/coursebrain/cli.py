"""Command line interface.

Output rules: human-readable goes to stdout via Rich, machine-readable goes to
stdout as JSON under ``--json``, and anything that is not the answer (progress,
warnings, diagnostics) goes to stderr so piping stays clean.
"""

from __future__ import annotations

import json as jsonlib
import sys
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from . import work
from .build import DEFAULT_WORKERS, assemble_course, build_course, prepare_course
from .evals import run_eval, write_template
from .manifest import Manifest
from .models import slugify
from .paths import BrainPaths, CourseConfig, CoursePaths, find_workspace, list_courses
from .profiles import Profile, list_profiles
from .retrieval import search, vectors_available
from .sources import SourceError, load_sources, source_for
from .stages.distill import DEFAULT_MODEL, api_key_present
from .stages.index import index_all
from .stages.verify import verify_course

app = typer.Typer(
    name="coursebrain",
    help="Turn long-form video into notes your agent can read, cite, and write from.",
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)

out = Console()
err = Console(stderr=True)


def fail(message: str, hint: str | None = None) -> Any:
    """Report a problem and exit. Every failure should name its fix."""
    err.print(f"[bold red]error[/] {message}")
    if hint:
        err.print(f"[dim]try:[/] {hint}")
    raise typer.Exit(1)


def emit(payload: Any, as_json: bool) -> bool:
    """Print JSON and report whether it handled the output."""
    if as_json:
        out.print_json(jsonlib.dumps(payload, default=str))
        return True
    return False


def _course_or_fail(course_id: str) -> CoursePaths:
    paths = CoursePaths.for_course(course_id)
    if not paths.exists():
        known = list_courses()
        hint = "coursebrain list" if known else "coursebrain learn <url>"
        fail(f"no course named '{course_id}' in {find_workspace()}", hint)
    return paths


def complete_course(incomplete: str) -> list[str]:
    return [c for c in list_courses() if c.startswith(incomplete)]


def complete_profile(incomplete: str) -> list[str]:
    return [p for p in list_profiles() if p.startswith(incomplete)]


CourseArg = Annotated[str, typer.Argument(help="Course id", autocompletion=complete_course)]
OptionalCourseArg = Annotated[
    str | None, typer.Argument(help="Course id (default: all)", autocompletion=complete_course)
]
JsonOpt = Annotated[bool, typer.Option("--json", help="Machine-readable output")]


# --------------------------------------------------------------------------- ingest


@app.command()
def learn(
    url: Annotated[str, typer.Argument(help="Video, playlist, or channel URL")],
    course_id: Annotated[
        str | None, typer.Option("--id", help="Course id (default: derived from the URL)")
    ] = None,
    title: Annotated[str, typer.Option("--title", help="Human-readable course title")] = "",
    profile: Annotated[
        str, typer.Option("--profile", "-p", autocompletion=complete_profile)
    ] = "general",
    language: Annotated[str, typer.Option("--language", "-l")] = "en",
    limit: Annotated[int | None, typer.Option("--limit", help="Only the first N episodes")] = None,
    workers: Annotated[
        int, typer.Option("--workers", "-j", help="Parallel fetches")
    ] = DEFAULT_WORKERS,
) -> None:
    """Create a course and stage its transcripts, in one step.

    Then write a note per staged episode and run [bold]coursebrain assemble[/].
    Inside Claude Code, [bold]/learn[/] drives the whole loop for you.
    """
    if profile not in list_profiles():
        fail(f"unknown profile '{profile}'", f"one of: {', '.join(list_profiles())}")

    try:
        source = source_for(url)
    except SourceError as e:
        fail(str(e))
        return

    cid = course_id or slugify(title or url.rstrip("/").split("/")[-1].split("?")[0] or "course")
    paths = CoursePaths.for_course(cid)
    if paths.exists():
        err.print(f"[dim]using existing course '{cid}'[/]")
    else:
        paths.ensure_dirs()
        CourseConfig(id=cid, source_url=url, title=title, profile=profile, language=language).dump(
            paths.config
        )
        err.print(f"[green]created[/] course '{cid}' [dim](profile: {profile})[/]")

    err.print(f"[dim]source: {source.name}[/]")
    _prepare(cid, limit=limit, only=None, force=False, workers=workers)


@app.command()
def init(
    course_id: Annotated[str, typer.Argument(help="Course id (kebab-case)")],
    url: Annotated[str, typer.Argument(help="Video, playlist, or channel URL")],
    title: Annotated[str, typer.Option("--title")] = "",
    profile: Annotated[
        str, typer.Option("--profile", "-p", autocompletion=complete_profile)
    ] = "general",
    language: Annotated[str, typer.Option("--language", "-l")] = "en",
    repo: Annotated[str | None, typer.Option("--repo", help="Companion source repository")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Create a course without fetching anything yet."""
    if profile not in list_profiles():
        fail(f"unknown profile '{profile}'", f"one of: {', '.join(list_profiles())}")
    paths = CoursePaths.for_course(course_id)
    if paths.exists() and not force:
        fail(f"course '{course_id}' already exists at {paths.root}", "pass --force to overwrite")
    paths.ensure_dirs()
    CourseConfig(
        id=course_id,
        source_url=url,
        title=title,
        profile=profile,
        language=language,
        companion_repo=repo,
    ).dump(paths.config)
    out.print(f"[green]created[/] {paths.config}")
    out.print(f"[dim]next:[/] coursebrain prepare {course_id}")


def _prepare(
    course_id: str, limit: int | None, only: int | None, force: bool, workers: int
) -> None:
    paths = _course_or_fail(course_id)
    lines: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=err,
        transient=True,
    ) as progress:
        task = progress.add_task("fetching transcripts", total=None)

        def on_progress(title: str, done: int, total: int) -> None:
            progress.update(task, total=total, completed=done, description=f"[dim]{title[:44]}[/]")

        try:
            report = prepare_course(
                course_id,
                limit=limit,
                only=only,
                force=force,
                workers=workers,
                log=lines.append,
                on_progress=on_progress,
            )
        except SourceError as e:
            progress.stop()
            fail(str(e))
            return

    for line in lines:
        err.print(f"[dim]{line}[/]")

    todo = work.pending(paths)
    if todo:
        root = find_workspace()
        table = Table(title=f"{len(todo)} episode(s) to distill", title_justify="left", box=None)
        table.add_column("ep", style="cyan", no_wrap=True)
        table.add_column("read", style="dim")
        table.add_column("write")
        for item in todo:
            table.add_row(
                f"{item.episode:02d}",
                str(item.task.relative_to(root)),
                str(item.body.relative_to(root)),
            )
        out.print(table)
        out.print(f"\n[dim]then:[/] coursebrain assemble {course_id}")
    else:
        out.print(f"[green]{report.line()}[/]")

    if report.failed:
        raise typer.Exit(1)


@app.command()
def prepare(
    course_id: CourseArg,
    limit: Annotated[int | None, typer.Option("--limit")] = None,
    only: Annotated[int | None, typer.Option("--only", help="Just episode N")] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Restage episodes that already have notes")
    ] = False,
    workers: Annotated[int, typer.Option("--workers", "-j")] = DEFAULT_WORKERS,
) -> None:
    """Fetch transcripts and stage episodes for distillation."""
    _prepare(course_id, limit=limit, only=only, force=force, workers=workers)


@app.command()
def pending(course_id: OptionalCourseArg = None, json: JsonOpt = False) -> None:
    """List staged episodes still waiting for a note."""
    targets = [course_id] if course_id else list_courses()
    rows = [
        {"course": cid, "episode": item.episode, "task": str(item.task), "body": str(item.body)}
        for cid in targets
        for item in work.pending(CoursePaths.for_course(cid))
    ]
    if emit(rows, json):
        return
    if not rows:
        err.print("[dim]nothing pending[/]")
        return
    for row in rows:
        out.print(f"{row['course']}\t{row['episode']:02d}\t{row['task']}\t{row['body']}")


@app.command()
def assemble(course_id: CourseArg) -> None:
    """Turn written bodies into finished notes."""
    _course_or_fail(course_id)
    lines: list[str] = []
    report = assemble_course(course_id, log=lines.append)
    for line in lines:
        err.print(f"[dim]{line}[/]")
    out.print(f"[green]{report.line()}[/]")
    if report.failed:
        raise typer.Exit(1)


@app.command()
def build(
    course_id: CourseArg,
    limit: Annotated[int | None, typer.Option("--limit")] = None,
    only: Annotated[int | None, typer.Option("--only")] = None,
    model: Annotated[str, typer.Option("--model")] = DEFAULT_MODEL,
    force: Annotated[bool, typer.Option("--force")] = False,
    fetch_only: Annotated[bool, typer.Option("--fetch-only")] = False,
    workers: Annotated[int, typer.Option("--workers", "-j")] = DEFAULT_WORKERS,
) -> None:
    """Unattended end-to-end build through the Anthropic API.

    Inside Claude Code you do not need this — prepare/assemble cost nothing extra
    because the agent is already the model.
    """
    _course_or_fail(course_id)
    if not fetch_only and not api_key_present():
        fail(
            "build calls the Anthropic API directly, and no key is set",
            "coursebrain prepare (needs no key), or export ANTHROPIC_API_KEY",
        )
    lines: list[str] = []
    report = build_course(
        course_id,
        limit=limit,
        only=only,
        model=model,
        force=force,
        fetch_only=fetch_only,
        workers=workers,
        log=lines.append,
    )
    for line in lines:
        err.print(f"[dim]{line}[/]")
    out.print(f"[green]{report.line()}[/]")
    if report.failed:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------- query


@app.command(name="index")
def index_cmd(
    no_vectors: Annotated[bool, typer.Option("--no-vectors", help="Keyword index only")] = False,
) -> None:
    """Rebuild INDEX.md, CONCEPTS.md, BRAIN.md, and the search index."""
    lines: list[str] = []
    with err.status("[dim]indexing[/]"):
        total = index_all(use_vectors=not no_vectors, log=lines.append)
    for line in lines:
        err.print(f"[dim]{line}[/]")
    out.print(f"[green]{total} chunk(s) indexed[/]")


@app.command()
def ask(
    query: Annotated[str, typer.Argument(help="Question, in your own words")],
    k: Annotated[int, typer.Option("-k", help="Results to return")] = 5,
    course: Annotated[
        str | None, typer.Option("--course", "-c", autocompletion=complete_course)
    ] = None,
    chars: Annotated[int, typer.Option("--chars", help="Excerpt length")] = 400,
    no_vectors: Annotated[bool, typer.Option("--no-vectors")] = False,
    json: JsonOpt = False,
) -> None:
    """Search every course, by keyword and by meaning together."""
    brain = BrainPaths.for_workspace()
    if not brain.index_db.exists():
        fail("no search index yet", "coursebrain index")

    hits = search(brain.index_db, query, k=k, course=course, use_vectors=not no_vectors)
    if emit(
        [
            {
                "course": h.chunk.course,
                "episode": h.chunk.episode,
                "heading": h.chunk.heading,
                "url": h.chunk.url,
                "text": h.chunk.text,
                "score": round(h.score, 6),
                "sources": list(h.sources),
            }
            for h in hits
        ],
        json,
    ):
        return

    if not hits:
        out.print("[dim]no matches[/]")
        return
    for i, hit in enumerate(hits, start=1):
        body = " ".join(hit.chunk.text.split())
        excerpt = body[:chars] + ("…" if len(body) > chars else "")
        out.print(
            Panel(
                excerpt,
                title=f"[bold]{i}. {hit.chunk.label}[/]",
                subtitle=f"{hit.chunk.url}  [{'+'.join(hit.sources)}]",
                title_align="left",
                subtitle_align="left",
                border_style="dim",
            )
        )


@app.command(name="list")
def list_cmd(json: JsonOpt = False) -> None:
    """List courses in this workspace."""
    rows: list[dict[str, Any]] = []
    for course_id in list_courses():
        paths = CoursePaths.for_course(course_id)
        config = paths.load_config()
        manifest = Manifest.load(paths.manifest, course_id)
        rows.append(
            {
                "id": course_id,
                "title": config.title,
                "profile": config.profile,
                "language": config.language,
                "notes": len(list(paths.notes.glob("*.md"))) if paths.notes.exists() else 0,
                "episodes": len(manifest.episodes),
            }
        )
    if emit(rows, json):
        return
    if not rows:
        err.print(f"[dim]no courses in {find_workspace()}[/]")
        err.print("[dim]start one:[/] coursebrain learn <url>")
        return
    table = Table(box=None)
    table.add_column("course", style="cyan")
    for col in ("profile", "lang", "notes", "episodes"):
        table.add_column(col)
    for row in rows:
        table.add_row(
            str(row["id"]),
            str(row["profile"]),
            str(row["language"]),
            str(row["notes"]),
            str(row["episodes"]),
        )
    out.print(table)


@app.command()
def profiles(json: JsonOpt = False) -> None:
    """List note schemas. A profile decides what a note extracts."""
    rows = []
    for name in list_profiles():
        p = Profile.load(name)
        rows.append({"name": name, "description": p.description, "sections": p.headings})
    if emit(rows, json):
        return
    for row in rows:
        out.print(f"[bold cyan]{row['name']}[/]  [dim]{row['description']}[/]")
        out.print(f"  {' · '.join(row['sections'])}\n")


@app.command()
def sources(json: JsonOpt = False) -> None:
    """List installed ingest sources, including third-party plugins."""
    rows = [{"name": s.name, "module": type(s).__module__} for s in load_sources()]
    if emit(rows, json):
        return
    for row in rows:
        out.print(f"[bold cyan]{row['name']}[/]  [dim]{row['module']}[/]")


# ------------------------------------------------------------------------ integrity


@app.command()
def verify(course_id: OptionalCourseArg = None, json: JsonOpt = False) -> None:
    """Check notes for structural problems."""
    targets = [course_id] if course_id else list_courses()
    results: list[dict[str, Any]] = []
    failed = False
    for cid in targets:
        report = verify_course(cid)
        failed = failed or not report.ok
        results.append({"course": cid, "checked": report.checked, "problems": report.problems})

    if emit(results, json):
        raise typer.Exit(1 if failed else 0)

    for result in results:
        problems: list[str] = result["problems"]
        if not problems:
            out.print(f"[green]✓[/] {result['course']}  [dim]{result['checked']} note(s)[/]")
            continue
        out.print(
            f"[red]✗[/] {result['course']}  "
            f"[dim]{len(problems)} problem(s) in {result['checked']} note(s)[/]"
        )
        for problem in problems:
            out.print(f"    [dim]-[/] {problem}")
    if failed:
        raise typer.Exit(1)


@app.command(name="eval")
def eval_cmd(
    course_id: OptionalCourseArg = None,
    k: Annotated[int, typer.Option("-k")] = 5,
    init_set: Annotated[bool, typer.Option("--init", help="Write a starter question set")] = False,
    force: Annotated[bool, typer.Option("--force")] = False,
    no_vectors: Annotated[bool, typer.Option("--no-vectors")] = False,
    json: JsonOpt = False,
) -> None:
    """Score retrieval against a question set, so tuning is measured not guessed."""
    if init_set:
        if not course_id:
            fail("--init needs a course", "coursebrain eval <course> --init")
            return
        path = _course_or_fail(course_id).evals / "questions.yaml"
        if path.exists() and not force:
            fail(f"{path} already exists", "pass --force to overwrite")
        write_template(path)
        out.print(f"[green]wrote[/] {path}")
        out.print(f"[dim]fill it in, then:[/] coursebrain eval {course_id}")
        return

    result = run_eval(course_id, k=k, use_vectors=not no_vectors)
    if emit(
        {
            "total": result.total,
            "recall": result.recall,
            "mrr": result.mrr,
            "misses": result.misses,
        },
        json,
    ):
        return
    if not result.total:
        err.print("[dim]no eval questions found[/]")
        err.print("[dim]create some:[/] coursebrain eval <course> --init")
        return
    out.print(result.line(k))
    if 0 < result.total < 10:
        err.print(
            "[yellow]note[/] a small question set cannot discriminate — "
            "aim for ~20 spanning several episodes"
        )
    for miss in result.misses:
        out.print(f"  [red]missed[/] {miss}")


# --------------------------------------------------------------------------- doctor


@app.command()
def doctor(json: JsonOpt = False) -> None:
    """Check the setup and say exactly what to run for anything broken."""
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str, fix: str = "") -> None:
        checks.append({"check": name, "ok": ok, "detail": detail, "fix": fix})

    check("python", True, f"{sys.version.split()[0]}")

    workspace = find_workspace()
    writable = workspace.is_dir()
    check(
        "workspace",
        writable,
        str(workspace),
        "" if writable else "cd somewhere that exists, or set COURSEBRAIN_HOME",
    )

    try:
        check("yt-dlp", True, source_for("https://youtu.be/x").version())
    except SourceError as e:
        check("yt-dlp", False, str(e), "uv pip install --upgrade yt-dlp")

    if vectors_available():
        check("semantic search", True, "sqlite-vec + model2vec")
    else:
        check(
            "semantic search",
            False,
            "not installed — keyword search only",
            'uv pip install "coursebrain[rag]"',
        )

    check(
        "anthropic key",
        True,
        "set" if api_key_present() else "not set (only `build` needs it)",
    )
    check("courses", True, f"{len(list_courses())} in this workspace")

    brain = BrainPaths.for_workspace()
    indexed = brain.index_db.exists()
    check(
        "search index",
        indexed,
        str(brain.index_db) if indexed else "not built",
        "" if indexed else "coursebrain index",
    )

    broken = [c for c in checks if not c["ok"]]
    if emit(checks, json):
        raise typer.Exit(1 if broken else 0)

    for c in checks:
        mark = "[green]✓[/]" if c["ok"] else "[red]✗[/]"
        out.print(f"{mark} [bold]{c['check']}[/]  [dim]{c['detail']}[/]")
        if c["fix"]:
            out.print(f"    [yellow]fix:[/] {c['fix']}")
    if broken:
        raise typer.Exit(1)
    out.print("\n[green]everything looks fine[/]")


def _version_callback(value: bool) -> None:
    if value:
        from importlib.metadata import version

        out.print(f"coursebrain {version('coursebrain')}")
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[
        bool, typer.Option("--version", "-V", callback=_version_callback, is_eager=True)
    ] = False,
) -> None:
    """Turn long-form video into notes your agent can read, cite, and write from."""


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
