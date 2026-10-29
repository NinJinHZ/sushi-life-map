import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H=1280,720
SONG='/System/Library/Fonts/Supplemental/Songti.ttc'
CALLI=str(Path(__file__).resolve().parent.parent/'sushi-terrain-test.ynv3ob'/'opening-v2'/'fonts'/'MaShanZheng-Regular.ttf')
GOLD=(226,187,108);PAPER=(238,232,215);MUTED=(174,191,190)
F={'brand':ImageFont.truetype(SONG,16),'small':ImageFont.truetype(SONG,13),'year':ImageFont.truetype(SONG,39),'subtitle':ImageFont.truetype(SONG,22),'label':ImageFont.truetype(CALLI,27),'chapter':ImageFont.truetype(CALLI,100),'chapter_small':ImageFont.truetype(CALLI,52),'credit':ImageFont.truetype(SONG,11)}


def fade(frame,start,end,edge=14):
    if frame<start or frame>=end:return 0
    a=min(1,(frame-start)/edge,(end-frame)/edge)
    return max(0,a)


def sprite(text,font,fill,blur=0,alpha=255,stroke=0):
    pad=18
    probe=Image.new('RGBA',(10,10));d=ImageDraw.Draw(probe)
    box=d.textbbox((pad,pad),text,font=font,stroke_width=stroke)
    im=Image.new('RGBA',(box[2]+pad,box[3]+pad),(0,0,0,0));d=ImageDraw.Draw(im)
    d.text((pad,pad),text,font=font,fill=fill+(alpha,),stroke_width=stroke,stroke_fill=(3,8,10,alpha))
    if blur>0:im=im.filter(ImageFilter.GaussianBlur(blur))
    return im


def place(base,text,font,fill,x,y,blur=0,alpha=255,anchor='la',stroke=0):
    if alpha<=0:return
    im=sprite(text,font,fill,blur,alpha,stroke)
    if anchor=='mm':x-=im.width/2;y-=im.height/2
    elif anchor=='ra':x-=im.width
    base.alpha_composite(im,(int(x),int(y)))


def glow(d,x,y,alpha=255,scale=1):
    if not(-30<x<W+30 and -30<y<H+30):return
    for r,a in [(18,12),(11,24),(6,55)]:
        rr=r*scale;d.ellipse((x-rr,y-rr,x+rr,y+rr),fill=GOLD+(int(a*alpha/255),))
    r=3*scale;d.ellipse((x-r,y-r,x+r,y+r),fill=(255,239,192,alpha))


def vignette():
    im=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(im)
    for i in range(55):
        a=int((1-i/55)*1.2)
        d.rectangle((i,i,W-i-1,H-i-1),outline=(0,4,7,a))
    return im


VIGNETTE=vignette()


def compose(root,frame,raw_path,out_path):
    projection=json.loads((root/'opening-v2'/'projection.json').read_text()) if frame==1 else PROJECTION
    data=projection['frames'][str(frame)]
    raw=Image.open(raw_path).convert('RGBA')
    raw=Image.alpha_composite(raw,VIGNETTE)
    overlay=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(overlay)
    # Persistent, quiet series mark.
    d.rectangle((40,30,62,52),fill=(132,55,45,230))
    d.text((51,40),'苏',font=F['small'],fill=PAPER+(255,),anchor='mm')
    d.text((73,29),'此心安处',font=F['brand'],fill=GOLD+(225,))
    d.text((73,51),'苏轼的人生地图',font=F['credit'],fill=MUTED+(190,))
    d.text((W-40,H-24),'真实 DEM 地形  ·  连续运镜测试',font=F['credit'],fill=MUTED+(150,),anchor='ra')

    # One narrative sentence at a time, with independent soft entrances and exits.
    subtitles=[(12,72,'这一年，苏轼出生。'),(76,120,'两年后，弟弟苏辙出生。'),(132,204,'父子三人，离开眉山，前往汴京。'),(210,280,'出成都，过剑门，越秦岭。')]
    for start,end,text in subtitles:
        a=fade(frame,start,end,16)
        if a:
            blur=(1-a)*4
            place(overlay,text,F['subtitle'],PAPER,W/2,72,blur,int(255*a),'mm',1)

    # Small year readout, not a large information card.
    year_states=[(1,72,'1037','北宋 · 眉州眉山'),(72,120,'1039','北宋 · 眉州眉山'),(120,289,'1056','嘉祐元年 · 三苏出蜀')]
    for start,end,year,info in year_states:
        a=fade(frame,start,end,12)
        if a:
            place(overlay,year,F['year'],PAPER,52,545,(1-a)*3,int(245*a),'la',1)
            place(overlay,info,F['small'],MUTED,54,599,0,int(230*a))
            d.line((54,632,54+int(150*a),632),fill=GOLD+(int(130*a),),width=1)

    # Screen-space head and companions keep a constant, restrained glow.
    hx,hy,hz=data['head']
    if frame<24:
        t=frame/24;end_y=hy-170+170*t
        d.line((hx,hy-170,hx,end_y),fill=GOLD+(int(170*t),),width=1)
        glow(d,hx,end_y,int(255*t),.8)
    else:
        glow(d,hx,hy)
    if 72<=frame<120:
        a=fade(frame,72,120,12)
        glow(d,hx-25,hy+17,int(220*a),.62);glow(d,hx+25,hy+17,int(220*a),.62)
        place(overlay,'苏洵 · 父',F['small'],PAPER,hx-38,hy+27,0,int(220*a),'ra',1)
        place(overlay,'苏辙 · 弟',F['small'],PAPER,hx+38,hy+27,0,int(220*a),'la',1)
    elif frame>=120:
        next_data=projection['frames'][str(min(288,frame+1))]['head']
        dx,dy=next_data[0]-hx,next_data[1]-hy;length=max(math.hypot(dx,dy),.001)
        nx,ny=-dy/length,dx/length
        glow(d,hx+nx*9,hy+ny*9,220,.64);glow(d,hx-nx*9,hy-ny*9,220,.64)

    # Place names arrive with the route, using the same calligraphic voice as the chapter.
    offsets={'眉山':(16,10,'la'),'成都':(-16,-34,'ra'),'剑门关':(-18,-43,'ra'),'广元':(18,18,'la'),'汉中':(18,-30,'la')}
    for name,(x,y,z) in data['labels'].items():
        arrival=projection['arrivals'][name]
        if frame<arrival-5 or z<0:continue
        a=min(1,(frame-arrival+5)/16)
        if frame>276:a*=min(1,(288-frame)/12)
        dx,dy,anchor=offsets[name]
        place(overlay,name,F['label'],GOLD,x+dx,y+dy,(1-a)*3,int(245*a),anchor,1)

    # Calligraphic chapter characters enter independently, never as a solid card.
    chapter=[('壹',F['chapter'],1030,158,132),('出',F['chapter_small'],1056,294,140),('蜀',F['chapter_small'],1056,350,148)]
    for text,font,x,y,start in chapter:
        a=fade(frame,start,282,20)
        if a:
            place(overlay,text,font,GOLD,x,y+12*(1-a),(1-a)*7,int(245*a),'la',1)

    result=Image.alpha_composite(raw,overlay).convert('RGB')
    result.save(out_path,quality=95,subsampling=0)


def main():
    global PROJECTION
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--proof',action='store_true');args=parser.parse_args()
    root=Path(args.root);PROJECTION=json.loads((root/'opening-v2'/'projection.json').read_text())
    if args.proof:
        for frame in [1,72,132,216,288]:
            compose(root,frame,root/'opening-v2'/'proofs'/f'raw-{frame:04d}.png',root/'opening-v2'/'proofs'/f'final-{frame:04d}.jpg')
    else:
        for frame in range(1,289):
            compose(root,frame,root/'opening-v2'/'raw'/f'frame-{frame:04d}.png',root/'opening-v2'/'final'/f'frame-{frame:04d}.jpg')
            if frame%48==0:print(f'COMPOSITED {frame}/288')


if __name__=='__main__':main()
