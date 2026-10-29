import argparse
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


EXPECTED_FRAMES = 7824
KEY_TIMES = [
    ('01-title', 1.5),
    ('02-meishan', 12.0),
    ('03-bianjing', 33.0),
    ('04-mizhou', 108.0),
    ('05-wutai', 144.0),
    ('06-huangzhou', 171.5),
    ('07-hangzhou', 213.5),
    ('08-huizhou', 251.0),
    ('09-danzhou', 274.0),
    ('10-changzhou', 300.0),
    ('11-credits', 320.0),
]


def run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True)


def contact_sheet(paths, destination, labels):
    columns = 4
    tile_width, tile_height, label_height = 640, 360, 34
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * tile_width, rows * (tile_height + label_height)), (8, 9, 7))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 19)
    except OSError:
        font = ImageFont.load_default()
    for index, (path, label) in enumerate(zip(paths, labels)):
        x = (index % columns) * tile_width
        y = (index // columns) * (tile_height + label_height)
        with Image.open(path) as source:
            image = source.convert('RGB').resize((tile_width, tile_height), Image.Resampling.LANCZOS)
        sheet.paste(image, (x, y + label_height))
        draw.text((x + 10, y + 6), label, font=font, fill=(225, 216, 190))
    sheet.save(destination, quality=94, subsampling=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--video', required=True)
    parser.add_argument('--report-dir', default='qa-video-v4k')
    args = parser.parse_args()
    root = Path(args.root)
    out = root / 'final-film'
    video = Path(args.video)
    report_dir = out / args.report_dir
    periodic_dir = report_dir / 'periodic'
    key_dir = report_dir / 'keyframes'
    periodic_dir.mkdir(parents=True, exist_ok=True)
    key_dir.mkdir(parents=True, exist_ok=True)

    probe = json.loads(run([
        'ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format',
        '-show_chapters', '-of', 'json', str(video),
    ]).stdout)
    video_stream = next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')
    audio_stream = next(stream for stream in probe['streams'] if stream['codec_type'] == 'audio')

    decode = subprocess.run([
        'ffmpeg', '-hide_banner', '-v', 'error', '-i', str(video),
        '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-',
    ], capture_output=True, text=True)
    (report_dir / 'decode-errors.txt').write_text(decode.stderr)
    if decode.returncode:
        raise RuntimeError(f'Full decode failed with exit code {decode.returncode}')

    loudness = subprocess.run([
        'ffmpeg', '-hide_banner', '-nostats', '-i', str(video), '-map', '0:a:0',
        '-af', 'ebur128=peak=true', '-f', 'null', '-',
    ], capture_output=True, text=True, check=True)
    summary_start = loudness.stderr.rfind('Summary:')
    loudness_summary = loudness.stderr[summary_start:] if summary_start >= 0 else loudness.stderr[-4000:]
    (report_dir / 'loudness.txt').write_text(loudness_summary)

    periodic_indices = [round(index * (EXPECTED_FRAMES - 1) / 15) for index in range(16)]
    select = '+'.join(f'eq(n\\,{frame})' for frame in periodic_indices)
    run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-i', str(video),
        '-vf', f"select='{select}',scale=1920:1080", '-fps_mode', 'vfr',
        '-q:v', '2', str(periodic_dir / 'periodic-%02d.jpg'),
    ])
    periodic_paths = [periodic_dir / f'periodic-{index:02d}.jpg' for index in range(1, 17)]
    if not all(path.exists() for path in periodic_paths):
        raise RuntimeError('Periodic extraction did not produce 16 frames')

    key_paths = []
    for name, seconds in KEY_TIMES:
        target = key_dir / f'{name}.jpg'
        run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-ss', str(seconds),
            '-i', str(video), '-frames:v', '1', '-q:v', '2', str(target),
        ])
        key_paths.append(target)

    contact_sheet(periodic_paths, report_dir / 'periodic-contact.jpg',
                  [f'frame {frame + 1} / {(frame / 24):.3f}s' for frame in periodic_indices])
    contact_sheet(key_paths, report_dir / 'keyframes-contact.jpg',
                  [f'{name} / {seconds:.3f}s' for name, seconds in KEY_TIMES])

    srt = (out / '此心安处-V4K-字幕.srt').read_text()
    subtitle_entries = len([block for block in re.split(r'\n\s*\n', srt.strip()) if block.strip()])
    integrated = re.search(r'Integrated loudness:\s*I:\s*(-?[\d.]+) LUFS', loudness_summary)
    lra = re.search(r'Loudness range:\s*LRA:\s*(-?[\d.]+) LU', loudness_summary)
    peak = re.search(r'True peak:\s*Peak:\s*(-?[\d.]+) dBFS', loudness_summary)
    checks = {
        'width_3840': video_stream.get('width') == 3840,
        'height_2160': video_stream.get('height') == 2160,
        'fps_24': video_stream.get('avg_frame_rate') == '24/1',
        'frames_7824': int(video_stream.get('nb_read_frames', 0)) == EXPECTED_FRAMES,
        'duration_326': abs(float(probe['format']['duration']) - 326.0) < .05,
        'audio_aac_48k_stereo': (audio_stream.get('codec_name') == 'aac'
                                 and audio_stream.get('sample_rate') == '48000'
                                 and audio_stream.get('channels') == 2),
        'chapters_15': len(probe.get('chapters', [])) == 15,
        'subtitles_56': subtitle_entries == 56,
        'full_decode_no_errors': decode.returncode == 0 and not decode.stderr.strip(),
        'periodic_frames_16': len(periodic_paths) == 16,
        'keyframes_11': len(key_paths) == 11,
    }
    report = {
        'video': str(video),
        'bytes': video.stat().st_size,
        'checks': checks,
        'passed': all(checks.values()),
        'duration_seconds': float(probe['format']['duration']),
        'video_stream': video_stream,
        'audio_stream': audio_stream,
        'chapter_count': len(probe.get('chapters', [])),
        'subtitle_entries': subtitle_entries,
        'loudness': {
            'integrated_lufs': float(integrated.group(1)) if integrated else None,
            'lra_lu': float(lra.group(1)) if lra else None,
            'true_peak_dbtp': float(peak.group(1)) if peak else None,
        },
        'periodic_source_frames': [frame + 1 for frame in periodic_indices],
        'key_times_seconds': {name: seconds for name, seconds in KEY_TIMES},
        'viewing_boundary': 'Technical decode and sampled-frame QA only; not continuous frame-by-frame viewing or full-film listening.',
    }
    (report_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if not report['passed']:
        raise RuntimeError('One or more V4K delivery checks failed')


if __name__ == '__main__':
    main()
