"""终端底座：原始按键、替换屏幕、图片协议。"""

from __future__ import annotations

import base64
import os
import re
import select
import shutil
import sys
import termios
import tty
import time

import gfx
import sixel

IMAGE_ID = 42

PROTOCOLS = ("kitty", "sixel", "iterm", "half")
PROTOCOL_LABEL = {
    "kitty": "Kitty 图形协议",
    "sixel": "Sixel 图片（DCS）",
    "iterm": "iTerm2 内联图片（OSC 1337）",
    "half": "半块字符 ▀",
}

# Kitty / Ghostty / WezTerm 会回 \x1b_Gi=31;OK\x1b\\
KITTY_QUERY = b"\x1b_Gi=31,s=1,v=1,a=q,t=d,f=24;AAAA\x1b\\"
# iTerm2 会回 \x1b]1337;ReportCellSize=...\x07
CELL_SIZE_QUERY = b"\x1b]1337;ReportCellSize\x07"
# 主设备属性：Tabby 的 addon-image 会回 \x1b[?62;4;9;22c，普通 xterm.js 只会回 \x1b[?1;2c
DA1_QUERY = b"\x1b[c"
# 次级设备属性：xterm.js（Tabby / VS Code / Hyper）固定回 \x1b[>0;276;0c
DA2_QUERY = b"\x1b[>c"
# XTVERSION：WezTerm 会回 \x1bP>|WezTerm <version>\x1b\\
XTVERSION_QUERY = b"\x1b[>0q"
# xterm.js：CSI 16 t 单元格像素尺寸，CSI 14 t 窗口像素尺寸
CELL_PIXELS_QUERY = b"\x1b[16t\x1b[14t"
# 只匹配 addon-image，别把 foot / xterm 的 sixel 误判成 iTerm2
TABBY_DA1 = b"\x1b[?62;4;9;22c"
XTERMJS_DA2 = b"\x1b[>0;276;0c"
# Windows ConPTY / 老 conhost 的固定签名：DA1 ?61;... + DA2 >0;10;1c。
# 它会抢答 DA1/DA2，而且不转发图片序列，必须绕开。
CONPTY_DA1 = b"\x1b[?61;"
CONPTY_DA2 = b"\x1b[>0;10;1c"

PROBE_SIGNALS = ("kitty", "iterm", "wezterm", "tabby", "xterm.js", "conpty")

# 最近一次探测命中的信号，给启动提示和 iTerm2 参数用
PROBED_SIGNALS: set[str] = set()

ENV_KEYS = (
    "TERM",
    "TERM_PROGRAM",
    "TERM_PROGRAM_VERSION",
    "LC_TERMINAL",
    "COLORTERM",
    "KITTY_WINDOW_ID",
    "WEZTERM_PANE",
    "WEZTERM_EXECUTABLE",
    "WEZTERM_UNIX_SOCKET",
    "GHOSTTY_RESOURCES_DIR",
    "TABBY_CONFIG_DIRECTORY",
    "TMUX",
    "STY",
    "SSH_TTY",
)


def _env(name: str) -> str:
    return os.environ.get(name, "").strip().lower()


def is_wezterm() -> bool:
    return (
        _env("TERM_PROGRAM") == "wezterm"
        or bool(os.environ.get("WEZTERM_PANE"))
        or bool(os.environ.get("WEZTERM_EXECUTABLE"))
        or bool(os.environ.get("WEZTERM_UNIX_SOCKET"))
    )


def is_tabby() -> bool:
    return _env("TERM_PROGRAM") == "tabby" or any(
        k.startswith("TABBY_") for k in os.environ
    )


def terminal_flavor() -> str:
    """尽量判断外层终端，返回 kitty / ghostty / wezterm / iterm / tabby / 空。"""
    term = _env("TERM")
    prog = _env("TERM_PROGRAM")
    lc = _env("LC_TERMINAL")

    if os.environ.get("KITTY_WINDOW_ID") or "kitty" in term or prog == "kitty":
        return "kitty"
    if "ghostty" in term or prog == "ghostty" or os.environ.get("GHOSTTY_RESOURCES_DIR"):
        return "ghostty"
    if is_wezterm():
        return "wezterm"
    if is_tabby():
        return "tabby"
    if prog in ("iterm.app", "iterm2", "iterm") or lc in ("iterm2", "iterm.app", "iterm"):
        return "iterm"
    return ""


def env_protocol() -> str:
    """只根据环境变量推断，返回 kitty / sixel / iterm / half。"""
    # tmux / screen 默认会拦下图片转义序列；宁可退回半块，也别留下空白框
    if os.environ.get("TMUX") or os.environ.get("STY"):
        return "half"
    flavor = terminal_flavor()
    if flavor in ("kitty", "ghostty"):
        return "kitty"
    # Tabby 的 OSC 处理器会吞掉 OSC 1337，只能走 sixel
    if flavor == "tabby":
        return "sixel"
    if flavor in ("wezterm", "iterm"):
        return "iterm"
    return "half"


def detect_image_protocol() -> str:
    """返回 kitty / sixel / iterm / half。环境变量 LUG_IMAGE 可以强制指定。"""
    force = os.environ.get("LUG_IMAGE", "").strip().lower()
    if force == "iterm2":
        force = "iterm"
    if force in PROTOCOLS:
        return force
    return env_protocol()


def _probe_buf_signals(buf: bytes) -> set[str]:
    signals: set[str] = set()
    if b";OK" in buf:
        signals.add("kitty")
    if b"ReportCellSize" in buf:
        signals.add("iterm")
    if TABBY_DA1 in buf:
        signals.add("tabby")
    if XTERMJS_DA2 in buf:
        signals.add("xterm.js")
    # 两个签名同时出现才判定：单独 ?61; 有些老 xterm 也会回，容易误伤
    if CONPTY_DA1 in buf and CONPTY_DA2 in buf:
        signals.add("conpty")
    # XTVERSION: \x1bP>|WezTerm 20240203\x1b\\ / \x1bP>|kitty(0.40.0)\x1b\\
    for m in re.finditer(rb"\x1bP>\|([^\x1b\r\n]+)", buf):
        name = m.group(1).decode("utf-8", "replace").strip().lower()
        if name.startswith("wezterm"):
            signals.add("wezterm")
        elif name.startswith("kitty") or name.startswith("ghostty"):
            signals.add("kitty")
    return signals


def _drain(fd_in: int, seconds: float = 0.06) -> bytes:
    """把探测后仍在路上的回复读掉，免得变成假的按键。"""
    out = b""
    deadline = time.monotonic() + seconds
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            break
        ready, _, _ = select.select([fd_in], [], [], left)
        if not ready:
            break
        try:
            chunk = os.read(fd_in, 2048)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    return out


def _query_terminal(payload: bytes, timeout: float, done=None) -> bytes:
    """在 cbreak 下发查询并收回复；done(buf) 为真时提前结束。"""
    try:
        fd_in = sys.stdin.fileno()
        fd_out = sys.stdout.fileno()
        old = termios.tcgetattr(fd_in)
    except (OSError, ValueError, termios.error):
        return b""

    buf = b""
    try:
        tty.setcbreak(fd_in)
        os.write(fd_out, payload)
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            ready, _, _ = select.select([fd_in], [], [], left)
            if not ready:
                break
            try:
                chunk = os.read(fd_in, 4096)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            if done is not None and done(buf):
                break
        buf += _drain(fd_in)
    finally:
        try:
            termios.tcsetattr(fd_in, termios.TCSADRAIN, old)
        except termios.error:
            pass
    return buf


def _image_reply_done(buf: bytes) -> bool:
    signals = _probe_buf_signals(buf)
    if signals & {"wezterm", "iterm", "tabby", "xterm.js"}:
        return True
    return "kitty" in signals and b"\x1bP>|" in buf


def probe_image_protocol(
    timeout: float = 0.4,
    details: list[str] | None = None,
    raw: list[bytes] | None = None,
) -> str | None:
    """直接问终端支不支持图片，返回 kitty / sixel / iterm / half / None。"""
    buf = _query_terminal(
        KITTY_QUERY + CELL_SIZE_QUERY + DA1_QUERY + DA2_QUERY + XTVERSION_QUERY,
        timeout,
        _image_reply_done,
    )
    signals = _probe_buf_signals(buf)
    global PROBED_SIGNALS
    PROBED_SIGNALS = signals

    if details is not None:
        details.extend(s for s in PROBE_SIGNALS if s in signals)
        if not signals:
            details.append("无响应")
    if raw is not None:
        raw.append(buf)

    # ConPTY 优先级最高：它抢答 DA1/DA2 且不转发图片序列，任何图片协议都没用
    if "conpty" in signals:
        return "half"
    # Tabby 的 OSC 处理器会丢弃 OSC 1337，但放行 DCS，所以走 sixel
    if "tabby" in signals:
        return "sixel"
    # WezTerm 优先 iTerm2：它的 Kitty 图形协议在部分版本上会把画面留白
    if "wezterm" in signals:
        return "iterm"
    if "kitty" in signals:
        return "kitty"
    if signals & {"iterm", "xterm.js"}:
        return "iterm"
    return None


def probe_cell_pixels(timeout: float = 0.35) -> tuple[int, int] | None:
    """问 xterm.js 单元格像素尺寸，返回 (宽, 高)。失败返回 None。"""
    pattern = re.compile(rb"\x1b\[(?:6|4);\d+;\d+t")
    buf = _query_terminal(CELL_PIXELS_QUERY, timeout, pattern.search)

    # CSI 6 ; height ; width t = 单元格；CSI 4 ; height ; width t = 窗口
    m = re.search(rb"\x1b\[6;(\d+);(\d+)t", buf)
    if m:
        h, w = int(m.group(1)), int(m.group(2))
        if w > 0 and h > 0:
            return (w, h)
    m = re.search(rb"\x1b\[4;(\d+);(\d+)t", buf)
    if m:
        wh, ww = int(m.group(1)), int(m.group(2))
        try:
            cols, rows = os.get_terminal_size(sys.stdout.fileno())
        except OSError:
            cols = rows = 0
        if cols > 0 and rows > 0 and ww >= cols and wh >= rows:
            return (max(1, ww // cols), max(1, wh // rows))
    return None


def describe_environment() -> list[tuple[str, str]]:
    """给 --doctor 用的环境快照。"""
    return [(k, os.environ.get(k, "")) for k in ENV_KEYS]


class Terminal:
    def __init__(self, image_mode: str = "auto"):
        self.fd_in = sys.stdin.fileno()
        self.fd_out = sys.stdout.fileno()
        self._auto = image_mode == "auto"
        self.protocol = detect_image_protocol() if self._auto else image_mode
        self.old_attrs = None
        self._entered = False
        self._last_image = None
        self._queue: list[str] = []
        self.hint = ""
        self.cell_px: tuple[int, int] | None = None

    # ---------- 生命周期 ----------

    def __enter__(self):
        self.enter()
        return self

    def __exit__(self, *exc):
        self.leave()
        return False

    def enter(self) -> None:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise RuntimeError("需要一个真正的终端（TTY）才能摆摊。")
        self.old_attrs = termios.tcgetattr(self.fd_in)
        new = termios.tcgetattr(self.fd_in)
        new[0] &= ~(termios.IXON | termios.IXOFF)
        new[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG)
        new[6][termios.VMIN] = 1
        new[6][termios.VTIME] = 0
        termios.tcsetattr(self.fd_in, termios.TCSADRAIN, new)
        # 环境变量认不出来时（SSH、WSL），直接问终端本身。
        # SSH 里也探一次：ConPTY 会把 DA1/DA2 全抢答，不能只信环境变量。
        if self._auto and (self.protocol == "half" or os.environ.get("SSH_TTY")):
            probed = probe_image_protocol()
            if probed is not None:
                self.protocol = probed
        if self.protocol == "sixel":
            self.cell_px = probe_cell_pixels()
        if self._auto and "conpty" in PROBED_SIGNALS:
            self.hint = "图片被 Windows ConPTY 拦住了：WezTerm 用 wezterm ssh，Tabby 用内置 SSH 连接"
        # xterm.js 认出来了、但 addon-image 没应答：多半是图片开关关着
        elif (
            self._auto
            and "xterm.js" in PROBED_SIGNALS
            and "tabby" not in PROBED_SIGNALS
            and not is_tabby()
        ):
            self.hint = "像是 xterm.js 内核，但没检测到图片插件；若这是 Tabby，请打开 设置 → 终端 → Sixel / 图片"
        self.write("\x1b]2;ZJUT LUG · Linux 新手村\x07\x1b[?1049h\x1b[?1000h\x1b[?1006h\x1b[2J\x1b[H\x1b[?25l")
        self._entered = True

    def leave(self) -> None:
        if not self._entered:
            return
        try:
            self.clear_image()
            self.write("\x1b[0m\x1b[?1006l\x1b[?1000l\x1b]2;\x07\x1b[?25h\x1b[?1049l")
        finally:
            if self.old_attrs is not None:
                termios.tcsetattr(self.fd_in, termios.TCSADRAIN, self.old_attrs)
            self._entered = False

    # ---------- 输出 ----------

    def write(self, s: str) -> None:
        os.write(self.fd_out, s.encode("utf-8", "replace"))

    def size(self) -> tuple[int, int]:
        s = shutil.get_terminal_size((100, 30))
        return s.columns, s.lines

    def clear(self) -> None:
        self.write("\x1b[2J\x1b[H")

    # ---------- 输入 ----------

    def read_key(self, timeout: float = 0.1) -> str | None:
        if self._queue:
            return self._queue.pop(0)
        try:
            ready, _, _ = select.select([self.fd_in], [], [], timeout)
        except InterruptedError:
            return None
        if not ready:
            return None
        try:
            data = os.read(self.fd_in, 128)
        except OSError:
            return "ctrl-c"
        if not data:
            return "ctrl-c"
        self._parse(data)
        return self._queue.pop(0) if self._queue else None

    def _parse(self, data: bytes) -> None:
        if b"\x03" in data:
            self._queue.append("ctrl-c")
            return
        text = data.decode("utf-8", "ignore")
        # 终端对探测的回复（DCS / OSC）不能当成按键
        text = re.sub(r"\x1bP.*?\x1b\\", "", text, flags=re.DOTALL)
        text = re.sub(r"\x1b\].*?(?:\x07|\x1b\\)", "", text, flags=re.DOTALL)
        # SGR 鼠标：\x1b[<b;x;yM
        for m in re.finditer(r"\x1b\[<(\d+);(\d+);(\d+)([Mm])", text):
            b, x, y, final = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
            if final == "M" and b < 64:
                button = b & 3
                if button == 0:
                    self._queue.append(f"mouse:left:{x - 1}:{y - 1}")
                elif button == 2:
                    self._queue.append(f"mouse:right:{x - 1}:{y - 1}")
        text = re.sub(r"\x1b\[<\d+;\d+;\d+[Mm]", "", text)
        text = re.sub(r"\x1b\[A|\x1bOA", "\ue000", text)
        text = re.sub(r"\x1b\[B|\x1bOB", "\ue001", text)
        text = re.sub(r"\x1b\[C|\x1bOC", "\ue003", text)
        text = re.sub(r"\x1b\[D|\x1bOD", "\ue002", text)
        text = re.sub(r"\x1b\[Z", "\ue004", text)
        # 其余方向键、功能键、光标位置报告：吞掉
        text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
        text = re.sub(r"\x1bO.", "", text)
        for ch in text:
            if ch == "\ue000":
                self._queue.append("up")
            elif ch == "\ue001":
                self._queue.append("down")
            elif ch == "\ue003":
                self._queue.append("right")
            elif ch == "\ue002":
                self._queue.append("left")
            elif ch == "\ue004":
                self._queue.append("tab")
            elif ch == "\x1b":
                self._queue.append("esc")
            elif ch in ("\r", "\n"):
                self._queue.append("enter")
            elif ch == "\t":
                self._queue.append("tab")
            elif ch == " ":
                self._queue.append("space")
            elif ch in ("\x7f", "\b"):
                self._queue.append("backspace")
            elif ch.isprintable():
                self._queue.append(ch)

    # ---------- 图片 ----------

    def place_image(self, img: gfx.Img | None, png: bytes | None, x: int, y: int,
                    cols: int, rows: int) -> None:
        """x/y/cols/rows 都是 0 基单元格坐标。img 是原始 RGB，sixel 用。"""
        if self.protocol == "kitty" and png is not None:
            self._kitty_image(png, x, y, cols, rows)
        elif self.protocol == "iterm" and png is not None:
            self._iterm_image(png, x, y, cols, rows)
        elif self.protocol == "sixel" and img is not None:
            self._sixel_image(img, x, y, cols, rows)
        self._last_image = (x, y, cols, rows)

    def _kitty_image(self, png: bytes, x: int, y: int, cols: int, rows: int) -> None:
        b64 = base64.standard_b64encode(png).decode("ascii")
        out = [f"\x1b[{y + 1};{x + 1}H"]
        first = True
        while b64:
            chunk, b64 = b64[:4096], b64[4096:]
            more = 1 if b64 else 0
            if first:
                # C=1：放完图别动光标，免得把后面的文字挤走
                head = f"a=T,f=100,i={IMAGE_ID},q=2,C=1,c={cols},r={rows},m={more}"
                first = False
            else:
                head = f"m={more}"
            out.append(f"\x1b_G{head};{chunk}\x1b\\")
        self.write("".join(out))

    def _iterm_image(self, png: bytes, x: int, y: int, cols: int, rows: int) -> None:
        b64 = base64.standard_b64encode(png).decode("ascii")
        args = [
            # xterm.js 的 addon-image 强制要求 size，缺了会直接丢弃整张图
            f"size={len(png)}",
            "inline=1",
            f"width={cols}",
            f"height={rows}",
            "preserveAspectRatio=0",
        ]
        # WezTerm 额外支持 doNotMoveCursor=1；iTerm2 / Tabby 不加，避免不认识的参数
        if is_wezterm() or "wezterm" in PROBED_SIGNALS:
            args.append("doNotMoveCursor=1")
        # 参数用 ; 分隔，参数和数据之间必须是 :，少了它终端会把 base64 当参数
        self.write(
            f"\x1b[{y + 1};{x + 1}H"
            f"\x1b]1337;File={';'.join(args)}:{b64}\x07"
        )

    def _sixel_image(self, img: gfx.Img, x: int, y: int, cols: int, rows: int) -> None:
        cw, ch = self.cell_px or (8, 16)
        tw, th = max(1, cols * cw), max(1, rows * ch)
        if img.w != tw or img.h != th:
            img = gfx.resize(img, tw, th)
        self.write(f"\x1b[{y + 1};{x + 1}H")
        self.write(sixel.encode(img).decode("ascii"))

    def clear_image(self) -> None:
        if self.protocol == "kitty":
            self.write(f"\x1b_Ga=d,d=i,i={IMAGE_ID},q=2\x1b\\")
        self._last_image = None
