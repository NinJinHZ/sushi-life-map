import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    root = Path(args.root)
    final = root / 'final-film'
    opening = root / 'opening-v3'
    pairs = [
        ('眉山近景', opening / 'direct-v3.1/final-21s/frame-0192.jpg',
         opening / 'direct-4k/proofs/star-0120.jpg'),
        ('乌台中段', final / 'composed-v3.1/frame-3060.jpg', final / 'proofs-4k/frame-3060.jpg'),
        ('全国终帧', final / 'composed-v3.1/frame-7320.jpg', final / 'proofs-4k/frame-7320.jpg'),
    ]
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Songti.ttc', 24)
    sheet = Image.new('RGB', (1920, 3 * 590), (7, 9, 6))
    draw = ImageDraw.Draw(sheet)
    for index, (label, old_path, new_path) in enumerate(pairs):
        y = index * 590
        old = Image.open(old_path).convert('RGB').resize((960, 540), Image.Resampling.LANCZOS)
        new = Image.open(new_path).convert('RGB').resize((960, 540), Image.Resampling.LANCZOS)
        sheet.paste(old, (0, y + 50))
        sheet.paste(new, (960, y + 50))
        draw.text((20, y + 10), f'{label}｜V3.1 · 1920×1080', font=font, fill=(241, 235, 219))
        draw.text((980, y + 10), f'{label}｜V4K · 3840×2160', font=font, fill=(226, 190, 116))
    sheet.save(final / 'proofs-4k/V3.1-vs-V4K-contact.jpg', quality=94, subsampling=0)

    old = Image.open(pairs[1][1]).convert('RGB')
    new = Image.open(pairs[1][2]).convert('RGB')
    old_box = (1200, 270, 1680, 540)
    new_box = tuple(value * 2 for value in old_box)
    old_crop = old.crop(old_box).resize((960, 540), Image.Resampling.LANCZOS)
    new_crop = new.crop(new_box)
    detail = Image.new('RGB', (1920, 590), (7, 9, 6))
    detail.paste(old_crop, (0, 50))
    detail.paste(new_crop, (960, 50))
    draw = ImageDraw.Draw(detail)
    draw.text((20, 10), '同区域细节｜V3.1 裁切放大（仅用于对照）', font=font, fill=(241, 235, 219))
    draw.text((980, 10), '同区域细节｜V4K 原生像素', font=font, fill=(226, 190, 116))
    detail.save(final / 'proofs-4k/V3.1-vs-V4K-native-detail.jpg', quality=96, subsampling=0)
    print('4K COMPARISON SHEETS READY')


if __name__ == '__main__':
    main()
