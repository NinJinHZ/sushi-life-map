import argparse
import json
import math
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose_archival as ca
import landmark_icons

W, H = 1280, 720
QUOTE_FONT = ImageFont.truetype(ca.CALLI, 42)
OFFSETS = {
    '眉山': (14, 12), '成都': (-14, -28), '剑门关': (-14, -30),
    '广元': (14, 12), '汉中': (-14, -28), '长安': (-14, 12),
    '洛阳': (14, -28), '汴京': (14, -28), '凤翔': (-14, -28),
    '杭州': (14, 12), '密州': (14, -28), '徐州': (-14, 12),
    '湖州': (14, -28), '黄州': (-14, 12), '汝州': (-14, -28),
    '登州': (14, -28), '颍州': (-14, 12), '扬州': (14, 12),
    '定州': (14, -28), '惠州': (14, 12), '雷州': (-14, 12),
    '儋州': (14, 12), '赣州': (-14, 12), '金陵': (-14, -28),
    '常州': (14, -28),
}
FINAL_SITES = ['眉山', '凤翔', '汴京', '登州', '密州', '徐州', '黄州',
               '杭州', '定州', '惠州', '儋州', '常州']
CN_NUM = '〇一二三四五六七八九'


def chinese_num(number):
    if number == 1:
        return '元'
    digits = ''
    if number >= 10:
        digits += '十' if number < 20 else CN_NUM[number // 10] + '十'
        if number % 10:
            digits += CN_NUM[number % 10]
    else:
        digits = CN_NUM[number]
    return digits


def era(year):
    if year < 1056:
        return '北宋'
    if year <= 1063:
        return f'北宋 · 嘉祐{chinese_num(year - 1055)}年'
    if year <= 1067:
        return f'北宋 · 治平{chinese_num(year - 1063)}年'
    if year <= 1077:
        return f'北宋 · 熙宁{chinese_num(year - 1067)}年'
    if year <= 1085:
        return f'北宋 · 元丰{chinese_num(year - 1077)}年'
    if year <= 1093:
        return f'北宋 · 元祐{chinese_num(year - 1085)}年'
    if year <= 1097:
        return f'北宋 · 绍圣{chinese_num(year - 1093)}年'
    if year <= 1100:
        return f'北宋 · 元符{chinese_num(year - 1097)}年'
    return '北宋 · 建中靖国元年'


ERA_FONT = ImageFont.truetype(ca.SONG, 32)
FINAL_CREDITS = []


def make_card(chapter, quote=False, asset_path=None):
    panel = Image.new('RGBA', (330, 548), (9, 11, 8, 242))
    d = ImageDraw.Draw(panel)
    d.rectangle((0, 0, 329, 547), outline=(139, 121, 73, 125), width=1)
    d.line((22, 23, 66, 23), fill=ca.GOLD + (220,), width=2)
    if quote and chapter.get('quote'):
        item = chapter['quote']
        ca.text(d, (78, 18), '作品摘句 · 人生行迹', ca.F['micro'], ca.MUTED, 230)
        ca.text(d, (23, 55), item['title'], ca.F['small'], ca.GOLD, 245)
        d.line((24, 94, 306, 94), fill=(135, 119, 77, 110), width=1)
        font = ImageFont.truetype(ca.SONG, 23)
        for i, line in enumerate(item['lines']):
            ca.text(d, (24, 166 + i * 58), line, font, ca.PAPER, 245)
        d.line((24, 318, 86, 318), fill=ca.GOLD + (150,), width=1)
        ca.text(d, (24, 342), item['source'], ca.F['card_sub'], ca.MUTED, 220)
    else:
        item = chapter['card']
        ca.text(d, (78, 18), item['eyebrow'], ca.F['micro'], ca.MUTED, 230)
        ca.text(d, (23, 55), chapter['title'], ca.F['card_title'], ca.PAPER, 255)
        ca.text(d, (24, 106), item['subtitle'], ca.F['card_sub'], ca.GOLD, 245)
        d.line((24, 145, 306, 145), fill=(135, 119, 77, 110), width=1)
        if asset_path:
            ca.paste_card_image(panel, asset_path, (23, 158, 284, 132), (.5, .5))
            ca.text(d, (25, 299), chapter.get('asset_caption', '今日实景 · 非北宋原貌'),
                    ca.F['micro'], ca.MUTED, 210)
            for i, line in enumerate(item['lines']):
                ca.text(d, (24, 326 + i * 28), line, ca.F['body'], ca.PAPER, 225)
        else:
            for i, line in enumerate(item['lines']):
                ca.text(d, (24, 176 + i * 34), line, ca.F['body'], ca.PAPER, 225)
            destination = chapter['waypoints'][-1]
            ca.text(d, (24, 363), '行迹坐标', ca.F['micro'], ca.GOLD, 190)
            ca.text(d, (24, 387), destination, ca.F['card_sub'], ca.PAPER, 225)
    destination = chapter['waypoints'][-1]
    # Coordinates are supplied by the compositor, which owns the site table.
    lon, lat = chapter['_coordinates']
    ca.text(d, (24, 451), f'东经 {lon:.3f}°  ·  北纬 {lat:.3f}°', ca.F['micro'], ca.MUTED, 185)
    ca.text(d, (24, 518), '宋代地名 · 今大致地理位置', ca.F['micro'], ca.MUTED, 170)
    return panel


def add_furniture(layer, chapter, year, opacity=1.0):
    d = ImageDraw.Draw(layer)
    alpha = lambda value: int(value * opacity)
    d.rectangle((26, 22, 1253, 696), outline=(152, 133, 82, alpha(80)), width=1)
    for x, y, sx, sy in [(26, 22, 1, 1), (1253, 22, -1, 1), (26, 696, 1, -1), (1253, 696, -1, -1)]:
        d.line((x, y, x + sx * 14, y), fill=ca.GOLD + (alpha(170),), width=1)
        d.line((x, y, x, y + sy * 14), fill=ca.GOLD + (alpha(170),), width=1)
    d.rectangle((42, 37, 64, 63), fill=ca.RED + (alpha(235),))
    ca.text(d, (53, 50), '苏', ca.F['small'], ca.PAPER, alpha(255), 'mm')
    ca.tracked_text(d, (76, 34), '苏轼行迹图', ca.F['brand'], 3, ca.PAPER, alpha(245))
    ca.tracked_text(d, (77, 58), 'SU SHI  ·  NORTHERN SONG', ca.F['micro'], 1, ca.MUTED, alpha(210))
    ca.text(d, (1219, 33), chapter['index'], ca.F['index'], ca.PAPER, alpha(240), 'ra')
    ca.text(d, (1219, 62), chapter['place'], ca.F['small'], ca.GOLD, alpha(220), 'ra')
    ca.text(d, (42, 598), era(year), ca.F['small'], ca.GOLD, alpha(230))
    ca.text(d, (40, 616), str(year), ca.F['year'], ca.PAPER, alpha(250))
    ca.text(d, (143, 646), '年', ca.F['small'], ca.MUTED, alpha(220))
    ca.text(d, (42, 664), chapter['title'], ca.F['small'], ca.PAPER, alpha(225))
    y = 684
    d.line((224, y, 1218, y), fill=(171, 149, 91, alpha(115)), width=1)
    for year_value, tick_label in ca.TIMELINE_TICKS:
        x = 224 + (year_value - 1037) / 64 * 994
        d.line((x, y - 4, x, y + 4), fill=ca.GOLD + (alpha(160),), width=1)
        ca.text(d, (x, y - 9), tick_label, ca.F['micro'], ca.MUTED, alpha(180), 'ms')
    x = 224 + (max(1037, min(1101, year)) - 1037) / 64 * 994
    d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=ca.PAPER + (alpha(240),))


def intersects(a, b):
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def add_sites_and_traveler(layer, projection, frame, chapter, final_alpha, card_visible):
    data = projection['frames'][str(frame)]
    arrivals = projection['arrivals']
    d = ImageDraw.Draw(layer)
    visible = {}
    for name, (x, y, z) in data['labels'].items():
        if name not in arrivals or frame < arrivals[name] or z <= 0:
            continue
        max_y = 650 if final_alpha > .01 else 585
        if not (30 < x < 1245 and 70 < y < max_y):
            continue
        visible[name] = (x, y)
        if final_alpha > .01 and name not in FINAL_SITES:
            continue
    names = [name for name in FINAL_SITES if name in visible] if final_alpha > .01 else []
    if final_alpha <= .01:
        current = data['current']
        names = [current] if current in visible else []
        names += sorted((name for name in visible if name not in names),
                        key=lambda name: arrivals[name], reverse=True)
    occupied = [(892, 68, 1236, 628)] if card_visible else []
    for name, (x, y) in visible.items():
        if final_alpha > .01 and name not in FINAL_SITES:
            continue
        age = frame - arrivals[name]
        alpha = int((190 if final_alpha > .01 else 145) * ca.smooth((age + 3) / 12))
        icon_scale = .66 if final_alpha > .01 else .78
        landmark_icons.draw_landmark(d, x, y, name, alpha=alpha, scale=icon_scale)
        occupied.append((x - 16 * icon_scale, y - 42 * icon_scale,
                         x + 16 * icon_scale, y + 3))
    label_font = ImageFont.truetype(ca.SONG, 16 if final_alpha > .01 else 17)
    for name in names:
        x, y = visible[name]
        base = OFFSETS.get(name, (14, -48))
        if base[1] < 0:
            base = (base[0], -52)
        choices = [base, (14, -52), (-14, 12), (14, 12), (-14, -52)]
        for dx, dy in choices:
            anchor = 'ra' if dx < 0 else 'la'
            bbox = d.textbbox((x + dx, y + dy), name, font=label_font, anchor=anchor, stroke_width=1)
            padded = (bbox[0] - 3, bbox[1] - 2, bbox[2] + 3, bbox[3] + 2)
            if padded[0] < 32 or padded[2] > 1248 or padded[1] < 72 or padded[3] > 650:
                continue
            if any(intersects(padded, other) for other in occupied):
                continue
            alpha = int(235 * max(final_alpha, .72))
            ca.text(d, (x + dx, y + dy), name, label_font, ca.PAPER, alpha, anchor, 1)
            occupied.append(padded)
            break

    # The tail is projected from the current terrain path, not from old screen
    # positions, so it remains visible while the camera follows the traveler.
    if data['moving']:
        recent = [tuple(item[:2]) for item in data.get('trail', []) if item[2] > 0]
        points = []
        if recent:
            points = [recent[-1]]
            length = 0.0
            for older in reversed(recent[:-1]):
                newer = points[-1]
                dx, dy = older[0] - newer[0], older[1] - newer[1]
                distance = math.hypot(dx, dy)
                if length + distance > 150:
                    ratio = (150 - length) / distance if distance else 0
                    points.append((newer[0] + dx * ratio, newer[1] + dy * ratio))
                    break
                points.append(older)
                length += distance
            points.reverse()
        if len(points) > 1:
            streak = Image.new('RGBA', layer.size, (0, 0, 0, 0))
            sd = ImageDraw.Draw(streak)
            for i in range(len(points) - 1):
                strength = (i + 1) / (len(points) - 1)
                sd.line((points[i], points[i + 1]),
                        fill=(228, 202, 146, int(12 + 82 * strength ** 1.7)),
                        width=2 if strength > .72 else 1)
            glow = streak.filter(ImageFilter.GaussianBlur(4))
            glow.putalpha(glow.getchannel('A').point(lambda p: int(p * .35)))
            layer.alpha_composite(glow)
            layer.alpha_composite(streak)
    hx, hy, hz = data['head']
    if hz > 0 and 25 < hx < 1250 and 65 < hy < 660:
        pulse = .5 + .5 * math.sin(frame * math.pi / 18)
        halo = Image.new('RGBA', layer.size, (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        hd.ellipse((hx - 8, hy - 8, hx + 8, hy + 8), fill=(231, 199, 128, 72))
        halo = halo.filter(ImageFilter.GaussianBlur(5.5))
        layer.alpha_composite(halo)
        d = ImageDraw.Draw(layer)
        d.ellipse((hx - 5.4, hy - 5.4, hx + 5.4, hy + 5.4),
                  outline=ca.GOLD + (int(70 + 24 * pulse),), width=1)
        cross_alpha = int(82 + 30 * pulse)
        d.line((hx - 8, hy, hx - 3.8, hy), fill=ca.PAPER + (cross_alpha,), width=1)
        d.line((hx + 3.8, hy, hx + 8, hy), fill=ca.PAPER + (cross_alpha,), width=1)
        d.line((hx, hy - 8, hx, hy - 3.8), fill=ca.PAPER + (cross_alpha,), width=1)
        d.line((hx, hy + 3.8, hx, hy + 8), fill=ca.PAPER + (cross_alpha,), width=1)
        d.ellipse((hx - 2.2, hy - 2.2, hx + 2.2, hy + 2.2), fill=(247, 230, 187, 250))
        d.ellipse((hx - .7, hy - .7, hx + .7, hy + .7), fill=(255, 250, 226, 255))


def add_quote_calligraphy(layer, chapter, alpha, quote=None):
    quote = quote or chapter.get('quote')
    if not quote or alpha <= 0:
        return
    d = ImageDraw.Draw(layer)
    opacity = int(245 * alpha)
    text_width = max([d.textlength(line, font=QUOTE_FONT) for line in quote['lines']] +
                     [d.textlength(quote['title'], font=ca.F['small'])])
    right = min(700, max(500, 118 + text_width))
    backing = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(backing)
    bd.rounded_rectangle((46, 111, right, 362), radius=12,
                         fill=(5, 7, 5, int(118 * alpha)))
    backing = backing.filter(ImageFilter.GaussianBlur(15))
    layer.alpha_composite(backing)
    d = ImageDraw.Draw(layer)
    d.line((66, 142, 66, 320), fill=ca.GOLD + (int(115 * alpha),), width=1)
    ca.text(d, (90, 137), quote['title'], ca.F['small'], ca.GOLD,
            int(220 * alpha), 'la', 1)
    for index, line in enumerate(quote['lines']):
        ca.text(d, (88, 178 + index * 66), line, QUOTE_FONT, ca.PAPER,
                opacity, 'la', 2)
    ca.text(d, (91, 322), quote.get('source', ''), ca.F['micro'], ca.MUTED,
            int(200 * alpha), 'la', 1)


def add_exam_heroes(layer, chapter, hold_age):
    start = 8 * 24
    if chapter['id'] != 'bijing' or hold_age < start:
        return
    fade = ca.smooth((hold_age - start) / 18)
    fade *= ca.smooth((chapter['hold_frames'] - hold_age) / 18)
    if fade <= 0:
        return
    panel = Image.new('RGBA', (386, 372), (8, 10, 7, int(226 * fade)))
    d = ImageDraw.Draw(panel)
    border = int(128 * fade)
    d.rectangle((0, 0, 385, 371), outline=ca.GOLD + (border,), width=1)
    d.line((22, 24, 68, 24), fill=ca.GOLD + (int(220 * fade),), width=2)
    ca.text(d, (22, 43), '嘉祐二年 · 千年龙虎榜', ca.F['card_sub'], ca.GOLD,
            int(245 * fade))
    ca.text(d, (22, 72), '同榜群英与主考官', ca.F['micro'], ca.MUTED, int(205 * fade))
    people = [
        ('主考官', '欧阳修', '文坛宗师'),
        ('同榜进士', '苏　轼', '唐宋八大家'),
        ('', '苏　辙', '唐宋八大家'),
        ('', '曾　巩', '唐宋八大家'),
        ('', '张　载', '关学开创者'),
        ('', '程　颢', '理学奠基者'),
    ]
    name_font = ImageFont.truetype(ca.SONG, 21)
    for i, (group, name, note) in enumerate(people):
        reveal = ca.smooth((hold_age - start - 6 - i * 19) / 15)
        if reveal <= 0:
            continue
        y = 108 + i * 39
        x = 22 + 8 * (1 - reveal)
        alpha = int(235 * fade * reveal)
        if group:
            ca.text(d, (x, y + 4), group, ca.F['micro'], ca.MUTED, int(alpha * .82))
        ca.text(d, (x + 82, y), name, name_font, ca.PAPER, alpha)
        ca.text(d, (x + 188, y + 5), note, ca.F['small'], ca.GOLD, int(alpha * .88))
        d.line((x + 82, y + 31, x + 330 * reveal, y + 31),
               fill=ca.GOLD + (int(38 * fade * reveal),), width=1)
    ca.text(d, (22, 349), '苏轼、苏辙、曾巩：同榜三位后来的“唐宋八大家”',
            ca.F['micro'], ca.MUTED, int(185 * fade))
    layer.alpha_composite(panel, (70, 145))


def add_final_credits(layer, frame, chapter, final_start, alpha):
    if not FINAL_CREDITS or alpha <= 0:
        return
    panel_box = (948, 462)
    panel = Image.new('RGBA', (280, 184), (7, 9, 6, int(194 * alpha)))
    d = ImageDraw.Draw(panel)
    d.rectangle((0, 0, 279, 183), outline=ca.GOLD + (int(90 * alpha),), width=1)
    ca.text(d, (16, 14), '资料与来源', ca.F['card_sub'], ca.GOLD, int(235 * alpha))
    ca.text(d, (257, 17), '滚动 credits', ca.F['micro'], ca.MUTED, int(150 * alpha), 'ra')
    d.line((16, 42, 264, 42), fill=ca.GOLD + (int(70 * alpha),), width=1)
    roll = Image.new('RGBA', panel.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(roll)
    line_height = 21
    total_height = len(FINAL_CREDITS) * line_height
    duration = max(1, chapter['end_frame'] - final_start)
    progress = max(0.0, min(1.0, (frame - final_start) / duration))
    y = 156 - progress * max(0, total_height - 11)
    for value, kind in FINAL_CREDITS:
        font = ca.F['small'] if kind == 'head' else ca.F['micro']
        color = ca.GOLD if kind == 'head' else ca.PAPER
        opacity = 220 if kind == 'head' else 185
        ca.text(rd, (16, y), value, font, color, int(opacity * alpha))
        y += line_height
    mask = Image.new('L', panel.size, 0)
    md = ImageDraw.Draw(mask)
    md.rectangle((0, 50, 279, 170), fill=255)
    roll.putalpha(Image.composite(roll.getchannel('A'), Image.new('L', panel.size, 0), mask))
    panel.alpha_composite(roll)
    layer.alpha_composite(panel, panel_box)


def compose(root, out, projection, cards, frame, raw_dir_name='raw'):
    chapter_index = next(i for i, item in enumerate(projection['chapters'])
                         if item['start_frame'] <= frame <= item['end_frame'])
    chapter = projection['chapters'][chapter_index]
    data = projection['frames'][str(frame)]
    raw_path = out / raw_dir_name / f'frame-{frame:04d}.png'
    raw = ca.grade_map(Image.open(raw_path), frame)
    output_size = raw.size
    shade = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for i in range(120):
        alpha = int(105 * (1 - i / 120) ** 1.8)
        sd.line((0, i, W, i), fill=(3, 5, 3, alpha))
        sd.line((0, H - 1 - i, W, H - 1 - i), fill=(3, 5, 3, alpha))
    for i in range(75):
        sd.rectangle((i, i, W - 1 - i, H - 1 - i), outline=(2, 4, 2, int(70 * (1 - i / 75))))
    if shade.size != output_size:
        shade = shade.resize(output_size, Image.Resampling.LANCZOS)
    raw = Image.alpha_composite(raw, shade)

    final_start = chapter['travel_end'] + round(chapter.get('final_title_after_s', 999) * 24)
    credits_start = chapter['travel_end'] + round(chapter.get('credits_after_s', 999) * 24)
    final_alpha = ca.smooth((frame - final_start) / 36) if frame >= final_start else 0
    hold_age = frame - chapter['travel_end']
    local = frame - chapter['start_frame'] + 1
    card_layers = []
    quote_layers = []
    if hold_age > 0 and final_alpha < 1:
        base_alpha = ca.smooth(hold_age / 18) * (1 - final_alpha)
        quote = chapter.get('quote')
        early_quote = chapter.get('early_quote')
        closing_quote = chapter.get('closing_quote')
        quote_start = round(quote['after_s'] * 24) if quote else 10 ** 9
        early_start = round(early_quote['after_s'] * 24) if early_quote else 10 ** 9
        closing_start = round(closing_quote['after_s'] * 24) if closing_quote else 10 ** 9
        first_quote_start = min(quote_start, early_start)
        if hold_age >= first_quote_start:
            mix = ca.smooth((hold_age - first_quote_start) / 18)
            if mix < 1:
                card_layers.append(('event', base_alpha * (1 - mix)))
        else:
            card_layers.append(('event', base_alpha))
        if early_quote and hold_age >= early_start:
            early_alpha = base_alpha * ca.smooth((hold_age - early_start) / 18)
            if hold_age >= quote_start:
                early_alpha *= 1 - ca.smooth((hold_age - quote_start) / 18)
            if early_alpha > 0:
                quote_layers.append((chapter['id'], early_alpha, early_quote))
        if quote and hold_age >= quote_start:
            quote_alpha = base_alpha * ca.smooth((hold_age - quote_start) / 18)
            if closing_quote and hold_age >= closing_start:
                quote_alpha *= 1 - ca.smooth((hold_age - closing_start) / 18)
            if quote_alpha > 0:
                quote_layers.append((chapter['id'], quote_alpha, quote))
        if closing_quote and hold_age >= closing_start:
            mix = ca.smooth((hold_age - closing_start) / 18)
            quote_layers.append((chapter['id'], base_alpha * mix, closing_quote))
    elif local <= 18 and chapter_index > 0:
        previous = projection['chapters'][chapter_index - 1]
        previous_alpha = 1 - ca.smooth(local / 18)
        if previous.get('quote'):
            quote_layers.append((previous['id'], previous_alpha, previous['quote']))
        else:
            card_layers.append(('event', previous_alpha, previous['id']))
    card_visible = any(item[1] > .02 for item in card_layers)
    map_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    add_sites_and_traveler(map_layer, projection, frame, chapter, final_alpha, card_visible)
    if map_layer.size != output_size:
        map_layer = map_layer.resize(output_size, Image.Resampling.LANCZOS)
    raw = Image.alpha_composite(raw, map_layer)

    ui = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    display_year = quote_layers[-1][2].get('year', data['year']) if quote_layers else data['year']
    add_furniture(ui, chapter, display_year, 1 - final_alpha)
    for item in card_layers:
        kind, alpha = item[:2]
        owner = item[2] if len(item) > 2 else chapter['id']
        if alpha <= 0:
            continue
        card = cards[owner][kind].copy()
        card.putalpha(card.getchannel('A').point(lambda p: int(p * alpha)))
        ui.alpha_composite(card, (899, 74))
    for owner, alpha, quote_data in quote_layers:
        quote_chapter = next(item for item in projection['chapters'] if item['id'] == owner)
        add_quote_calligraphy(ui, quote_chapter, alpha, quote_data)
    if hold_age > 0:
        add_exam_heroes(ui, chapter, hold_age)
    if final_alpha > 0:
        title_backing = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        td = ImageDraw.Draw(title_backing)
        td.rounded_rectangle((142, 202, 498, 444), radius=18,
                             fill=(4, 6, 4, int(138 * final_alpha)))
        title_backing = title_backing.filter(ImageFilter.GaussianBlur(20))
        ui.alpha_composite(title_backing)
        fd = ImageDraw.Draw(ui)
        fd.rectangle((0, 0, W, H), fill=(4, 6, 4, int(52 * final_alpha)))
        ca.tracked_text(fd, (320, 258), '此心安处', ca.F['title'], 12,
                        ca.PAPER, int(255 * final_alpha), 'mm', 1)
        ca.tracked_text(fd, (320, 340), '苏轼的人生地图', ca.F['small'], 5,
                        ca.GOLD, int(245 * final_alpha), 'mm', 1)
        fd.line((238, 378, 402, 378), fill=ca.GOLD + (int(110 * final_alpha),), width=1)
        ca.text(fd, (320, 403), '1037—1101', ca.F['card_sub'], ca.MUTED,
                int(225 * final_alpha), 'mm', 1)
        ca.text(fd, (320, 586), '真实地形：现代 DEM 与卫星影像', ca.F['micro'],
                ca.MUTED, int(190 * final_alpha), 'mm')
        ca.text(fd, (320, 607), '行迹依宋代地名与大致地理位置绘制，非北宋河道及疆界复原',
                ca.F['micro'], ca.MUTED, int(190 * final_alpha), 'mm')
        add_final_credits(ui, frame, chapter, credits_start, final_alpha)
    if ui.size != output_size:
        ui = ui.resize(output_size, Image.Resampling.LANCZOS)
    return Image.alpha_composite(raw, ui).convert('RGB')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--projection-file', default='projection.json')
    parser.add_argument('--sources-name', default='事实与来源-V3.1.md')
    parser.add_argument('--proof', action='store_true')
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--end', type=int, default=0)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--follow', action='store_true')
    parser.add_argument('--raw-dir', default='raw')
    parser.add_argument('--composed-dir', default='composed')
    parser.add_argument('--proof-dir', default='proofs')
    parser.add_argument('--frames', type=int, nargs='+')
    args = parser.parse_args()
    root = Path(args.root)
    out = root / 'final-film'
    raw_dir_name = args.raw_dir
    projection = json.loads((out / args.projection_file).read_text())
    timeline = json.loads((out / 'timeline.json').read_text())
    sites = timeline['sites']
    asset_root = out / 'asset-downloads'
    asset_credits = json.loads((asset_root / 'credits.json').read_text()) if (asset_root / 'credits.json').exists() else []
    credits_by_id = {item['id']: item for item in asset_credits}
    cards = {}
    for chapter in projection['chapters']:
        chapter['_coordinates'] = sites[chapter['waypoints'][-1]]
        asset_path = asset_root / chapter['id'] / 'source.jpg'
        cards[chapter['id']] = {
            'event': make_card(chapter, asset_path=asset_path if asset_path.exists() else None),
            'quote': make_card(chapter, True),
        }
    FINAL_CREDITS.extend([
        ('地形与影像', 'head'),
        ('Mapzen Terrarium DEM · AWS Open Data', 'body'),
        ('Esri World Imagery 卫星影像', 'body'),
        ('Blender 真实三维地形与运镜', 'body'),
        ('史实、年表与作品', 'head'),
        ('《宋史》卷三三八《苏轼传》', 'body'),
        ('三苏祠博物馆 · 故宫博物院', 'body'),
        ('北京大学：嘉祐二年贡举相关研究', 'body'),
        ('司法部：乌台诗案与北宋监察制度', 'body'),
        ('江苏省地方志 · 中国日报：徐州黄楼', 'body'),
        ('实景图片 · Wikimedia Commons', 'head'),
    ])
    for chapter_id, place_name in (('hangzhou2', '杭州苏堤'), ('xuzhou', '徐州黄楼'),
                                   ('huangzhou', '黄州赤壁'), ('huizhou', '惠州纪念'),
                                   ('danzhou', '儋州书院')):
        credit = credits_by_id.get(chapter_id)
        if credit:
            label = f"{credit['creator']} · {credit['license']}"
            FINAL_CREDITS.append((f"{place_name}｜{label}"[:48], 'body'))
    FINAL_CREDITS.extend([
        ('历史画像与字体', 'head'),
        ('三苏画像：清宫殿藏本 · Public domain', 'body'),
        ('Ma Shan Zheng 书法字体 · SIL OFL 1.1', 'body'),
        ('声音与制作', 'head'),
        ('旁白：VoxCPM2 本地生成 · 非用户本人音色', 'body'),
        ('配乐与音效：原创程序合成', 'body'),
        ('Pillow · NumPy · FFmpeg', 'body'),
        (f'完整链接见《{args.sources_name}》', 'body'),
    ])
    if args.proof:
        proofs = out / args.proof_dir
        proofs.mkdir(exist_ok=True)
        sheet_items = []
        if args.frames:
            proof_frames = [(f'frame-{frame:04d}', frame) for frame in args.frames]
        else:
            proof_frames = []
            for chapter in projection['chapters']:
                proof_frames.extend([
                    (f"{chapter['id']}-travel", chapter['start_frame'] + chapter['travel_frames'] // 2),
                    (f"{chapter['id']}-hold", chapter['travel_end'] + max(1, chapter['hold_frames'] // 2)),
                ])
            proof_frames.append(('finale', projection['total_frames']))
        for label, frame in proof_frames:
            image = compose(root, out, projection, cards, frame, raw_dir_name)
            path = proofs / f'{label}.jpg'
            image.save(path, quality=95, subsampling=0)
            chapter = next(item for item in projection['chapters']
                           if item['start_frame'] <= frame <= item['end_frame'])
            sheet_items.append((f'{label} · {chapter["title"]}', image))
        cell_w, cell_h = 480, 306
        sheet = Image.new('RGB', (cell_w * 3, cell_h * math.ceil(len(sheet_items) / 3)), (7, 9, 6))
        sd = ImageDraw.Draw(sheet)
        for i, (label, image) in enumerate(sheet_items):
            x, y = (i % 3) * cell_w, (i // 3) * cell_h
            sheet.paste(image.resize((480, 270)), (x, y + 36))
            sd.text((x + 12, y + 8), label, font=ca.F['small'], fill=ca.PAPER)
        sheet.save(proofs / 'contact-sheet.jpg', quality=93, subsampling=0)
    else:
        composed = out / args.composed_dir
        composed.mkdir(exist_ok=True)
        last_frame = min(projection['total_frames'], args.end or projection['total_frames'])
        frame = max(1, args.start)
        while frame <= last_frame:
            target = composed / f'frame-{frame:04d}.jpg'
            if args.resume and target.exists():
                try:
                    with Image.open(target) as existing:
                        existing.verify()
                    frame += 1
                    continue
                except Exception:
                    pass
            raw_path = out / raw_dir_name / f'frame-{frame:04d}.png'
            if args.follow and not raw_path.exists():
                time.sleep(2)
                continue
            try:
                image = compose(root, out, projection, cards, frame, raw_dir_name)
            except (OSError, ValueError, SyntaxError):
                if not args.follow:
                    raise
                time.sleep(.5)
                continue
            temporary = composed / f'frame-{frame:04d}.writing.jpg'
            image.save(temporary, quality=94, subsampling=0)
            temporary.replace(target)
            frame += 1
            if (frame - 1) % 240 == 0:
                print(f'COMPOSED {frame - 1}/{projection["total_frames"]}', flush=True)
    print('FINAL MAP COMPOSITE COMPLETE', flush=True)


if __name__ == '__main__':
    main()
