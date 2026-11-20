"""极简 sixel 编码器。

Tabby 的 OSC 处理器会把 OSC 1337 整段吃掉（它只认 CurrentDir），但不会动
DCS，所以给 Tabby 走 sixel。这里不依赖 Pillow / libsixel，调色板和 32³
最近色表由场景采样离线生成，运行时只做 O(1) 查表。
"""

from __future__ import annotations

import base64
import zlib

from gfx import Img
from sixel_data import LUT_B64, PALETTE_HEX

PALETTE: list[tuple[int, int, int]] = [
    (int(PALETTE_HEX[i:i + 2], 16),
     int(PALETTE_HEX[i + 2:i + 4], 16),
     int(PALETTE_HEX[i + 4:i + 6], 16))
    for i in range(0, len(PALETTE_HEX), 6)
]

_LUT: bytes | None = None


def _lut() -> bytes:
    global _LUT
    if _LUT is None:
        _LUT = zlib.decompress(base64.b64decode("".join(LUT_B64)))
    return _LUT


def _indices(img: Img) -> bytearray:
    w, h = img.w, img.h
    buf = img.buf
    lut = _lut()
    idx = bytearray(w * h)
    for y in range(h):
        row = y * w
        for x in range(w):
            i = (row + x) * 3
            r = buf[i] >> 3
            g = buf[i + 1] >> 3
            b = buf[i + 2] >> 3
            idx[row + x] = lut[(r << 10) | (g << 5) | b]
    return idx


def encode(img: Img) -> bytes:
    """返回完整的 sixel 序列（含 ESC P ... ESC \\）。"""
    w, h = img.w, img.h
    idx = _indices(img)
    used = sorted(set(idx))

    out = bytearray()
    out += b"\x1bPq"
    out += f'"1;1;{w};{h}'.encode()
    for c in used:
        r, g, b = PALETTE[c]
        out += f"#{c};2;{r * 100 // 255};{g * 100 // 255};{b * 100 // 255}".encode()

    colors = len(used)
    masks = bytearray(colors * w)
    pos = {c: i for i, c in enumerate(used)}
    present = bytearray(colors)
    for by in range(0, h, 6):
        masks[:] = b"\x00" * (colors * w)
        present[:] = b"\x00" * colors
        for j in range(6):
            y = by + j
            if y >= h:
                break
            bit = 1 << j
            row = y * w
            for x in range(w):
                c = idx[row + x]
                ci = pos[c]
                masks[ci * w + x] |= bit
                present[ci] = 1
        for ci, c in enumerate(used):
            if not present[ci]:
                continue
            base = ci * w
            out += f"#{c}".encode()
            x = 0
            while x < w:
                m = masks[base + x]
                run = 1
                while x + run < w and masks[base + x + run] == m:
                    run += 1
                ch = 63 + m
                if run >= 4:
                    out += f"!{run}".encode()
                    out.append(ch)
                else:
                    out += bytes((ch,)) * run
                x += run
            out += b"$"
        if by + 6 < h:
            out += b"-"
    out += b"\x1b\\"
    return bytes(out)
