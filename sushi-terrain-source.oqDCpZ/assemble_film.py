import argparse
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose_archival as ca


def srt_time(seconds):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f'{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--projection-file', default='projection.json')
    parser.add_argument('--blend-file', default='sushi-life-map.blend')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--opening-dir', default='route-star/final-21s')
    parser.add_argument('--composed-dir', default='composed')
    parser.add_argument('--final-dir', default='final-frames')
    parser.add_argument('--tag', default='')
    args = parser.parse_args()
    root = Path(args.root)
    out = root / 'final-film'
    projection = json.loads((out / args.projection_file).read_text())
    schedule = json.loads((out / 'voice' / 'schedule.json').read_text())
    opening_frames = projection['opening_frames']
    total_frames = opening_frames + projection['total_frames']
    opening_dir = root / args.opening_dir
    composed_dir = out / args.composed_dir
    targets = out / args.final_dir
    if targets.exists() and any(targets.iterdir()) and not args.resume:
        raise FileExistsError(f'Final frame directory already exists; use --resume explicitly: {targets}')
    targets.mkdir(exist_ok=True)
    opening_last = Image.open(opening_dir / f'frame-{opening_frames:04d}.jpg').convert('RGB')
    ui_scale = opening_last.width / 1280
    subtitle_font = ImageFont.truetype(ca.SONG, round(22 * ui_scale))
    subtitles = {}
    for entry in schedule['entries']:
        for sub in entry['subtitles']:
            first = max(1, round(sub['start'] * 24) + 1)
            last = min(total_frames, round(sub['end'] * 24) + 1)
            for frame in range(first, last):
                subtitles[frame] = sub
    for frame in range(1, total_frames + 1):
        if frame <= opening_frames:
            source = opening_dir / f'frame-{frame:04d}.jpg'
            post_frame = 0
        else:
            post_frame = frame - opening_frames
            source = composed_dir / f'frame-{post_frame:04d}.jpg'
        target = targets / f'frame-{frame:04d}.jpg'
        if target.exists():
            if args.resume:
                continue
            raise FileExistsError(target)
        transitioning = 1 <= post_frame <= 12
        if frame not in subtitles and not transitioning:
            os.link(source, target)
        else:
            image = Image.open(source).convert('RGB')
            if transitioning:
                image = Image.blend(opening_last, image, ca.smooth(post_frame / 12))
            if frame in subtitles:
                sub = subtitles[frame]
                time = (frame - 1) / 24
                alpha = ca.smooth((time - sub['start']) / .12) * ca.smooth((sub['end'] - time) / .12)
                overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
                d = ImageDraw.Draw(overlay)
                center = (round(720 * ui_scale), round(640 * ui_scale))
                stroke = max(1, round(2 * ui_scale))
                bbox = d.textbbox(center, sub['text'], font=subtitle_font, anchor='mm', stroke_width=stroke)
                d.rectangle((bbox[0] - round(13 * ui_scale), bbox[1] - round(5 * ui_scale),
                             bbox[2] + round(13 * ui_scale), bbox[3] + round(5 * ui_scale)),
                            fill=(4, 6, 4, int(72 * alpha)))
                ca.text(d, center, sub['text'], subtitle_font, ca.PAPER,
                        int(248 * alpha), 'mm', stroke)
                image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
            temporary = targets / f'frame-{frame:04d}.writing.jpg'
            image.save(temporary, quality=95, subsampling=0)
            temporary.replace(target)
        if frame % 504 == 0:
            print(f'ASSEMBLED {frame}/{total_frames}', flush=True)

    srt = []
    index = 1
    for entry in schedule['entries']:
        for sub in entry['subtitles']:
            srt.extend([str(index), f"{srt_time(sub['start'])} --> {srt_time(sub['end'])}", sub['text'], ''])
            index += 1
    (out / f'此心安处{args.tag}-字幕.srt').write_text('\n'.join(srt))

    metadata = [';FFMETADATA1', 'title=此心安处——苏轼的人生地图']
    chapters = [(0, 3000, '片名 · 此心安处'), (3000, opening_frames * 1000 // 24, '眉山出生 · 三苏出蜀')]
    for chapter in projection['chapters']:
        start = round((opening_frames + chapter['start_frame'] - 1) * 1000 / 24)
        end = round((opening_frames + chapter['end_frame']) * 1000 / 24)
        chapters.append((start, end, f"{chapter['index']} {chapter['title']}"))
    for start, end, title in chapters:
        metadata.extend(['[CHAPTER]', 'TIMEBASE=1/1000', f'START={start}', f'END={end}', f'title={title}'])
    (out / f'chapters{args.tag}.ffmeta').write_text('\n'.join(metadata))
    manifest = {
        'title': '此心安处——苏轼的人生地图',
        'width': opening_last.width, 'height': opening_last.height, 'fps': 24,
        'frames': total_frames, 'duration_seconds': total_frames / 24,
        'narration_segments': len(schedule['entries']),
        'source_blender': str(out / args.blend_file),
        'chapters': [{'title': title, 'start_ms': start, 'end_ms': end} for start, end, title in chapters],
    }
    (out / f'film-manifest{args.tag}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    Image.open(composed_dir / f"frame-{projection['total_frames']:04d}.jpg").save(
        out / f'此心安处{args.tag}-封面.jpg', quality=96, subsampling=0)
    print(f'FINAL FRAMES READY: {total_frames} frames, {total_frames / 24:.3f}s', flush=True)


if __name__ == '__main__':
    main()
