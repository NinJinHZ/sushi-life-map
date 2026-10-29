import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

import landmark_icons

W, H = 1280, 720
SONG = '/System/Library/Fonts/Supplemental/Songti.ttc'
CALLI = str(Path(__file__).resolve().parent.parent / 'sushi-terrain-test.ynv3ob' / 'opening-v2' / 'fonts' / 'MaShanZheng-Regular.ttf')
LATIN = '/System/Library/Fonts/Helvetica.ttc'
PAPER = (224, 215, 190)
GOLD = (185, 155, 94)
MUTED = (151, 146, 124)
RED = (126, 49, 36)
F = {
    'brand': ImageFont.truetype(SONG, 18),
    'micro': ImageFont.truetype(SONG, 10),
    'small': ImageFont.truetype(SONG, 12),
    'body': ImageFont.truetype(SONG, 14),
    'label': ImageFont.truetype(SONG, 17),
    'card_title': ImageFont.truetype(SONG, 31),
    'card_sub': ImageFont.truetype(SONG, 14),
    'title': ImageFont.truetype(CALLI, 58),
    'year': ImageFont.truetype(LATIN, 40),
    'index': ImageFont.truetype(LATIN, 23),
}

TIMELINE_TICKS = (
    (1037, '1037'), (1056.5, '1056–57'), (1061, '1061'),
    (1071, '1071'), (1079.5, '1079–80'), (1089, '1089'),
    (1094, '1094'), (1097, '1097'), (1101, '1101'),
)


def clamp(v):
    return max(0.0, min(1.0, v))


def smooth(v):
    v = clamp(v)
    return v * v * (3 - 2 * v)


def visibility(frame, start, end, edge=14):
    return smooth((frame - start) / edge) * smooth((end - frame) / edge)


def text(draw, xy, value, font, fill=PAPER, alpha=255, anchor='la', stroke=0):
    if alpha <= 0:
        return
    draw.text(xy, value, font=font, fill=fill + (int(alpha),), anchor=anchor,
              stroke_width=stroke, stroke_fill=(7, 9, 7, int(alpha * .8)))


def tracked_text(draw, xy, value, font, tracking, fill, alpha=255, anchor='la', stroke=0):
    widths = [draw.textlength(c, font=font) for c in value]
    total = sum(widths) + tracking * (len(value) - 1)
    x, y = xy
    if anchor == 'mm':
        x -= total / 2
    elif anchor == 'ra':
        x -= total
    for c, width in zip(value, widths):
        text(draw, (x, y), c, font, fill, alpha, stroke=stroke)
        x += width + tracking


def grade_map(raw, frame):
    raw = ImageEnhance.Brightness(raw.convert('RGB')).enhance(1.20)
    raw = ImageEnhance.Color(raw).enhance(.62)
    a = np.asarray(raw).astype(np.float32)
    a[..., 0] = a[..., 0] * 1.10 + 5
    a[..., 1] = a[..., 1] * 1.05 + 4
    a[..., 2] = a[..., 2] * .88 + 3
    rng = np.random.default_rng(8000 + frame)
    a += rng.normal(0, .65, (raw.height, raw.width, 1))
    graded = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
    radius = .8 if raw.width <= 1280 else 1.0
    return graded.filter(ImageFilter.UnsharpMask(radius=radius, percent=45, threshold=3)).convert('RGBA')


def portrait(path, size, centering=(.5, .24)):
    source = Image.open(path).convert('L')
    source = ImageOps.autocontrast(source, cutoff=1)
    source = ImageOps.fit(source, size, Image.Resampling.LANCZOS, centering=centering)
    toned = ImageOps.colorize(source, (29, 27, 20), (190, 177, 143))
    toned = ImageEnhance.Contrast(toned).enhance(1.08)
    return toned


def paste_card_image(panel, path, box, centering=(.5, .24)):
    x, y, w, h = box
    image = portrait(path, (w, h), centering)
    panel.paste(image, (x, y))
    d = ImageDraw.Draw(panel)
    d.rectangle((x, y, x + w - 1, y + h - 1), outline=(133, 117, 76, 130), width=1)
    shade = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for i in range(28):
        a = int(65 * (i / 28) ** 2)
        sd.line((0, h - 1 - i, w, h - 1 - i), fill=(9, 10, 7, a))
    panel.alpha_composite(shade, (x, y))


def family_triptych(panel, archives, box):
    x, y, w, h = box
    gap = 7
    cell = (w - gap * 2) // 3
    items = [('su-xun.jpg', '苏洵 · 父'), ('su-shi.jpg', '苏轼 · 兄'), ('su-zhe.jpg', '苏辙 · 弟')]
    d = ImageDraw.Draw(panel)
    for i, (filename, caption) in enumerate(items):
        xx = x + i * (cell + gap)
        paste_card_image(panel, archives / filename, (xx, y, cell, h - 25), (.5, .2))
        text(d, (xx + cell / 2, y + h - 13), caption, F['micro'], PAPER, 220, 'mm')


def make_card(root, kind):
    panel = Image.new('RGBA', (330, 548), (9, 11, 8, 242))
    d = ImageDraw.Draw(panel)
    d.rectangle((0, 0, 329, 547), outline=(139, 121, 73, 125), width=1)
    d.line((22, 23, 66, 23), fill=GOLD + (220,), width=2)
    configs = {
        'birth': ('人物档案 · 001', '苏轼出生', '北宋 · 景祐三年',
                  ['苏轼生于眉州眉山。', '父苏洵，母程氏。', '两年后，弟弟苏辙出生。', '兄弟二人，自此相伴成长。']),
        'brother': ('人物档案 · 002', '苏辙出生', '北宋 · 宝元二年',
                    ['弟弟苏辙出生。', '苏轼与苏辙，兄弟相携，', '此后同出蜀、同登第，', '也共同经历仕途浮沉。']),
        'journey': ('人物档案 · 002', '三苏出蜀', '北宋 · 嘉祐元年',
                    ['苏洵携苏轼、苏辙离蜀，', '自眉山启程，赴东京汴京。',
                     '地图略去沿途停驻。', '父子三人，走向更广阔的天地。']),
    }
    eyebrow, title, subtitle, lines = configs[kind]
    text(d, (78, 18), eyebrow, F['micro'], MUTED, 230)
    if kind == 'journey':
        family_triptych(panel, root / 'opening-v2' / 'archives', (22, 52, 286, 207))
    else:
        filename = 'su-shi.jpg' if kind == 'birth' else 'su-zhe.jpg'
        paste_card_image(panel, root / 'opening-v2' / 'archives' / filename, (22, 52, 286, 182),
                         (.5, .24 if kind == 'birth' else .48))
    title_y = 278 if kind == 'journey' else 253
    text(d, (23, title_y), title, F['card_title'], PAPER, 255)
    text(d, (24, title_y + 51), subtitle, F['card_sub'], GOLD, 245)
    d.line((24, title_y + 82, 306, title_y + 82), fill=(135, 119, 77, 110), width=1)
    for i, line in enumerate(lines):
        text(d, (24, title_y + 105 + i * 26), line, F['body'], PAPER, 220)
    footer = '眉山苏氏 · 人物像为后世历史画像'
    text(d, (24, 518), footer, F['micro'], MUTED, 170)
    return panel


def add_frame_furniture(overlay, frame):
    d = ImageDraw.Draw(overlay)
    # Restrained archival frame and corner registration marks.
    d.rectangle((26, 22, 1253, 696), outline=(152, 133, 82, 80), width=1)
    for x, y, sx, sy in [(26, 22, 1, 1), (1253, 22, -1, 1), (26, 696, 1, -1), (1253, 696, -1, -1)]:
        d.line((x, y, x + sx * 14, y), fill=GOLD + (170,), width=1)
        d.line((x, y, x, y + sy * 14), fill=GOLD + (170,), width=1)
    d.rectangle((42, 37, 64, 63), fill=RED + (235,))
    text(d, (53, 50), '苏', F['small'], PAPER, 255, 'mm')
    tracked_text(d, (76, 34), '苏轼行迹图', F['brand'], 3, PAPER, 245)
    tracked_text(d, (77, 58), 'SU SHI  ·  1037—1101', F['micro'], 1, MUTED, 210)

    if frame < 108:
        index, place = '01', '眉州眉山'
    elif frame < 264:
        index, place = '02', '出蜀之路'
    else:
        index, place = '02', '三苏出蜀'
    text(d, (1219, 33), index, F['index'], PAPER, 240, 'ra')
    text(d, (1219, 62), place, F['small'], GOLD, 220, 'ra')

    if frame < 60:
        year, era, event = '1037', '北宋 · 景祐三年', '苏轼出生'
    elif frame < 108:
        year, era, event = '1039', '北宋 · 宝元二年', '苏辙出生'
    else:
        year, era, event = '1056', '北宋 · 嘉祐元年', '三苏出蜀'
    text(d, (42, 598), era, F['small'], GOLD, 230)
    text(d, (40, 616), year, F['year'], PAPER, 250)
    text(d, (143, 646), '年', F['small'], MUTED, 220)
    text(d, (42, 664), event, F['small'], PAPER, 225)

    y = 684
    d.line((224, y, 1218, y), fill=(171, 149, 91, 115), width=1)
    for year_value, label in TIMELINE_TICKS:
        x = 224 + (year_value - 1037) / 64 * 994
        d.line((x, y - 4, x, y + 4), fill=GOLD + (160,), width=1)
        text(d, (x, y - 9), label, F['micro'], MUTED, 180, 'ms')
    current = 1037 if frame < 60 else 1039 if frame < 108 else 1056
    x = 224 + (current - 1037) / 64 * 994
    d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=PAPER + (240,))


def add_map_labels(overlay, projection, frame, draw_head=True):
    d = ImageDraw.Draw(overlay)
    data = projection['frames'][str(frame)]
    offsets = {'眉山': (15, 12), '汴京': (16, 12), '成都': (-14, -48),
               '剑门关': (-14, -48), '广元': (14, 12), '汉中': (14, -48)}
    for name, (x, y, z) in data['labels'].items():
        arrival = projection['arrivals'][name]
        if frame < arrival - 3 or z < 0 or not (30 < x < 1245 and 70 < y < 650):
            continue
        a = int(235 * smooth((frame - arrival + 3) / 12))
        landmark_icons.draw_landmark(d, x, y, name, alpha=int(a * .78), scale=.78)
        dx, dy = offsets.get(name, (15, 12))
        anchor = 'ra' if dx < 0 else 'la'
        if name == '眉山':
            bbox = d.textbbox((x + dx, y + dy), name, font=F['label'], anchor=anchor)
            d.rectangle((bbox[0] - 7, bbox[1] - 4, bbox[2] + 7, bbox[3] + 4), fill=RED + (int(a * .88),))
            text(d, (x + dx, y + dy), name, F['label'], PAPER, a, anchor)
        else:
            text(d, (x + dx, y + dy), name, F['label'], PAPER, a, anchor, 1)
    hx, hy, hz = data['head']
    if draw_head and hz > 0 and 25 < hx < 1250 and 65 < hy < 660:
        halo = Image.new('RGBA', overlay.size, (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        hd.ellipse((hx - 7, hy - 7, hx + 7, hy + 7), fill=(231, 199, 128, 64))
        overlay.alpha_composite(halo.filter(ImageFilter.GaussianBlur(4.5)))
        d = ImageDraw.Draw(overlay)
        d.ellipse((hx - 4.8, hy - 4.8, hx + 4.8, hy + 4.8), outline=GOLD + (88,), width=1)
        d.line((hx - 7, hy, hx - 3.5, hy), fill=PAPER + (90,), width=1)
        d.line((hx + 3.5, hy, hx + 7, hy), fill=PAPER + (90,), width=1)
        d.line((hx, hy - 7, hx, hy - 3.5), fill=PAPER + (90,), width=1)
        d.line((hx, hy + 3.5, hx, hy + 7), fill=PAPER + (90,), width=1)
        d.ellipse((hx - 2, hy - 2, hx + 2, hy + 2), fill=(247, 230, 187, 250))
        d.ellipse((hx - .65, hy - .65, hx + .65, hy + .65), fill=(255, 250, 226, 255))


def compose(root, projection, cards, frame, raw_path, out_path):
    raw = grade_map(Image.open(raw_path), frame)
    shade = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for i in range(120):
        a = int(105 * (1 - i / 120) ** 1.8)
        sd.line((0, i, W, i), fill=(3, 5, 3, a))
        sd.line((0, H - 1 - i, W, H - 1 - i), fill=(3, 5, 3, a))
    for i in range(75):
        a = int(70 * (1 - i / 75))
        sd.rectangle((i, i, W - 1 - i, H - 1 - i), outline=(2, 4, 2, a))
    raw = Image.alpha_composite(raw, shade)

    map_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    add_map_labels(map_layer, projection, frame)
    raw = Image.alpha_composite(raw, map_layer)

    ui = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    add_frame_furniture(ui, frame)

    title_alpha = visibility(frame, 1, 43, 16)
    if title_alpha > 0:
        d = ImageDraw.Draw(ui)
        tracked_text(d, (426, 281), '此心安处', F['title'], 12, PAPER, int(255 * title_alpha), 'mm')
        tracked_text(d, (426, 361), '苏轼的人生地图', F['small'], 5, GOLD, int(235 * title_alpha), 'mm')
        d.line((344, 394, 508, 394), fill=GOLD + (int(110 * title_alpha),), width=1)

    card_alpha = visibility(frame, 25, 288, 18)
    if card_alpha > 0:
        if frame < 60:
            kind = 'birth'
        elif frame < 108:
            kind = 'brother'
        else:
            kind = 'journey'
        card = cards[kind]
        # A fixed card with brief, clean content dissolves; no sliding widgets or bouncing type.
        if 48 < frame < 60:
            mix = smooth((frame - 48) / 12)
            layer = Image.new('RGBA', card.size, (0, 0, 0, 0))
            layer = Image.alpha_composite(layer, Image.blend(Image.new('RGBA', card.size), cards['birth'], 1 - mix))
            layer = Image.alpha_composite(layer, Image.blend(Image.new('RGBA', card.size), cards['brother'], mix))
            card = layer
        elif 96 < frame < 108:
            mix = smooth((frame - 96) / 12)
            layer = Image.new('RGBA', card.size, (0, 0, 0, 0))
            layer = Image.alpha_composite(layer, Image.blend(Image.new('RGBA', card.size), cards['brother'], 1 - mix))
            layer = Image.alpha_composite(layer, Image.blend(Image.new('RGBA', card.size), cards['journey'], mix))
            card = layer
        if card_alpha < 1:
            card = card.copy()
            card.putalpha(card.getchannel('A').point(lambda p: int(p * card_alpha)))
        ui.alpha_composite(card, (899, 74))
    result = Image.alpha_composite(raw, ui).convert('RGB')
    result.save(out_path, quality=95, subsampling=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--proof', action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    projection = json.loads((root / 'opening-v2' / 'projection.json').read_text())
    cards = {name: make_card(root, name) for name in ('birth', 'brother', 'journey')}
    if args.proof:
        out = root / 'opening-v2' / 'archive-proofs'
        out.mkdir(exist_ok=True)
        frames = [24, 48, 84, 156, 240, 288]
        for frame in frames:
            compose(root, projection, cards, frame,
                    root / 'opening-v2' / 'raw' / f'frame-{frame:04d}.png',
                    out / f'archive-{frame:04d}.jpg')
        sheet = Image.new('RGB', (1280, 720 * len(frames)), (8, 9, 7))
        for i, frame in enumerate(frames):
            sheet.paste(Image.open(out / f'archive-{frame:04d}.jpg'), (0, i * 720))
        sheet.save(out / 'contact-sheet.jpg', quality=92)
    else:
        out = root / 'opening-v2' / 'archive-final'
        out.mkdir(exist_ok=True)
        for frame in range(1, 289):
            compose(root, projection, cards, frame,
                    root / 'opening-v2' / 'raw' / f'frame-{frame:04d}.png',
                    out / f'frame-{frame:04d}.jpg')
            if frame % 48 == 0:
                print(f'ARCHIVAL COMPOSITED {frame}/288', flush=True)


if __name__ == '__main__':
    main()
