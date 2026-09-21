"""Parse a git repository's history into a list of Commit objects.

Uses only `git log --raw --numstat` (stdlib subprocess, no third-party deps)
so the whole tool works with nothing but git + a stock Python install.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

HEADER_PREFIX = "@@GL@@"


@dataclass
class FileChange:
    path: str
    status: str  # 'A' (added), 'M' (modified), 'D' (deleted)
    insertions: int
    deletions: int


@dataclass
class Commit:
    sha: str
    author: str
    timestamp: int
    subject: str
    changes: list = field(default_factory=list)


class GitLogError(RuntimeError):
    pass


def _run_git_log(repo_path: str, branch: str | None) -> str:
    fmt = f"{HEADER_PREFIX}%H%x1f%an%x1f%ct%x1f%s"
    cmd = [
        "git",
        "-C",
        repo_path,
        "log",
        "--reverse",
        "--no-renames",
        "--raw",
        "--numstat",
        f"--format={fmt}",
    ]
    if branch:
        cmd.append(branch)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        )
    except FileNotFoundError as exc:
        raise GitLogError("git executable not found on PATH") from exc

    if result.returncode != 0:
        raise GitLogError(
            f"git log failed (is '{repo_path}' a git repository?): "
            f"{result.stderr.strip()}"
        )
    return result.stdout


def _parse_raw_line(line: str) -> tuple[str, str] | None:
    # format: ":oldmode newmode oldsha newsha STATUS\tpath"
    if not line.startswith(":"):
        return None
    try:
        meta, path = line.split("\t", 1)
    except ValueError:
        return None
    status = meta.split()[-1][0]  # first char handles e.g. "M100" scores
    return status, path.strip()


def _parse_numstat_line(line: str) -> tuple[str, int, int] | None:
    parts = line.split("\t")
    if len(parts) != 3:
        return None
    ins_s, del_s, path = parts
    ins = 0 if ins_s == "-" else int(ins_s)
    dele = 0 if del_s == "-" else int(del_s)
    return path.strip(), ins, dele


def parse_commits(repo_path: str = ".", branch: str | None = None) -> list[Commit]:
    output = _run_git_log(repo_path, branch)
    if not output.strip():
        raise GitLogError("no commits found in this repository")

    commits: list[Commit] = []
    blocks = output.split(HEADER_PREFIX)[1:]  # first split chunk is empty

    for block in blocks:
        header_line, _, rest = block.partition("\n")
        sha, author, ts, subject = header_line.split("\x1f", 3)

        statuses: dict[str, str] = {}
        numstats: dict[str, tuple[int, int]] = {}

        for line in rest.splitlines():
            if not line:
                continue
            raw = _parse_raw_line(line)
            if raw is not None:
                status, path = raw
                statuses[path] = status
                continue
            ns = _parse_numstat_line(line)
            if ns is not None:
                path, ins, dele = ns
                numstats[path] = (ins, dele)

        changes = []
        for path, status in statuses.items():
            ins, dele = numstats.get(path, (0, 0))
            changes.append(FileChange(path=path, status=status, insertions=ins, deletions=dele))

        commits.append(
            Commit(
                sha=sha,
                author=author,
                timestamp=int(ts),
                subject=subject,
                changes=changes,
            )
        )

    return commits
