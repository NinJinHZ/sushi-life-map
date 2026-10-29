import json
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose_archival as ca
import compose_archival_18s as body

FRAMES = [1, 18, 36, 52, 66, 96, 192, 240, 312, 396, 432]


def add_star_descent(layer, projection, frame):
    fall_end = projection.get('fall_end', 52)
    if not fall_end or frame > fall_end + 32:
        return
    frames = projection['frames']
    landing_x, landing_y, _ = frames[str(fall_end)]['head']

    def descent_point(value):
        t = max(0.0, min(1.0, (value - 1) / max(1, fall_end - 1)))
        eased = ca.smooth(t)
        x = landing_x - 112 * (1 - eased) + 25 * math.sin(math.pi * eased) * (1 - eased)
        y = landing_y - 334 * (1 - eased) ** 1.15
        return x, y

    # 文曲星是一种文学暗喻：一缕有纵深的微光穿过夜空，而非真实天象。
    # 余辉、细小星屑和落地涟漪都只在这段出现，落地后仍只有一个主光点。
    if frame <= fall_end:
        recent = []
        for past in range(max(1, frame - 17), frame + 1):
            recent.append(descent_point(past))
        points = []
        if recent:
            points = [recent[-1]]
            length = 0.0
            for older in reversed(recent[:-1]):
                newer = points[-1]
                dx, dy = older[0] - newer[0], older[1] - newer[1]
                distance = (dx * dx + dy * dy) ** .5
                if length + distance > 154:
                    ratio = (154 - length) / distance if distance else 0
                    points.append((newer[0] + dx * ratio, newer[1] + dy * ratio))
                    break
                points.append(older)
                length += distance
            points.reverse()
        birth = ca.smooth(frame / 11)
        if len(points) > 1:
            streak = Image.new('RGBA', layer.size, (0, 0, 0, 0))
            sd = ImageDraw.Draw(streak)
            for i in range(len(points) - 1):
                strength = (i + 1) / (len(points) - 1)
                alpha = int(birth * (5 + 105 * strength ** 2.1))
                sd.line((points[i], points[i + 1]),
                        fill=(235, 213, 164, alpha), width=2 if strength > .78 else 1)
            glow = streak.filter(ImageFilter.GaussianBlur(5.5))
            glow.putalpha(glow.getchannel('A').point(lambda p: int(p * .48)))
            layer.alpha_composite(glow)
            layer.alpha_composite(streak)

            dust = Image.new('RGBA', layer.size, (0, 0, 0, 0))
            dd = ImageDraw.Draw(dust)
            for i, (x, y) in enumerate(points[:-1]):
                if i % 2:
                    continue
                strength = (i + 1) / len(points)
                offset = 3.2 * math.sin(i * 2.17 + frame * .08)
                radius = .45 + .45 * strength
                alpha = int(70 * birth * strength)
                dd.ellipse((x + offset - radius, y - offset * .3 - radius,
                            x + offset + radius, y - offset * .3 + radius),
                           fill=ca.PAPER + (alpha,))
            layer.alpha_composite(dust)

        x, y = descent_point(frame)
        z = 1
        if z > 0:
            core = Image.new('RGBA', layer.size, (0, 0, 0, 0))
            cd = ImageDraw.Draw(core)
            pulse = .85 + .15 * math.sin(frame * .42)
            cd.ellipse((x - 9.2, y - 9.2, x + 9.2, y + 9.2),
                       fill=(236, 207, 145, int(78 * birth)))
            core = core.filter(ImageFilter.GaussianBlur(6.2))
            layer.alpha_composite(core)
            d = ImageDraw.Draw(layer)
            ray = (8.6 + 2.6 * pulse) * birth
            alpha = int(175 * birth)
            d.line((x - ray, y, x + ray, y), fill=ca.PAPER + (alpha,), width=1)
            d.line((x, y - ray * 1.45, x, y + ray * 1.45),
                   fill=ca.PAPER + (alpha,), width=1)
            d.ellipse((x - 2.3, y - 2.3, x + 2.3, y + 2.3),
                      fill=(255, 244, 211, int(250 * birth)))
        return

    x, y, z = frames[str(fall_end)]['head']
    if z <= 0:
        return
    rings = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(rings)
    for delay, reach, lifetime in ((0, 58, 30), (7, 37, 25)):
        age = frame - fall_end - delay
        if age < 0 or age > lifetime:
            continue
        progress = age / lifetime
        radius = 5 + reach * ca.smooth(progress)
        alpha = int(105 * (1 - progress) ** 1.7)
        rd.ellipse((x - radius, y - radius * .28,
                    x + radius, y + radius * .28),
                   outline=ca.GOLD + (alpha,), width=1)
    age = frame - fall_end
    if 0 <= age < 18:
        progress = age / 18
        for i in range(12):
            angle = i * math.tau / 12
            inner = 5 + 7 * progress
            outer = inner + 12 * (1 - progress)
            rd.line((x + math.cos(angle) * inner, y + math.sin(angle) * inner * .28,
                     x + math.cos(angle) * outer, y + math.sin(angle) * outer * .28),
                    fill=ca.PAPER + (int(70 * (1 - progress)),), width=1)
    layer.alpha_composite(rings)


def add_route_motion(layer, projection, frame):
    add_star_descent(layer, projection, frame)
    if not 193 <= frame <= 384:
        return
    points = []
    for past in range(max(193, frame - 15), frame + 1):
        x, y, z = projection['frames'][str(past)]['head']
        if z > 0:
            points.append((x, y))
    if len(points) < 2:
        return
    streak = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(streak)
    for i in range(len(points) - 1):
        strength = (i + 1) / (len(points) - 1)
        sd.line((points[i], points[i + 1]),
                fill=(231, 204, 148, int(8 + 86 * strength ** 1.8)),
                width=2 if strength > .76 else 1)
    glow = streak.filter(ImageFilter.GaussianBlur(4.5))
    glow.putalpha(glow.getchannel('A').point(lambda p: int(p * .32)))
    layer.alpha_composite(glow)
    layer.alpha_composite(streak)


def main():
    root = Path(sys.argv[1])
    full = len(sys.argv) > 2 and sys.argv[2] == '--full'
    study = sys.argv[3] if len(sys.argv) > 3 else 'route-study'
    title_dir = root / sys.argv[4] if len(sys.argv) > 4 else root / 'opening-v3' / 'final-21s'
    raw_name = sys.argv[5] if len(sys.argv) > 5 else 'raw'
    out = root / study
    proofs = out / 'proofs'
    final = out / 'final'
    proofs.mkdir(exist_ok=True)
    projection = json.loads((out / 'projection.json').read_text())
    cards = {name: ca.make_card(root, name) for name in ('birth', 'journey')}
    label_font = ImageFont.truetype(ca.SONG, 20)
    frames = range(1, 433) if full else ([int(value) for value in sys.argv[6].split(',')]
                                         if len(sys.argv) > 6 else FRAMES)
    if full:
        final.mkdir(exist_ok=True)
    for frame in frames:
        target = final / f'frame-{frame:04d}.jpg' if full else proofs / f'star-{frame:04d}.jpg'
        raw = out / raw_name / f'frame-{frame:04d}.png'
        if not raw.exists():
            proof_raw = out / 'proofs' / f'raw-{frame:04d}.png'
            raw = proof_raw if proof_raw.exists() else raw
        if not raw.exists() and raw_name == 'raw':
            clean_raw = root / 'route-clean' / 'raw' / f'frame-{frame:04d}.png'
            raw = clean_raw if clean_raw.exists() else root / 'opening-v3' / 'raw' / f'frame-{frame:04d}.png'
        body.compose(root, projection, cards, frame, raw, target,
                     map_effect=lambda layer: add_route_motion(layer, projection, frame))
        if full:
            if frame % 72 == 0:
                print(f'ROUTE ECHO COMPOSITED {frame}/432', flush=True)
            continue
        old_path = root / 'route-clean' / 'final' / f'frame-{frame:04d}.jpg'
        if not old_path.exists():
            old_path = root / 'opening-v3' / 'archive-final' / f'frame-{frame:04d}.jpg'
        old = Image.open(old_path).resize((960, 540))
        new = Image.open(target).resize((960, 540))
        comparison = Image.new('RGB', (1920, 590), (7, 9, 6))
        comparison.paste(old, (0, 50))
        comparison.paste(new, (960, 50))
        d = ImageDraw.Draw(comparison)
        d.text((28, 13), '此前｜眉山静止光点', font=label_font, fill=ca.PAPER)
        d.text((988, 13), '修改｜天降光点＋落地涟漪', font=label_font, fill=ca.GOLD)
        comparison.save(proofs / f'compare-{frame:04d}.jpg', quality=94, subsampling=0)
    if full:
        final21 = out / 'final-21s'
        final21.mkdir(exist_ok=True)
        for frame in range(1, 73):
            destination = final21 / f'frame-{frame:04d}.jpg'
            if destination.exists():
                raise FileExistsError(f'Refusing to replace existing frame: {destination}')
            os.link(title_dir / f'frame-{frame:04d}.jpg', destination)
        for frame in range(1, 433):
            destination = final21 / f'frame-{frame + 72:04d}.jpg'
            if destination.exists():
                raise FileExistsError(f'Refusing to replace existing frame: {destination}')
            os.link(final / f'frame-{frame:04d}.jpg', destination)
    print('ROUTE ECHO COMPARISONS COMPLETE' if not full else 'ROUTE ECHO 21S FRAMES COMPLETE', flush=True)


if __name__ == '__main__':
    main()
