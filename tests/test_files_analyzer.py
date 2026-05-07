"""Tests for local file scanning."""

from analyzer.files import count_lines_of_code, scan_directory
from utils.helpers import RepoAnalyzerError


class TestScanDirectory:
    def test_counts_and_loc(self, poly_repo) -> None:
        analysis = scan_directory(poly_repo)
        assert analysis.total_files == 4
        assert analysis.total_lines_of_code == 30 + 10 + 1

    def test_type_and_byte_maps(self, poly_repo) -> None:
        analysis = scan_directory(poly_repo)
        assert analysis.type_counts["py"] == 1
        assert analysis.type_counts["js"] == 1
        assert analysis.type_counts["bin"] == 1
        assert analysis.byte_counts["md"] > 0
        assert "py" in analysis.byte_counts

    def test_skips_noise_dirs(self, poly_repo) -> None:
        analysis = scan_directory(poly_repo)
        paths = [info.path for info in analysis.biggest_files]
        all_paths = " ".join(paths)
        assert "node_modules" not in all_paths
        assert analysis.type_counts.get("js", 0) == 1

    def test_binary_files_have_no_loc(self, poly_repo) -> None:
        analysis = scan_directory(poly_repo)
        binary_entry = next(
            info for info in analysis.biggest_files if info.extension == "bin"
        )
        assert binary_entry.lines_of_code is None

    def test_biggest_files_sorted_desc(self, poly_repo) -> None:
        analysis = scan_directory(poly_repo)
        sizes = [info.size_bytes for info in analysis.biggest_files]
        assert sizes == sorted(sizes, reverse=True)

    def test_missing_root_raises(self, tmp_path) -> None:
        try:
            scan_directory(tmp_path / "ghost")
        except RepoAnalyzerError as exc:
            assert "Not a directory" in str(exc)
        else:
            raise AssertionError("Expected RepoAnalyzerError")


class TestCountLinesOfCode:
    def test_blank_lines_excluded(self, tmp_path) -> None:
        target = tmp_path / "code.py"
        target.write_text("a = 1\n\n\nb = 2\n", encoding="utf-8")
        assert count_lines_of_code(target, target.stat().st_size) == 2

    def test_binary_returns_none(self, tmp_path) -> None:
        target = tmp_path / "blob.bin"
        target.write_bytes(b"\x00\x01\x02data\xff")
        assert count_lines_of_code(target, target.stat().st_size) is None
