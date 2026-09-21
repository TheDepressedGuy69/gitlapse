"""Deterministic author -> color assignment, with a curses fallback palette."""
from __future__ import annotations

import curses
import zlib

# A hand-picked set of readable 256-color codes (skip near-black/near-white/gray).
PALETTE_256 = [
    39, 45, 51, 214, 208, 197, 205, 141, 105, 76, 82, 226, 220, 111, 159,
    203, 173, 118, 148, 63, 99, 135, 172, 178,
]
PALETTE_8 = [
    curses.COLOR_CYAN, curses.COLOR_YELLOW, curses.COLOR_MAGENTA,
    curses.COLOR_GREEN, curses.COLOR_BLUE, curses.COLOR_RED,
]

PAIR_BASE = 10  # leave 0-9 free for UI chrome pairs
PULSE_PAIR = 1
DYING_PAIR = 2
DIR_PAIR = 3
UI_PAIR = 4
DIM_PAIR = 5


class ColorMap:
    def __init__(self):
        self.has_color = curses.has_colors()
        self.palette = PALETTE_256 if curses.COLORS >= 256 else PALETTE_8
        self._cache: dict[str, int] = {}
        self._setup_pairs()

    def _setup_pairs(self):
        if not self.has_color:
            return
        curses.start_color()
        try:
            curses.use_default_colors()
            bg = -1
        except curses.error:
            bg = curses.COLOR_BLACK

        for i, fg in enumerate(self.palette):
            curses.init_pair(PAIR_BASE + i, fg, bg)

        curses.init_pair(PULSE_PAIR, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(DYING_PAIR, curses.COLOR_RED, bg)
        curses.init_pair(DIR_PAIR, curses.COLOR_BLUE, bg)
        curses.init_pair(UI_PAIR, curses.COLOR_CYAN, bg)
        curses.init_pair(DIM_PAIR, curses.COLOR_WHITE, bg)

    def author_pair(self, author: str) -> int:
        if not self.has_color:
            return 0
        if author not in self._cache:
            idx = zlib.crc32(author.encode("utf-8")) % len(self.palette)
            self._cache[author] = PAIR_BASE + idx
        return self._cache[author]

    def author_attr(self, author: str) -> int:
        return curses.color_pair(self.author_pair(author))
