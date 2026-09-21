from __future__ import annotations

import argparse
import curses
import os
import sys

from . import __version__
from .app import run
from .gitlog import GitLogError, parse_commits


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitlapse",
        description="Watch a git repository's history replay live in your terminal.",
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="path to a git repository (default: current directory)"
    )
    parser.add_argument(
        "--branch", default=None, help="branch/ref to play (default: current HEAD)"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=45.0,
        help="target seconds to play the full history at 1.0x speed (default: 45)",
    )
    parser.add_argument(
        "--speed", type=float, default=1.0, help="initial playback speed multiplier (default: 1.0)"
    )
    parser.add_argument(
        "--auto-quit-after",
        type=float,
        default=None,
        metavar="SECONDS",
        help="exit automatically N seconds after playback finishes (useful for scripted recordings)",
    )
    parser.add_argument("--version", action="version", version=f"gitlapse {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_path = os.path.abspath(args.path)
    repo_name = os.path.basename(repo_path.rstrip(os.sep)) or repo_path

    try:
        commits = parse_commits(repo_path, args.branch)
    except GitLogError as exc:
        print(f"gitlapse: {exc}", file=sys.stderr)
        return 1

    def _main(stdscr):
        run(stdscr, commits, repo_name, args.duration, args.speed, args.auto_quit_after)

    try:
        curses.wrapper(_main)
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
