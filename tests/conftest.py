import os
import subprocess

import pytest

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Alice", "GIT_AUTHOR_EMAIL": "a@x.com",
    "GIT_COMMITTER_NAME": "Alice", "GIT_COMMITTER_EMAIL": "a@x.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, env=ENV, check=True, capture_output=True)


def commit(cwd, msg):
    git(cwd, "add", "-A")
    git(cwd, "commit", "-q", "--allow-empty", "-m", msg)


@pytest.fixture
def nasty_repo(tmp_path):
    """A repo full of the things that break naive git-history tools."""
    r = tmp_path / "nasty"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    (r / "café.txt").write_text("1")
    (r / "日本語.md").write_text("2")
    (r / "with space.py").write_text("3")
    (r / 'quo"te.txt').write_text("4")
    (r / "tab\tname.txt").write_text("5")
    (r / "d e").mkdir()
    (r / "d e" / "ünï.py").write_text("6")
    commit(r, "odd names")
    commit(r, "empty commit")
    (r / "café.txt").write_text("1\n7")
    commit(r, "modify")
    (r / "with space.py").unlink()
    commit(r, "delete")
    (r / "with space.py").write_text("8")
    commit(r, "re-add")
    (r / "blob.bin").write_bytes(bytes(range(256)) * 8)
    commit(r, "binary")
    git(r, "checkout", "-q", "-b", "feat")
    (r / "feat.txt").write_text("f")
    commit(r, "feature")
    git(r, "checkout", "-q", "main")
    (r / "main.txt").write_text("m")
    commit(r, "main work")
    git(r, "merge", "-q", "--no-ff", "feat", "-m", "merge feat")
    return str(r)
