import subprocess
import sys

import pytest

from gitlapse.cli import main


def _run(*args):
    return subprocess.run([sys.executable, "-m", "gitlapse", *args], stdin=subprocess.DEVNULL,
                          capture_output=True, text=True)


@pytest.mark.parametrize("flags", [["--duration", "-5"], ["--duration", "0"], ["--speed", "0"],
                                   ["--speed", "-1"], ["--auto-quit-after", "-1"]])
def test_nonsense_numbers_are_rejected(flags, nasty_repo):
    r = _run(nasty_repo, *flags)
    assert r.returncode == 2 and "Traceback" not in r.stderr


def test_no_tty_is_a_friendly_error_not_a_traceback(nasty_repo):
    r = _run(nasty_repo)
    assert r.returncode == 1 and "interactive terminal" in r.stderr and "Traceback" not in r.stderr


def test_bad_repo_and_branch_messages(tmp_path, nasty_repo, capsys):
    assert main([str(tmp_path)]) == 1
    assert "not a git repository" in capsys.readouterr().err
    assert main([nasty_repo, "--branch", "nope"]) == 1
    assert "no such branch" in capsys.readouterr().err
