#!/usr/bin/env python3
"""生成本地插画素材：桌面环境、发行版 Logo、Tux、奖品图标。"""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H = 960, 540


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(size, top, bottom):
    w, h = size
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=lerp(top, bottom, y / max(1, h - 1)))
    return img


def overlay(img, layer):
    img.alpha_composite(layer) if img.mode == "RGBA" else img.paste(layer, (0, 0), layer)
    return img


def rounded(draw, box, r, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def window(img, box, style="win11", title="Files", dark=False):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = 14 if style in ("win11", "gnome") else 8
    # shadow
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((x0 + 8, y0 + 10, x1 + 8, y1 + 10), radius=r, fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    layer.alpha_composite(shadow)
    body = (32, 37, 52, 248) if dark else (246, 248, 252, 248)
    text = (230, 236, 246) if dark else (36, 42, 56)
    sub = (150, 164, 188) if dark else (116, 126, 144)
    rounded(d, (x0, y0, x1, y1), r, body)
    # title bar
    barh = 38 if style != "gnome" else 44
    title_bg = (42, 48, 66) if dark else (232, 236, 244)
    if style == "gnome":
        title_bg = (238, 241, 247) if not dark else (40, 46, 62)
    d.rounded_rectangle((x0, y0, x1, y0 + barh), radius=r, fill=title_bg)
    d.rectangle((x0, y0 + barh - r, x1, y0 + barh), fill=title_bg)
    # window controls
    if style == "gnome":
        for i, c in enumerate(((236, 96, 92), (245, 189, 79), (98, 197, 84))):
            d.ellipse((x0 + 16 + i * 22, y0 + 15, x0 + 28 + i * 22, y0 + 27), fill=c)
        d.text((x0 + w / 2, y0 + barh / 2), title, font=font(17, True), fill=text, anchor="mm")
    else:
        d.text((x0 + 18, y0 + barh / 2), title, font=font(16, True), fill=text, anchor="lm")
        # minimize / maximize / close
        ccx = x1 - 82
        d.line((ccx - 6, y0 + 19, ccx + 6, y0 + 19), fill=(120, 128, 144), width=2)
        ccx = x1 - 52
        d.line((ccx - 6, y0 + 15, ccx - 6, y0 + 23), fill=(120, 128, 144), width=2)
        d.line((ccx - 6, y0 + 23, ccx + 6, y0 + 23), fill=(120, 128, 144), width=2)
        d.line((ccx + 6, y0 + 15, ccx + 6, y0 + 23), fill=(120, 128, 144), width=2)
        ccx = x1 - 22
        d.line((ccx - 6, y0 + 14, ccx + 6, y0 + 24), fill=(232, 92, 92), width=2)
        d.line((ccx - 6, y0 + 24, ccx + 6, y0 + 14), fill=(232, 92, 92), width=2)
    # content
    top = y0 + barh + 16
    if style in ("win11", "win10", "kde", "cinnamon"):
        # sidebar
        sw = 150
        d.rounded_rectangle((x0 + 18, top, x0 + 18 + sw, y1 - 18), radius=8,
                            fill=(44, 50, 70, 180) if dark else (235, 239, 246, 210))
        for i, label in enumerate(("Home", "Documents", "Pictures", "Downloads")):
            yy = top + 22 + i * 36
            d.ellipse((x0 + 32, yy, x0 + 46, yy + 14), fill=(98, 166, 255) if i == 0 else sub)
            d.text((x0 + 56, yy + 7), label, font=font(13), fill=text, anchor="lm")
        cx0 = x0 + 18 + sw + 18
    else:
        cx0 = x0 + 22
    # file rows
    for i in range(5):
        yy = top + i * 36
        d.rounded_rectangle((cx0, yy, x1 - 20, yy + 28), radius=5,
                            fill=(54, 61, 84, 160) if dark else (238, 242, 248, 220) if i % 2 else None)
        d.rectangle((cx0 + 10, yy + 8, cx0 + 24, yy + 22), fill=(110, 172, 255))
        d.text((cx0 + 34, yy + 14), ("notes.txt", "README.md", "photos", "project", "archive")[i],
               font=font(13), fill=text, anchor="lm")
        d.text((x1 - 34, yy + 14), "12 KB", font=font(11), fill=sub, anchor="rm")
    img.alpha_composite(layer)


def win11():
    img = vgrad((W, H), (24, 52, 120), (18, 22, 58)).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(8):
        x = 60 + i * 120
        d.ellipse((x, 70 + i * 18, x + 260, 330 + i * 18), fill=(60, 120, 255, 28))
    img.alpha_composite(layer)
    window(img, (130, 82, 830, 430), "win11", "Files")
    # centered taskbar
    x0, y0, x1, y1 = 250, 476, 710, 526
    d = ImageDraw.Draw(img)
    rounded(d, (x0, y0, x1, y1), 18, (28, 34, 52, 225))
    # start
    sx, sy = 282, 488
    for i in range(2):
        for j in range(2):
            d.rectangle((sx + i * 14, sy + j * 14, sx + i * 14 + 10, sy + j * 14 + 10),
                        fill=(96, 166, 255))
    for i, c in enumerate(((255, 196, 78), (98, 210, 170), (255, 120, 150),
                           (150, 150, 255), (100, 210, 230))):
        cx = 340 + i * 64
        d.rounded_rectangle((cx, 487, cx + 26, 513), radius=6, fill=c + (220,))
    d.text((900, 501), "14:32", font=font(14, True), fill=(230, 236, 248), anchor="rm")
    img.convert("RGB").save(ASSETS / "os_win11.png")


def win10():
    img = vgrad((W, H), (10, 42, 96), (4, 16, 42)).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(9):
        d.polygon([(0, H), (i * 120, 0), (i * 120 + 80, 0)], fill=(50, 120, 220, 18))
    img.alpha_composite(layer)
    window(img, (110, 70, 850, 440), "win10", "This PC")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 492, W, H), fill=(18, 24, 36, 240))
    sx, sy = 18, 503
    for i in range(2):
        for j in range(2):
            d.rectangle((sx + i * 13, sy + j * 13, sx + i * 13 + 9, sy + j * 13 + 9),
                        fill=(90, 170, 255))
    d.rounded_rectangle((70, 500, 330, 526), radius=3, fill=(32, 40, 58))
    d.text((86, 513), "Type here to search", font=font(12), fill=(140, 152, 176), anchor="lm")
    for i, c in enumerate(((255, 190, 70), (90, 210, 160), (250, 120, 150),
                           (140, 150, 255), (90, 210, 230))):
        cx = 380 + i * 58
        d.rounded_rectangle((cx, 501, cx + 24, 525), radius=3, fill=c + (215,))
    d.text((900, 513), "14:32", font=font(13, True), fill=(230, 236, 248), anchor="rm")
    img.convert("RGB").save(ASSETS / "os_win10.png")


def gnome(kind="ubuntu"):
    if kind == "ubuntu":
        img = vgrad((W, H), (42, 12, 66), (12, 10, 28)).convert("RGBA")
        ring = (233, 84, 32, 210)
    else:
        img = vgrad((W, H), (12, 44, 100), (6, 16, 42)).convert("RGBA")
        ring = (70, 140, 255, 210)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse((560, 40, 1080, 560), outline=ring, width=26)
    d.ellipse((640, 120, 1000, 480), outline=(ring[0], ring[1], ring[2], 70), width=10)
    img.alpha_composite(layer)
    window(img, (210, 108, 860, 440), "gnome", "Files", dark=True)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 34), fill=(14, 18, 28, 235))
    d.text((22, 17), "Activities", font=font(13, True), fill=(230, 236, 246), anchor="lm")
    d.text((W / 2, 17), "Thu 14:32", font=font(13, True), fill=(230, 236, 246), anchor="mm")
    for i in range(4):
        d.ellipse((W - 120 + i * 24, 10, W - 108 + i * 24, 22), fill=(150, 164, 188))
    # dock
    d.rounded_rectangle((18, 54, 76, 470), radius=16, fill=(18, 22, 34, 220))
    for i, c in enumerate(((255, 120, 80), (90, 180, 255), (120, 220, 160),
                           (190, 150, 255), (255, 200, 90))):
        cx = 47
        cy = 84 + i * 62
        d.rounded_rectangle((cx - 18, cy - 18, cx + 18, cy + 18), radius=10, fill=c + (220,))
    img.convert("RGB").save(ASSETS / ("os_ubuntu.png" if kind == "ubuntu" else "os_fedora.png"))


def kde():
    img = vgrad((W, H), (16, 52, 96), (8, 18, 42)).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(7):
        d.arc((100 + i * 110, 60 + i * 20, 700 + i * 110, 500 + i * 20),
              200, 340, fill=(60, 170, 230, 35), width=16)
    img.alpha_composite(layer)
    window(img, (130, 90, 820, 430), "kde", "Dolphin")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 486, W, H), fill=(20, 26, 40, 240))
    d.rounded_rectangle((16, 496, 54, 528), radius=8, fill=(80, 170, 255))
    d.text((68, 512), "Applications", font=font(12), fill=(180, 194, 216), anchor="lm")
    for i, c in enumerate(((255, 190, 70), (90, 210, 160), (250, 120, 150))):
        d.rounded_rectangle((300 + i * 46, 500, 324 + i * 46, 524), radius=4, fill=c + (210,))
    d.text((900, 512), "14:32", font=font(13, True), fill=(230, 236, 246), anchor="rm")
    img.convert("RGB").save(ASSETS / "os_kde.png")


def cinnamon():
    img = vgrad((W, H), (12, 78, 64), (4, 28, 28)).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(10):
        d.ellipse((80 + i * 80, 40 + i * 12, 420 + i * 80, 380 + i * 12),
                  fill=(70, 200, 160, 18))
    img.alpha_composite(layer)
    window(img, (150, 96, 830, 430), "cinnamon", "Nemo")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 490, W, H), fill=(20, 34, 34, 240))
    d.ellipse((18, 500, 52, 534), fill=(100, 220, 150))
    d.text((66, 516), "Menu", font=font(13, True), fill=(220, 240, 230), anchor="lm")
    d.text((180, 516), "Files", font=font(12), fill=(200, 220, 210), anchor="lm")
    d.text((900, 516), "14:32", font=font(13, True), fill=(220, 240, 230), anchor="rm")
    img.convert("RGB").save(ASSETS / "os_mint.png")


def logo_base():
    return Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))


def save_logo(img, name):
    img.resize((512, 512), Image.LANCZOS).save(ASSETS / name)


def logo_ubuntu():
    img = logo_base(); d = ImageDraw.Draw(img)
    d.ellipse((190, 190, 834, 834), outline=(233, 84, 32, 255), width=86)
    for ang in (90, 210, 330):
        a = math.radians(ang)
        cx, cy = 512 + 300 * math.cos(a), 512 - 300 * math.sin(a)
        d.ellipse((cx - 58, cy - 58, cx + 58, cy + 58), fill=(255, 255, 255, 255))
    save_logo(img, "logo_ubuntu.png")


def logo_debian():
    img = logo_base(); d = ImageDraw.Draw(img)
    pts = []
    for i in range(220):
        t = i / 219 * 5.2 * math.pi
        r = 34 + 29 * t
        pts.append((512 + r * math.cos(t), 512 + r * math.sin(t)))
    for i in range(0, len(pts) - 1, 2):
        d.line((pts[i], pts[i + 1]), fill=(215, 45, 55, 255), width=34)
    save_logo(img, "logo_debian.png")


def logo_arch():
    img = logo_base(); d = ImageDraw.Draw(img)
    pts = [(512, 96), (164, 900), (360, 900), (512, 560), (664, 900), (860, 900)]
    d.polygon(pts, fill=(80, 170, 255, 255))
    d.polygon([(512, 260), (400, 620), (512, 560), (624, 620)], fill=(12, 36, 70, 255))
    save_logo(img, "logo_arch.png")


def logo_fedora():
    img = logo_base(); d = ImageDraw.Draw(img)
    d.ellipse((128, 128, 896, 896), fill=(41, 100, 180, 255))
    d.ellipse((214, 214, 810, 810), fill=(255, 255, 255, 255))
    d.ellipse((330, 300, 760, 730), fill=(41, 100, 180, 255))
    d.rectangle((470, 250, 560, 700), fill=(255, 255, 255, 255))
    d.arc((390, 170, 760, 520), 200, 330, fill=(255, 255, 255, 255), width=74)
    save_logo(img, "logo_fedora.png")


def logo_mint():
    img = logo_base(); d = ImageDraw.Draw(img)
    # leaf
    d.polygon([(512, 100), (820, 330), (720, 760), (512, 930), (304, 760), (204, 330)],
              fill=(120, 205, 120, 255))
    d.line((512, 170, 512, 860), fill=(245, 255, 245, 235), width=18)
    for i in range(5):
        y = 330 + i * 100
        d.line((512, y, 700 - i * 24, y - 70), fill=(245, 255, 245, 180), width=9)
        d.line((512, y, 324 + i * 24, y - 70), fill=(245, 255, 245, 180), width=9)
    save_logo(img, "logo_mint.png")


def logo_suse():
    img = logo_base(); d = ImageDraw.Draw(img)
    green = (115, 186, 70, 255)
    d.ellipse((180, 300, 840, 820), fill=green)
    d.ellipse((620, 190, 880, 450), fill=green)
    d.ellipse((700, 270, 760, 330), fill=(20, 40, 20, 255))
    d.ellipse((800, 270, 860, 330), fill=(20, 40, 20, 255))
    d.arc((690, 330, 850, 430), 20, 160, fill=(20, 40, 20, 255), width=14)
    # tail
    d.arc((60, 520, 420, 900), 120, 330, fill=green, width=70)
    # legs
    for x in (330, 540):
        d.rounded_rectangle((x, 720, x + 60, 900), radius=26, fill=green)
    save_logo(img, "logo_suse.png")


def tux():
    img = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((180, 120, 844, 930), fill=(20, 24, 34, 255))
    d.ellipse((300, 300, 724, 880), fill=(246, 246, 238, 255))
    d.ellipse((250, 170, 500, 560), fill=(28, 32, 42, 255))
    d.ellipse((524, 170, 774, 560), fill=(28, 32, 42, 255))
    d.ellipse((330, 250, 450, 370), fill=(255, 255, 250, 255))
    d.ellipse((574, 250, 694, 370), fill=(255, 255, 250, 255))
    d.ellipse((375, 295, 420, 340), fill=(20, 20, 24, 255))
    d.ellipse((604, 295, 649, 340), fill=(20, 20, 24, 255))
    d.ellipse((462, 340, 562, 420), fill=(245, 158, 62, 255))
    d.ellipse((270, 800, 450, 900), fill=(245, 158, 62, 255))
    d.ellipse((574, 800, 754, 900), fill=(245, 158, 62, 255))
    d.ellipse((120, 560, 300, 780), fill=(28, 32, 42, 255))
    d.ellipse((724, 560, 904, 780), fill=(28, 32, 42, 255))
    save_logo(img, "tux.png")


def sticker():
    img = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((80, 80, 944, 944), radius=180, fill=(255, 255, 255, 255),
                        outline=(84, 156, 255, 255), width=34)
    d.ellipse((260, 260, 764, 764), fill=(24, 30, 42, 255))
    d.ellipse((340, 340, 684, 760), fill=(255, 255, 250, 255))
    d.ellipse((390, 340, 500, 450), fill=(255, 255, 250, 255))
    d.ellipse((524, 340, 634, 450), fill=(255, 255, 250, 255))
    d.ellipse((425, 380, 465, 420), fill=(20, 20, 24, 255))
    d.ellipse((559, 380, 599, 420), fill=(20, 20, 24, 255))
    d.ellipse((470, 430, 554, 500), fill=(245, 158, 62, 255))
    save_logo(img, "prize_sticker.png")


def postcard():
    img = Image.new("RGBA", (1024, 680), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((20, 20, 1004, 660), radius=36, fill=(251, 249, 240, 255),
                        outline=(84, 156, 255, 255), width=20)
    d.line((700, 40, 700, 640), fill=(180, 190, 210, 255), width=6)
    d.rectangle((60, 60, 660, 420), fill=(168, 214, 250, 255))
    d.rectangle((60, 350, 660, 420), fill=(116, 200, 150, 255))
    d.ellipse((520, 90, 600, 170), fill=(255, 226, 130, 255))
    d.polygon([(80, 350), (240, 170), (400, 350)], fill=(80, 150, 210, 255))
    d.rounded_rectangle((760, 100, 940, 280), radius=12, fill=(255, 255, 255, 255),
                        outline=(180, 190, 210, 255), width=5)
    d.ellipse((810, 140, 890, 220), fill=(250, 190, 80, 255))
    d.line((780, 300, 920, 300), fill=(180, 190, 210, 255), width=5)
    d.line((780, 340, 920, 340), fill=(180, 190, 210, 255), width=5)
    save_logo(img, "prize_postcard.png")


def main():
    ASSETS.mkdir(exist_ok=True)
    win11(); win10(); gnome("ubuntu"); kde(); cinnamon(); gnome("fedora")
    logo_ubuntu(); logo_debian(); logo_arch(); logo_fedora(); logo_mint(); logo_suse()
    tux(); sticker(); postcard()
    print("assets:", len(list(ASSETS.glob("*.png"))))


if __name__ == "__main__":
    main()
