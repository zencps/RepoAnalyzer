"""Reusable Rich table and panel builders for repository data."""

from rich.box import DOUBLE, SIMPLE
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models.repository import (
    AnalysisReport,
    CommitStatistics,
    ContributorInfo,
    HealthBreakdown,
    HealthScore,
    LanguageUsage,
    RepositoryStats,
)
from utils.formatter import (
    build_language_bar,
    console,
    format_timestamp,
    generate_sparkline,
    humanize_bytes,
    humanize_number,
    humanize_size_kb,
)

SOURCE_LABELS: dict[str, tuple[str, str]] = {
    "github": ("GitHub", "primary"),
    "local": ("Local", "secondary"),
}


def build_stats_table(stats: RepositoryStats) -> Table:
    """Key/value grid of repository metadata with themed borders."""
    table: Table = Table(
        show_header=False,
        box=SIMPLE,
        border_style="border",
        pad_edge=False,
        expand=False,
    )
    table.add_column(style="secondary", justify="right", no_wrap=True)
    table.add_column(style="primary")

    source_label, source_style = SOURCE_LABELS.get(stats.source, (stats.source, "primary"))
    table.add_row("Source", Text(source_label, style=source_style))
    if stats.url:
        table.add_row("URL", stats.url)
    if stats.description:
        description: str = stats.description
        if len(description) > 90:
            description = description[:87] + "…"
        table.add_row("About", description)
    table.add_row("Branch", stats.default_branch)
    license_value: str = stats.license.name if stats.license else "—"
    table.add_row("License", license_value)
    table.add_row("Stars", humanize_number(stats.stars))
    table.add_row("Forks", humanize_number(stats.forks))
    table.add_row("Open issues", humanize_number(stats.open_issues))
    table.add_row("Watchers", humanize_number(stats.watchers))
    if stats.size_kb:
        table.add_row("Repo size", humanize_size_kb(stats.size_kb))
    table.add_row("Commits", humanize_number(stats.total_commits))
    table.add_row("Contributors", humanize_number(stats.total_contributors))
    table.add_row("Created", format_timestamp(stats.created_at))
    table.add_row("Updated", format_timestamp(stats.updated_at))
    table.add_row("Last push", format_timestamp(stats.pushed_at))
    return table


def build_summary_panel(stats: RepositoryStats) -> Panel:
    """Double-line highlight panel with headline metrics."""
    segments: list[tuple[str, str]] = []
    metrics: list[tuple[str, int | None]] = [
        ("Stars", stats.stars),
        ("Forks", stats.forks),
        ("Issues", stats.open_issues),
        ("Watchers", stats.watchers),
    ]
    for index, (label, value) in enumerate(metrics):
        if index:
            segments.append(("  ·  ", "muted"))
        segments.append((f"{label} ", "secondary"))
        segments.append((humanize_number(value), "metric"))
    if stats.total_commits is not None:
        segments.append(("  ·  ", "muted"))
        segments.append(("Commits ", "secondary"))
        segments.append((humanize_number(stats.total_commits), "metric"))

    body: Text = Text()
    for text, style in segments:
        body.append(text, style=style)

    timeline: str = (
        f"Created {format_timestamp(stats.created_at)}   "
        f"Updated {format_timestamp(stats.updated_at)}   "
        f"Pushed {format_timestamp(stats.pushed_at)}"
    )
    body.append("\n")
    body.append(timeline, style="muted")

    subtitle: str = stats.full_name
    if stats.local_path is not None:
        subtitle = f"{subtitle}  ·  {stats.local_path.as_posix()}"
    return Panel(
        body,
        box=DOUBLE,
        border_style="border",
        title="[table.header]Repository Snapshot[/]",
        subtitle=f"[muted]{subtitle}[/]",
    )


def build_contributors_table(contributors: list[ContributorInfo]) -> Table:
    """Ranked contributor listing by commit count."""
    table: Table = Table(
        title="[table.header]Top Contributors[/]",
        title_justify="left",
        box=DOUBLE,
        border_style="border",
        header_style="table.header",
    )
    table.add_column("#", style="muted", justify="right")
    table.add_column("Author", style="primary")
    table.add_column("Email", style="secondary")
    table.add_column("Commits", style="metric", justify="right")
    for rank, contributor in enumerate(contributors, start=1):
        table.add_row(
            str(rank),
            contributor.name,
            contributor.email or "—",
            humanize_number(contributor.commit_count),
        )
    return table


def build_languages_table(languages: list[LanguageUsage]) -> Table:
    """Language byte breakdown with block bars (percentages once computed)."""
    table: Table = Table(
        title="[table.header]Languages[/]",
        title_justify="left",
        box=DOUBLE,
        border_style="border",
        header_style="table.header",
    )
    table.add_column("Language", style="primary")
    table.add_column("Share", ratio=2)
    table.add_column("Size", style="secondary", justify="right")
    for usage in languages:
        bar: Text = build_language_bar(usage.name, usage.share_pct)
        table.add_row(usage.name, bar, humanize_bytes(usage.byte_size))
    return table


def build_commit_analytics_panel(
    stats: CommitStatistics,
    activity: list[int],
    *,
    subtitle: str = "",
) -> Panel:
    """Double-line panel with commit KPIs and a monthly activity sparkline."""
    body: Text = Text()

    def line(pieces: list[tuple[str, str]]) -> None:
        for text, style in pieces:
            body.append(text, style=style)

    size_line: str = (
        f"~{stats.avg_commit_size:g} lines changed"
        if stats.avg_commit_size is not None
        else "not computed"
    )
    peak_detail: str = (
        f"{stats.most_active_month} ({stats.most_active_month_count} commits)"
        if stats.most_active_month
        else "—"
    )

    line(
        [
            ("Total ", "secondary"),
            (humanize_number(stats.total_commits), "metric"),
            ("  ·  Avg/day ", "secondary"),
            (f"{stats.avg_per_day:g}", "metric"),
            ("  ·  Active days ", "secondary"),
            (str(stats.active_days), "metric"),
        ]
    )
    body.append("\n")
    line([("Most active month ", "secondary"), (peak_detail, "metric")])
    body.append("\n\n")
    body.append("Activity  ", style="secondary")
    body.append(generate_sparkline(activity))
    body.append(f"   last {len(activity)} months", style="muted")
    body.append("\n")
    line([("Avg commit size ", "secondary"), (size_line, "metric")])
    body.append("\n")
    line(
        [
            ("Oldest ", "secondary"),
            (format_timestamp(stats.oldest_at), "metric"),
            ("   Latest ", "secondary"),
            (format_timestamp(stats.latest_at), "metric"),
        ]
    )

    return Panel(
        body,
        box=DOUBLE,
        border_style="border",
        title="[table.header]Commit Analytics[/]",
        subtitle=f"[muted]{subtitle}[/]" if subtitle else None,
    )


def _score_style(points: int, maximum: int) -> str:
    ratio: float = points / maximum if maximum else 0.0
    if ratio >= 0.7:
        return "success"
    if ratio >= 0.4:
        return "warning"
    return "error"


_HEALTH_COMPONENTS: tuple[tuple[str, str, int], ...] = (
    ("Recency", "recency", 30),
    ("Activity", "activity", 25),
    ("Community", "community", 20),
    ("Governance", "governance", 15),
    ("Engagement", "engagement", 10),
)


def build_health_panel(score: HealthScore) -> Panel:
    """Double-line panel visualizing the composite health score."""
    grade_style: str = _score_style(score.total, 100)
    body: Text = Text()
    body.append("Grade ", style="secondary")
    body.append(score.grade, style=f"bold {grade_style}")
    body.append("   Score ", style="secondary")
    body.append(f"{score.total}/100", style="metric")
    body.append("\n\n")

    breakdown: HealthBreakdown = score.breakdown
    for label, field_name, maximum in _HEALTH_COMPONENTS:
        points: int = getattr(breakdown, field_name)
        style: str = _score_style(points, maximum)
        filled: int = round(points / maximum * 20) if maximum else 0
        body.append(f"{label:<12}", style="secondary")
        body.append("█" * filled + "░" * (20 - filled), style=style)
        body.append(f" {points:>2}/{maximum}\n", style="muted")

    if score.notes:
        body.append("\n")
        for note in score.notes:
            body.append("• ", style="warning")
            body.append(note + "\n", style="secondary")

    return Panel(
        body,
        box=DOUBLE,
        border_style="border",
        title="[table.header]Repository Health[/]",
        subtitle=f"[muted]{score.total}/100 · {score.grade}[/]",
    )


def build_about_table(
    *,
    version: str,
    python_version: str,
    operating_system: str,
    token_display: str,
    token_source: str | None,
    clone_dir: str,
) -> Table:
    """Environment/configuration summary used by the about command."""
    table: Table = Table(
        show_header=False,
        box=DOUBLE,
        border_style="border",
        pad_edge=False,
        expand=False,
    )
    table.add_column(style="secondary", justify="right", no_wrap=True)
    table.add_column(style="primary")
    table.add_row("Version", version)
    table.add_row("Python", python_version)
    table.add_row("Platform", operating_system)
    source_note: str = f" ({token_source})" if token_source else ""
    table.add_row("GitHub token", f"{token_display}{source_note}")
    table.add_row("Clone directory", clone_dir)
    return table


def render_report(report: AnalysisReport, out: Console | None = None) -> None:
    """Print every populated section of an analysis report in order."""
    target: Console = out if out is not None else console

    target.print(build_summary_panel(report.repository))
    if report.health_score is not None:
        target.print()
        target.print(build_health_panel(report.health_score))
    target.print()
    target.print(build_stats_table(report.repository))
    if report.contributors:
        target.print()
        target.print(build_contributors_table(report.contributors))
    if report.languages:
        target.print()
        target.print(build_languages_table(report.languages))
