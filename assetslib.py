"""本地图片素材：PNG、RGB 缓冲、半块降采样。"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

import gfx

ROOT = Path(__file__).resolve().parent
IMAGE_BG = (12, 18, 32)


@dataclass
class Asset:
    name: str
    png: bytes
    img: gfx.Img
    w: int
    h: int


_cache: dict[str, Asset] = {}
_half_cache: dict[tuple[str, int, int], gfx.Img | None] = {}


def load(name: str) -> Asset | None:
    if name in _cache:
        return _cache[name]
    path = ROOT / name
    try:
        src = Image.open(path).convert("RGBA")
    except (OSError, ValueError):
        return None
    mat = Image.new("RGBA", src.size, IMAGE_BG + (255,))
    mat.alpha_composite(src)
    rgb = mat.convert("RGB")
    buf = rgb.tobytes()
    img = gfx.Img(rgb.width, rgb.height)
    img.buf[:] = buf
    out = io.BytesIO()
    rgb.save(out, format="PNG", optimize=True)
    asset = Asset(name, out.getvalue(), img, rgb.width, rgb.height)
    _cache[name] = asset
    return asset


def half(name: str, cols: int, rows: int) -> gfx.Img | None:
    """把图片降采样成半块字符用的 cols x rows*2 RGB。"""
    key = (name, cols, rows)
    if key in _half_cache:
        return _half_cache[key]
    asset = load(name)
    if asset is None:
        return None
    src = Image.frombytes("RGB", (asset.w, asset.h), bytes(asset.img.buf))
    small = src.resize((max(1, cols), max(1, rows * 2)), Image.LANCZOS)
    img = gfx.Img(small.width, small.height)
    img.buf[:] = small.tobytes()
    _half_cache[key] = img
    return img
