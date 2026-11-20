"""发行版盲盒：记住短暂出现的目标 Logo，盒子关上后选中它。"""

from __future__ import annotations

import random

import assetslib
from canvas import (
    AMBER, AMBER2, BG, BLUE, BLUE2, DIM, FAINT, GREEN, INK, PANEL, PANEL2,
    PINK, RED, WHITE, Canvas, bar, truncate, width,
)
from village import Outcome

DISTROS = (
    ("Ubuntu", "assets/logo_ubuntu.png", (233, 84, 32)),
    ("Debian", "assets/logo_debian.png", (220, 66, 80)),
    ("Arch Linux", "assets/logo_arch.png", (74, 163, 255)),
    ("Fedora", "assets/logo_fedora.png", (60, 110, 232)),
    ("Linux Mint", "assets/logo_mint.png", (95, 191, 127)),
    ("openSUSE", "assets/logo_suse.png", (115, 186, 70)),
)


class BoxGame:
    ROUNDS = 8
    LIVES = 3
    COLS, ROWS = 4, 3
    PRE = 0.45
    REVEAL = 1.35
    CHOOSE = 4.5
    FEEDBACK = 0.85

    def __init__(self, w: int, h: int, seed: int | None = None) -> None:
        self.w = w
        self.h = h
        self.rng = random.Random(seed)
        self.status = "playing"
        self.score = 0
        self.lives = self.LIVES
        self.combo = 0
        self.max_combo = 0
        self.elapsed = 0.0
        self.round = 0
        self.correct = 0
        self.cursor = 0
        self.phase = "pre"
        self.timer = self.PRE
        self.target = -1
        self.target_box = 0
        self.revealed: set[int] = set()
        self.reveal_set: set[int] = set()
        self.logos: list[int] = [0] * 12
        self.selected: int | None = None
        self.feedback = ""
        self.feedback_color = GREEN
        self._start_round()

    # ---------- 布局 ----------

    @property
    def box_h(self) -> int:
        return 7 if self.h >= 28 else 6

    def box_rect(self, idx: int) -> tuple[int, int, int, int]:
        gap = 2
        bw = max(14, (self.w - 8 - gap * (self.COLS - 1)) // self.COLS)
        total = bw * self.COLS + gap * (self.COLS - 1)
        x0 = max(2, (self.w - total) // 2)
        y0 = 3
        r, c = divmod(idx, self.COLS)
        return (x0 + c * (bw + gap), y0 + r * (self.box_h + 1), bw, self.box_h)

    # ---------- 回合 ----------

    def _start_round(self) -> None:
        choices = [i for i in range(len(DISTROS)) if i != self.target] or list(range(len(DISTROS)))
        self.target = self.rng.choice(choices)
        self.target_box = self.rng.randrange(self.COLS * self.ROWS)
        others = [i for i in range(self.COLS * self.ROWS) if i != self.target_box]
        self.reveal_set = {self.target_box, *self.rng.sample(others, 3)}
        self.revealed = set()
        self.logos = [self.rng.choice([d for d in range(len(DISTROS)) if d != self.target])
                      for _ in range(self.COLS * self.ROWS)]
        self.logos[self.target_box] = self.target
        self.selected = None
        self.phase = "pre"
        self.timer = self.PRE
        self.feedback = ""

    def _resolve(self, idx: int | None) -> None:
        if self.status != "playing" or self.phase != "choose":
            return
        self.selected = idx
        good = idx == self.target_box
        choose_left = max(0.0, self.timer)
        self.phase = "feedback"
        self.timer = self.FEEDBACK
        self.revealed = {self.target_box}
        if good:
            self.correct += 1
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            gained = 150 + self.combo * 50 + int(choose_left * 20)
            self.score += gained
            self.feedback = f"✓ 找到了  +{gained}"
            self.feedback_color = GREEN
        else:
            self.lives -= 1
            self.combo = 0
            self.feedback = "× 不是这个盒子"
            self.feedback_color = RED
            if self.lives <= 0:
                self.status = "lost"

    def click(self, x: int, y: int) -> None:
        if self.phase != "choose":
            return
        for i in range(self.COLS * self.ROWS):
            bx, by, bw, bh = self.box_rect(i)
            if bx <= x < bx + bw and by <= y < by + bh:
                self.cursor = i
                self._resolve(i)
                return

    def move_cursor(self, dx: int, dy: int) -> None:
        if self.status != "playing" or self.phase != "choose":
            return
        r, c = divmod(self.cursor, self.COLS)
        r = (r + dy) % self.ROWS
        c = (c + dx) % self.COLS
        self.cursor = r * self.COLS + c

    def handle_key(self, key: str) -> None:
        if self.status != "playing":
            return
        if key in ("left", "a", "A"):
            self.move_cursor(-1, 0)
        elif key in ("right", "d", "D"):
            self.move_cursor(1, 0)
        elif key in ("up", "w", "W"):
            self.move_cursor(0, -1)
        elif key in ("down", "s", "S"):
            self.move_cursor(0, 1)
        elif key in ("enter", "space") and self.phase == "choose":
            self._resolve(self.cursor)

    def update(self, dt: float) -> None:
        dt = min(0.06, dt)
        if self.status != "playing":
            return
        self.elapsed += dt
        self.timer -= dt
        if self.timer > 0:
            return
        if self.phase == "pre":
            self.phase = "reveal"
            self.timer = self.REVEAL
            self.revealed = set(self.reveal_set)
        elif self.phase == "reveal":
            self.phase = "choose"
            self.timer = self.CHOOSE
            self.revealed = set()
        elif self.phase == "choose":
            self.lives -= 1
            self.combo = 0
            self.phase = "feedback"
            self.timer = self.FEEDBACK
            self.revealed = {self.target_box}
            self.feedback = "× 超时"
            self.feedback_color = RED
            self.selected = None
            if self.lives <= 0:
                self.status = "lost"
        elif self.phase == "feedback":
            self.round += 1
            if self.round >= self.ROUNDS:
                if self.lives > 0:
                    self.status = "won"
            else:
                self._start_round()

    def outcome(self) -> Outcome:
        return Outcome(
            "box", self.status == "won", int(self.score), self.elapsed,
            [
                ("成功轮次", f"{self.correct} / {self.ROUNDS}"),
                ("最大连击", f"x{self.max_combo}"),
                ("剩余生命", f"{max(0, self.lives)} / {self.LIVES}"),
            ],
        )

    # ---------- 渲染 ----------

    def _logo(self, c: Canvas, logo: int, x: int, y: int, cols: int, rows: int) -> None:
        name, path, _ = DISTROS[logo]
        small = assetslib.half(path, cols, rows)
        if small is None:
            c.put(x, y, "缺失", RED, PANEL)
            return
        for yy in range(small.h // 2):
            for xx in range(small.w):
                i = (yy * 2 * small.w + xx) * 3
                j = ((yy * 2 + 1) * small.w + xx) * 3
                top = (small.buf[i], small.buf[i + 1], small.buf[i + 2])
                bot = (small.buf[j], small.buf[j + 1], small.buf[j + 2])
                c.put(x + xx, y + yy, "▀", top, bot)

    def render(self, c: Canvas) -> None:
        w, h = c.w, c.h
        c.fill(0, 0, w, h, " ", INK, BG)
        c.fill(0, 0, w, 2, " ", INK, BG)
        c.put(0, 0, " ZJUT LUG ", BG, (214, 160, 255), bold=True)
        c.put(12, 0, "Linux 新手村", INK, BG, bold=True)
        c.center(0, "发行版盲盒 · 第 3 关", WHITE, BG, bold=True)
        c.right(w - 1, 0, f"轮次 {min(self.round + 1, self.ROUNDS)}/{self.ROUNDS}", (214, 160, 255), BG, bold=True)
        c.put(1, 1, "SCORE", FAINT, BG)
        c.put(7, 1, f"{int(self.score):05d}", WHITE, BG, bold=True)
        hearts = "♥" * max(0, self.lives) + "♡" * (self.LIVES - max(0, self.lives))
        c.put(17, 1, hearts, PINK, BG, bold=True)
        c.put(24, 1, f"COMBO x{self.combo}", AMBER if self.combo else FAINT, BG, bold=True)
        c.right(w - 1, 1, "记住位置", DIM, BG)

        name, _, color = DISTROS[self.target]
        c.put(2, 2, "找出", FAINT, BG)
        c.put(7, 2, name, color, BG, bold=True)
        phase_text = {
            "pre": "准备，盒子马上打开",
            "reveal": "观察 4 个盲盒",
            "choose": "盒子关上了，选一个",
            "feedback": self.feedback or "看看结果",
        }.get(self.phase, "")
        c.put(7 + width(name) + 2, 2, phase_text, DIM, BG)
        if self.phase in ("choose", "reveal"):
            total = self.CHOOSE if self.phase == "choose" else self.REVEAL
            c.right(w - 2, 2, bar(max(0.0, self.timer), total, 12), GREEN if self.timer > total / 2 else RED, BG, bold=True)

        for i in range(self.COLS * self.ROWS):
            bx, by, bw, bh = self.box_rect(i)
            open_ = i in self.revealed
            selected = i == self.selected
            focused = i == self.cursor and self.phase == "choose"
            if self.phase == "feedback" and i == self.target_box:
                border = GREEN
            elif selected:
                border = self.feedback_color
            elif open_:
                border = AMBER
            elif focused:
                border = (214, 160, 255)
            else:
                border = BLUE
            bg = PANEL if open_ else PANEL2
            c.fill(bx, by, bw, bh, " ", INK, bg)
            c.box(bx, by, bw, bh, border, "", border, bg)
            if open_:
                logo = self.logos[i]
                self._logo(c, logo, bx + 2, by + 1, bw - 4, bh - 3)
                lname = truncate(DISTROS[logo][0], bw - 3)
                c.put(bx + max(1, (bw - width(lname)) // 2), by + bh - 2,
                      lname, DISTROS[logo][2], bg, bold=True)
            else:
                c.put(bx + bw // 2, by + bh // 2 - 1, "?", (214, 160, 255) if focused else FAINT, bg, bold=True)
                c.put(bx + max(1, (bw - 5) // 2), by + bh // 2 + 1, "BOX", (60, 76, 106), bg)
            if focused:
                c.put(bx + 1, by + bh - 1, "▸", (214, 160, 255), bg, bold=True)

        c.put(2, h - 1, "方向键选择 · Enter 开盒 · 鼠标点击 · Esc 暂停 · Ctrl-C 退出", FAINT, BG)
