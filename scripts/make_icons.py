"""Create original colorful SORTIQ icons, not copied from WinRAR."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
import math

OUT = Path(__file__).resolve().parent.parent / 'assets' / 'icons'
OUT.mkdir(parents=True, exist_ok=True)
S=4

def shape(name, size=48):
    z=size*S
    im=Image.new('RGBA',(z,z),(0,0,0,0)); d=ImageDraw.Draw(im)
    sc=lambda v: int(v*S)
    def rect(coords,fill,outline=None,radius=0,width=1):
        a=tuple(sc(v) for v in coords)
        if radius: d.rounded_rectangle(a, radius=sc(radius), fill=fill, outline=outline, width=sc(width))
        else: d.rectangle(a,fill=fill,outline=outline,width=sc(width))
    def ellipse(coords, fill, outline=None, width=1):
        d.ellipse(tuple(sc(v) for v in coords),fill=fill,outline=outline,width=sc(width))
    def line(coords, fill, width=2, joint='curve'):
        d.line([(sc(x),sc(y)) for x,y in coords],fill=fill,width=sc(width),joint=joint)
    def polygon(points, fill): d.polygon([(sc(x),sc(y)) for x,y in points],fill=fill)
    def text(x,y,s,fill=(255,255,255),sz=20):
        try: f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',sc(sz))
        except: f=ImageFont.load_default()
        d.text((sc(x),sc(y)),s,font=f,fill=fill,stroke_width=0)
    def folder(color=(245,172,46),front=(255,198,76)):
        rect((5,12,21,20),color,radius=3)
        rect((5,17,43,38),front,radius=4,outline=(183,114,34),width=1)
        rect((7,20,41,25),(255,226,150),radius=2)
    def paper(color):
        rect((10,5,35,42),(255,255,255),outline=(147,158,171),radius=2)
        polygon([(27,5),(35,13),(27,13)],(228,231,238))
        rect((11,19,34,40),color,radius=1)
        line([(15,12),(25,12)], (186,197,208),2)
    if name=='add':
        folder();ellipse((29,24,47,42),(40,168,89),(17,108,55),2);line([(38,28),(38,38)],'white',3);line([(33,33),(43,33)],'white',3)
    elif name=='remove':
        folder((231,144,57),(255,185,88));ellipse((29,24,47,42),(225,78,77),(165,43,51),2);line([(33,33),(43,33)],'white',3)
    elif name=='scan':
        folder((89,152,221),(108,184,239));ellipse((18,10,37,29),(245,251,255),(27,110,178),3);line([(33,27),(44,40)],(35,91,152),5)
    elif name=='organize':
        rect((5,27,43,42),(54,121,206),radius=3,outline=(31,71,144));rect((9,30,39,34),(146,206,255),radius=1)
        paper((83,192,112));polygon([(24,3),(24,18),(16,18),(31,32),(44,18),(35,18),(35,3)],(54,175,93));line([(31,8),(31,25)],(237,255,239),2)
    elif name=='undo':
        ellipse((7,7,41,41),(226,243,255),(56,131,212),2)
        d.arc((sc(12),sc(13),sc(37),sc(37)),start=305,end=140,fill=(32,110,195),width=sc(5))
        polygon([(8,22),(21,17),(18,30)],(32,110,195))
    elif name=='files':
        paper((61,138,234));text(14,20,'D',sz=14)
        rect((31,25,44,41),(62,178,94),radius=2)
    elif name=='history':
        ellipse((5,5,43,43),(241,250,255),(55,133,214),3);ellipse((10,10,38,38),(255,255,255))
        line([(24,12),(24,25),(33,30)],(28,112,188),4);ellipse((21,21,27,27),(45,126,202))
    elif name=='export':
        paper((50,166,99));text(11,20,'X',sz=14)
        polygon([(32,30),(40,30),(40,23),(48,34),(40,45),(40,38),(32,38)],(248,165,52))
    elif name=='demo':
        rect((7,14,41,40),(111,92,195),radius=5)
        for x,y,r in [(12,10,3),(36,8,4),(29,18,3),(40,25,2)]:
            line([(x-r,y),(x+r,y)],(255,180,38),2);line([(x,y-r),(x,y+r)],(255,180,38),2)
        text(13,21,'S',sz=15)
    elif name=='why':
        ellipse((5,4,43,42),(122,176,236),(30,90,171),2);text(16,9,'?',sz=25)
    elif name=='folder':
        folder()
    elif name=='folder-blue':
        folder((74,133,207),(112,174,245))
    elif name=='folder-purple':
        folder((138,105,203),(185,153,237))
    elif name=='folder-gray':
        folder((133,144,158),(183,191,201))
    elif name=='pdf':
        paper((213,55,64));text(12,22,'P',sz=11)
    elif name=='ppt':
        paper((230,113,34));text(13,21,'P',sz=12)
    elif name=='word':
        paper((39,111,203));text(11,21,'W',sz=10)
    elif name=='excel':
        paper((34,153,84));text(13,21,'X',sz=12)
    elif name=='archive':
        for off, c in [(6,(152,76,207)),(18,(79,146,221)),(30,(54,180,115))]:
            rect((8,off,39,off+10),c,radius=2,outline=(58,72,87))
        rect((22,7,25,40),(250,212,110));rect((21,24,27,32),(231,208,149),outline=(119,96,58),radius=1)
    elif name=='image':
        rect((5,7,43,40),(233,249,255),radius=3,outline=(75,141,196),width=2)
        ellipse((27,13,37,23),(252,197,76));polygon([(9,35),(19,22),(28,32),(34,27),(40,35)],(78,175,103))
    elif name=='file':
        paper((126,139,155));text(13,22,'•',sz=12)
    elif name=='app':
        folder((54,120,204),(83,169,248))
        rect((19,6,35,18),(250,175,54),radius=2)
        rect((30,23,43,40),(43,181,118),radius=3)
        text(32,24,'S',sz=12)
    return im.resize((size,size),Image.Resampling.LANCZOS)

names=['app','add','remove','scan','organize','undo','files','history','export','demo','why','folder','folder-blue','folder-purple','folder-gray','pdf','ppt','word','excel','archive','image','file']
for n in names:
    shape(n,48).save(OUT/f'{n}.png')
    shape(n,20).save(OUT/f'{n}-small.png')
shape('app',256).save(OUT/'app-256.png')
shape('app',256).save(OUT/'sortiq.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print('Created',len(names)*2+2,'icon assets')
