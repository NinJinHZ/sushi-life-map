import json
from pathlib import Path

PATH = Path('/Volumes/2T硬盘/NinjinOS/projects/此心安处-苏轼人生地图/sushi-terrain-test.ynv3ob/final-film/timeline.json')
CHANGES = {
    'fengxiang': {'year_end': 1064, 'arrival_year': 1061},
    'hangzhou': {'year_start': 1064, 'year_end': 1074, 'arrival_year': 1071},
    'mizhou': {'year_end': 1076, 'arrival_year': 1074},
    'xuzhou': {'year_start': 1076, 'year_end': 1079, 'arrival_year': 1077},
    'wutai': {'year_start': 1079, 'year_end': 1079, 'arrival_year': 1079},
}


def main():
    data = json.loads(PATH.read_text())
    for chapter in data['chapters']:
        chapter.update(CHANGES.get(chapter['id'], {}))
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print('Tenure years and poem years aligned.')


if __name__ == '__main__':
    main()
