from __future__ import annotations

import curses
import time
from collections import Counter
from datetime import datetime

from .colors import ColorMap, DIR_PAIR, DYING_PAIR, UI_PAIR
from .gitlog import Commit
from .model import FileTree

MIN_DELAY = 0.02
MAX_DELAY = 1.2
TICK_INTERVAL = 0.08


def _fmt_size(n: int) -> str:
    if n < 1000:
        return str(n)
    return f"{n / 1000:.1f}k"


def _safe_addstr(stdscr, y, x, text, attr=0):
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or x >= w:
        return
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass  # writing to the bottom-right cell raises; harmless to ignore


class Playback:
    def __init__(self, commits: list[Commit], target_duration: float):
        self.commits = commits
        self.tree = FileTree()
        self.idx = 0
        self.playing = True
        self.speed = 1.0
        self.author_counts: Counter = Counter()
        self.total_insertions = 0
        self.total_deletions = 0
        n = max(1, len(commits))
        self.base_delay = min(MAX_DELAY, max(MIN_DELAY, target_duration / n))
        self.scroll = 0

    @property
    def delay(self) -> float:
        return max(MIN_DELAY, self.base_delay / self.speed)

    def _apply(self, commit: Commit, animate: bool) -> None:
        for change in commit.changes:
            if change.status == "D":
                self.tree.remove(change.path, animate=animate)
            else:
                delta = change.insertions - change.deletions
                self.tree.touch(change.path, commit.author, delta, animate=animate)
            self.total_insertions += change.insertions
            self.total_deletions += change.deletions
        self.author_counts[commit.author] += 1

    def advance(self) -> None:
        if self.idx >= len(self.commits):
            self.playing = False
            return
        self._apply(self.commits[self.idx], animate=True)
        self.idx += 1

    def seek(self, target: int) -> None:
        target = max(0, min(target, len(self.commits)))
        self.tree = FileTree()
        self.author_counts = Counter()
        self.total_insertions = 0
        self.total_deletions = 0
        for i in range(target):
            self._apply(self.commits[i], animate=False)
        self.idx = target

    def adjust_speed(self, factor: float) -> None:
        self.speed = max(0.1, min(32.0, self.speed * factor))


def _draw(stdscr, cmap: ColorMap, pb: Playback, repo_name: str) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    if h < 10 or w < 44:
        _safe_addstr(stdscr, 0, 0, "gitlapse: resize terminal to at least 44x10", curses.A_BOLD)
        stdscr.refresh()
        return

    total = len(pb.commits)
    pct = pb.idx / total if total else 0.0
    bar_w = 20
    filled = int(bar_w * pct)
    bar = "#" * filled + "-" * (bar_w - filled)
    title = f" gitlapse — {repo_name} "
    progress = f"[{bar}] {pb.idx}/{total} commits "
    _safe_addstr(stdscr, 0, 0, title, curses.color_pair(UI_PAIR) | curses.A_BOLD)
    _safe_addstr(stdscr, 0, max(0, w - len(progress) - 1), progress, curses.color_pair(UI_PAIR))

    top_authors = pb.author_counts.most_common(3)
    x = 0
    _safe_addstr(stdscr, 1, x, "top: ", curses.A_DIM)
    x = 5
    for name, cnt in top_authors:
        label = f"{name} ({cnt})  "
        if x + len(label) >= w - 1:
            break
        _safe_addstr(stdscr, 1, x, label, cmap.author_attr(name) | curses.A_BOLD)
        x += len(label)

    tree_top, tree_bottom = 3, h - 6
    tree_h = max(1, tree_bottom - tree_top)
    flat = pb.tree.flatten()

    active = [i for i, (_, n) in enumerate(flat) if n.pulse > 0 or n.dying > 0]
    if active:
        center = active[len(active) // 2]
        pb.scroll = max(0, center - tree_h // 2)
    pb.scroll = max(0, min(pb.scroll, max(0, len(flat) - tree_h)))

    for row_i, (depth, node) in enumerate(flat[pb.scroll: pb.scroll + tree_h]):
        y = tree_top + row_i
        indent = "  " * depth
        if node.is_dir:
            label = f"{indent}{node.name}/"
            attr = curses.color_pair(DIR_PAIR)
        else:
            label = f"{indent}{node.name} ({_fmt_size(node.size)})"
            attr = cmap.author_attr(node.author or "")
            if node.dying:
                attr = curses.color_pair(DYING_PAIR) | curses.A_BOLD
            elif node.pulse:
                attr |= curses.A_BOLD | curses.A_REVERSE
        _safe_addstr(stdscr, y, 1, label[: max(0, w - 2)], attr)

    _safe_addstr(stdscr, h - 5, 0, "-" * w, curses.A_DIM)

    if 0 < pb.idx <= len(pb.commits):
        c = pb.commits[pb.idx - 1]
        when = datetime.fromtimestamp(c.timestamp).strftime("%Y-%m-%d %H:%M")
        line1 = f"{c.sha[:7]}  {c.author}  ·  {when}"
        _safe_addstr(stdscr, h - 4, 1, line1[: w - 2], cmap.author_attr(c.author) | curses.A_BOLD)
        _safe_addstr(stdscr, h - 3, 1, c.subject[: w - 2])

    stats = (
        f"+{pb.total_insertions}  -{pb.total_deletions} lines   ·   "
        f"{pb.tree.file_count()} files   ·   {pb.idx}/{total} commits"
    )
    _safe_addstr(stdscr, h - 2, 1, stats[: w - 2], curses.color_pair(UI_PAIR))

    status = "PLAYING" if pb.playing else "PAUSED"
    hint = f"[{status}]  space=pause  +/-=speed({pb.speed:.1f}x)  ←/→=step  r=restart  q=quit"
    _safe_addstr(stdscr, h - 1, 1, hint[: w - 2], curses.A_DIM)

    stdscr.refresh()


def run(
    stdscr,
    commits: list[Commit],
    repo_name: str,
    target_duration: float,
    initial_speed: float = 1.0,
) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(16)

    cmap = ColorMap()
    pb = Playback(commits, target_duration)
    pb.speed = max(0.1, min(32.0, initial_speed))

    last_advance = time.monotonic()
    last_tick = time.monotonic()

    while True:
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1

        if key in (ord("q"), 27):
            return
        elif key == ord(" "):
            pb.playing = not pb.playing
        elif key in (ord("+"), ord("=")):
            pb.adjust_speed(1.25)
        elif key in (ord("-"), ord("_")):
            pb.adjust_speed(0.8)
        elif key == curses.KEY_RIGHT:
            pb.playing = False
            pb.advance()
        elif key == curses.KEY_LEFT:
            pb.playing = False
            pb.seek(max(0, pb.idx - 1))
        elif key == ord("r"):
            pb.seek(0)
            pb.playing = True

        now = time.monotonic()
        if pb.playing and now - last_advance >= pb.delay:
            last_advance = now
            pb.advance()

        if now - last_tick >= TICK_INTERVAL:
            last_tick = now
            pb.tree.tick()

        _draw(stdscr, cmap, pb, repo_name)
        time.sleep(0.01)
