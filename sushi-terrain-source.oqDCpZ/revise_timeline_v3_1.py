import json
import shutil
from pathlib import Path

ROOT = Path('/Volumes/2T硬盘/NinjinOS/projects/此心安处-苏轼人生地图/sushi-terrain-test.ynv3ob/final-film')
PATH = ROOT / 'timeline.json'


def main():
    data = json.loads(PATH.read_text())
    backup = ROOT / 'timeline-before-v3.1.json'
    if not backup.exists():
        shutil.copy2(PATH, backup)
    chapters = {chapter['id']: chapter for chapter in data['chapters']}
    wutai = chapters['wutai']
    wutai['quote'] = {
        'after_s': 5.0,
        'title': '狱中寄子由二首 · 其一',
        'lines': ['与君世世为兄弟，', '更结来生未了因。'],
        'source': '元丰二年 · 御史台狱',
        'year': 1079,
    }
    wutai['narration'][1]['text'] = (
        '这就是乌台诗案。关押四个多月后，他走出御史台狱。'
    )
    wutai['narration'] = [item for item in wutai['narration']
                          if item['text'] != '与君世世为兄弟，更结来生未了因。']
    wutai['narration'].append({
        'after_arrival': 5.8,
        'text': '与君世世为兄弟，更结来生未了因。',
    })
    chapters['huangzhou']['narration'][0]['text'] = (
        '出狱以后，他被贬到黄州，没有实权。俸禄微薄，便在城东的坡地耕种；'
        '自此，世间多了一个名字，苏东坡。'
    )
    danzhou = chapters['danzhou']
    danzhou['quote'] = {
        'after_s': 4.6,
        'title': '减字木兰花 · 己卯儋耳春词',
        'lines': ['不似天涯，', '卷起杨花似雪花。'],
        'source': '元符二年 · 儋州',
        'year': 1099,
    }
    danzhou['narration'] = [item for item in danzhou['narration']
                            if item['text'] != '不似天涯，卷起杨花似雪花。']
    danzhou['narration'].append({
        'after_arrival': 5.2,
        'text': '不似天涯，卷起杨花似雪花。',
    })
    changzhou = chapters['changzhou']
    # 6648 + round(17.041666… * 24) = national frame 7057.
    # With the 504-frame opening, the finale begins at exactly 05:15.000.
    changzhou['final_title_after_s'] = 17.041666666666668
    changzhou['credits_after_s'] = 17.041666666666668
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print('V3.1 timeline: Danzhou quote added; finale starts at 05:15.000')


if __name__ == '__main__':
    main()
