"""字幕・エンジン不変・シーン境界・全演出の相対時刻を検算する。"""
from pathlib import Path
from bs4 import BeautifulSoup as BS
from html.parser import HTMLParser
import json, re, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
raw=(ROOT/'index.html').read_text();s=BS(raw,'html.parser')
tl=json.loads((ROOT/'_audio/timeline_v2.json').read_text())
errors=[]
def check(ok,msg):
    if not ok:errors.append(msg)
js=s.select_one('script').string
with tempfile.NamedTemporaryFile('w',suffix='.js') as f:
    f.write(js);f.flush();r=subprocess.run(['node','--check',f.name],capture_output=True,text=True)
    check(r.returncode==0,r.stderr)
def array(name):return json.loads(re.search(r'const '+name+r' = (\[.*?\]);',js,re.S).group(1))
caps=array('CAPS');ch=array('CH')
check(caps==[[r['start'],r['end'],r['cap'],r.get('read','')] for r in tl['rows'] if r['kind']=='cut'],'CAPS differs from timeline')
check([c[0] for c in ch]==[r['start'] for r in tl['rows'] if r['kind']=='title'],'CH timing differs')
check(float(re.search(r'const TOTAL = ([\d.]+)',js).group(1))==tl['total'],'TOTAL mismatch')
def normalize(v):
    v=re.sub(r'const TOTAL = [\d.]+','const TOTAL = X',v)
    for name in ['CH','CAPS']:v=re.sub(r'const '+name+r' = \[.*?\];','const '+name+' = X;',v,flags=re.S)
    return v
base=subprocess.check_output(['git','show','475de1f:index.html'],cwd=ROOT,text=True)
check(normalize(js)==normalize(BS(base,'html.parser').select_one('script').string),'Playback engine changed outside TOTAL/CH/CAPS')
scenes=s.select('.scene');prev=0
for i,sec in enumerate(scenes):
    a,b=map(float,[sec['data-start'],sec['data-end']]);d=round(b-a,5)
    check(abs(a-prev)<.001,f'scene {i}: gap/overlap {prev} to {a}')
    check(b>a,f'scene {i}: empty duration');prev=b
    for el in sec.find_all(True):
        for attr in ['data-in','data-out','data-click','data-sel','data-on','data-dur']:
            if attr in el.attrs:check(0<=float(el[attr])<=d+.001,f'scene {i}: {attr}={el[attr]} > {d} ({str(el)[:100]})')
        if el.has_attr('data-type') or el.has_attr('data-count'):
            end=float(el.get('data-in',0))+float(el.get('data-dur',2))
            check(end<=d+.001,f'scene {i}: type/count ends {end} > {d}')
        if el.has_attr('data-fx'):
            st,en=map(float,el['data-fx'].split(':')[:2])
            check(0<=st<en<=d+.001,f'scene {i}: fx {el["data-fx"]} outside {d}')
    if sec.has_attr('data-scroll'):
        times=[float(p.split(':')[0]) for p in sec['data-scroll'].split(',')]
        check(times==sorted(times) and max(times)<=d+.001,f'scene {i}: scroll invalid')
check(abs(prev-tl['total'])<.001,'Last scene end differs from TOTAL')
check(all(caps[i][1]<=caps[i+1][0] for i in range(len(caps)-1)),'CAPS overlap')
check(len(scenes)==raw.count('</section>'),'section closing count mismatch')
ids=[e['id'] for e in s.select('[id]')];check(len(ids)==len(set(ids)),'Duplicate element IDs')
for im in s.select('img[src]'):
    p=ROOT/im['src'];check(p.is_file(),f'Missing image {p}');check(p.stat().st_size<200000,f'Image over 200KB: {p}')
for id in ['calltimer','cc-calls','cc-conn','rec-elapsed','rec-sent','rec-seg','mt-us','mt-them']:
    check(s.select_one('#'+id) is not None,f'Missing engine ID: {id}')
for id in re.findall(r"\$\('#([\w-]+)'\)",js):
    check(s.select_one('#'+id) is not None,f'Missing player control: {id}')
if errors:
    print('\n'.join(errors));raise SystemExit(1)
print(f'PASS: JS構文 / エンジン不変 / {len(scenes)}連続シーン / {len(caps)}字幕 / {len(ch)}タイトル / 全演出時刻 / 画像 / ID')
