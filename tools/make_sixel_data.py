#!/usr/bin/env python3
"""从本地素材采样，生成 Sixel 调色板与 32^3 最近色表。"""

from __future__ import annotations

import base64
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
N = 192
GRID = 32


def sample(path: Path, step=6):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    out = []
    for y in range(0, h, step):
        for x in range(0, w, step):
            out.append(px[x, y])
    return out


def avg(box):
    n = len(box)
    return (sum(p[0] for p in box) // n,
            sum(p[1] for p in box) // n,
            sum(p[2] for p in box) // n)


def rng(box):
    return (max(p[0] for p in box) - min(p[0] for p in box),
            max(p[1] for p in box) - min(p[1] for p in box),
            max(p[2] for p in box) - min(p[2] for p in box))


def main():
    samples = []
    for path in sorted(ASSETS.glob("*.png")):
        samples.extend(sample(path))
    print("samples", len(samples))
    boxes = [samples]
    while len(boxes) < N:
        best, score = -1, -1
        for i, b in enumerate(boxes):
            if len(b) < 2:
                continue
            r = rng(b)
            s = max(r) * len(b)
            if s > score:
                best, score = i, s
        if best < 0:
            break
        b = boxes[best]
        r = rng(b)
        ch = r.index(max(r))
        b.sort(key=lambda p: p[ch])
        mid = len(b) // 2
        boxes[best:best + 1] = [b[:mid], b[mid:]]
    pal = [avg(b) for b in boxes]
    print("palette", len(pal))

    lut = bytearray(GRID ** 3)
    for ri in range(GRID):
        r = ri * 255 // (GRID - 1)
        for gi in range(GRID):
            g = gi * 255 // (GRID - 1)
            for bi in range(GRID):
                b = bi * 255 // (GRID - 1)
                best, bd = 0, 1 << 30
                for k, (pr, pg, pb) in enumerate(pal):
                    d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
                    if d < bd:
                        bd, best = d, k
                lut[(ri * GRID + gi) * GRID + bi] = best
    comp = zlib.compress(bytes(lut), 9)
    hx = "".join(f"{r:02x}{g:02x}{b:02x}" for r, g, b in pal)
    b64 = base64.b64encode(comp).decode("ascii")
    with open(ROOT / "sixel_data.py", "w", encoding="utf-8") as f:
        f.write('"""素材采样生成的 Sixel 调色板与 32^3 最近色表。"""\n\n')
        f.write("PALETTE_HEX = (\n")
        for i in range(0, len(hx), 96):
            f.write("    " + repr(hx[i:i + 96]) + "\n")
        f.write(")\n\nLUT_B64 = (\n")
        for i in range(0, len(b64), 96):
            f.write("    " + repr(b64[i:i + 96]) + "\n")
        f.write(")\n")
    print("wrote sixel_data.py", len(hx), len(b64))


if __name__ == "__main__":
    main()
