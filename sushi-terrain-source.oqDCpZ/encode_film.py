import argparse
import json
import re
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--final-dir', default='final-frames')
    parser.add_argument('--tag', default='')
    args = parser.parse_args()
    out = Path(args.root) / 'final-film'
    manifest = json.loads((out / f'film-manifest{args.tag}.json').read_text())
    basename = f'此心安处-苏轼的人生地图{args.tag}'
    destination = out / f'{basename}.mp4'
    temporary = out / f'{basename}.encoding.mp4'
    for path in (destination, temporary):
        if path.exists():
            raise FileExistsError(f'Refusing to overwrite existing video: {path}')
    audio_path = out / 'audio' / 'mix-pre-master.wav'
    measured = subprocess.run([
        'ffmpeg', '-hide_banner', '-nostats', '-i', str(audio_path),
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json',
        '-f', 'null', '-',
    ], check=True, capture_output=True, text=True)
    matches = re.findall(r'\{\s*"input_i".*?\}', measured.stderr, re.S)
    if not matches:
        raise RuntimeError('Unable to read first-pass loudnorm measurements')
    loudness = json.loads(matches[-1])
    loudnorm = (
        'loudnorm=I=-16:TP=-1.5:LRA=11:'
        f"measured_I={loudness['input_i']}:measured_TP={loudness['input_tp']}:"
        f"measured_LRA={loudness['input_lra']}:measured_thresh={loudness['input_thresh']}:"
        f"offset={loudness['target_offset']}:linear=true:print_format=summary"
    )
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-n',
        '-framerate', str(manifest['fps']), '-start_number', '1',
        '-i', str(out / args.final_dir / 'frame-%04d.jpg'),
        '-i', str(audio_path),
        '-i', str(out / f'chapters{args.tag}.ffmeta'),
        '-map', '0:v:0', '-map', '1:a:0',
        '-map_metadata', '2', '-map_chapters', '2',
        '-frames:v', str(manifest['frames']),
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
        '-pix_fmt', 'yuv420p', '-r', str(manifest['fps']),
        '-af', loudnorm,
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
        '-movflags', '+faststart',
        '-metadata', 'title=此心安处——苏轼的人生地图',
        str(temporary),
    ]
    subprocess.run(command, check=True)
    probe = subprocess.run([
        'ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format',
        '-of', 'json', str(temporary),
    ], check=True, capture_output=True, text=True)
    info = json.loads(probe.stdout)
    video = next(stream for stream in info['streams'] if stream['codec_type'] == 'video')
    if int(video['nb_read_frames']) != manifest['frames']:
        raise RuntimeError(f"Encoded {video['nb_read_frames']} frames, expected {manifest['frames']}")
    temporary.replace(destination)
    print(f'FINAL VIDEO READY: {destination}', flush=True)


if __name__ == '__main__':
    main()
