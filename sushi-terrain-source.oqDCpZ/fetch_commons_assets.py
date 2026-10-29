import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image


ASSETS = {
    'hangzhou2': 'File:Su Causeway 1 (2548).jpg',
    'xuzhou': 'File:徐州市黄楼.jpg',
    'huangzhou': 'File:Dōngpō - Red Cliff.jpg',
    'danzhou': 'File:Dongpo Academy 04.jpg',
    'huizhou': 'File:Dongpo-memorial.JPG',
}


def clean(value):
    return re.sub(r'<[^>]+>', '', value or '').replace('&quot;', '"').replace('&amp;', '&').strip()


def main():
    root = Path('/Volumes/2T硬盘/NinjinOS/projects/此心安处-苏轼人生地图/sushi-terrain-test.ynv3ob/final-film/asset-downloads')
    root.mkdir(exist_ok=True)
    credits = []
    for asset_id, title in ASSETS.items():
        directory = root / asset_id
        directory.mkdir(exist_ok=True)
        query = {
            'action': 'query', 'titles': title, 'prop': 'imageinfo',
            'iiprop': 'url|extmetadata', 'iiurlwidth': 1400, 'format': 'json',
        }
        request = urllib.request.Request(
            'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(query),
            headers={'User-Agent': 'SuShiFilmResearch/0.2'})
        data = json.load(urllib.request.urlopen(request, timeout=45))
        page = next(iter(data['query']['pages'].values()))
        info = page['imageinfo'][0]
        metadata = info.get('extmetadata', {})
        image_request = urllib.request.Request(info['thumburl'], headers={'User-Agent': 'SuShiFilmResearch/0.2'})
        content = urllib.request.urlopen(image_request, timeout=60).read()
        path = directory / 'source.jpg'
        path.write_bytes(content)
        with Image.open(path) as image:
            image.verify()
        credit = {
            'id': asset_id,
            'title': title,
            'creator': clean(metadata.get('Artist', {}).get('value')) or 'Wikimedia Commons contributor',
            'license': clean(metadata.get('LicenseShortName', {}).get('value')),
            'license_url': metadata.get('LicenseUrl', {}).get('value', ''),
            'source': info['descriptionurl'],
            'file': str(path),
        }
        (directory / 'credit.json').write_text(json.dumps(credit, ensure_ascii=False, indent=2))
        credits.append(credit)
        print(asset_id, title, credit['license'], flush=True)
    (root / 'credits.json').write_text(json.dumps(credits, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
