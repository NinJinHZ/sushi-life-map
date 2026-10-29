import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose_archival as ca

W, H = 1280, 720
OUTPUT_SIZE = (W, H)
OPENING_FRAMES = 72
TITLE_FONT = ImageFont.truetype(ca.CALLI, 82)
SUBTITLE_FONT = ImageFont.truetype(ca.SONG, 17)
YEAR_FONT = ImageFont.truetype(ca.LATIN, 12)
TERRAIN = None
RELIEF = None


def prepare_terrain(path):
    global TERRAIN, RELIEF
    base = Image.open(path).convert('RGB').resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
    base = ImageEnhance.Color(base).enhance(.38)
    base = ImageEnhance.Brightness(base).enhance(.28)
    TERRAIN = base.filter(ImageFilter.GaussianBlur(.35))
    edges = base.convert('L').filter(ImageFilter.GaussianBlur(1.6)).filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.autocontrast(edges).point(lambda p: max(0, p - 42))
    RELIEF = Image.new('RGBA', OUTPUT_SIZE, (151, 134, 88, 0))
    RELIEF.putalpha(edges.point(lambda p: int(p * .11)))


def background(frame):
    out_w, out_h = OUTPUT_SIZE
    zoom = 1.0 + .018 * frame / OPENING_FRAMES
    size = (round(out_w * zoom), round(out_h * zoom))
    terrain = TERRAIN.resize(size, Image.Resampling.LANCZOS)
    left, top = (terrain.width - out_w) // 2, (terrain.height - out_h) // 2
    image = terrain.crop((left, top, left + out_w, top + out_h)).convert('RGBA')
    relief = RELIEF.resize(size, Image.Resampling.LANCZOS).crop((left, top, left + out_w, top + out_h))
    image = Image.alpha_composite(image, relief)
    yy, xx = np.mgrid[0:out_h, 0:out_w]
    distance = np.sqrt(((xx - out_w / 2) / (out_w * .70)) ** 2 + ((yy - out_h * .47) / (out_h * .82)) ** 2)
    shade = np.clip(distance * .72, 0, .82)
    a = np.asarray(image.convert('RGB'), dtype=np.float32)
    a *= (1 - shade[..., None])
    a += np.array([3, 5, 3], dtype=np.float32)
    rng = np.random.default_rng(31000 + frame)
    a += rng.normal(0, .34, (out_h, out_w, 1))
    return Image.fromarray(np.uint8(np.clip(a, 0, 255))).convert('RGBA')


def compose_title(frame, path):
    image = background(frame)
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    out_alpha = ca.smooth((OPENING_FRAMES - frame) / 18)
    in_alpha = ca.smooth(frame / 16)
    furniture_alpha = int(190 * in_alpha * out_alpha)
    d.rectangle((26, 22, 1253, 696), outline=(152, 133, 82, int(furniture_alpha * .52)), width=1)
    for x, y, sx, sy in [(26, 22, 1, 1), (1253, 22, -1, 1), (26, 696, 1, -1), (1253, 696, -1, -1)]:
        d.line((x, y, x + sx * 18, y), fill=ca.GOLD + (furniture_alpha,), width=1)
        d.line((x, y, x, y + sy * 18), fill=ca.GOLD + (furniture_alpha,), width=1)
    grid_alpha = int(28 * in_alpha * out_alpha)
    for x in (160, 1120):
        d.line((x, 102, x, 614), fill=ca.GOLD + (grid_alpha,), width=1)
    for y in (112, 610):
        d.line((160, y, 1120, y), fill=ca.GOLD + (grid_alpha,), width=1)
    ca.tracked_text(d, (54, 48), '行迹档案  ·  001', ca.F['micro'], 2,
                    ca.MUTED, int(175 * in_alpha * out_alpha))
    ca.tracked_text(d, (1225, 48), '真实地形  ·  生平编年', ca.F['micro'], 2,
                    ca.MUTED, int(175 * in_alpha * out_alpha), 'ra')

    seal_alpha = int(232 * ca.smooth((frame - 3) / 13) * out_alpha)
    d.rectangle((625, 157, 655, 190), fill=ca.RED + (int(seal_alpha * .82),),
                outline=(179, 91, 61, seal_alpha), width=1)
    d.rectangle((628, 160, 652, 187), outline=(218, 153, 112, int(seal_alpha * .52)), width=1)
    seal_font = ImageFont.truetype(ca.CALLI, 22)
    ca.text(d, (640, 174), '苏', seal_font, ca.PAPER, seal_alpha, 'mm')
    eyebrow_alpha = int(205 * ca.smooth((frame - 9) / 14) * out_alpha)
    ca.tracked_text(d, (640, 215), '北宋人物行迹', ca.F['small'], 6, ca.MUTED, eyebrow_alpha, 'mm')

    title = '此心安处'
    tracking = 20
    widths = [d.textlength(char, font=TITLE_FONT) for char in title]
    total = sum(widths) + tracking * (len(title) - 1)
    x = (W - total) / 2
    for i, (char, width) in enumerate(zip(title, widths)):
        progress = ca.smooth((frame - (10 + i * 5)) / 15)
        alpha = int(255 * progress * out_alpha)
        ca.text(d, (x, 269 + 5 * (1 - progress)), char, TITLE_FONT, ca.PAPER, alpha, 'la', 1)
        x += width + tracking

    sub_alpha = ca.smooth((frame - 29) / 15) * out_alpha
    line_width = 192 * sub_alpha
    d.line((640 - line_width, 390, 640 + line_width, 390),
           fill=ca.GOLD + (int(135 * sub_alpha),), width=1)
    for direction in (-1, 1):
        x = 640 + direction * line_width
        d.ellipse((x - 1.5, 388.5, x + 1.5, 391.5), fill=ca.GOLD + (int(170 * sub_alpha),))
    ca.tracked_text(d, (640, 417), '苏轼的人生地图', SUBTITLE_FONT, 6,
                    ca.GOLD, int(240 * sub_alpha), 'mm')
    ca.tracked_text(d, (640, 461), '1037 — 1101', YEAR_FONT, 3,
                    ca.MUTED, int(190 * sub_alpha), 'mm')
    ca.tracked_text(d, (640, 596), '一生行迹  ·  山河为证', ca.F['micro'], 4,
                    ca.MUTED, int(130 * ca.smooth((frame - 38) / 16) * out_alpha), 'mm')
    if layer.size != image.size:
        layer = layer.resize(image.size, Image.Resampling.LANCZOS)
    result = Image.alpha_composite(image, layer).convert('RGB')
    result.save(path, quality=96, subsampling=0)


def main():
    global OUTPUT_SIZE
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--proof', action='store_true')
    parser.add_argument('--terrain', required=True)
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    parser.add_argument('--out-dir', default='opening-v3/title-v2')
    args = parser.parse_args()
    OUTPUT_SIZE = (args.width, args.height)
    root = Path(args.root)
    prepare_terrain(args.terrain)
    if args.proof:
        out = root / args.out_dir
        out.mkdir(parents=True, exist_ok=True)
        for frame in [1, 18, 36, 54, 66, 72]:
            compose_title(frame, out / f'frame-{frame:04d}.jpg')
        return
    out = root / args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    for frame in range(1, OPENING_FRAMES + 1):
        compose_title(frame, out / f'frame-{frame:04d}.jpg')
    print(f'REFINED COLD OPEN COMPLETE: {OPENING_FRAMES} frames', flush=True)


if __name__ == '__main__':
    main()
