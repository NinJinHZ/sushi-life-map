import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Songti.ttc"
SPECS = {
    "china": ("地形测试 01  ·  中国", "眉山 → 汴京", "1037—1057  ｜  出蜀行迹的空间示意"),
    "sichuan": ("地形测试 02  ·  四川盆地", "穿越盆地，北出蜀道", "眉山 → 成都 → 剑门关 → 广元 → 汉中"),
    "meishan": ("地形测试 03  ·  成都平原", "眉山", "1037  ｜  苏轼出生地"),
}


def font(size):
    return ImageFont.truetype(FONT, int(size))


def make_overlay(name, size, markers=None):
    w, h = size
    s = w / 1600
    layer = Image.new("RGBA", size, (0,0,0,0))
    # A restrained left-side scrim keeps the terrain visible.
    mask = Image.new("L", (w, 1))
    mask.putdata([int(125 * max(0, 1-x/(w*.48))**1.5) for x in range(w)])
    mask = mask.resize(size)
    layer = Image.composite(Image.new("RGBA", size, (3,10,13,255)), layer, mask)
    d = ImageDraw.Draw(layer)
    eyebrow, title, subtitle = SPECS[name]
    x, y = int(66*s), int(52*s)
    d.text((x,y), eyebrow, font=font(21*s), fill=(210,190,145,235))
    d.line((x,y+int(39*s),x+int(100*s),y+int(39*s)), fill=(205,169,100,160), width=max(1,int(s)))
    d.text((x,y+int(57*s)), title, font=font(48*s), fill=(241,235,218,255), stroke_width=max(1,int(s)), stroke_fill=(4,10,12,150))
    d.text((x,y+int(126*s)), subtitle, font=font(22*s), fill=(195,207,204,245), stroke_width=1, stroke_fill=(4,10,12,150))
    d.text((x,h-int(43*s)), "高程：Mapzen Terrain Tiles  ｜  影像：Esri World Imagery", font=font(15*s), fill=(190,201,198,190))
    d.text((w-int(66*s),h-int(45*s)), "真实 DEM 地形 · Blender", font=font(16*s), fill=(210,190,145,210), anchor="ra")
    if markers:
        for label, (mx, my) in markers.items():
            mx, my = mx*s, my*s
            dx = int(20*s) if label not in {"汴京", "成都"} else -int(20*s)
            anchor = "la" if dx > 0 else "ra"
            d.text((mx+dx,my-int(31*s)), label, font=font(25*s), fill=(245,226,180,255), anchor=anchor, stroke_width=max(1,int(2*s)), stroke_fill=(4,9,11,220))
    return layer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--video", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    for name in SPECS:
        if args.video:
            overlay = make_overlay(name, (1280,720))
            overlay.save(root / "renders" / f"{name}-video-overlay.png")
        else:
            raw = Image.open(root / "renders" / f"{name}-raw.png").convert("RGBA")
            markers = json.loads((root / "renders" / f"{name}-markers.json").read_text())
            overlay = make_overlay(name, raw.size, markers)
            out = Image.alpha_composite(raw, overlay).convert("RGB")
            out.save(root / "renders" / f"{name}-final.png")


if __name__ == "__main__":
    main()
