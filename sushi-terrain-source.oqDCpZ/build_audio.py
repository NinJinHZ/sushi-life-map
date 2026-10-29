import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 48000


def subtitle_chunks(text, limit=25):
    clauses = [part for part in re.findall(r'[^，。；！？：]+[，。；！？：]?', text) if part]
    chunks = []
    current = ''
    for clause in clauses:
        if current and len(current) + len(clause) > limit:
            chunks.append(current)
            current = ''
        while len(clause) > limit:
            if current:
                chunks.append(current)
                current = ''
            chunks.append(clause[:limit])
            clause = clause[limit:]
        current += clause
    if current:
        chunks.append(current)
    return chunks


def prepare_narration(out, total_duration):
    voice = out / 'voice'
    script = json.loads((voice / 'script.json').read_text())
    schedule = []
    cursor = 0.0
    audio_dir = voice / 'segments'
    for item in script['entries']:
        path = audio_dir / f"{item['id']}.wav"
        if not path.exists():
            raise FileNotFoundError(f'Missing narration segment: {path}')
        audio, rate = sf.read(path, dtype='float32')
        if rate != SR:
            raise ValueError(f'Unexpected sample rate {rate}: {path}')
        active = np.flatnonzero(np.abs(audio) > .003)
        if active.size:
            padding = round(.05 * SR)
            first = max(0, int(active[0]) - padding)
            last = min(len(audio), int(active[-1]) + padding + 1)
            audio = audio[first:last]
        duration = len(audio) / SR
        start = max(item['preferred_start'], cursor)
        end = start + duration
        cursor = end + item.get('gap_after', .42)
        chunks = subtitle_chunks(item['text'])
        weights = [max(1, len(re.sub(r'\W', '', chunk))) for chunk in chunks]
        total_weight = sum(weights)
        subs = []
        elapsed = 0.0
        for chunk, weight in zip(chunks, weights):
            sub_start = start + duration * elapsed / total_weight
            elapsed += weight
            sub_end = start + duration * elapsed / total_weight
            subs.append({'start': sub_start, 'end': sub_end, 'text': chunk})
        schedule.append({**item, 'start': start, 'end': end, 'duration': duration,
                         'subtitles': subs})
        audio = np.asarray(audio, dtype=np.float32)
        rms = float(np.sqrt(np.mean(audio * audio)) + 1e-9)
        gain = min(5.0, .082 / rms)
        peak = float(np.max(np.abs(audio)) * gain)
        if peak > .88:
            gain *= .88 / peak
        fade = min(480, len(audio) // 2)
        if fade:
            audio[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
            audio[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
        schedule[-1]['_audio'] = audio * gain
    n = math.ceil(total_duration * SR)
    narration = np.zeros((n, 2), dtype=np.float32)
    for item in schedule:
        audio = item.pop('_audio')
        start = round(item['start'] * SR)
        end = min(n, start + len(audio))
        if end > start:
            narration[start:end, 0] += audio[:end - start]
            narration[start:end, 1] += audio[:end - start]
    (voice / 'schedule.json').write_text(json.dumps({'total_duration': total_duration, 'entries': schedule},
                                                    ensure_ascii=False, indent=2))
    audio_out = out / 'audio'
    audio_out.mkdir(exist_ok=True)
    sf.write(audio_out / 'narration.wav', narration, SR, subtype='PCM_24')
    chapter_ends = {chapter['id']: chapter['end_frame'] for chapter in
                    json.loads((out / 'projection.json').read_text())['chapters']}
    opening_frames = json.loads((out / 'timeline.json').read_text())['opening_frames']
    for item in schedule:
        if item['chapter'] in chapter_ends:
            end_s = (opening_frames + chapter_ends[item['chapter']]) / 24
            if item['end'] > end_s + 1.5:
                print(f"NOTE {item['id']} bridges beyond its chapter by {item['end'] - end_s:.2f}s", flush=True)
    if schedule[-1]['end'] > total_duration - 1:
        raise RuntimeError(f'Final narration ends at {schedule[-1]["end"]:.2f}s, too close to {total_duration:.2f}s')
    return narration, schedule, audio_out


def add_pluck(score, start, duration, frequency, amplitude, pan=0.0):
    begin = round(start * SR)
    length = min(round(duration * SR), len(score) - begin)
    if begin < 0 or length <= 0:
        return
    t = np.arange(length, dtype=np.float32) / SR
    envelope = (1 - np.exp(-t / .006)) * np.exp(-t / (duration * .28))
    envelope *= np.minimum(1, (duration - t) / .18)
    tone = (np.sin(2 * np.pi * frequency * t) +
            .42 * np.sin(2 * np.pi * frequency * 2.003 * t + .2) +
            .18 * np.sin(2 * np.pi * frequency * 3.011 * t + .5) +
            .08 * np.sin(2 * np.pi * frequency * 4.021 * t))
    signal = amplitude * envelope * tone
    score[begin:begin + length, 0] += signal * math.sqrt((1 - pan) / 2)
    score[begin:begin + length, 1] += signal * math.sqrt((1 + pan) / 2)


def add_pad(score, start, duration, frequencies, amplitude, attack_time=3.0, release_time=4.0):
    begin = round(start * SR)
    length = min(round(duration * SR), len(score) - begin)
    if begin < 0 or length <= 0:
        return
    t = np.arange(length, dtype=np.float32) / SR
    attack = np.minimum(1, t / min(attack_time, duration / 3))
    release = np.minimum(1, (duration - t) / min(release_time, duration / 3))
    envelope = np.maximum(0, attack * release)
    left = np.zeros(length, dtype=np.float32)
    right = np.zeros(length, dtype=np.float32)
    for i, frequency in enumerate(frequencies):
        vibrato = .0015 * np.sin(2 * np.pi * (.07 + i * .013) * t + i)
        phase = 2 * np.pi * frequency * t + vibrato
        left += (np.sin(phase + i * .4) +
                 .16 * np.sin(2 * phase + i * .4 + .1) +
                 .06 * np.sin(3 * phase + i * .4 + .2)) / (i + 1)
        right += (np.sin(phase * 1.0007 - i * .3) +
                  .16 * np.sin(2 * phase * 1.0007 - i * .3 + .1) +
                  .06 * np.sin(3 * phase * 1.0007 - i * .3 + .2)) / (i + 1)
    score[begin:begin + length, 0] += amplitude * envelope * left
    score[begin:begin + length, 1] += amplitude * envelope * right


def add_bell(score, start, frequency=293.66, amplitude=.022):
    begin = round(start * SR)
    duration = 2.8
    length = min(round(duration * SR), len(score) - begin)
    if begin < 0 or length <= 0:
        return
    t = np.arange(length, dtype=np.float32) / SR
    signal = np.zeros(length, dtype=np.float32)
    for ratio, gain, decay in [(1, 1, 1.2), (2.01, .38, .65), (3.97, .15, .35)]:
        signal += gain * np.sin(2 * np.pi * frequency * ratio * t) * np.exp(-t / decay)
    signal *= amplitude * (1 - np.exp(-t / .008))
    score[begin:begin + length, 0] += signal * .72
    score[begin:begin + length, 1] += signal * .68


def add_wind(score, start, duration, seed, amplitude=.004):
    begin = round(start * SR)
    length = min(round(duration * SR), len(score) - begin)
    if begin < 0 or length <= 0:
        return
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, length).astype(np.float32)
    kernel = np.ones(360, dtype=np.float32) / 360
    soft = np.convolve(noise, kernel, mode='same')
    t = np.arange(length, dtype=np.float32) / SR
    envelope = np.minimum(1, t / 2) * np.minimum(1, (duration - t) / 2)
    signal = amplitude * soft * np.maximum(0, envelope)
    score[begin:begin + length, 0] += signal
    score[begin:begin + length, 1] += np.roll(signal, 170) * .9


def midi_to_hz(note):
    return 440.0 * 2 ** ((note - 69) / 12)


def pentatonic_hz(root, degree, mode='major', octave=2):
    scale = (0, 2, 4, 7, 9) if mode == 'major' else (0, 3, 5, 7, 10)
    scale_octave, index = divmod(degree, len(scale))
    return midi_to_hz(root + 12 * (octave + scale_octave) + scale[index])


def add_bass(score, start, duration, frequency, amplitude):
    begin = round(start * SR)
    length = min(round(duration * SR), len(score) - begin)
    if begin < 0 or length <= 0:
        return
    t = np.arange(length, dtype=np.float32) / SR
    envelope = np.minimum(1, t / .09) * np.minimum(1, (duration - t) / .7)
    envelope *= np.exp(-t / max(1.0, duration * 1.8))
    tone = (np.sin(2 * np.pi * frequency * t) +
            .22 * np.sin(2 * np.pi * frequency * 2 * t + .1) +
            .06 * np.sin(2 * np.pi * frequency * 3 * t + .3))
    signal = amplitude * np.maximum(0, envelope) * tone
    score[begin:begin + length, 0] += signal * .707
    score[begin:begin + length, 1] += signal * .707


# An original four-bar theme and its response. Beat positions are deliberate:
# every chapter states a complete phrase instead of scattering random notes.
QUESTION_PHRASES = (
    ((0, 0, 1.5), (2, 2, 1), (4, 3, 1.5), (6, 2, 1),
     (8, 1, 1), (10, 2, 1), (12, 4, 3)),
    ((0, 2, 1.5), (2, 3, 1), (4, 4, 1.5), (6, 3, 1),
     (8, 2, 1), (10, 1, 1), (12, 1, 3)),
)
RESPONSE_PHRASE = ((0, 3, 1.5), (2, 4, 1), (4, 3, 1.5), (6, 2, 1),
                   (8, 1, 1), (10, 2, 1), (12, 0, 3))


def add_instrumental_section(score, start, end, root, mode='major', level=1.0, variant=0, shimmer=False):
    duration = end - start
    available = duration - .6
    if available <= 0:
        return

    # Keep the four-bar phrasing intact; only the tempo bends slightly to fit.
    phrase_count = max(1, int(available / 16.0 + .5))
    bar = min(5.0, available / (phrase_count * 4))
    beat = bar / 4
    total_bars = max(phrase_count * 4, math.ceil((duration - .25) / bar))
    question_harmony = ((0, 4), (-3, 3), (5, 4), (7, 4))
    response_harmony = ((0, 4), (5, 4), (7, 4), (0, 4))
    if mode == 'minor':
        question_harmony = ((0, 3), (8, 4), (3, 4), (10, 4))
        response_harmony = ((0, 3), (8, 4), (10, 4), (0, 3))

    for bar_index in range(total_bars):
        chord_start = start + bar_index * bar
        if chord_start >= end - .2:
            break
        phrase_index = bar_index // 4
        harmony = response_harmony if phrase_index >= phrase_count - 1 else question_harmony
        offset, third = harmony[bar_index % 4]
        chord_root = root + offset
        chord_duration = min(bar + .45, end - chord_start)
        frequencies = [midi_to_hz(chord_root + 12),
                       midi_to_hz(chord_root + 12 + third),
                       midi_to_hz(chord_root + 19)]
        add_pad(score, chord_start, chord_duration, frequencies, .0105 * level,
                attack_time=.85, release_time=1.25)
        add_bass(score, chord_start, min(bar * .92, end - chord_start),
                 midi_to_hz(chord_root), .009 * level)

        # A quiet, regular broken chord binds the melody to the harmony.
        chord_tones = (chord_root + 24, chord_root + 24 + third, chord_root + 31)
        arpeggio = (0, 1, 2, 1)
        pans = (-.24, .12, .28, -.08)
        note_duration = max(1.2, min(2.8, bar * .72))
        for step, tone_index in enumerate(arpeggio):
            if mode == 'minor' and step in (1, 3):
                continue
            note_start = chord_start + step * beat + .035
            if note_start < end - .2:
                add_pluck(score, note_start, note_duration, midi_to_hz(chord_tones[tone_index]),
                          .0048 * level, pans[step])

    for phrase_index in range(phrase_count):
        if phrase_index == phrase_count - 1:
            phrase = RESPONSE_PHRASE
        else:
            phrase = QUESTION_PHRASES[(phrase_index + variant) % len(QUESTION_PHRASES)]
        phrase_start = start + phrase_index * bar * 4
        for note_index, (beat_offset, degree, beats) in enumerate(phrase):
            note_start = phrase_start + beat_offset * beat
            if note_start >= end - .2:
                continue
            note_duration = min(max(1.3, beats * beat * 1.45), end - note_start)
            add_pluck(score, note_start, note_duration,
                      pentatonic_hz(root, degree, mode), .0185 * level,
                      .10 if note_index % 2 else -.10)
            if shimmer and phrase_index == phrase_count - 1:
                add_pluck(score, note_start + .018, note_duration * .72,
                          pentatonic_hz(root, degree, mode, octave=3), .0034 * level,
                          -.16 if note_index % 2 else .16)


def build_score(out, projection, timeline, schedule, total_duration):
    n = math.ceil(total_duration * SR)
    score = np.zeros((n, 2), dtype=np.float32)
    opening_s = timeline['opening_frames'] / 24
    add_instrumental_section(score, 0, opening_s + 4, 38, level=.82)
    add_bell(score, 5.125, 587.33, .020)

    # Shared melodic identity, transposed by chapter. Huangzhou returns to the
    # opening D tonality; Wutai alone contracts into a quieter minor mode.
    moods = {
        'bijing': (38, 'major', .90, 0),
        'fengxiang': (40, 'major', .90, 1),
        'hangzhou': (43, 'major', .92, 0),
        'mizhou': (38, 'major', .90, 1),
        'xuzhou': (36, 'major', .88, 0),
        'wutai': (35, 'minor', .72, 1),
        'huangzhou': (38, 'major', .94, 0),
        'return': (40, 'major', .90, 1),
        'hangzhou2': (43, 'major', .92, 0),
        'later': (36, 'major', .86, 1),
        'huizhou': (43, 'major', .90, 0),
        'danzhou': (38, 'major', .88, 1),
        'changzhou': (38, 'major', .92, 0),
    }
    for chapter_index, chapter in enumerate(projection['chapters']):
        start = (timeline['opening_frames'] + chapter['start_frame'] - 1) / 24
        arrival = (timeline['opening_frames'] + chapter['travel_end'] - 1) / 24
        end = (timeline['opening_frames'] + chapter['end_frame']) / 24
        root, mode, level, variant = moods[chapter['id']]
        add_instrumental_section(score, start, end, root, mode, level, variant,
                                 shimmer=chapter['id'] in {'hangzhou', 'hangzhou2', 'huangzhou', 'changzhou'})
        add_wind(score, start, max(.1, arrival - start), 800 + chapter_index)

    # A short, quiet reverb made only from delays; no external impulse or song.
    dry = score.copy()
    for delay, gain in [(.113, .16), (.227, .11), (.379, .075), (.613, .045)]:
        offset = round(delay * SR)
        score[offset:] += dry[:-offset] * gain
    duck = np.ones(n, dtype=np.float32)
    voice_mask = np.zeros(n, dtype=bool)
    for item in schedule:
        start = max(0, round((item['start'] - .35) * SR))
        voice_start = round(item['start'] * SR)
        voice_end = min(n, round(item['end'] * SR))
        release = 2.0 if item is schedule[-1] else .65
        end = min(n, round((item['end'] + release) * SR))
        voice_mask[voice_start:voice_end] = True
        duck[voice_start:voice_end] = np.minimum(duck[voice_start:voice_end], .46)
        if voice_start > start:
            ramp = np.linspace(1, .46, voice_start - start, dtype=np.float32)
            duck[start:voice_start] = np.minimum(duck[start:voice_start], ramp)
        if end > voice_end:
            ramp = np.linspace(.46, 1, end - voice_end, dtype=np.float32)
            duck[voice_end:end] = np.minimum(duck[voice_end:end], ramp)
    rms_before = float(np.sqrt(np.mean(score * score)) + 1e-12)
    score *= duck[:, None]
    rms_after = float(np.sqrt(np.mean(score * score)) + 1e-12)
    fade_frames = min(n, 3 * SR)
    score[-fade_frames:] *= np.linspace(1, 0, fade_frames, dtype=np.float32)[:, None]
    # 连续器乐应能被听见，而不只是偶尔冒出音效；保留约 10 dB 余量后再限峰。
    score *= 3.2
    peak = float(np.max(np.abs(score)) + 1e-9)
    peak_gain = 1.0
    if peak > .32:
        peak_gain = .32 / peak
        score *= peak_gain
    voice_rms = float(np.sqrt(np.mean(score[voice_mask] * score[voice_mask])) + 1e-12)
    quiet_rms = float(np.sqrt(np.mean(score[~voice_mask] * score[~voice_mask])) + 1e-12)
    print(f'SCORE RMS: pre-duck {20 * math.log10(rms_before):.2f} dBFS, '
          f'post-duck {20 * math.log10(rms_after):.2f} dBFS, '
          f'voice {20 * math.log10(voice_rms):.2f} dBFS, '
          f'gaps {20 * math.log10(quiet_rms):.2f} dBFS, peak gain {peak_gain:.3f}', flush=True)
    return score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    root = Path(args.root)
    out = root / 'final-film'
    projection = json.loads((out / 'projection.json').read_text())
    timeline = json.loads((out / 'timeline.json').read_text())
    total_duration = (timeline['opening_frames'] + projection['total_frames']) / 24
    narration, schedule, audio_out = prepare_narration(out, total_duration)
    score = build_score(out, projection, timeline, schedule, total_duration)
    sf.write(audio_out / 'score-original.wav', score, SR, subtype='PCM_24')
    mix = narration + score
    peak = float(np.max(np.abs(mix)))
    if peak > .96:
        mix *= .96 / peak
    sf.write(audio_out / 'mix-pre-master.wav', mix, SR, subtype='PCM_24')
    print(f'AUDIO COMPLETE: {total_duration:.3f}s, {len(schedule)} narration segments', flush=True)


if __name__ == '__main__':
    main()
