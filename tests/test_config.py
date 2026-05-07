"""Tests for configuration loading (.env + config.toml)."""

from pathlib import Path

import pytest

from utils.config import (
    ConfigError,
    Settings,
    _read_toml,
    get_settings,
    reset_settings_cache,
)


@pytest.fixture(autouse=True)
def clean_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    reset_settings_cache()
    yield
    reset_settings_cache()


class TestTomlParsing:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert _read_toml(tmp_path / "absent.toml") == {}

    def test_valid_sections(self, tmp_path: Path) -> None:
        target = tmp_path / "config.toml"
        target.write_text(
            '[github]\ntoken = "abc123"\n\n[paths]\nclone_base_dir = "~/clones"\n',
            encoding="utf-8",
        )
        data = _read_toml(target)
        github_section = data["github"]
        assert isinstance(github_section, dict)
        assert github_section["token"] == "abc123"

    def test_invalid_toml_raises(self, tmp_path: Path) -> None:
        target = tmp_path / "broken.toml"
        target.write_text("not [valid toml", encoding="utf-8")
        with pytest.raises(ConfigError):
            _read_toml(target)


class TestGetSettings:
    def test_env_token_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "env-token-1234")
        settings: Settings = get_settings()
        assert settings.github_token == "env-token-1234"

    def test_toml_token_used_when_no_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.toml").write_text(
            '[github]\ntoken = "toml-token-5678"\n',
            encoding="utf-8",
        )
        reset_settings_cache()
        settings: Settings = get_settings()
        assert settings.github_token == "toml-token-5678"

    def test_none_without_any_config(self) -> None:
        settings: Settings = get_settings()
        assert settings.github_token is None
        assert settings.token_source is None

    def test_env_token_reports_environment_source(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "env-token-1234")
        assert get_settings().token_source == "environment"

    def test_dotenv_token_reports_dotenv_source(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("GITHUB_TOKEN=dotenv-token-99\n", encoding="utf-8")
        reset_settings_cache()
        settings: Settings = get_settings()
        assert settings.github_token == "dotenv-token-99"
        assert settings.token_source == ".env"

    def test_toml_token_reports_toml_source(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.toml").write_text(
            '[github]\ntoken = "toml-token-5678"\n',
            encoding="utf-8",
        )
        reset_settings_cache()
        settings: Settings = get_settings()
        assert settings.github_token == "toml-token-5678"
        assert settings.token_source == "config.toml"

    def test_clone_dir_from_toml(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        clone_target = (tmp_path / "clones").as_posix()
        (tmp_path / "config.toml").write_text(
            f"[paths]\nclone_base_dir = '{clone_target}'\n",
            encoding="utf-8",
        )
        reset_settings_cache()
        assert get_settings().clone_base_dir == tmp_path / "clones"
