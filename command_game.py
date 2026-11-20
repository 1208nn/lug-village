"""命令行猜词：看中文任务，把命令块拼进终端。"""

from __future__ import annotations

import random

from canvas import (
    AMBER, AMBER2, BG, BLUE, BLUE2, DIM, FAINT, GREEN, INK, PANEL, PANEL2,
    PINK, RED, TEAL, WHITE, Canvas, bar, truncate, width,
)
from village import Outcome

TASKS = (
    ("列出所有文件（含隐藏）", ("ls", "-la")),
    ("回到上一级目录", ("cd", "..")),
    ("显示当前工作目录", ("pwd",)),
    ("创建 demo 目录", ("mkdir", "demo")),
    ("把 a.txt 复制为 b.txt", ("cp", "a.txt", "b.txt")),
    ("删除 note.txt", ("rm", "note.txt")),
    ("搜索 TODO", ("grep", "-r", "TODO", ".")),
    ("查看 README.md", ("cat", "README.md")),
)

DECOYS = (
    "ls", "-l", "cd", "/", "pwd", "mkdir", "tmp", "cp", "mv", "rm",
    "grep", "-n", "TODO", "src", ".", "cat", "less", "README.md",
    "chmod", "+x", "run.sh", "sudo", "apt", "update", "echo", "$HOME",
)


class CommandGame:
    GOAL = 6
    LIVES = 3
    ITEM_TIME = 12.0
    COLS, ROWS = 4, 2

    def __init__(self, w: int, h: int, seed: int | None = None) -> None:
        self.w = w
        self.h = h
        self.rng = random.Random(seed)
        self.tasks = self.rng.sample(list(TASKS), self.GOAL)
        self.index = 0
        self.status = "playing"
        self.score = 0
        self.lives = self.LIVES
        self.combo = 0
        self.max_combo = 0
        self.elapsed = 0.0
        self.item_time = 0.0
        self.cursor = 0
        self.selected: list[int] = []
        self.used: set[int] = set()
        self.tasks_done = 0
        self.phase = "choose"  # choose / feedback
        self.lock = 0.0
        self.pending = ""
        self.feedback = ""
        self.feedback_color = GREEN
        self.tokens: list[str] = []
        self._load_task()

    # ---------- 布局 ----------

    def token_rects(self) -> list[tuple[int, int, int, int]]:
        gap = 2
        tw = max(14, (self.w - 10 - gap * 3) // self.COLS)
        total = tw * self.COLS + gap * (self.COLS - 1)
        x0 = max(2, (self.w - total) // 2)
        y0 = 13 if self.h < 28 else 15
        bh = 3 if self.h < 28 else 4
        out = []
        for i in range(len(self.tokens)):
            r, c = divmod(i, self.COLS)
            out.append((x0 + c * (tw + gap), y0 + r * (bh + 1), tw, bh))
        return out

    # ---------- 任务 ----------

    def _load_task(self) -> None:
        prompt, answer = self.tasks[self.index]
        self.answer = list(answer)
        pool = list(answer)
        decoys = [d for d in DECOYS if d not in answer]
        self.rng.shuffle(decoys)
        pool.extend(decoys[: max(0, 8 - len(pool))])
        self.rng.shuffle(pool)
        self.tokens = pool
        self.selected = []
        self.used = set()
        self.cursor = 0
        self.item_time = 0.0
        self.phase = "choose"
        self.feedback = ""

    @property
    def prompt(self) -> str:
        return self.tasks[self.index][0]

    @property
    def command(self) -> str:
        return " ".join(self.tokens[i] for i in self.selected)

    # ---------- 输入 ----------

    def move_cursor(self, dx: int, dy: int) -> None:
        if self.status != "playing" or self.phase != "choose":
            return
        r, c = divmod(self.cursor, self.COLS)
        r = (r + dy) % self.ROWS
        c = (c + dx) % self.COLS
        i = r * self.COLS + c
        if i < len(self.tokens):
            self.cursor = i

    def add(self, i: int | None = None) -> None:
        if self.status != "playing" or self.phase != "choose":
            return
        if i is None:
            i = self.cursor
        if i < 0 or i >= len(self.tokens) or i in self.used:
            return
        self.selected.append(i)
        self.used.add(i)
        self.cursor = i

    def undo(self) -> None:
        if self.status != "playing" or self.phase != "choose" or not self.selected:
            return
        i = self.selected.pop()
        self.used.discard(i)

    def execute(self) -> None:
        if self.status != "playing" or self.phase != "choose":
            return
        if not self.selected:
            self.phase = "feedback"
            self.lock = 0.5
            self.pending = "same"
            self.feedback = "先拼一条命令"
            self.feedback_color = AMBER
            return
        cmd = [self.tokens[i] for i in self.selected]
        if cmd == self.answer:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            gained = 200 + self.combo * 50 + int((self.ITEM_TIME - self.item_time) * 15)
            self.score += gained
            self.feedback = f"✓ 命令正确  +{gained}"
            self.feedback_color = GREEN
            self.pending = "next"
            self.phase = "feedback"
            self.lock = 0.6
            self.tasks_done += 1
            if self.tasks_done >= self.GOAL:
                self.status = "won"
        else:
            self.lives -= 1
            self.combo = 0
            self.feedback = f"× 命令不对  正确：{' '.join(self.answer)}"
            self.feedback_color = RED
            self.pending = "retry"
            self.phase = "feedback"
            self.lock = 0.9
            if self.lives <= 0:
                self.status = "lost"

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
        elif key in ("space", "enter"):
            if key == "enter":
                self.execute()
            else:
                self.add()
        elif key == "backspace":
            self.undo()
        elif len(key) == 1 and key.isdigit():
            n = int(key) - 1
            if 0 <= n < len(self.tokens):
                self.add(n)

    def click(self, x: int, y: int) -> None:
        for i, (bx, by, bw, bh) in enumerate(self.token_rects()):
            if bx <= x < bx + bw and by <= y < by + bh:
                self.add(i)
                return

    def update(self, dt: float) -> None:
        dt = min(0.06, dt)
        if self.status != "playing":
            return
        self.elapsed += dt
        if self.phase == "feedback":
            self.lock -= dt
            if self.lock <= 0:
                if self.pending == "next":
                    self.index += 1
                    if self.index >= self.GOAL:
                        self.status = "won"
                    else:
                        self._load_task()
                elif self.pending == "retry":
                    self.selected = []
                    self.used = set()
                    self.item_time = 0.0
                    self.phase = "choose"
                    self.feedback = ""
                else:
                    self.phase = "choose"
                    self.feedback = ""
            return
        self.item_time += dt
        if self.item_time >= self.ITEM_TIME:
            self.lives -= 1
            self.combo = 0
            self.feedback = f"× 超时  正确：{' '.join(self.answer)}"
            self.feedback_color = RED
            self.phase = "feedback"
            self.pending = "retry"
            self.lock = 0.9
            if self.lives <= 0:
                self.status = "lost"

    def outcome(self) -> Outcome:
        return Outcome(
            "command", self.status == "won", int(self.score), self.elapsed,
            [
                ("完成任务", f"{self.tasks_done} / {self.GOAL}"),
                ("最大连击", f"x{self.max_combo}"),
                ("剩余生命", f"{max(0, self.lives)} / {self.LIVES}"),
            ],
        )

    # ---------- 渲染 ----------

    def render(self, c: Canvas) -> None:
        w, h = c.w, c.h
        c.fill(0, 0, w, h, " ", INK, BG)
        c.fill(0, 0, w, 2, " ", INK, BG)
        c.put(0, 0, " ZJUT LUG ", BG, AMBER, bold=True)
        c.put(12, 0, "Linux 新手村", INK, BG, bold=True)
        c.center(0, "命令行猜词 · 第 2 关", WHITE, BG, bold=True)
        c.right(w - 1, 0, f"任务 {min(self.index + 1, self.GOAL)}/{self.GOAL}", AMBER2, BG, bold=True)
        c.put(1, 1, "SCORE", FAINT, BG)
        c.put(7, 1, f"{int(self.score):05d}", WHITE, BG, bold=True)
        hearts = "♥" * max(0, self.lives) + "♡" * (self.LIVES - max(0, self.lives))
        c.put(17, 1, hearts, PINK, BG, bold=True)
        c.put(24, 1, f"COMBO x{self.combo}", AMBER if self.combo else FAINT, BG, bold=True)
        c.right(w - 1, 1, "拼出命令后 Enter", DIM, BG)

        # 任务面板
        c.box(2, 2, w - 4, 5, AMBER, "TASK", AMBER2, PANEL, fill_inner=True)
        c.put(4, 3, f"0{self.index + 1}", AMBER, PANEL, bold=True)
        c.put(7, 3, self.prompt, INK, PANEL, bold=True)
        left = max(0.0, self.ITEM_TIME - self.item_time)
        col = GREEN if left > 6 else AMBER if left > 3 else RED
        c.put(4, 5, bar(left, self.ITEM_TIME, max(10, w - 24)), col, PANEL, bold=True)
        c.right(w - 3, 5, f"{left:0.1f}s", col, PANEL, bold=True)

        # 终端
        ty = 7
        c.box(2, ty, w - 4, 5, TEAL, "TERMINAL", TEAL, PANEL, fill_inner=True)
        c.put(4, ty + 1, "lug@village:~$ ", GREEN, PANEL, bold=True)
        cmd = self.command
        c.put(19, ty + 1, truncate(cmd, w - 24), AMBER2, PANEL, bold=True)
        if self.phase == "choose" and int(self.elapsed * 6) % 2 == 0:
            c.put(19 + width(cmd), ty + 1, "█", AMBER, PANEL)
        if self.phase == "feedback" and self.feedback:
            c.put(4, ty + 3, truncate(self.feedback, w - 8), self.feedback_color, PANEL, bold=True)
        else:
            c.put(4, ty + 3, "方向键选词块 · 空格加入 · Enter 执行", FAINT, PANEL)

        # 词块
        for i, (bx, by, bw, bh) in enumerate(self.token_rects()):
            used = i in self.used
            focused = i == self.cursor and self.phase == "choose"
            bg = PANEL2 if not focused else AMBER
            fg = BG if focused else (FAINT if used else INK)
            border = AMBER if focused else (FAINT if used else BLUE)
            c.fill(bx, by, bw, bh, " ", fg, bg)
            c.box(bx, by, bw, bh, border, "", border, bg)
            label = truncate(self.tokens[i], bw - 4)
            c.put(bx + max(2, (bw - width(label)) // 2), by + 1, label, fg, bg, bold=focused)
            c.put(bx + 2, by, f" {i + 1} ", FAINT if not focused else BG, bg)

        c.put(2, h - 2, "Backspace 删除 · Enter 执行", FAINT, BG)
        c.put(34, h - 2, "Esc 暂停", FAINT, BG)
        c.right(w - 2, h - 2, "Ctrl-C 退出", FAINT, BG)
        c.hline(0, h - 1, w, "─", FAINT, BG)
