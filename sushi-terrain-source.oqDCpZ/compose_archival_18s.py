import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose_archival as ca

W, H = 1280, 720
END = 432
ERA_YEAR_FONT = ImageFont.truetype(ca.SONG, 32)


def add_frame_furniture(overlay, frame):
    d = ImageDraw.Draw(overlay)
    d.rectangle((26,22,1253,696),outline=(152,133,82,80),width=1)
    for x,y,sx,sy in [(26,22,1,1),(1253,22,-1,1),(26,696,1,-1),(1253,696,-1,-1)]:
        d.line((x,y,x+sx*14,y),fill=ca.GOLD+(170,),width=1)
        d.line((x,y,x,y+sy*14),fill=ca.GOLD+(170,),width=1)
    d.rectangle((42,37,64,63),fill=ca.RED+(235,))
    ca.text(d,(53,50),'苏',ca.F['small'],ca.PAPER,255,'mm')
    ca.tracked_text(d,(76,34),'苏轼行迹图',ca.F['brand'],3,ca.PAPER,245)
    ca.tracked_text(d,(77,58),'SU SHI  ·  1037—1101',ca.F['micro'],1,ca.MUTED,210)

    if frame < 192:
        index,place = '01','眉州眉山'
    elif frame < 396:
        index,place = '02','出蜀之路'
    else:
        index,place = '02','三苏出蜀'
    ca.text(d,(1219,33),index,ca.F['index'],ca.PAPER,240,'ra')
    ca.text(d,(1219,62),place,ca.F['small'],ca.GOLD,220,'ra')

    if frame < 96:
        year,era,event = '1037','北宋 · 景祐三年','苏轼出生'
    elif frame < 192:
        year,era,event = '1039','北宋 · 宝元二年','苏辙出生'
    else:
        year,era,event = '嘉祐元年','北宋 · 公元1056年','三苏出蜀'
    ca.text(d,(42,598),era,ca.F['small'],ca.GOLD,230)
    ca.text(d,(40,616),year,ERA_YEAR_FONT if frame >= 192 else ca.F['year'],ca.PAPER,250)
    if frame < 192:
        ca.text(d,(143,646),'年',ca.F['small'],ca.MUTED,220)
    ca.text(d,(42,664),event,ca.F['small'],ca.PAPER,225)

    y = 684
    d.line((224,y,1218,y),fill=(171,149,91,115),width=1)
    for year_value,label in ca.TIMELINE_TICKS:
        x = 224+(year_value-1037)/64*994
        d.line((x,y-4,x,y+4),fill=ca.GOLD+(160,),width=1)
        ca.text(d,(x,y-9),label,ca.F['micro'],ca.MUTED,180,'ms')
    current = 1037 if frame < 96 else 1039 if frame < 192 else 1056
    x = 224+(current-1037)/64*994
    d.ellipse((x-3,y-3,x+3,y+3),fill=ca.PAPER+(240,))


def compose(root,projection,cards,frame,raw_path,out_path,map_effect=None):
    raw = ca.grade_map(Image.open(raw_path),frame)
    output_size = raw.size
    shade = Image.new('RGBA',(W,H),(0,0,0,0))
    sd = ImageDraw.Draw(shade)
    for i in range(120):
        a = int(105*(1-i/120)**1.8)
        sd.line((0,i,W,i),fill=(3,5,3,a))
        sd.line((0,H-1-i,W,H-1-i),fill=(3,5,3,a))
    for i in range(75):
        a = int(70*(1-i/75))
        sd.rectangle((i,i,W-1-i,H-1-i),outline=(2,4,2,a))
    if shade.size != output_size:
        shade = shade.resize(output_size,Image.Resampling.LANCZOS)
    raw = Image.alpha_composite(raw,shade)
    map_layer = Image.new('RGBA',(W,H),(0,0,0,0))
    if map_effect is not None:
        map_effect(map_layer)
    ca.add_map_labels(map_layer, projection, frame,
                      draw_head=frame > projection.get('fall_end', 52))
    if map_layer.size != output_size:
        map_layer = map_layer.resize(output_size,Image.Resampling.LANCZOS)
    raw = Image.alpha_composite(raw,map_layer)

    ui = Image.new('RGBA',(W,H),(0,0,0,0))
    add_frame_furniture(ui,frame)
    # The main title has its own cold open; the map begins without duplicate typography.
    card_alpha = ca.visibility(frame,30,END,24)
    if card_alpha > 0:
        if 168 <= frame < 192:
            mix = ca.smooth((frame-168)/24)
            card = Image.blend(cards['birth'],cards['journey'],mix)
        else:
            card = cards['birth'] if frame < 168 else cards['journey']
        if card_alpha < 1:
            card = card.copy()
            card.putalpha(card.getchannel('A').point(lambda p:int(p*card_alpha)))
        ui.alpha_composite(card,(899,74))
    if ui.size != output_size:
        ui = ui.resize(output_size,Image.Resampling.LANCZOS)
    result = Image.alpha_composite(raw,ui).convert('RGB')
    if frame < 12:
        result = Image.blend(Image.new('RGB',output_size,(6,8,5)),result,ca.smooth(frame/12))
    result.save(out_path,quality=95,subsampling=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--proof',action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    projection = json.loads((root/'opening-v3'/'projection.json').read_text())
    cards = {name:ca.make_card(root,name) for name in ('birth','journey')}
    if args.proof:
        out = root/'opening-v3'/'archive-proofs'
        out.mkdir(exist_ok=True)
        for frame in [36,120,204,312,396,432]:
            compose(root,projection,cards,frame,
                    root/'opening-v3'/'proofs'/f'raw-{frame:04d}.png',
                    out/f'archive-{frame:04d}.jpg')
    else:
        out = root/'opening-v3'/'archive-final'
        out.mkdir(exist_ok=True)
        for frame in range(1,END+1):
            compose(root,projection,cards,frame,
                    root/'opening-v3'/'raw'/f'frame-{frame:04d}.png',
                    out/f'frame-{frame:04d}.jpg')
            if frame%72==0:
                print(f'18S COMPOSITED {frame}/{END}',flush=True)


if __name__ == '__main__':
    main()
