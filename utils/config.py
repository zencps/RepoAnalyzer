"""Configuration loading: GitHub token and defaults from .env and config.toml."""

import os
import tomllib
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from utils.helpers import RepoAnalyzerError

ENV_TOKEN_VAR: str = "GITHUB_TOKEN"


class ConfigError(RepoAnalyzerError):
    """Raised when a config file exists but cannot be parsed."""


class Settings(BaseModel):
    github_token: str | None = None
    token_source: str | None = None
    clone_base_dir: Path = Field(default_factory=lambda: Path.cwd() / "repos")


def candidate_config_paths() -> tuple[Path, ...]:
    """Config lookup order: project dir first, then the user config dir."""
    return (
        Path.cwd() / "config.toml",
        Path.home() / ".config" / "repo-analyzer" / "config.toml",
    )


def candidate_env_paths() -> tuple[Path, ...]:
    return (
        Path.cwd() / ".env",
        Path.home() / ".config" / "repo-analyzer" / ".env",
    )


def _read_toml(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as handle:
            data: object = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc
    return data if isinstance(data, dict) else {}


def _load_env_files() -> None:
    for candidate in candidate_env_paths():
        if candidate.is_file():
            load_dotenv(candidate, override=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    token_preexisting: bool = os.environ.get(ENV_TOKEN_VAR) is not None
    _load_env_files()

    token: str | None = os.environ.get(ENV_TOKEN_VAR)
    source: str | None = None
    if token is not None:
        source = "environment" if token_preexisting else ".env"

    clone_dir: Path | None = None

    for path in candidate_config_paths():
        data: dict[str, object] = _read_toml(path)

        github_section = data.get("github")
        if token is None and isinstance(github_section, dict):
            value = github_section.get("token")
            if isinstance(value, str) and value.strip():
                token = value.strip()
                source = "config.toml"

        paths_section = data.get("paths")
        if clone_dir is None and isinstance(paths_section, dict):
            value = paths_section.get("clone_base_dir")
            if isinstance(value, str) and value.strip():
                clone_dir = Path(value.strip()).expanduser()

    settings: Settings = Settings(github_token=token, token_source=source)
    if clone_dir is not None:
        settings.clone_base_dir = clone_dir
    return settings


def reset_settings_cache() -> None:
    get_settings.cache_clear()
