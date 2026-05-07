"""Tests for contributor ranking and language share computation."""

from datetime import UTC, datetime

from analyzer.contributors import rank_contributors
from analyzer.language import compute_shares, usage_from_extensions
from models.repository import CommitInfo, LanguageUsage


def _commit(author: str, email: str | None = "a@x.io") -> CommitInfo:
    return CommitInfo(
        sha=author,
        committed_at=datetime(2026, 1, 1, tzinfo=UTC),
        author_name=author,
        author_email=email,
    )


class TestRankContributors:
    def test_ranking_and_share(self) -> None:
        commits = [_commit("Ada")] * 7 + [_commit("Grace")] * 3
        ranked = rank_contributors(commits)
        assert [p.name for p in ranked] == ["Ada", "Grace"]
        assert ranked[0].share_pct == 70.0
        assert ranked[1].share_pct == 30.0

    def test_top_slice(self) -> None:
        commits = [_commit("Ada")] * 5 + [_commit("Grace")] * 2 + [_commit("Linus")]
        top = rank_contributors(commits, top=2)
        assert len(top) == 2
        assert top[0].name == "Ada"

    def test_email_captured_first_seen(self) -> None:
        first = CommitInfo(
            sha="x",
            committed_at=datetime(2026, 1, 1, tzinfo=UTC),
            author_name="Ada",
            author_email="ada@x.io",
        )
        second = CommitInfo(
            sha="y",
            committed_at=datetime(2026, 1, 2, tzinfo=UTC),
            author_name="Ada",
            author_email="other@x.io",
        )
        ranked = rank_contributors([first, second])
        assert ranked[0].email == "ada@x.io"


class TestComputeShares:
    def test_sorted_desc_and_percentages(self) -> None:
        usages = [
            LanguageUsage(name="A", byte_size=100),
            LanguageUsage(name="B", byte_size=300),
        ]
        result = compute_shares(usages)
        assert [u.name for u in result] == ["B", "A"]
        assert result[0].share_pct == 75.0
        assert result[1].share_pct == 25.0

    def test_does_not_mutate_input(self) -> None:
        original = LanguageUsage(name="A", byte_size=100)
        compute_shares([original])
        assert original.share_pct == 0.0


class TestUsageFromExtensions:
    def test_maps_known_and_skips_unknown(self) -> None:
        usage = usage_from_extensions({"py": 700, "js": 300, "lock": 500})
        assert [u.name for u in usage] == ["Python", "JavaScript"]
        assert usage[0].share_pct == 70.0

    def test_case_insensitive_extensions(self) -> None:
        usage = usage_from_extensions({"PY": 100, ".Rs": 0})
        assert usage[0].name in {"Python", "Rust"}
