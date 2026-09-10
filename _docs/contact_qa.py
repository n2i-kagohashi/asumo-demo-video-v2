from pathlib import Path
from PIL import Image, ImageDraw
p=Path(__file__).resolve().parent/'qa'
files=sorted((f for f in p.glob('*.png') if f.stem.replace('.','').isdigit()),key=lambda f:float(f.stem))
for batch in range((len(files)+11)//12):
    group=files[batch*12:(batch+1)*12]
    out=Image.new('RGB',(1920,1528),'#dbe5e2');draw=ImageDraw.Draw(out)
    for i,f in enumerate(group):
        im=Image.open(f);x=(i%3)*640;y=(i//3)*382
        out.paste(im.resize((640,360)),(x,y+22))
        draw.text((x+12,y+4),f.stem+' seconds',fill='#163e31')
    out.save(p/f'contact-{batch+1}.jpg')
