import json
import shutil
from pathlib import Path

ROOT = Path('/Volumes/2T硬盘/NinjinOS/projects/此心安处-苏轼人生地图/sushi-terrain-test.ynv3ob/final-film')
PATH = ROOT / 'timeline.json'


def main():
    data = json.loads(PATH.read_text())
    backup = ROOT / 'timeline-before-v3.json'
    if not backup.exists():
        shutil.copy2(PATH, backup)
    data['previous_sites'] = ['眉山']
    chapters = {chapter['id']: chapter for chapter in data['chapters']}
    bijing = chapters['bijing']
    bijing['waypoints'] = ['眉山', '汴京']
    bijing['travel_s'] = 0
    bijing['hold_s'] = 24
    huangzhou = chapters['huangzhou']
    huangzhou['narration'][2]['text'] = '《定风波》，也写于这里。竹杖芒鞋轻胜马，谁怕？一蓑烟雨任平生。'
    huangzhou['narration'][2]['after_arrival'] = 17.7
    huangzhou['quote']['after_s'] = 16.9
    changzhou = chapters['changzhou']
    changzhou['hold_s'] = 28
    changzhou['closing_quote'] = {
        'after_s': 12,
        'title': '定风波 · 南海归赠王定国侍人寓娘',
        'lines': ['此心安处，', '是吾乡。'],
        'source': '元丰六年 · 片名出处',
        'year': 1083,
    }
    changzhou['final_title_after_s'] = 18.4
    changzhou['credits_after_s'] = 18.4
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    national = sum(round(c['travel_s'] * 24) + round(c['hold_s'] * 24) for c in data['chapters'])
    print(f'V3 timeline: {national + data["opening_frames"]} frames, {(national + data["opening_frames"]) / 24:.2f}s')


if __name__ == '__main__':
    main()
