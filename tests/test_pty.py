"""Drive the real curses UI through a pseudo-terminal."""
import os
import sys

import pytest

pytestmark = pytest.mark.skipif(os.name != "posix", reason="needs a POSIX pty")
sys.path.insert(0, os.path.dirname(__file__))
from pty_harness import run  # noqa: E402


def _ok(result, expect_rc=0):
    rc, timed_out, out = result
    assert not timed_out, "never exited"
    assert rc == expect_rc, out[-300:]
    assert "Traceback" not in out and "_curses.error" not in out, out[-300:]
    return out


def test_every_key_then_quit(nasty_repo):
    keys = [(1.0, b" "), (1.2, b" "), (1.4, b"+"), (1.6, b"-"), (1.8, b"\x1b[C"), (2.0, b"\x1b[D"),
            (2.2, b"r"), (2.8, b"q")]
    assert "gitlapse" in _ok(run([nasty_repo, "--duration", "4"], script=keys))


@pytest.mark.parametrize("rows,cols", [(6, 20), (10, 44), (80, 300), (1, 200)])
def test_odd_terminal_sizes(nasty_repo, rows, cols):
    _ok(run([nasty_repo], rows=rows, cols=cols, script=[(1.0, b"q")]))


def test_resize_storm(nasty_repo):
    script = [(1.0, ("resize", 12, 50)), (1.4, ("resize", 5, 20)), (1.8, ("resize", 60, 200)),
              (2.2, ("resize", 3, 10)), (2.6, ("resize", 30, 120)), (3.2, b"q")]
    _ok(run([nasty_repo, "--duration", "6"], script=script))


def test_key_mashing_including_left_at_the_very_start(nasty_repo):
    script = [(0.6, b"\x1b[D"), (0.7, b"\x1b[D")] + [
        (0.8 + i * 0.02, k) for i, k in enumerate([b"\x1b[C", b"\x1b[D", b"+", b"-", b" ", b"r"] * 10)
    ] + [(3.0, b"q")]
    _ok(run([nasty_repo, "--duration", "6"], script=script))


def test_ctrl_c_exits_cleanly(nasty_repo):
    _ok(run([nasty_repo, "--duration", "20"], script=[(1.0, "SIGINT")]))


def test_auto_quit_after(nasty_repo):
    _ok(run([nasty_repo, "--duration", "1", "--auto-quit-after", "0.5"], total=12))


@pytest.mark.parametrize("term", ["vt100", "xterm"])
def test_limited_terminals(nasty_repo, term):
    _ok(run([nasty_repo, "--duration", "2", "--auto-quit-after", "0.5"], term=term, total=12))


@pytest.mark.parametrize("term", ["dumb", None])
def test_unusable_terminals_give_a_message_or_run(nasty_repo, term):
    rc, timed_out, out = run([nasty_repo, "--duration", "2", "--auto-quit-after", "0.5"], term=term, total=12)
    assert not timed_out and "Traceback" not in out and "_curses.error" not in out
