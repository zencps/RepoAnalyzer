"""Working-copy file scanning: sizes, type counts, LOC, and biggest files."""

import logging
import os
from pathlib import Path

from models.repository import FileAnalysis, FileInfo
from utils.helpers import RepoAnalyzerError

logger: logging.Logger = logging.getLogger(__name__)

SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".idea",
        ".vscode",
        "dist",
        "build",
        "target",
        ".next",
        ".cache",
    }
)

BINARY_SNIFF_BYTES: int = 8_192
TEXT_SCAN_LIMIT_BYTES: int = 2_000_000
DEFAULT_TOP_FILES: int = 10


class NotADirectoryError_(RepoAnalyzerError):
    """Raised when the scan root is missing or not a directory."""


def scan_directory(root: Path, *, top_files: int = DEFAULT_TOP_FILES) -> FileAnalysis:
    """Walk a directory tree (pruning noise) and aggregate file metrics."""
    resolved: Path = root.expanduser().resolve()
    if not resolved.is_dir():
        raise NotADirectoryError_(f"Not a directory: {resolved}")

    type_counts: dict[str, int] = {}
    byte_counts: dict[str, int] = {}
    entries: list[FileInfo] = []
    total_bytes: int = 0
    total_loc: int = 0
    file_count: int = 0

    for current_dir, dir_names, file_names in os.walk(resolved):
        dir_names[:] = [d for d in dir_names if d not in SKIP_DIRS]
        base: Path = Path(current_dir)
        for file_name in file_names:
            path: Path = base / file_name
            try:
                size: int = path.stat().st_size
            except OSError as exc:
                logger.debug("Skipping unreadable file %s (%s)", path, exc)
                continue

            extension: str = path.suffix.lower().lstrip(".")
            type_counts[extension or "no_ext"] = type_counts.get(extension or "no_ext", 0) + 1
            byte_counts[extension or "no_ext"] = byte_counts.get(extension or "no_ext", 0) + size
            loc: int | None = count_lines_of_code(path, size)
            if loc is not None:
                total_loc += loc
            total_bytes += size
            file_count += 1
            entries.append(
                FileInfo(
                    path=path.relative_to(resolved).as_posix(),
                    name=file_name,
                    extension=extension,
                    size_bytes=size,
                    lines_of_code=loc,
                )
            )

    biggest: list[FileInfo] = sorted(
        entries, key=lambda info: info.size_bytes, reverse=True
    )[:top_files]

    return FileAnalysis(
        root=resolved,
        total_files=file_count,
        total_bytes=total_bytes,
        total_lines_of_code=total_loc,
        type_counts=type_counts,
        byte_counts=byte_counts,
        biggest_files=biggest,
    )


def count_lines_of_code(path: Path, size: int) -> int | None:
    """Count non-blank lines for text files; None for binary/oversized files."""
    if size > TEXT_SCAN_LIMIT_BYTES or size == 0:
        return None
    try:
        with path.open("rb") as handle:
            chunk: bytes = handle.read(BINARY_SNIFF_BYTES)
        if b"\x00" in chunk:
            return None
        with path.open("rb") as handle:
            raw: bytes = handle.read()
    except OSError as exc:
        logger.debug("Cannot read %s (%s)", path, exc)
        return None
    return sum(1 for line in raw.decode("utf-8", errors="ignore").splitlines() if line.strip())
