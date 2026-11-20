"""真彩画布与帧。图片区域会被跳过，交给终端图片协议。"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

import gfx

BG = (9, 12, 22)
PANEL = (16, 22, 38)
PANEL2 = (24, 32, 54)
INK = (235, 239, 247)
DIM = (138, 150, 174)
FAINT = (72, 86, 112)
BLUE = (84, 156, 255)
BLUE2 = (138, 196, 255)
AMBER = (255, 199, 92)
AMBER2 = (255, 224, 150)
GREEN = (112, 232, 164)
RED = (255, 108, 118)
PINK = (255, 142, 186)
PURPLE = (174, 142, 255)
TEAL = (82, 226, 208)
WHITE = (250, 250, 246)


def wcw(ch: str) -> int:
    if not ch:
        return 0
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def width(s: str) -> int:
    return sum(wcw(ch) for ch in s)


def truncate(s: str, maxw: int, tail: str = "…") -> str:
    if maxw <= 0:
        return ""
    if width(s) <= maxw:
        return s
    out = []
    used = 0
    limit = max(0, maxw - width(tail))
    for ch in s:
        w = wcw(ch)
        if used + w > limit:
            break
        out.append(ch)
        used += w
    return "".join(out) + tail


def bar(value: float, total: float, n: int, full="█", empty="░") -> str:
    f = int(round(max(0.0, min(1.0, value / max(1e-9, total))) * n))
    return full * f + empty * (n - f)


class Canvas:
    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        self.rows = [[[" ", INK, BG, False] for _ in range(w)] for _ in range(h)]

    def put(self, x: int, y: int, s: str, fg=INK, bg=None, bold: bool = False) -> None:
        if y < 0 or y >= self.h:
            return
        for ch in s:
            w = wcw(ch)
            if w == 0:
                continue
            if x >= self.w:
                break
            if x < 0:
                x += w
                continue
            if x + w > self.w:
                break
            cell = self.rows[y][x]
            cbg = cell[2] if bg is None else bg
            self.rows[y][x] = [ch, fg, cbg, bold]
            for k in range(1, w):
                self.rows[y][x + k] = ["", fg, cbg, bold]
            x += w

    def right(self, x_right: int, y: int, s: str, fg=INK, bg=None, bold: bool = False) -> None:
        self.put(x_right - width(s), y, s, fg, bg, bold)

    def center(self, y: int, s: str, fg=INK, bg=None, bold: bool = False) -> None:
        self.put(max(0, (self.w - width(s)) // 2), y, s, fg, bg, bold)

    def fill(self, x: int, y: int, w: int, h: int, ch: str = " ", fg=None, bg=PANEL) -> None:
        for yy in range(max(0, y), min(self.h, y + h)):
            for xx in range(max(0, x), min(self.w, x + w)):
                self.rows[yy][xx] = [ch, fg if fg is not None else INK, bg, False]

    def hline(self, x: int, y: int, w: int, ch: str = "─", fg=FAINT, bg=None) -> None:
        self.put(x, y, ch * max(0, w), fg, bg)

    def vline(self, x: int, y: int, h: int, ch: str = "│", fg=FAINT, bg=None) -> None:
        for yy in range(max(0, y), min(self.h, y + h)):
            self.put(x, yy, ch, fg, bg)

    def box(self, x: int, y: int, w: int, h: int, fg=FAINT, title: str = "",
            title_fg=DIM, bg=None, fill_inner: bool = False) -> None:
        if w <= 0 or h <= 0:
            return
        if fill_inner:
            self.fill(x, y, w, h, " ", None, bg or BG)
        self.put(x, y, "╭", fg)
        self.put(x + w - 1, y, "╮", fg)
        self.put(x, y + h - 1, "╰", fg)
        self.put(x + w - 1, y + h - 1, "╯", fg)
        for i in range(1, w - 1):
            self.put(x + i, y, "─", fg)
            self.put(x + i, y + h - 1, "─", fg)
        for j in range(1, h - 1):
            self.put(x, y + j, "│", fg)
            self.put(x + w - 1, y + j, "│", fg)
        if title:
            t = f" {title} "
            tx = x + 2
            self.put(tx, y, t, title_fg, bg or BG)
            for i in range(width(t)):
                if 0 <= y < self.h and 0 <= tx + i < self.w and tx + i < x + w - 1:
                    self.rows[y][tx + i][2] = bg or BG

    def _style(self, fg, bg, bold) -> str:
        parts = [f"38;2;{fg[0]};{fg[1]};{fg[2]}", f"48;2;{bg[0]};{bg[1]};{bg[2]}"]
        if bold:
            parts.append("1")
        return "\x1b[" + ";".join(parts) + "m"

    def _emit(self, out: list[str], y: int, x0: int, x1: int) -> None:
        style = None
        x = x0
        row = self.rows[y]
        while x < x1:
            ch, fg, bg, bold = row[x]
            if ch == "":
                x += 1
                continue
            w = wcw(ch)
            if x + w > x1:
                break
            st = (fg, bg, bold)
            if st != style:
                out.append(self._style(fg, bg, bold))
                style = st
            out.append(ch)
            x += w

    def render(self, skip: tuple[int, int, int, int] | None = None) -> str:
        out: list[str] = []
        for y in range(self.h):
            out.append(f"\x1b[{y + 1};1H")
            skipped = False
            if skip and skip[1] <= y < skip[1] + skip[3]:
                sx, sy, sw, sh = skip
                self._emit(out, y, 0, sx)
                out.append("\x1b[0m")
                out.append(f"\x1b[{y + 1};{sx + sw + 1}H")
                self._emit(out, y, sx + sw, self.w)
                skipped = True
            else:
                self._emit(out, y, 0, self.w)
            out.append("\x1b[0m")
            if not skipped:
                out.append("\x1b[K")
        return "".join(out)


@dataclass
class Frame:
    text: str
    png: bytes | None = None
    rect: tuple[int, int, int, int] | None = None
    art_key: tuple | None = None
    img: gfx.Img | None = None
