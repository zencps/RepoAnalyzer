"""Pydantic domain models shared by analyzers, commands, and exporters."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

DataSource = Literal["github", "local"]


class LicenseInfo(BaseModel):
    name: str
    spdx_id: str | None = None


class RepositoryStats(BaseModel):
    full_name: str
    source: DataSource
    url: str = ""
    description: str | None = None
    default_branch: str = "HEAD"
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    watchers: int = 0
    size_kb: int = 0
    total_commits: int | None = None
    total_contributors: int | None = None
    license: LicenseInfo | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    pushed_at: datetime | None = None
    local_path: Path | None = None


class CommitInfo(BaseModel):
    sha: str
    committed_at: datetime
    message: str = ""
    author_name: str = "unknown"
    author_email: str | None = None
    additions: int | None = None
    deletions: int | None = None
    files_changed: int | None = None


class ContributorInfo(BaseModel):
    name: str
    commit_count: int
    email: str | None = None
    profile_url: str | None = None
    share_pct: float = 0.0


class CommitStatistics(BaseModel):
    """Derived analytics over a normalized commit history."""

    total_commits: int = 0
    avg_per_day: float = 0.0
    active_days: int = 0
    span_days: float = 0.0
    oldest_at: datetime | None = None
    latest_at: datetime | None = None
    oldest_sha: str | None = None
    latest_sha: str | None = None
    most_active_month: str | None = None
    most_active_month_count: int = 0
    avg_commit_size: float | None = None


class LanguageUsage(BaseModel):
    name: str
    byte_size: int
    share_pct: float = 0.0


class FileInfo(BaseModel):
    path: str
    name: str
    extension: str = ""
    size_bytes: int = 0
    lines_of_code: int | None = None


class FileAnalysis(BaseModel):
    """Aggregate results of scanning a working-copy directory tree."""

    root: Path | None = None
    total_files: int = 0
    total_bytes: int = 0
    total_lines_of_code: int = 0
    type_counts: dict[str, int] = Field(default_factory=dict)
    byte_counts: dict[str, int] = Field(default_factory=dict)
    biggest_files: list[FileInfo] = Field(default_factory=list)


class HealthBreakdown(BaseModel):
    recency: int = 0
    activity: int = 0
    community: int = 0
    governance: int = 0
    engagement: int = 0


class HealthScore(BaseModel):
    """Composite 0-100 repository health rating with per-component points."""

    total: int
    grade: str
    breakdown: HealthBreakdown
    notes: list[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    """Aggregate container produced by analyzers and consumed by exporters."""

    repository: RepositoryStats
    commits: list[CommitInfo] = Field(default_factory=list)
    contributors: list[ContributorInfo] = Field(default_factory=list)
    languages: list[LanguageUsage] = Field(default_factory=list)
    commit_statistics: CommitStatistics | None = None
    file_analysis: FileAnalysis | None = None
    health_score: HealthScore | None = None
    generated_at: datetime = Field(default_factory=datetime.now)
