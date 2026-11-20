"""系统识别：在倒计时内把桌面画面分进 Linux / Windows。"""

from __future__ import annotations

import random

import assetslib
from canvas import (
    AMBER, AMBER2, BG, BLUE, BLUE2, DIM, FAINT, GREEN, INK, PANEL, PANEL2,
    PINK, RED, WHITE, Canvas, bar, truncate, width,
)
from village import Outcome

DESKTOPS = (
    ("assets/os_win11.png", "Windows"),
    ("assets/os_win10.png", "Windows"),
    ("assets/os_ubuntu.png", "Linux"),
    ("assets/os_kde.png", "Linux"),
    ("assets/os_mint.png", "Linux"),
    ("assets/os_fedora.png", "Linux"),
)
WINDOWS = tuple(d for d in DESKTOPS if d[1] == "Windows")
LINUX = tuple(d for d in DESKTOPS if d[1] == "Linux")


class SortGame:
    ROUNDS = 10
    LIVES = 3
    ITEM_TIME = 6.0

    def __init__(self, w: int, h: int, seed: int | None = None) -> None:
        self.w = w
        self.h = h
        self.rng = random.Random(seed)
        wins = [self.rng.choice(WINDOWS) for _ in range(5)]
        lins = [self.rng.choice(LINUX) for _ in range(5)]
        self.deck = wins + lins
        self.rng.shuffle(self.deck)
        self.index = 0
        self.resolved = 0
        self.status = "playing"
        self.score = 0
        self.lives = self.LIVES
        self.combo = 0
        self.max_combo = 0
        self.correct = 0
        self.elapsed = 0.0
        self.item_time = 0.0
        self.phase = "choose"  # choose / feedback
        self.lock = 0.0
        self.feedback = ""
        self.feedback_color = GREEN

    @property
    def current(self) -> tuple[str, str]:
        return self.deck[min(self.index, len(self.deck) - 1)]

    # ---------- 布局 ----------

    def layout(self) -> tuple[int, int, int, int]:
        return 2, 2, self.w - 30, self.h - 8

    def bins(self) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
        bw = (self.w - 6) // 2
        y = self.h - 5
        return (2, y, bw, 3), (2 + bw + 2, y, bw, 3)

    # ---------- 输入 ----------

    def choose(self, label: str) -> None:
        if self.status != "playing" or self.phase != "choose":
            return
        want = self.current[1]
        self.resolved += 1
        self.phase = "feedback"
        self.lock = 0.55
        if label == want:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.correct += 1
            gained = 100 + self.combo * 30 + int((self.ITEM_TIME - self.item_time) * 12)
            self.score += gained
            self.feedback = f"✓ {label}  +{gained}"
            self.feedback_color = GREEN
        else:
            self.lives -= 1
            self.combo = 0
            self.feedback = f"× 这是 {want}"
            self.feedback_color = RED
            if self.lives <= 0:
                self.status = "lost"
        if self.status == "playing" and self.resolved >= self.ROUNDS:
            self.status = "won"

    def handle_key(self, key: str) -> None:
        if key in ("left", "a", "A", "1"):
            self.choose("Linux")
        elif key in ("right", "d", "D", "2"):
            self.choose("Windows")

    def click(self, x: int, y: int) -> None:
        left, right = self.bins()
        for rect, label in ((left, "Linux"), (right, "Windows")):
            bx, by, bw, bh = rect
            if bx <= x < bx + bw and by <= y < by + bh:
                self.choose(label)
                return

    def _timeout(self) -> None:
        if self.phase != "choose" or self.status != "playing":
            return
        self.resolved += 1
        self.lives -= 1
        self.combo = 0
        self.phase = "feedback"
        self.lock = 0.6
        self.feedback = f"× 超时，这是 {self.current[1]}"
        self.feedback_color = RED
        if self.lives <= 0:
            self.status = "lost"
        elif self.resolved >= self.ROUNDS:
            self.status = "won"

    def _next(self) -> None:
        self.index += 1
        self.phase = "choose"
        self.item_time = 0.0
        self.feedback = ""
        if self.index >= self.ROUNDS and self.status == "playing":
            self.status = "won"

    def update(self, dt: float) -> None:
        dt = min(0.06, dt)
        if self.status != "playing":
            return
        self.elapsed += dt
        if self.phase == "feedback":
            self.lock -= dt
            if self.lock <= 0:
                self._next()
            return
        self.item_time += dt
        if self.item_time >= self.ITEM_TIME:
            self._timeout()

    def outcome(self) -> Outcome:
        return Outcome(
            "sort", self.status == "won", int(self.score), self.elapsed,
            [
                ("正确分拣", f"{self.correct} / {self.ROUNDS}"),
                ("最大连击", f"x{self.max_combo}"),
                ("剩余生命", f"{max(0, self.lives)} / {self.LIVES}"),
            ],
        )

    # ---------- 渲染 ----------

    def _image(self, c: Canvas, x: int, y: int, iw: int, ih: int) -> None:
        c.fill(x, y, iw, ih, " ", INK, PANEL2)
        small = assetslib.half(self.current[0], iw, ih)
        if small is None:
            c.put(x + 2, y + 2, "桌面素材缺失", RED, PANEL2, bold=True)
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
        # HUD
        c.fill(0, 0, w, 2, " ", INK, BG)
        c.put(0, 0, " ZJUT LUG ", BG, BLUE, bold=True)
        c.put(12, 0, "Linux 新手村", INK, BG, bold=True)
        c.center(0, "系统识别 · 第 1 关", WHITE, BG, bold=True)
        c.right(w - 1, 0, f"桌面 {self.resolved}/{self.ROUNDS}", BLUE2, BG, bold=True)
        c.put(1, 1, "SCORE", FAINT, BG)
        c.put(7, 1, f"{int(self.score):05d}", WHITE, BG, bold=True)
        hearts = "♥" * max(0, self.lives) + "♡" * (self.LIVES - max(0, self.lives))
        c.put(17, 1, hearts, PINK, BG, bold=True)
        c.put(24, 1, f"COMBO x{self.combo}", AMBER if self.combo else FAINT, BG, bold=True)
        c.right(w - 1, 1, "哪边？", DIM, BG)

        px, py, pw, ph = self.layout()
        c.box(px, py, pw, ph, BLUE, "DESKTOP SCANNER", BLUE2, BG, fill_inner=True)
        iw, ih = pw - 4, ph - 4
        self._image(c, px + 2, py + 2, iw, ih)
        if self.phase == "choose":
            scan = py + 2 + int(self.elapsed * 9) % max(1, ih)
            c.hline(px + 2, scan, iw, "·", (54, 132, 190), PANEL2)
        elif self.feedback:
            fw = min(iw - 4, width(self.feedback) + 4)
            fx = px + 2 + (iw - fw) // 2
            fy = py + 2 + ih // 2 - 1
            c.fill(fx, fy, fw, 3, " ", INK, BG)
            c.box(fx, fy, fw, 3, self.feedback_color, "", self.feedback_color, BG)
            c.put(fx + max(1, (fw - width(self.feedback)) // 2), fy + 1,
                  self.feedback, self.feedback_color, BG, bold=True)

        # 右侧扫描信息
        rx = px + pw + 2
        rw = w - rx - 2
        c.box(rx, py, rw, ph, BLUE, "SCAN", BLUE2, BG, fill_inner=True)
        c.put(rx + 2, py + 2, "这是哪个系统？", AMBER2, PANEL, bold=True)
        c.put(rx + 2, py + 4, "看桌面特征：", FAINT, PANEL)
        c.put(rx + 2, py + 5, "任务栏 / 窗口 /", DIM, PANEL)
        c.put(rx + 2, py + 6, "默认风格", DIM, PANEL)
        left = max(0.0, self.ITEM_TIME - self.item_time)
        col = GREEN if left > 3 else AMBER if left > 1.5 else RED
        c.put(rx + 2, py + 8, "TIME", FAINT, PANEL)
        c.put(rx + 2, py + 9, bar(left, self.ITEM_TIME, max(8, rw - 4)), col, PANEL, bold=True)
        c.put(rx + 2, py + 10, f"{left:0.1f}s", col, PANEL, bold=True)
        c.put(rx + 2, py + 12, f"正确 {self.correct}", GREEN, PANEL)
        c.put(rx + 2, py + 13, f"剩余 {max(0, self.lives)} 命", PINK if self.lives > 1 else RED, PANEL)

        bl, br = self.bins()
        for rect, label, colr in ((bl, "←  Linux", BLUE), (br, "Windows  →", AMBER)):
            bx, by, bw, bh = rect
            focused = self.phase == "choose"
            c.fill(bx, by, bw, bh, " ", BG if focused else PANEL2, colr if focused else PANEL2)
            c.put(bx + max(1, (bw - width(label)) // 2), by + 1, label,
                  BG if focused else DIM, colr if focused else PANEL2, bold=focused)
            c.put(bx + 1, by + 2, "A / ←" if label.startswith("←") else "D / →", FAINT,
                  colr if focused else PANEL2)

        c.put(2, h - 2, "把桌面分进正确的系统", FAINT, BG)
        c.put(28, h - 2, "Esc 暂停", FAINT, BG)
        c.right(w - 2, h - 2, "Ctrl-C 退出", FAINT, BG)
        c.hline(0, h - 1, w, "─", FAINT, BG)
