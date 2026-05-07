"""Language share computation and file-extension to language mapping."""

from collections import Counter
from collections.abc import Mapping, Sequence

from models.repository import LanguageUsage

EXTENSION_LANGUAGES: dict[str, str] = {
    "py": "Python",
    "pyw": "Python",
    "ts": "TypeScript",
    "tsx": "TypeScript",
    "js": "JavaScript",
    "jsx": "JavaScript",
    "mjs": "JavaScript",
    "cjs": "JavaScript",
    "vue": "Vue",
    "svelte": "Svelte",
    "go": "Go",
    "rs": "Rust",
    "java": "Java",
    "kt": "Kotlin",
    "kts": "Kotlin",
    "swift": "Swift",
    "scala": "Scala",
    "rb": "Ruby",
    "php": "PHP",
    "cs": "C#",
    "fs": "F#",
    "c": "C",
    "h": "C",
    "cpp": "C++",
    "cc": "C++",
    "cxx": "C++",
    "hpp": "C++",
    "hh": "C++",
    "m": "Objective-C",
    "mm": "Objective-C",
    "zig": "Zig",
    "dart": "Dart",
    "lua": "Lua",
    "pl": "Perl",
    "r": "R",
    "jl": "Julia",
    "ex": "Elixir",
    "exs": "Elixir",
    "erl": "Erlang",
    "hs": "Haskell",
    "clj": "Clojure",
    "sh": "Shell",
    "bash": "Shell",
    "zsh": "Shell",
    "ps1": "PowerShell",
    "bat": "Batch",
    "sql": "SQL",
    "html": "HTML",
    "htm": "HTML",
    "css": "CSS",
    "scss": "SCSS",
    "sass": "Sass",
    "less": "Less",
}


def compute_shares(usages: Sequence[LanguageUsage]) -> list[LanguageUsage]:
    """Fill `share_pct` from byte sizes and sort by size, descending."""
    total: int = sum(usage.byte_size for usage in usages)
    ordered: list[LanguageUsage] = sorted(
        (usage.model_copy(deep=True) for usage in usages),
        key=lambda usage: usage.byte_size,
        reverse=True,
    )
    for usage in ordered:
        usage.share_pct = (
            round(usage.byte_size / total * 100, 1) if total else 0.0
        )
    return ordered


def usage_from_extensions(
    bytes_by_extension: Mapping[str, int],
) -> list[LanguageUsage]:
    """Aggregate per-extension byte counts into ranked LanguageUsage records."""
    aggregated: Counter[str] = Counter()
    for extension, size in bytes_by_extension.items():
        language: str | None = EXTENSION_LANGUAGES.get(extension.lower())
        if language is not None:
            aggregated[language] += size
    usages: list[LanguageUsage] = [
        LanguageUsage(name=name, byte_size=size)
        for name, size in aggregated.items()
    ]
    return compute_shares(usages)
