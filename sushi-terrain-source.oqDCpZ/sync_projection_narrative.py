import copy
import json
from pathlib import Path

ROOT = Path('/Volumes/2T硬盘/NinjinOS/projects/此心安处-苏轼人生地图/sushi-terrain-test.ynv3ob/final-film')
KEYS = ('card', 'quote', 'early_quote', 'closing_quote', 'narration', 'asset_caption',
        'year_start', 'year_end', 'arrival_year', 'final_title_after_s', 'credits_after_s')


def main():
    projection_path = ROOT / 'projection.json'
    projection = json.loads(projection_path.read_text())
    timeline = json.loads((ROOT / 'timeline.json').read_text())
    source = {chapter['id']: chapter for chapter in timeline['chapters']}
    for chapter in projection['chapters']:
        for key in KEYS:
            if key in source[chapter['id']]:
                chapter[key] = copy.deepcopy(source[chapter['id']][key])
            else:
                chapter.pop(key, None)
        arrival_year = chapter.get('arrival_year', chapter['year_end'])
        for frame in range(chapter['start_frame'], chapter['end_frame'] + 1):
            local = frame - chapter['start_frame'] + 1
            if local <= chapter['travel_frames']:
                progress = (local - 1) / max(1, chapter['travel_frames'] - 1)
                year = round(chapter['year_start'] + (arrival_year - chapter['year_start']) * progress)
            else:
                progress = (local - chapter['travel_frames'] - 1) / max(1, chapter['hold_frames'] - 1)
                year = round(arrival_year + (chapter['year_end'] - arrival_year) * progress)
            projection['frames'][str(frame)]['year'] = year
    projection_path.write_text(json.dumps(projection, ensure_ascii=False, separators=(',', ':')))
    print('Projection narrative content synchronized; camera geometry unchanged.')


if __name__ == '__main__':
    main()
