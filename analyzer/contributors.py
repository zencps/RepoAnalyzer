"""Contributor ranking from normalized commit records."""

from collections import Counter
from collections.abc import Sequence

from models.repository import CommitInfo, ContributorInfo


def rank_contributors(
    commits: Sequence[CommitInfo],
    top: int | None = None,
) -> list[ContributorInfo]:
    """Aggregate commits per author, ranked by count, with share of total."""
    counts: Counter[str] = Counter()
    emails: dict[str, str | None] = {}
    for commit in commits:
        name: str = commit.author_name or "unknown"
        counts[name] += 1
        emails.setdefault(name, commit.author_email)

    grand_total: int = sum(counts.values())
    ranked: list[ContributorInfo] = []
    for name, count in counts.most_common(top):
        share: float = (count / grand_total * 100) if grand_total else 0.0
        ranked.append(
            ContributorInfo(
                name=name,
                commit_count=count,
                email=emails.get(name),
                share_pct=round(share, 1),
            )
        )
    return ranked
