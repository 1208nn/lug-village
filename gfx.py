"""图像底座：RGB 缓冲、颜色、缩放和 PNG 编码。

具体场景在 scene.py，Sixel 编码在 sixel.py。这里只保留最基础的图元，
半块字符、PNG、Sixel 三种输出共用同一个 Img。
"""

from __future__ import annotations

import colorsys
import math
import struct
import zlib

Color = tuple[int, int, int]


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(c1: Color, c2: Color, t: float) -> Color:
    t = clamp(t)
    return (
        round(lerp(c1[0], c2[0], t)),
        round(lerp(c1[1], c2[1], t)),
        round(lerp(c1[2], c2[2], t)),
    )


def scale(c: Color, k: float) -> Color:
    return (
        max(0, min(255, round(c[0] * k))),
        max(0, min(255, round(c[1] * k))),
        max(0, min(255, round(c[2] * k))),
    )


def hsv(h: float, s: float, v: float) -> Color:
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, clamp(s), clamp(v))
    return (round(r * 255), round(g * 255), round(b * 255))


class Img:
    __slots__ = ("w", "h", "buf")

    def __init__(self, w: int, h: int):
        self.w = max(1, int(w))
        self.h = max(1, int(h))
        self.buf = bytearray(self.w * self.h * 3)


def resize(img: Img, w: int, h: int) -> Img:
    """双线性缩放。Sixel 需要严格按单元格像素尺寸出图时用。"""
    if w == img.w and h == img.h:
        return img
    out = Img(w, h)
    src = img.buf
    sw, sh = img.w, img.h
    for y in range(h):
        fy = (y + 0.5) * sh / h - 0.5
        y0 = int(math.floor(fy))
        ty = fy - y0
        y0 = max(0, min(sh - 1, y0))
        y1 = min(sh - 1, y0 + 1)
        for x in range(w):
            fx = (x + 0.5) * sw / w - 0.5
            x0 = int(math.floor(fx))
            tx = fx - x0
            x0 = max(0, min(sw - 1, x0))
            x1 = min(sw - 1, x0 + 1)
            i00 = (y0 * sw + x0) * 3
            i10 = (y0 * sw + x1) * 3
            i01 = (y1 * sw + x0) * 3
            i11 = (y1 * sw + x1) * 3
            o = (y * w + x) * 3
            for k in range(3):
                top = src[i00 + k] + (src[i10 + k] - src[i00 + k]) * tx
                bot = src[i01 + k] + (src[i11 + k] - src[i01 + k]) * tx
                out.buf[o + k] = int(top + (bot - top) * ty)
    return out


def png(img: Img, level: int = 6) -> bytes:
    w, h = img.w, img.h
    stride = w * 3
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += img.buf[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), level)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", comp)
        + chunk(b"IEND", b"")
    )
