import argparse
import json
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
FONT = "/System/Library/Fonts/Supplemental/Songti.ttc"
GOLD = (226,190,116)
PAPER = (241,235,219)
MUTED = (185,200,198)


def fnt(size):
    return ImageFont.truetype(FONT, size)


F = {'eyebrow':fnt(16),'date':fnt(47),'title':fnt(33),'subtitle':fnt(19),'quote':fnt(20),'label':fnt(20),'small':fnt(15),'credit':fnt(12)}


@lru_cache(maxsize=16)
def text_layer(date,title,subtitle,quote):
    layer = Image.new('RGBA',(W,H),(0,0,0,0))
    mask = Image.new('L',(W,1))
    mask.putdata([int(168*max(0,1-x/(W*.49))**1.4) for x in range(W)])
    mask = mask.resize((W,H))
    layer = Image.composite(Image.new('RGBA',(W,H),(3,10,13,255)),layer,mask)
    bottom = Image.new('L',(1,H))
    bottom.putdata([int(120*max(0,(y/H-.72)/.28)) for y in range(H)])
    bottom = bottom.resize((W,H))
    layer = Image.composite(Image.new('RGBA',(W,H),(3,10,13,255)),layer,bottom)
    d = ImageDraw.Draw(layer)
    d.text((52,38),'苏轼的人生地图  ·  序章',font=F['eyebrow'],fill=GOLD+(235,))
    d.line((52,66,138,66),fill=GOLD+(150,),width=1)
    d.text((52,79),date,font=F['date'],fill=PAPER+(255,),stroke_width=1,stroke_fill=(2,7,9,160))
    d.text((52,145),title,font=F['title'],fill=PAPER+(255,),stroke_width=2,stroke_fill=(2,7,9,180))
    d.text((52,195),subtitle,font=F['subtitle'],fill=MUTED+(245,),stroke_width=1,stroke_fill=(2,7,9,160))
    d.text((52,625),quote,font=F['quote'],fill=PAPER+(245,),stroke_width=2,stroke_fill=(2,7,9,190))
    d.text((W-50,42),'此心安处',font=F['subtitle'],fill=GOLD+(225,),anchor='ra')
    d.text((52,H-25),'真实 DEM 地形  ｜  行迹为片头空间示意',font=F['credit'],fill=MUTED+(175,))
    return layer


def glow(d,x,y,scale=1.0,alpha=255,color=GOLD):
    for radius,a in [(15,18),(10,32),(6,65)]:
        r=radius*scale
        d.ellipse((x-r,y-r,x+r,y+r),fill=color+(int(a*alpha/255),))
    r=3.2*scale
    d.ellipse((x-r,y-r,x+r,y+r),fill=(255,239,194,alpha))


def label(d,text,x,y,alpha=255):
    if not (-20 < x < W+20 and -20 < y < H+20):
        return
    offsets={'眉山':(16,12,'la'),'成都':(-14,-22,'ra'),'汴京':(18,-24,'la'),'长安':(-20,-35,'ra'),'洛阳':(20,35,'la'),'剑门关':(-20,-42,'ra'),'广元':(20,22,'la'),'汉中':(16,-22,'la')}
    dx,dy,anchor=offsets.get(text,(14,-22,'la'))
    d.text((x+dx,y+dy),text,font=F['label'],fill=(246,224,175,alpha),anchor=anchor,stroke_width=2,stroke_fill=(2,7,9,min(alpha,230)))


def route_point(route,progress):
    pos=min(max(progress,0),1)*(len(route)-1)
    i=min(int(pos),len(route)-2)
    t=pos-i
    a,b=route[i],route[i+1]
    x=a[0]*(1-t)+b[0]*t
    y=a[1]*(1-t)+b[1]*t
    z=a[2]*(1-t)+b[2]*t
    dx=b[0]-a[0];dy=b[1]-a[1]
    length=max(math.hypot(dx,dy),.001)
    return x,y,z,-dy/length,dx/length


def travelers(d,route,progress,count=3,alpha=255):
    x,y,z,nx,ny=route_point(route,progress)
    if z<0:
        return
    for j in range(count):
        offset=(j-(count-1)/2)*11
        glow(d,x+nx*offset,y+ny*offset,1.0 if j==count//2 else .72,alpha)


def raw_index(segment,i):
    if segment=='meishan':
        if i<24:return 48
        if i<72:return 48-(i-24)
        return 1
    return max(1,48-i) if i<48 else 1


def state(segment,i):
    if segment=='meishan':
        if i<72:return ('1037','苏轼出生','眉州 · 眉山','这一年，世上还没有“苏东坡”。')
        return ('1039','弟弟苏辙出生','眉州 · 眉山','父亲苏洵，将带着两个儿子走出四川。')
    if segment=='sichuan':
        return ('1056','三苏出蜀','苏洵 · 苏轼 · 苏辙','出成都，过剑门，越秦岭，前往汴京。')
    if i<84:
        return ('1056','一路向东','眉山 → 长安 → 洛阳 → 汴京','同一个光点，继续走向北宋的舞台。')
    return ('1057','二苏同榜进士及第','嘉祐二年 · 东京汴京','苏轼、苏辙、曾巩、张载、程颢……千年龙虎榜。')


def composite_segment(root,segment,length):
    projection=json.loads((root/'opening'/'projections'/f'{segment}.json').read_text())
    out_dir=root/'opening'/'composited'/segment
    out_dir.mkdir(parents=True,exist_ok=True)
    for i in range(length):
        raw_no=raw_index(segment,i)
        raw=Image.open(root/'frames'/segment/f'frame-{raw_no:04d}.png').convert('RGBA')
        frame_data=projection['frames'][str(raw_no)]
        layer=text_layer(*state(segment,i))
        dynamic=Image.new('RGBA',(W,H),(0,0,0,0))
        d=ImageDraw.Draw(dynamic)
        labels=frame_data['labels']
        if segment=='meishan':
            x,y,z=labels['眉山']
            if i<24:
                t=i/23
                end_y=y-180+180*t
                d.line((x,y-180,x,end_y),fill=GOLD+(int(180*t),),width=2)
                glow(d,x,end_y,.8,int(255*t))
            else:
                glow(d,x,y,1.0)
            if i>=72:
                a=min(255,int((i-72)/18*255))
                glow(d,x-30,y+20,.68,a)
                glow(d,x+30,y+22,.68,a)
                d.text((x-42,y+43),'苏洵 · 父',font=F['small'],fill=PAPER+(a,),anchor='ra',stroke_width=2,stroke_fill=(2,7,9,a))
                d.text((x+42,y+43),'苏辙 · 弟',font=F['small'],fill=PAPER+(a,),anchor='la',stroke_width=2,stroke_fill=(2,7,9,a))
            label(d,'眉山',x,y)
        elif segment=='sichuan':
            for name,(x,y,z) in labels.items():
                if z>0 and not (x<390 and y<235):label(d,name,x,y)
            travelers(d,frame_data['route'],i/(length-8),3)
        else:
            for name,(x,y,z) in labels.items():
                if i>=84 and name in {'长安','洛阳'}:
                    continue
                if z>0 and not (x<390 and y<235):label(d,name,x,y)
            travelers(d,frame_data['route'],min(1,i/84),3 if i<84 else 2)
            if i>=84:
                a=min(255,int((i-84)/20*255))
                bx,by,bz=labels['汴京']
                stars=[('苏辙',-48,42),('曾巩',60,-72),('张载',118,-12),('程颢',72,52)]
                for name,dx,dy in stars:
                    x,y=bx+dx,by+dy
                    d.line((bx,by,x,y),fill=GOLD+(int(a*.28),),width=1)
                    glow(d,x,y,.65,a)
                    d.text((x+10,y-19),name,font=F['small'],fill=PAPER+(a,),stroke_width=2,stroke_fill=(2,7,9,a))
        result=Image.alpha_composite(raw,layer)
        result=Image.alpha_composite(result,dynamic).convert('RGB')
        result.save(out_dir/f'frame-{i+1:04d}.jpg',quality=95,subsampling=0)
        if i in ({'meishan':[12,96],'sichuan':[72],'china':[120]}[segment]):
            result.save(root/'opening'/f'{segment}-{i+1:04d}-proof.jpg',quality=95,subsampling=0)
    print(f'COMPOSITED {segment}: {length} frames')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    args=parser.parse_args()
    root=Path(args.root)
    composite_segment(root,'meishan',120)
    composite_segment(root,'sichuan',120)
    composite_segment(root,'china',144)


if __name__=='__main__':
    main()
