import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    root = Path(args.root)
    out = root / 'final-film'
    voice = out / 'voice'
    voice.mkdir(exist_ok=True)
    timeline = json.loads((out / 'timeline.json').read_text())
    projection = json.loads((out / 'projection.json').read_text())
    opening_s = timeline['opening_frames'] / 24
    entries = [
        {'id': 'opening-birth', 'chapter': 'opening', 'preferred_start': 3.5,
         'text': '一千零三十七年，苏轼生于眉州眉山。两年后，弟弟苏辙出生。'},
        {'id': 'opening-journey', 'chapter': 'opening', 'preferred_start': 11.5,
         'text': '嘉祐元年，苏洵带着两个儿子离开眉山，前往汴京。'},
    ]
    for chapter in projection['chapters']:
        chapter_start = opening_s + (chapter['start_frame'] - 1) / 24
        arrival = opening_s + (chapter['travel_end'] - 1) / 24
        for i, item in enumerate(chapter.get('narration', []), 1):
            if 'after_arrival' in item:
                start = arrival + item['after_arrival']
            else:
                start = chapter_start + item.get('start', .8)
            entry = {'id': f"{chapter['id']}-{i:02d}", 'chapter': chapter['id'],
                     'preferred_start': round(start, 3), 'text': item['text']}
            if 'gap_after' in item:
                entry['gap_after'] = item['gap_after']
            entries.append(entry)
    data = {
        'reference_audio': str(voice / 'candidate-a.wav'),
        'reference_text': '一千零五十七年，苏轼来到汴京。此后，他的一生将在庙堂与江湖之间，徐徐展开。',
        'entries': entries,
    }
    (voice / 'script.json').write_text(json.dumps(data, ensure_ascii=False, indent=2))
    lines = ['# 《此心安处》旁白稿', '']
    for item in entries:
        lines.append(f"## {item['id']}｜{item['preferred_start']:.3f}s")
        lines.append(item['text'])
        lines.append('')
    (voice / 'script.md').write_text('\n'.join(lines))
    print(f'VOICE SCRIPT PREPARED: {len(entries)} segments')


if __name__ == '__main__':
    main()
