import argparse
import json
import math
import re
import subprocess
from pathlib import Path


def run(command):
    subprocess.run(command, check=True)


def frame_count(path):
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
        '-show_entries', 'stream=nb_read_frames', '-of', 'json', str(path),
    ], check=True, capture_output=True, text=True)
    streams = json.loads(result.stdout)['streams']
    return int(streams[0]['nb_read_frames']) if streams else 0


def measured_loudnorm(audio_path):
    measured = subprocess.run([
        'ffmpeg', '-hide_banner', '-nostats', '-i', str(audio_path),
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json',
        '-f', 'null', '-',
    ], check=True, capture_output=True, text=True)
    matches = re.findall(r'\{\s*"input_i".*?\}', measured.stderr, re.S)
    if not matches:
        raise RuntimeError('Unable to read first-pass loudnorm measurements')
    values = json.loads(matches[-1])
    return (
        'loudnorm=I=-16:TP=-1.5:LRA=11:'
        f"measured_I={values['input_i']}:measured_TP={values['input_tp']}:"
        f"measured_LRA={values['input_lra']}:measured_thresh={values['input_thresh']}:"
        f"offset={values['target_offset']}:linear=true:print_format=summary"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--final-dir', default='final-frames-4k')
    parser.add_argument('--tag', default='-V4K')
    parser.add_argument('--segment-frames', type=int, default=504)
    parser.add_argument('--segment', type=int, default=-1)
    parser.add_argument('--finalize-only', action='store_true')
    args = parser.parse_args()
    out = Path(args.root) / 'final-film'
    manifest = json.loads((out / f'film-manifest{args.tag}.json').read_text())
    total_frames = int(manifest['frames'])
    fps = int(manifest['fps'])
    if manifest['width'] != 3840 or manifest['height'] != 2160:
        raise ValueError('This encoder requires a true 3840x2160 manifest')
    basename = f'此心安处-苏轼的人生地图{args.tag}'
    destination = out / f'{basename}.mp4'
    if destination.exists():
        raise FileExistsError(f'Refusing to overwrite existing video: {destination}')
    work = out / 'encode-4k'
    work.mkdir(exist_ok=True)
    segment_count = math.ceil(total_frames / args.segment_frames)

    selected = range(segment_count) if args.segment < 0 else [args.segment]
    if not args.finalize_only:
        for index in selected:
            if not 0 <= index < segment_count:
                raise ValueError(f'Invalid segment {index}')
            start = index * args.segment_frames + 1
            count = min(args.segment_frames, total_frames - start + 1)
            target = work / f'segment-{index:03d}.mp4'
            if target.exists() and frame_count(target) == count:
                print(f'SEGMENT {index + 1}/{segment_count} ALREADY VERIFIED', flush=True)
                continue
            temporary = work / f'segment-{index:03d}.encoding.mp4'
            if temporary.exists():
                temporary.unlink()
            run([
                'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-n',
                '-framerate', str(fps), '-start_number', str(start),
                '-i', str(out / args.final_dir / 'frame-%04d.jpg'),
                '-frames:v', str(count), '-an',
                '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
                '-profile:v', 'high', '-level:v', '5.1',
                '-pix_fmt', 'yuv420p', '-r', str(fps),
                '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
                '-movflags', '+faststart', str(temporary),
            ])
            actual = frame_count(temporary)
            if actual != count:
                raise RuntimeError(f'Segment {index}: encoded {actual}, expected {count}')
            temporary.replace(target)
            print(f'SEGMENT {index + 1}/{segment_count} VERIFIED: {count} frames', flush=True)

    missing = []
    for index in range(segment_count):
        start = index * args.segment_frames + 1
        count = min(args.segment_frames, total_frames - start + 1)
        target = work / f'segment-{index:03d}.mp4'
        if not target.exists() or frame_count(target) != count:
            missing.append(index)
    if missing:
        print(f'SEGMENTS INCOMPLETE: {missing}', flush=True)
        return

    concat = work / 'concat.txt'
    concat.write_text(''.join(f"file '{work / f'segment-{index:03d}.mp4'}'\n" for index in range(segment_count)))
    video_only = work / 'picture-4k.mp4'
    if video_only.exists():
        video_only.unlink()
    run([
        'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-n',
        '-f', 'concat', '-safe', '0', '-i', str(concat),
        '-c', 'copy', '-movflags', '+faststart', str(video_only),
    ])
    if frame_count(video_only) != total_frames:
        raise RuntimeError('Concatenated 4K picture has an incorrect frame count')

    audio_path = out / 'audio' / 'mix-pre-master.wav'
    loudnorm = measured_loudnorm(audio_path)
    temporary = out / f'{basename}.encoding.mp4'
    if temporary.exists():
        temporary.unlink()
    run([
        'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-n',
        '-i', str(video_only), '-i', str(audio_path), '-i', str(out / f'chapters{args.tag}.ffmeta'),
        '-map', '0:v:0', '-map', '1:a:0', '-map_metadata', '2', '-map_chapters', '2',
        '-c:v', 'copy', '-af', loudnorm, '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
        '-frames:v', str(total_frames), '-movflags', '+faststart',
        '-metadata', 'title=此心安处——苏轼的人生地图', str(temporary),
    ])
    if frame_count(temporary) != total_frames:
        raise RuntimeError('Final 4K film has an incorrect frame count')
    temporary.replace(destination)
    print(f'FINAL TRUE 4K VIDEO READY: {destination}', flush=True)


if __name__ == '__main__':
    main()
