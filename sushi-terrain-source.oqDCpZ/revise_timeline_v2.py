import json
import shutil
from pathlib import Path

ROOT = Path('/Volumes/2T硬盘/NinjinOS/projects/此心安处-苏轼人生地图/sushi-terrain-test.ynv3ob/final-film')
PATH = ROOT / 'timeline.json'
BACKUP = ROOT / 'timeline-before-v2-narrative.json'


def main():
    data = json.loads(PATH.read_text())
    if not BACKUP.exists():
        shutil.copy2(PATH, BACKUP)
    chapters = {item['id']: item for item in data['chapters']}

    bijing = chapters['bijing']
    bijing['waypoints'] = ['汉中', '汴京']
    bijing['hold_s'] = 14
    bijing['card']['lines'] = [
        '嘉祐二年，苏轼、苏辙同榜及第。',
        '曾巩、张载、程颢同列榜单，',
        '欧阳修担任主考官。',
        '后世称为“千年龙虎榜”。',
    ]
    bijing['narration'] = [
        {'start': .8, 'text': '嘉祐二年，苏轼与苏辙同榜及第。欧阳修读到他的文章，惊叹不已。'},
        {'after_arrival': .8, 'text': '这一榜被称为千年龙虎榜。苏轼、苏辙、曾巩，后来同列唐宋八大家；张载、程颢也同榜及第。主考官，是欧阳修。'},
    ]

    fengxiang = chapters['fengxiang']
    fengxiang['place'] = '凤翔府'
    fengxiang['waypoints'] = ['汴京', '凤翔']
    fengxiang['quote']['year'] = 1061
    fengxiang['narration'][0]['text'] = '嘉祐六年，苏轼赴凤翔任签书判官。这是他第一次正式到地方任职。'

    hangzhou = chapters['hangzhou']
    hangzhou['quote']['year'] = 1073
    hangzhou['narration'][0]['text'] = '熙宁四年，因议论新法不合，苏轼自请外任，来到杭州。西湖让他暂时远离朝堂，也让他的诗词有了另一种开阔。'

    mizhou = chapters['mizhou']
    mizhou['quote']['year'] = 1076
    mizhou['narration'][1]['text'] = '熙宁九年中秋，他想念远在济南的苏辙，写下：但愿人长久，千里共婵娟。'

    xuzhou = chapters['xuzhou']
    xuzhou['asset_caption'] = '徐州黄楼 · 现代重建建筑'

    wutai = chapters['wutai']
    wutai['card']['lines'] = [
        '御史台摘引《湖州谢上表》，',
        '又指其诗文讥讽新法。',
        '苏轼在湖州被捕，押回汴京。',
        '关押四个多月后，贬居黄州。',
    ]
    wutai['narration'] = [
        {'start': .8, 'text': '元丰二年，御史台指控苏轼用诗文讥讽新法。他在湖州被捕，押回汴京，关进御史台狱。'},
        {'after_arrival': .8, 'text': '这就是乌台诗案。关押四个多月后，他出狱，被贬到黄州。'},
    ]

    huangzhou = chapters['huangzhou']
    huangzhou['asset_caption'] = '黄州东坡赤壁 · 今日实景'
    huangzhou['early_quote'] = {
        'after_s': 7,
        'title': '念奴娇 · 赤壁怀古',
        'lines': ['大江东去，浪淘尽，', '千古风流人物。'],
        'source': '元丰五年 · 黄州',
        'year': 1082,
    }
    huangzhou['quote']['year'] = 1082
    huangzhou['narration'][1]['text'] = '元丰五年，他在黄州写下《赤壁怀古》。大江东去，浪淘尽，千古风流人物。'

    return_chapter = chapters['return']
    return_chapter['card']['lines'] = [
        '先量移汝州，继知登州。',
        '元丰八年回朝，',
        '后官至翰林学士。',
        '却仍不肯随声附和。',
    ]
    return_chapter['narration'][0]['text'] = '元丰七年，他离开黄州，量移汝州；次年短暂知登州，又被召回朝廷。'

    hangzhou2 = chapters['hangzhou2']
    hangzhou2['asset_caption'] = '杭州苏堤 · 今日实景'
    hangzhou2['card']['lines'] = [
        '元祐四年再任杭州，',
        '次年疏浚西湖，',
        '以葑泥筑成长堤，',
        '后人把它称为苏堤。',
    ]
    hangzhou2['narration'][0]['text'] = '元祐四年，他重返杭州。这一次，不只是游湖。第二年，他主持疏浚西湖，以葑草淤泥筑成长堤。后人把它叫作，苏堤。'

    huizhou = chapters['huizhou']
    huizhou['asset_caption'] = '惠州东坡纪念馆 · 现代建筑'
    huizhou['quote']['year'] = 1096
    huizhou['narration'][0]['text'] = '绍圣元年，苏轼被贬惠州。岭南路远，亲友离散，他仍种药、酿酒、修桥，认真安排眼前的生活。'

    danzhou = chapters['danzhou']
    danzhou['asset_caption'] = '儋州东坡书院 · 今址建筑'

    changzhou = chapters['changzhou']
    changzhou['hold_s'] = 24
    changzhou['quote']['year'] = 1101
    changzhou['narration'][0]['text'] = '元符三年，他获赦北归。渡海、入赣、下江南，路越走，故乡越近，身体却一天天衰弱。'

    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    total = sum(round(c['travel_s'] * 24) + round(c['hold_s'] * 24) for c in data['chapters'])
    print(f'V2 timeline: national={total} frames, all={total + data["opening_frames"]} frames, duration={(total + data["opening_frames"]) / 24:.2f}s')


if __name__ == '__main__':
    main()
