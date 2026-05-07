"""Shared pytest fixtures."""

from pathlib import Path

import pytest
from git import Actor, Repo


@pytest.fixture
def local_repo(tmp_path: Path) -> Repo:
    """A small real Git repository with three commits from two authors."""
    repo: Repo = Repo.init(tmp_path / "sample")
    with repo.config_writer() as config:
        config.set_value("user", "name", "Ada Lovelace")
        config.set_value("user", "email", "ada@example.com")

    ada: Actor = Actor("Ada Lovelace", "ada@example.com")
    grace: Actor = Actor("Grace Hopper", "grace@example.com")

    workdir: Path = Path(repo.working_dir)

    (workdir / "README.md").write_text("# sample\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit", author=ada, committer=ada)

    (workdir / "app.py").write_text("print('hi')\n", encoding="utf-8")
    repo.index.add(["app.py"])
    repo.index.commit("add app", author=ada, committer=ada)

    (workdir / "app.py").write_text("print('hello')\n", encoding="utf-8")
    repo.index.add(["app.py"])
    repo.index.commit("tweak app", author=grace, committer=grace)
    return repo


@pytest.fixture(name="poly_repo")
def poly_repo_fixture(tmp_path: Path) -> Path:
    """A non-git directory tree with mixed languages and noise dirs."""
    root: Path = tmp_path / "poly"
    (root / "src").mkdir(parents=True)
    (root / "assets").mkdir()
    (root / "node_modules" / "junk").mkdir(parents=True)
    (root / ".git" / "objects").mkdir(parents=True)

    python_source = "\n".join(f"x{i} = {i}" for i in range(30)) + "\n"
    (root / "src" / "main.py").write_text(python_source, encoding="utf-8")

    js_source = "\n".join(f"const v{i} = {i};" for i in range(10)) + "\n"
    (root / "src" / "util.js").write_text(js_source, encoding="utf-8")

    (root / "assets" / "logo.bin").write_bytes(b"\x00\x01\x02binary\xff")
    (root / "README.md").write_text("# poly\n", encoding="utf-8")
    (root / "node_modules" / "junk.js").write_text("junk();\n", encoding="utf-8")
    (root / ".git" / "objects" / "pack.py").write_text("internal = 1\n", encoding="utf-8")
    return root
