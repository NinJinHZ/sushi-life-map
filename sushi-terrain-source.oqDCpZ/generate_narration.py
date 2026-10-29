import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf
from voxcpm.core import VoxCPM


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--only', nargs='+')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    voice = root / 'final-film' / 'voice'
    segments = voice / 'segments'
    segments.mkdir(exist_ok=True)
    script = json.loads((voice / 'script.json').read_text())
    reference = voice / 'candidate-a.wav'
    model = VoxCPM(voxcpm_model_path=args.model, zipenhancer_model_path=None,
                   enable_denoiser=False, optimize=True, device='mps')
    report_path = voice / 'generation-report.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    for index, item in enumerate(script['entries'], 1):
        if args.only and item['id'] not in args.only:
            continue
        path = segments / f"{item['id']}.wav"
        if path.exists() and not args.force:
            try:
                info = sf.info(path)
                if info.frames > 0:
                    print(f'SKIP {index}/{len(script["entries"])} {item["id"]}', flush=True)
                    continue
            except Exception as error:
                quarantine = path.with_suffix('.incomplete.wav')
                path.replace(quarantine)
                print(f'QUARANTINED incomplete {path.name}: {error}', flush=True)
        print(f'GENERATE {index}/{len(script["entries"])} {item["id"]}: {item["text"]}', flush=True)
        audio = model.generate(text=item['text'], prompt_wav_path=str(reference),
                               prompt_text=script['reference_text'], cfg_value=2.0,
                               inference_timesteps=16, normalize=False, denoise=False)
        if not np.isfinite(audio).all():
            raise RuntimeError(f'Non-finite audio generated for {item["id"]}')
        peak = float(np.max(np.abs(audio)))
        if peak < .01:
            raise RuntimeError(f'Empty or nearly silent audio generated for {item["id"]}')
        temporary = path.with_suffix('.writing.wav')
        sf.write(temporary, audio, model.tts_model.sample_rate)
        if path.exists():
            backups = voice / 'repaired-backups'
            backups.mkdir(exist_ok=True)
            backup = backups / f"{item['id']}-{datetime.now():%Y%m%d-%H%M%S}.wav"
            path.replace(backup)
        temporary.replace(path)
        report[item['id']] = {'text': item['text'], 'duration': len(audio) / model.tts_model.sample_rate,
                              'peak': peak, 'file': path.name}
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(f'SAVED {item["id"]} {report[item["id"]]["duration"]:.2f}s', flush=True)
    print('NARRATION GENERATION COMPLETE', flush=True)


if __name__ == '__main__':
    main()
