"""新手村共用界面：标题、关卡介绍、结果、暂停、毕业。"""

from __future__ import annotations

from dataclasses import dataclass

import assetslib
import gfx
from canvas import (
    AMBER, AMBER2, BG, BLUE, BLUE2, DIM, FAINT, GREEN, INK, PANEL, PANEL2,
    PINK, PURPLE, RED, TEAL, WHITE, Canvas, Frame, truncate, width,
)
from village import LEVELS, LevelDef, Outcome, Run

MIN_W, MIN_H = 80, 24

LINUX_ART = (
    "██╗     ██╗███╗   ██╗██╗   ██╗██╗  ██╗",
    "██║     ██║████╗  ██║██║   ██║╚██╗██╔╝",
    "██║     ██║██╔██╗ ██║██║   ██║ ╚███╔╝ ",
    "██║     ██║██║╚██╗██║██║   ██║ ██╔██╗ ",
    "███████╗██║██║ ╚████║╚██████╔╝██╔╝ ██╗",
    "╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝",
)


def wrap(s: str, w: int) -> list[str]:
    if w <= 0:
        return [""]
    out: list[str] = []
    line = ""
    used = 0
    for ch in s:
        cw = width(ch)
        if used + cw > w:
            out.append(line)
            line = ""
            used = 0
        line += ch
        used += cw
    out.append(line)
    return out


@dataclass
class Button:
    x: int
    y: int
    w: int
    h: int
    label: str
    action: str


class Menu:
    def __init__(self) -> None:
        self.buttons: list[Button] = []
        self.focus = 0
        self.accent = AMBER

    def row(self, c: Canvas, items: list[tuple[str, str]], y: int,
            height: int = 3, gap: int = 2, x: int | None = None,
            accent=AMBER) -> None:
        self.accent = accent
        total = sum(width(label) + 8 for label, _ in items) + gap * (len(items) - 1)
        if x is None:
            x = max(1, (c.w - total) // 2)
        self.buttons = []
        for label, action in items:
            bw = width(label) + 8
            self.buttons.append(Button(x, y, bw, height, label, action))
            x += bw + gap

    def col(self, c: Canvas, items: list[tuple[str, str]], y: int,
            width_: int = 30, height: int = 3, gap: int = 1,
            x: int | None = None, accent=AMBER) -> None:
        self.accent = accent
        if x is None:
            x = max(1, (c.w - width_) // 2)
        self.buttons = []
        for label, action in items:
            self.buttons.append(Button(x, y, width_, height, label, action))
            y += height + gap

    def draw(self, c: Canvas) -> None:
        for i, b in enumerate(self.buttons):
            focused = i == self.focus
            bg = self.accent if focused else PANEL2
            fg = BG if focused else INK
            c.fill(b.x, b.y, b.w, b.h, " ", fg, bg)
            tx = b.x + max(1, (b.w - width(b.label)) // 2)
            ty = b.y + max(0, (b.h - 1) // 2)
            c.put(tx, ty, b.label, fg, bg, bold=focused)
            if focused:
                c.put(b.x + 1, ty, "›", fg, bg, bold=True)

    def move(self, delta: int) -> None:
        if self.buttons:
            self.focus = (self.focus + delta) % len(self.buttons)

    def selected(self) -> str | None:
        if not self.buttons:
            return None
        return self.buttons[self.focus].action

    def hit(self, x: int, y: int) -> str | None:
        for b in self.buttons:
            if b.x <= x < b.x + b.w and b.y <= y < b.y + b.h:
                return b.action
        return None

    def hover_focus(self, x: int, y: int) -> None:
        for i, b in enumerate(self.buttons):
            if b.x <= x < b.x + b.w and b.y <= y < b.y + b.h:
                self.focus = i


def header(c: Canvas, section: str, right: str = "", accent=AMBER) -> None:
    c.fill(0, 0, c.w, 2, " ", INK, BG)
    c.put(0, 0, " ZJUT LUG ", BG, accent, bold=True)
    c.put(12, 0, "Linux 新手村", INK, BG, bold=True)
    c.center(0, section, WHITE, BG, bold=True)
    if right:
        c.right(c.w - 1, 0, right, DIM, BG, bold=True)
    c.hline(0, 1, c.w, "─", FAINT, BG)


def footer(c: Canvas, left: str, right: str = "") -> None:
    c.hline(0, c.h - 1, c.w, "─", FAINT, BG)
    c.put(1, c.h - 1, left, FAINT, BG)
    if right:
        c.right(c.w - 1, c.h - 1, right, FAINT, BG)


def panel(c: Canvas, x: int, y: int, w: int, h: int, title: str = "",
          accent=BLUE, bg=PANEL) -> None:
    c.box(x, y, w, h, accent, title, accent, bg, fill_inner=True)


def stars(c: Canvas, now: float, strong: bool = False) -> None:
    for i in range(52):
        x = (i * 47 + int(now * (0 if i % 3 else 9))) % max(1, c.w)
        y = 2 + (i * 19 + i * i * 3) % max(1, c.h - 4)
        ch = "✦" if i % 9 == 0 else "·"
        c.put(x, y, ch, (50, 82, 140) if not strong else (86, 136, 206), BG)


def level_icon(c: Canvas, level: LevelDef, x: int, y: int, now: float) -> None:
    if level.key == "sort":
        c.put(x, y, "╭──────╮  ╭──────╮", BLUE, PANEL)
        c.put(x, y + 1, "│ ███  │  │ ███  │", BLUE2, PANEL, bold=True)
        c.put(x, y + 2, "│ ███  │  │ ███  │", BLUE2, PANEL, bold=True)
        c.put(x, y + 3, "╰──────╯  ╰──────╯", BLUE, PANEL)
        c.put(x + 1, y + 5, "Linux", BLUE2, PANEL, bold=True)
        c.put(x + 12, y + 5, "Windows", AMBER2, PANEL, bold=True)
    elif level.key == "command":
        c.put(x, y, "lug@village:~$ ", GREEN, PANEL, bold=True)
        c.put(x + 15, y, "ls -la", AMBER2, PANEL, bold=True)
        if int(now * 3) % 2 == 0:
            c.put(x + 21, y, "█", AMBER, PANEL)
        c.put(x, y + 2, "[ls] [-la] [cd] [pwd]", DIM, PANEL)
        c.put(x, y + 3, "[mkdir] [demo] [cp] [rm]", DIM, PANEL)
        c.put(x, y + 5, "拼出命令", FAINT, PANEL)
    else:
        c.put(x, y, "╭─────╮  ╭─────╮", AMBER, PANEL)
        c.put(x, y + 1, "│ ? ? │  │ ? ? │", AMBER2, PANEL, bold=True)
        c.put(x, y + 2, "╰─────╯  ╰─────╯", AMBER, PANEL)
        c.put(x, y + 4, "观察 · 记住 · 选中", DIM, PANEL)


def _tux(c: Canvas, protocol: str, w: int, h: int) -> tuple[tuple | None, bytes | None, gfx.Img | None]:
    tw, th = (24, 12) if w >= 96 else (20, 10)
    x = w - tw - 3
    y = max(2, (h - th) // 2 - 4)
    c.box(x - 1, y - 1, tw + 2, th + 2, BLUE, "TUX", BLUE2, BG)
    asset = assetslib.load("assets/tux.png")
    if asset is None:
        c.center(y + th // 2, "素材缺失", RED, PANEL2, bold=True)
        return None, None, None
    if protocol == "half":
        small = assetslib.half("assets/tux.png", tw, th)
        if small:
            for yy in range(small.h // 2):
                for xx in range(small.w):
                    i = (yy * 2 * small.w + xx) * 3
                    j = ((yy * 2 + 1) * small.w + xx) * 3
                    top = (small.buf[i], small.buf[i + 1], small.buf[i + 2])
                    bot = (small.buf[j], small.buf[j + 1], small.buf[j + 2])
                    c.put(x + xx, y + yy, "▀", top, bot)
        return None, None, None
    return (x, y, tw, th), asset.png, asset.img


def render_title(c: Canvas, menu: Menu, now: float, protocol: str) -> Frame:
    c.fill(0, 0, c.w, c.h, " ", INK, BG)
    stars(c, now, True)
    header(c, "开源 · 学习 · 分享 · 实践", "THREE GAMES", AMBER)
    c.put(2, 2, "OPEN SOURCE / LINUX / ZJUT", FAINT, BG)

    rect, png, img = _tux(c, protocol, c.w, c.h)
    x = 5
    top = 4 if c.h >= 28 else 3
    for i, line in enumerate(LINUX_ART):
        c.put(x, top + i, line, BLUE2 if i < 3 else BLUE, BG, bold=True)
    c.put(x + 1, top + 7, "新 手 村", AMBER, BG, bold=True)
    c.put(x + 1, top + 9, "三个小游戏 · 一次毕业 · 直接开玩", INK, BG)
    c.put(x + 1, top + 10, " / ".join(lv.name for lv in LEVELS), DIM, BG)

    chip_y = max(top + 11, c.h - 10)
    chip_w = 22 if c.w < 96 else 26
    gap = 2
    total = chip_w * 3 + gap * 2
    cx = (c.w - total) // 2
    for i, lv in enumerate(LEVELS):
        px = cx + i * (chip_w + gap)
        panel(c, px, chip_y, chip_w, 4, "", lv.accent, PANEL)
        c.put(px + 2, chip_y + 1, f"{i + 1}", lv.accent, PANEL, bold=True)
        c.put(px + 4, chip_y + 1, lv.name, INK, PANEL, bold=True)
        c.put(px + 2, chip_y + 2, truncate(lv.subtitle, chip_w - 4), DIM, PANEL)

    by = c.h - 6
    menu.row(c, (("开始闯关", "start"), ("操作说明", "about"), ("退出", "quit")),
             by, 3, 2, accent=AMBER)
    menu.draw(c)
    c.center(c.h - 3, "Tab / ←→ 选择 · Enter 确认 · 鼠标可点",
             AMBER2 if int(now * 2) % 2 == 0 else AMBER, BG)
    footer(c, "ZJUT LUG · Linux 新手村", "3 mini games")
    key = ("title", c.w, c.h, protocol)
    return Frame(c.render(rect), png, rect, key, img)


def render_about(c: Canvas, menu: Menu, now: float) -> Frame:
    c.fill(0, 0, c.w, c.h, " ", INK, BG)
    stars(c, now)
    header(c, "操作说明", "NO LOGIN", AMBER)
    pw = min(72, c.w - 8)
    px = (c.w - pw) // 2
    ph = min(14, c.h - 10)
    py = max(4, (c.h - ph - 3) // 2)
    panel(c, px, py, pw, ph, "怎么玩", AMBER, PANEL)
    lines = [
        ("三个小游戏", AMBER2, True),
        ("1. 系统识别   看桌面，分进 Linux / Windows。", INK, False),
        ("2. 命令行猜词 看任务，把命令块拼出来。", INK, False),
        ("3. 发行版盲盒 记住 Logo，选中对应的盲盒。", INK, False),
        ("", DIM, False),
        ("操作", AMBER2, True),
        ("← / → 分拣 · 方向键选词块 · 鼠标点击", DIM, False),
        ("空格加入 · Enter 执行/开盒 · Esc 暂停", DIM, False),
        ("", DIM, False),
        ("不收集身份、没有数据库、不联网。成绩只留在这一局屏幕上。", FAINT, False),
    ]
    y = py + max(2, (ph - len(lines)) // 2)
    for text, color, bold in lines:
        if text:
            c.put(px + 3, y, truncate(text, pw - 6), color, PANEL, bold=bold)
        y += 1
    menu.row(c, (("返回", "back"),), c.h - 6, 3, 2, accent=AMBER)
    menu.draw(c)
    footer(c, "Esc 返回 · Ctrl-C 退出", "")
    return Frame(c.render())


def render_intro(c: Canvas, run: Run, menu: Menu, now: float) -> Frame:
    lv = run.level
    c.fill(0, 0, c.w, c.h, " ", INK, BG)
    stars(c, now, True)
    header(c, f"第 {run.index + 1} / 3 关", lv.name, lv.accent)
    pw = min(70, c.w - 8)
    px = (c.w - pw) // 2
    py = 4
    panel(c, px, py, pw, c.h - 11, lv.name, lv.accent, PANEL)
    c.put(px + 3, py + 2, f"0{run.index + 1}", lv.accent, PANEL, bold=True)
    c.put(px + 7, py + 2, lv.subtitle, INK, PANEL, bold=True)
    c.put(px + 3, py + 4, "目标", FAINT, PANEL)
    yy = py + 5
    for line in wrap(lv.goal, pw - 8):
        c.put(px + 3, yy, line, INK, PANEL)
        yy += 1
    c.put(px + 3, yy + 1, "操作", FAINT, PANEL)
    for line in wrap(lv.controls, pw - 8):
        c.put(px + 3, yy + 2, line, TEAL, PANEL)
        yy += 1
    if c.h >= 30:
        level_icon(c, lv, px + 4, py + 12, now)

    menu.row(c, (("开始", "start"), ("返回标题", "title")), c.h - 6, 3, 2, accent=lv.accent)
    menu.draw(c)
    footer(c, "Enter 开始 · P 暂停 · Q 退出", "ZJUT LUG")
    return Frame(c.render())


def render_result(c: Canvas, run: Run, outcome: Outcome, menu: Menu, now: float) -> Frame:
    lv = run.level
    c.fill(0, 0, c.w, c.h, " ", INK, BG)
    stars(c, now, True)
    header(c, f"第 {run.index + 1} / 3 关 · {lv.name}",
           "通关" if outcome.won else "失败", GREEN if outcome.won else RED)
    pw = min(68, c.w - 8)
    px = (c.w - pw) // 2
    ph = 14
    py = 4 if c.h < 28 else max(4, (c.h - ph) // 2 - 1)
    panel(c, px, py, pw, ph, lv.name, lv.accent, PANEL)
    stamp = "✓" if outcome.won else "×"
    c.put(px + 4, py + 2, stamp, GREEN if outcome.won else RED, PANEL, bold=True)
    c.put(px + 7, py + 2, "本关通过" if outcome.won else "本关失败", 
          GREEN if outcome.won else RED, PANEL, bold=True)
    c.put(px + 7, py + 3, f"得分 {outcome.score:04d}   ·   用时 {outcome.seconds:0.1f}s", INK, PANEL)
    yy = py + 5
    for label, value in outcome.stats:
        c.put(px + 4, yy, label, FAINT, PANEL)
        c.put(px + 18, yy, value, INK, PANEL, bold=True)
        yy += 1
    c.put(px + 4, py + 10, "下一关" if run.index < 2 else "毕业", AMBER2, PANEL, bold=True)
    c.put(px + 12, py + 10,
          "继续往前，别让企鹅等太久。" if run.index < 2 else "三关都走完了，去看看毕业画面。",
          DIM, PANEL)

    labels = [("下一关" if run.index < 2 else "查看毕业", "next"),
              ("重玩本关", "retry"), ("回标题", "title")]
    menu.row(c, labels, c.h - 6, 3, 2, accent=lv.accent)
    menu.draw(c)
    footer(c, "Tab / ←→ 选择 · Enter 确认 · 鼠标可点", "ZJUT LUG")
    return Frame(c.render())


def render_final(c: Canvas, run: Run, menu: Menu, now: float, protocol: str) -> Frame:
    c.fill(0, 0, c.w, c.h, " ", INK, BG)
    stars(c, now, True)
    header(c, "★ 新手村毕业 ★", "SESSION REPORT", AMBER)
    if c.w >= 96:
        rect, png, img = _tux(c, protocol, c.w, c.h)
        pw = min(64, c.w - 30)
    else:
        rect = png = img = None
        pw = c.w - 8
    px = 4
    py = 4
    panel(c, px, py, pw, c.h - 11, "毕业证书", AMBER, PANEL)
    c.put(px + 3, py + 2, "Linux 新手村", AMBER2, PANEL, bold=True)
    c.put(px + 3, py + 3, "三星毕业" if run.all_won else "完成挑战", 
          GREEN if run.all_won else AMBER, PANEL, bold=True)
    yy = py + 5
    for lv in LEVELS:
        o = run.outcomes.get(lv.key)
        mark = "✓" if o and o.won else "·"
        color = GREEN if o and o.won else FAINT
        c.put(px + 3, yy, mark, color, PANEL, bold=True)
        c.put(px + 5, yy, lv.name, INK, PANEL)
        c.put(px + 17, yy, f"{o.score:04d}" if o else "----", AMBER2 if o and o.won else DIM, PANEL)
        c.put(px + 24, yy, f"{o.seconds:0.1f}s" if o else "", DIM, PANEL)
        yy += 1
    c.put(px + 3, yy + 1, "总分", FAINT, PANEL)
    c.put(px + 9, yy + 1, f"{run.total_score:05d}", WHITE, PANEL, bold=True)
    c.put(px + 20, yy + 1, "总用时", FAINT, PANEL)
    c.put(px + 28, yy + 1, f"{run.elapsed:0.0f}s", INK, PANEL)
    msg = "向工作人员出示此画面" if run.all_won else "再玩一次，把三个章都点亮"
    c.put(px + 3, py + (c.h - 11) - 3, msg, AMBER, PANEL, bold=True)
    c.put(px + 3, py + (c.h - 11) - 2, "不收集身份，没有上传，只记录这一局。", FAINT, PANEL)

    menu.row(c, (("再来一轮", "again"), ("退出", "quit")), c.h - 6, 3, 2, accent=AMBER)
    menu.draw(c)
    footer(c, "ZJUT LUG · Linux 新手村", "SEE YOU NEXT TIME")
    key = ("final", c.w, c.h, protocol, run.won_count, run.total_score)
    return Frame(c.render(rect), png, rect, key, img)


def render_pause(c: Canvas, menu: Menu, level: LevelDef) -> None:
    pw = min(52, c.w - 8)
    ph = 11
    px = (c.w - pw) // 2
    py = max(3, (c.h - ph) // 2)
    c.fill(px, py, pw, ph, " ", INK, PANEL)
    panel(c, px, py, pw, ph, "PAUSED", level.accent, PANEL)
    c.put(px + 3, py + 2, "暂停中", WHITE, PANEL, bold=True)
    c.put(px + 3, py + 3, f"{level.name} · 休息一下，企鹅不会跑。", DIM, PANEL)
    menu.row(c, (("继续", "resume"), ("重开", "retry"), ("退出", "title")),
             py + ph - 4, 3, 2, accent=level.accent)
    menu.draw(c)


def render_too_small(c: Canvas) -> Frame:
    c.fill(0, 0, c.w, c.h, " ", INK, BG)
    c.center(max(0, c.h // 2 - 2), "终端太小了", AMBER, BG, bold=True)
    c.center(max(0, c.h // 2), f"至少需要 {MIN_W} x {MIN_H}", DIM, BG)
    c.center(max(0, c.h // 2 + 1), f"当前 {c.w} x {c.h}", FAINT, BG)
    c.center(max(0, c.h // 2 + 3), "放大窗口后自动继续", FAINT, BG)
    return Frame(c.render())
