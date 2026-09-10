"""v1 の画面部品を再編集。元 worktree・元音声・再生エンジンは変更しない。"""
from pathlib import Path
from copy import deepcopy
import json, re, subprocess, shutil
from html import escape
from bs4 import BeautifulSoup as BS

ROOT = Path(__file__).resolve().parents[1]
BASE = subprocess.check_output(['git', 'show', '475de1f:index.html'], cwd=ROOT, text=True)
doc = BS(BASE, 'html.parser')
tl = json.loads((ROOT/'_audio/timeline_v2.json').read_text())
rows = {r['no']: r for r in tl['rows']}
original = list(doc.select('.scene'))
def old(nav, idx=0): return deepcopy([s for s in original if s.get('data-nav')==nav][idx])
def html(s): return BS(s, 'html.parser').find()
def textof(el): return el.get_text(' ', strip=True)
def pick(root, selector, phrase):
    return next(e for e in root.select(selector) if phrase in textof(e))
def clean(el):
    """旧時間だけ外す。画面の部品・文言を再利用。"""
    for e in [el]+list(el.find_all(True)):
        if e.has_attr('data-type'): e.clear(); e.append(e['data-type'])
        for k in list(e.attrs):
            if k.startswith('data-'): del e[k]
        if e.has_attr('class'):
            e['class']=[c for c in e['class'] if c not in ['cue','show','gone','click']]
    return el
def strip_fx(el):
    for e in [el]+list(el.select('[data-fx],[data-fxz]')):
        e.attrs.pop('data-fx',None);e.attrs.pop('data-fxz',None)
def cls(el, name): el['class']=list(dict.fromkeys(el.get('class',[])+name.split()));return el
def cue(el, start=0, end=None, layout=False):
    cls(el,'show' if layout else 'cue');el['data-in']=str(start)
    if end is not None:el['data-out']=str(end)
    return el
def fx(el,a,b,label,z=1.1): el['data-fx']=f'{a}:{b}:{label}';el['data-fxz']=str(z);return el
def typing(el, start, dur, value=None):
    value = value if value is not None else el.get('data-type',textof(el))
    el.clear();el['data-type']=value;el['data-in']=str(start);el['data-dur']=str(dur);cls(el,'type');return el
def click(el,t):el['data-click']=str(t);return el
def put(target,*parts):
    for p in parts:target.append(html(p) if isinstance(p,str) else p)
def only_rows(el,n):
    for tb in el.select('tbody'):
        for r in tb.find_all('tr',recursive=False)[n:]:r.decompose()
def columns(table, indexes):
    for tr in table.select('tr'):
        for i,cell in enumerate(tr.find_all(['td','th'],recursive=False)):
            if i not in indexes:cell.decompose()
def panel(root, title):
    exact=[p for p in root.select('.panel') if p.select_one('h2,h3') and title in textof(p.select_one('h2,h3'))]
    return clean((exact[0] if exact else pick(root,'.panel',title)).extract())
def remove(root, selector):
    for e in list(root.select(selector)):e.decompose()
def toast(sec,msg,t,end):
    put(sec,f'<div class="toast cue" data-in="{t}" data-out="{end}"><div class="banner ok">{msg}</div></div>')
def scene(nav, step, a, b, source=None):
    s=html(f'<section class="scene edited" data-start="{a}" data-end="{b}" data-nav="{nav}" data-step="{step}"><div class="page"><div class="container"></div></div></section>')
    c=s.select_one('.container')
    if source:put(c,clean(source.select_one('.page-head').extract()))
    return s,c
def slot(sec,el,a,b=None):
    cls(el,'v2-slot');cue(el,a,b);sec.select_one('.container').append(el);return el
new=[]
def add(s):new.append(s);return s

# 既存の長い導入エフェクトを使わず、章カードは0.3秒のフェードだけ。
for n in [1,2,4,14,23,27,34,44,50]:
    r=rows[n];nextrow=tl['rows'][tl['rows'].index(r)+1] if n!=50 else None
    end=nextrow['start'] if nextrow else tl['total']
    if n==44:end=202.5  # 2秒のカード後、無音部分は入金画面の見せ場へ。
    s=html(f'<section class="scene full v2-title" data-cinema="1" data-start="{r["start"]}" data-end="{end}" data-step="0" data-row="{n}"><div class="tcard"><div class="tcard-brand">ASUMO</div></div></section>')
    card=s.select_one('.tcard')
    if n==1:
        lines=r['cap'].split('\n')
        for i,line in enumerate(lines):
            label=escape(line).replace('営業プロセスを','営業プロセスを<br>') if i==0 else escape(line)
            el=html(f'<h2 class="tcard-title title-line">{label}</h2>')
            cue(el,0 if i==0 else 5.65,5.5 if i==0 else None);put(card,el)
    elif n==50:
        ending=deepcopy(original[-1].select_one('.end-title'))
        clean(ending);remove(ending,'.et-halo,.et-flash,.et-shine')
        ending.select_one('.et-sub').string=r['cap'].replace('ASUMO','')
        card.clear();put(card,ending)
    else:put(card,f'<h2 class="tcard-title">{escape(r["cap"]).replace(chr(10),"<br>")}</h2>')
    add(s)

# 実際の11工程と一致する進行ボード。左側は既存の実サイドバー。
s,c=scene('/list-build',0,12.67,16.96,old('/list-build'))
c.select_one('h1').string='求人広告営業の11工程'
c.select_one('.meta').string='リスト作成から請求まで'
remove(c,'.flow-strip')
board=clean(deepcopy(original[-1].select_one('.end-board')))
board['class']=['overview-board'];remove(board,'.eb-h,.eb-note')
names=['リスト作成','メール送信','フォーム送信','テレアポ','初回商談資料','商談議事録','2回目商談資料','見積','申し込み','掲載','請求']
for i,(el,name) in enumerate(zip(board.select('.eb'),names)):
    el.clear();put(el,f'<i>{i+1}</i>');el.append(name);cue(el,.15+i*.14)
put(c,board)
marker=html('<div class="sidebar-focus" aria-hidden="true"></div>');fx(marker,.4,4.1,'11工程をひとつのシステムで',1);put(s,marker);add(s)

# リスト作成: 2つの作り方 → 条件 → 作成 → 根拠つき結果。スクロール圧縮はしない。
o=old('/list-build');s,c=scene('/list-build',1,19.31,54.2,o)
ps=o.select('.container > .panel')
choice=clean(ps[0].extract());choice.append(clean(o.select_one('.banner.info').extract()))
choice.select_one('.banner').string='asumo が持っている企業を ICP適合とインテントで選びます。'
typing(choice.select_one('.banner'),4.5,2.8)
slot(s,choice,0,14.05);fx(choice,4.5,13.7,'2つの作り方',1.06)
buttons=choice.select('.btn')
if buttons:click(buttons[0],10.7)
cond=clean(ps[1].extract())
for e in list(cond.select('details')):
    if not e.has_attr('open'):e.decompose()
for e in list(cond.find_all(recursive=False)):
    if e.name=='p' or e.get('style','').startswith('border-top:') or (e.get('class')==['row'] and 'キーワード' in textof(e)):e.decompose()
for field in cond.select('details .field'):
    groups=field.select('.pickset')
    if len(groups)==2:
        t=16 if '所在地' in textof(field) else 17.5
        cue(groups[0],0,t,True);cue(groups[1],t,None,True)
        click(groups[0].select('.pill')[0 if t==16 else 3],t-.45)
for field in cond.select('.field'):
    if 'ICP適合 最低点' in textof(field):
        for el in field.select('.inp')[1:]:el.decompose()
for el in cond.select('.inp'):
    if textof(el).replace(' ','')=='6060':el.string='60'
cls(cond,'conditions-compact');slot(s,cond,14.05,20.55);fx(cond,14.2,20.2,'地域・業種で条件を絞る',1.02)
create=clean(ps[2].extract());slot(s,create,20.55,26.2)
for i,e in enumerate(create.select('.type')):typing(e,20.8+i*1.5,1.4)
click(pick(create,'.btn','リストを作る'),23.25);fx(create,20.8,26,'条件に合う企業をリストに',1.08)
result=clean(ps[3].extract());only_rows(result,2)
columns(result.select_one('table'),[0,1,2,3,8,9])
slot(s,result,26.2);cls(result,'result-list')
for i,e in enumerate(result.select('tbody > tr')):cue(e,26.2+i*.45)
fx(result,28.25,34.5,'1社ごとの「なぜ今か」まで',1.06)
toast(s,'✅ 「首都圏・運輸物流・未架電（9月第2週）」（BL0007）を作りました。そのまま架電できます。',25.3,28.2);add(s)

# CSV は列対応が分かるプレビューと投入完了に絞る。
o=old('/list-import');s,c=scene('/list-import',1,54.2,57.89,o)
p=panel(o,'プレビュー');only_rows(p,2);put(c,p)
e=panel(o,'投入実行');confirm=pick(e,'.btn','確定して投入').extract();e.clear();put(e,confirm)
put(e,'<span class="small cue" data-in="1.45" style="margin-left:20px">投入結果 ／ 合計 378 行　登録 341　更新 24　スキップ 13</span>')
put(c,e);click(pick(e,'.btn','確定して投入'),.55)
fx(p,.1,3.5,'CSVの列対応を自動推定',1.03)
toast(s,'✅ 投入完了：新規 341 / 更新 24 件',1.45,3.69);add(s)

# 一斉DM: 一覧は2社、プレビューと送信結果のみに絞る。
o=old('/outreach');s,c=scene('/outreach',2,57.89,63.44,o)
left=panel(o,'対象企業（DM可）');only_rows(left,2);columns(left.select_one('table'),[0,1,6,7])
right=panel(o,'一斉DM')
for field in list(right.find_all('div',class_='field',recursive=False)):
    if not any(k in textof(field) for k in ['プレビュー（','文面のパーソナライズ']):field.decompose()
remove(right,'.field > .small.muted')
for e in list(right.select('.chk'))[1:]:e.decompose()
g=html('<div class="v2-two"></div>');put(g,left,right);put(c,g)
for i,el in enumerate(right.select('.type')):typing(el,.25+i*.6,1.8)
click(pick(right,'.btn','選択企業に一斉DM'),2.6)
for td in left.select('tbody tr td:last-child'):
    td.clear();put(td,'<span class="pill pending show" data-in="0" data-out="3.25">未着手</span>','<span class="pill done show" data-in="3.25">送信済</span>')
fx(right,.1,5.4,'企業の情報から文面を作り、Gmailから送信',1.06);add(s)

# フォーム: 実投稿はしない。下調べ→文面・URLの準備のみ。
o=old('/form-outreach');s,c=scene('/form-outreach',3,63.44,69.71,o)
grid=o.select_one('.container > div[style*="grid"]');clean(grid);cls(grid,'form-compact')
only_rows(grid,2)
for table in grid.select('table'):columns(table,[0,1,2,4])
for pill in list(grid.select('tbody .pill')):
    if textof(pill)=='送信済':pill.decompose()
banner=grid.select_one('.banner.error')
banner.string='「営業お断り」の明記がある企業は選べません。'
remove(grid,'p.tiny, p.small.muted, div.small.muted, ol.small.muted')
put(c,grid)
bs=grid.select('.btn')
for b in bs:
    if '下調べ' in textof(b):click(b,.6)
    if 'フォームを展開' in textof(b):click(b,3.25)
toast(s,'下調べ 2 社（フォーム特定 2 社・営業お断り 0 社）',1.3,3.15)
toast(s,'2社のフォーム文面を展開しました',4.1,6.27)
preview=html('<div class="panel cue form-output" data-in="3.8"><h2>ロジテック物流株式会社</h2><div class="small muted">https://www.logitech-buturyu.example.jp/contact</div><h3>貼り付けシート</h3><div class="field"><label>本文</label><div class="ta"><span class="type" data-in="3.9" data-dur="1.35" data-type="貴社の採用ページで中型ドライバーの募集を拝見しました。通勤圏の登録者データをもとに、採用の進め方をご案内いたします。"></span></div></div><span class="btn secondary">📋 URL開く+文面コピー</span> <span class="small muted">投稿は担当者が手で行う</span></div>')
put(c,preview)
preview['data-in']='3.65';preview.select_one('h3').string='貼り付ける項目'
cue(grid.select_one('.panel'),0,3.65)
fx(preview,3.65,6.25,'貼り付けシートで文面を準備',1.02)
add(s)

# テレアポは旧コックピットをそのまま再配置。約40秒を確保。
o=old('/teleapo');s,c=scene('/teleapo',4,72.06,111.98,o)
cock=o.select_one('.tcpit').extract();strip_fx(cock)
# 個別の時間は台本の意味に合わせて付け直す（全体倍率で圧縮しない）。
mapping={5.1:0,7:7,17.8:10.2,18.4:11.0,20:12.6,26.5:34.0,10.5:23.5,13.2:24.2,16.3:19.8,
  23:28,23.2:28.2,23.4:28.4,23.5:28.5,23.7:28.7,23.8:28.8,24:29,24.2:29.2,
  9.9:22.8,12.7:25.6,13.1:18.4,17:21.4,25:30,
  27.3:35.0,27.7:35.4,28.1:35.8,28.5:36.2,29:36.5,29.4:36.8,29.8:37,30.3:37.2,32:35}
for el in [cock]+list(cock.find_all(True)):
    for k in ['data-in','data-out','data-on','data-sel']:
        if k in el.attrs:el[k]=str(mapping.get(float(el[k]),float(el[k])))
    el.attrs.pop('data-click',None)
cock['data-in']='0';cls(cock,'v2-cockpit')
left,center,right=cock.select_one('.cockpit').find_all(recursive=False)
for e in list(left.select('.rs-sec'))[1:]:e.decompose()
remove(left,'.co-person + .small, .f, .hotset')
remove(right,'.auto')
memo=right.select_one('.memo-big');typing(memo.select_one('.type'),7.2,21.0)
memo.select_one('.ta')['style']='min-height:115px;font-size:13px'
for lab in list(right.select('.seclab')):
    if any(k in textof(lab) for k in ['手ごたえ','担当者接続','採用ニーズ']):
        nxt=lab.find_next_sibling();nxt.decompose();lab.decompose()
for e in list(right.select('.show[style*="border:1px solid"]')):e.decompose()
flags=pick(right,'.pickset','リストホット化') if False else right.select_one('.pickset')
for i,e in enumerate(flags.select('.pick')):
    e.attrs.pop('data-on',None);e['data-on']=str([23.2,18.5,17.2][i] if i<3 else 19.8)
for el in flags.select('[data-in="23.5"]'):el['data-in']='23.2'
for el in flags.select('[data-out="23.5"]'):el['data-out']='23.2'
results=right.select_one('.results')
for el in list(results.select('.res')):
    if not any(k in textof(el) for k in ['アポ獲得','断り','営業フォロー','再架電']):el.decompose()
click(pick(results,'.res','アポ獲得'),31.1)
hearing=right.find_all('div',class_='show',recursive=False)[1]
for sec in list(hearing.select('.hear-sec')):
    if '初回商談の日程' in textof(sec) or '追加ヒアリング' in textof(sec):sec.decompose()
for field in list(hearing.select('.hf')):
    if not any(k in textof(field.select_one('label')) for k in ['担当者氏名','採用目標','採用対象','課題感']):field.decompose()
remove(hearing,'.savebar,.hs,.fhint')
for el in hearing.select('.note'):el.string='架電履歴から自動入力済み。内容を確認して確定してください。'
# タイマーのIDと動作は既存エンジンを維持。
click(cock.select_one('.dial-row .btn'),6.5)
fx(cock.select_one('.dial-row'),4.75,10.0,'ワンクリックで発信、終話は自動',1.13)
fx(center,11.05,16,'録音・文字起こしが自動で残る',1.12)
record=center.select('.tab-panel')[1]
trans=html('<div class="note cue" data-in="12.8"><b>文字起こし・要約</b><p class="type" data-in="12.8" data-dur="2.4" data-type="来期4月に10名を増員予定。若手の応募不足が課題。採用の進め方を次回ご提案。"></p></div>');put(record,trans)
fx(flags,16.75,25.6,'会話からフラグ・予算時期・ニーズを把握',1.13)
fx(memo,25.8,30.1,'架電メモ',1.1)
fx(results,30.3,33.9,'架電結果をワンタップ',1.12)
fx(hearing,34.3,39.65,'ヒアリングは自動入力',1.1)
put(c,cock);put(s,clean(o.select_one('.callcount').extract()));add(s)

# 日程調整: 候補枠とメールを同時に表示。スマホは独立した確認画面。
o=old('/outreach',1);s,c=scene('/outreach',2,114.33,129.14,o)
cand=panel(o,'STEP1｜');mail=panel(o,'STEP2｜')
only_rows(cand,3)
for el in mail.select('.field'):
    if '本文' in textof(el):el.select_one('.ta')['style']='min-height:100px;font-size:13px'
g=html('<div class="v2-two schedule-grid"></div>');put(g,cand,mail);put(c,g)
for field in list(mail.select('.field')):
    if textof(field).startswith('件名'):field.decompose()
click(pick(cand,'.btn','空き枠を取得'),.55)
for e in cand.select('tbody tr'):cue(e,1.2)
click(pick(mail,'.btn','直接送信'),4.8)
fx(cand,.15,4.15,'カレンダーから空き枠を取得',1.07)
fx(mail,4.3,8.6,'候補日をそのまま送信',1.05)
toast(s,'送信しました。',5.5,8.5)
picker=o.select_one('.picker-wrap').extract();strip_fx(picker)
for el in [picker]+list(picker.select('[data-in],[data-out],[data-click],[data-on]')):
    for k in ['data-in','data-out','data-click','data-on']:
        if k in el.attrs:
            v=float(el[k]);el[k]=str({5.5:9.07,5.7:9.07,6.9:10.1,7:10.2,7.8:11.4,8.5:12.2}.get(v,v))
put(s,picker);add(s)

# 提案書は入力材料→課題仮説→生成に絞り、書面の実物へつなぐ。
o=old('/proposal');s,c=scene('/proposal',5,131.49,143.5,o)
material=panel(o,'初回ヒアリングの議事録');remove(material,'p,.row,div[style*="border-top"]')
slot(s,material,0,5.4)
typing(material.select_one('.type'),.4,3.0)
fx(material,.2,5.15,'テレアポヒアリング・議事録を材料に',1.08)
hyp=panel(o,'課題仮説（3つ）');remove(hyp,'p')
for e in list(hyp.select('.field'))[1:]:e.decompose()
hyp.select_one('h2').string='課題仮説（3つ）'
for e in hyp.select('.type'):typing(e,5.7,2.1)
gen=panel(o,'提案書の生成');remove(gen,'p,table,.cue')
# 生成先の断定はしない（環境でPPTX/Slidesが変わる）。
for e in list(gen.find_all('div',recursive=False))[1:]:e.decompose()
click(pick(gen,'.btn','提案書を生成'),8.25)
combo=html('<div></div>');put(combo,hyp,gen);slot(s,combo,5.4)
fx(combo,5.5,11.8,'課題仮説から提案書を生成',1.05)
toast(s,'✅ 提案書を生成しました',9.1,12.01);add(s)

# 3枚を各2.8秒。文字まで読める長さを優先。
s=html('<section class="scene full deck-scene" data-cinema="1" data-start="143.5" data-end="151.9" data-step="5"></section>')
(ROOT/'deck').mkdir(exist_ok=True)
for i,(name,title) in enumerate([('p01','表紙'),('p06','お客様の課題仮説'),('p13','お見積り')]):
    shutil.copy2(ROOT/f'_assets/proposal/{name}.png',ROOT/f'deck/{name}.png')
    put(s,f'<div class="deck-page cue" data-in="{i*2.8:.1f}" data-out="{(i+1)*2.8:.1f}"><img src="deck/{name}.png" alt="提案書実物 — {title}" width="1440" height="810"><span class="deck-label">提案書実物　{i+1} / 3</span></div>')
add(s)

# 議事録: 収録UI・議事録・お礼メールを順に、原部品のまま大きく。
o=old('/minutes2');s,c=scene('/minutes2',6,151.9,162.65,o)
live=o.select('.m2-live')[1].extract();strip_fx(live);live['data-out']='4.15';slot(s,live,.8,4.15)
intro=o.select('.m2-live')[0].extract();strip_fx(intro);slot(s,intro,0,.8)
draft=panel(o,'ロジテック物流株式会社 社外')
for e in list(draft.select('.m2-sec')):
    if not any(k in textof(e.select_one('h3')) for k in ['要約','決定事項']):e.decompose()
for e in draft.select('.type'):typing(e,4.3,1.5)
for e in list(draft.select('.btn')):
    if textof(e)=='確認した・確定する':click(e,6.0)
    elif textof(e) not in ['閉じる']:e.decompose()
for pill in list(draft.select('.pill')):
    if textof(pill)=='確定':cue(pill,6.35)
    if textof(pill)=='下書き':cue(pill,0,6.35)
slot(s,draft,4.15,6.65)
thanks=clean(o.select_one('#thanks').extract());remove(thanks,'.row.small')
for e in thanks.select('.type'):typing(e,6.8,2.7)
for e in list(thanks.select('.btn')):
    if '送信' in textof(e):e.attrs.pop('data-click',None)
slot(s,thanks,6.65);add(s)

o=old('/proposal2');s,c=scene('/proposal2',7,162.65,166.62,o)
template=panel(o,'資料テンプレート:');put(c,template)
generate=panel(o,'構成の下見と生成');put(c,generate)
click(pick(generate,'.btn','商談資料を生成'),.7)
history=panel(o,'2回目以降の商談資料 履歴');only_rows(history,1);cue(history,1.65);put(c,history)
fx(template,.1,3.75,'資料の型は議事録から自動判定',1.04)
toast(s,'✅ 2回目提案書を生成しました。工程7完了。',1.7,3.97);add(s)

# 見積: 既存の無割引見積を提示後、別の追加見積で割引承認を示す。
# 次の申込に使うQ20260925-001の金額は変えない。
o=old('/estimate');s,c=scene('/estimate',8,168.97,178.36,o)
form=panel(o,'見積を発行');put(c,form)
for e in list(form.select('.sel')):
    if '会社宛のみ' in textof(e):e.decompose()
table=clean(o.select_one('.panel.p0').extract());only_rows(table,1);columns(table.select_one('table'),[0,1,2,3,4,5,9]);put(c,table)
discount=pick(form,'.field','割引率').select_one('.inp');typing(discount,5.9,.45,'20')
click(pick(form,'.btn','内容を確認'),6.15)
newrow=html('<tr class="cue" data-in="6.85"><td class="mono small">Q20260925-002</td><td>ロジテック物流株式会社</td><td>ドライバーズワーク 掲載</td><td>¥26,224</td><td>20%（¥5,960） <span class="pill pending">承認待ち</span></td><td>発行済</td><td class="small muted">承認待ち（本人以外が承認）</td></tr>')
put(table.select_one('tbody'),newrow)
fx(table,.2,5.7,'提案した媒体プランを見積へ',1.05)
fx(form,5.9,9.25,'大きな割引は本人以外の承認へ',1.04)
toast(s,'⚠ 割引が承認待ちです。別の担当者の承認後に申込を起こせます。',6.9,9.39);add(s)

# 申込: 合意済みの元見積を参照し、既存の実物風書面を約3秒見せる。
o=old('/contract');s,c=scene('/contract',9,178.36,185.69,o)
form=panel(o,'申込書を発行');put(c,form)
click(pick(form,'.btn','内容を確認'),2.0)
fx(form,.1,3.45,'合意した見積をそのまま申込書へ',1.05)
paper=clean(o.select_one('.fullcard').extract());remove(paper,'.fc-h,.fc-sub');cue(paper,3.55)
cls(paper,'contract-paper');put(s,paper);add(s)

# 指定ブランチではAI原稿・校了UIを確認できない。創作せず既存掲載フローを使う。
o=old('/publication');s,c=scene('/publication',10,185.69,200.15,o)
form=panel(o,'掲載を登録');put(c,form)
for e in form.select('.field'):
    sels=e.select('.sel,.inp')
    if len(sels)>1:sels[0].decompose()
table=clean(o.select_one('.panel.p0').extract());only_rows(table,1);put(c,table)
row=table.select_one('tbody tr');cue(row,3.1)
click(pick(form,'.btn','掲載を登録'),2.3)
pill0=pick(row,'.pill','入稿待ち');cue(pill0,0,9.45,True)
pill1=pick(row,'.pill','掲載中');cue(pill1,9.45,None,True)
start=pick(row,'.btn','掲載開始');cue(start,0,9.45,True);click(start,8.7)
invoice=pick(row,'.btn','請求へ');cue(invoice,9.45,None,True);click(invoice,12)
fx(form,.15,5.8,'申込から掲載を登録',1.03)
fx(table,8.35,14.2,'掲載中の分が請求対象に',1.08)
toast(s,'✅ 掲載を登録しました。原稿が入稿できたら「掲載開始」を押してください。',3.2,6.5)
toast(s,'✅ 掲載中にしました。今月分から請求対象に並びます。',9.6,14.46);add(s)

# 入金・督促: PaymentModal / DunningModal の見出しとボタン名を使用。
s,c=scene('/issuance',11,202.5,220.1)
put(c,'<div class="page-head"><h1>発行状況</h1><div class="meta">未入金を追う</div></div>')
put(c,'<div class="panel"><table class="tbl"><thead><tr><th>請求番号</th><th>会社</th><th>請求額（税込）</th><th>入金済</th><th>残額</th></tr></thead><tbody><tr><td>I20261031-001</td><td>ロジテック物流株式会社</td><td>¥32,780</td><td><span class="show" data-in="0" data-out="8.2">¥0</span><span class="show" data-in="8.2">¥20,000</span></td><td><span class="show" data-in="0" data-out="8.2">¥32,780</span><span class="show" data-in="8.2">¥12,780</span></td></tr></tbody></table></div>')
pay=html('<div class="panel payment-panel"><div class="h2row"><h2>入金を登録</h2><span class="btn secondary sm">✕ 閉じる</span></div><p class="small muted">I20261031-001 ／ ロジテック物流株式会社</p><div class="row"><div class="field"><label>入金日</label><div class="inp">2026-12-01</div></div><div class="field"><label>入金額（円）</label><div class="inp"><span class="type" data-in="3" data-dur="1.2" data-type="20000"></span></div></div><span class="btn secondary">残額を全額</span></div><p class="small cue" data-in="4.2">残額に満たないので<b>一部入金</b>として記録します。残り ¥12,780 は未入金のまま発行状況で追い続けます。</p><p class="small muted">登録した入金は取り消せません。金額と日付を確かめてから押してください。</p><div class="row"><span class="btn secondary">やめる</span><span class="btn success" data-click="6.75">💴 一部入金として登録</span></div></div>')
cue(pay,.6,8.2);put(c,pay);fx(pay,2.65,8.1,'日付と金額で一部入金を記録',1.08)
toast(s,'I20261031-001 に ¥20,000 の一部入金を記録しました。残額 ¥12,780 は引き続きここで追います。',8.2,10.5)
dun=html('<div class="panel dunning-panel cue" data-in="10.5"><div class="h2row"><h2>督促を記録</h2><span class="btn secondary sm">✕ 閉じる</span></div><p class="small muted">I20261031-001 ／ ロジテック物流株式会社 ／ 残額 <b>¥12,780</b></p><div class="row"><div class="field"><label>手段</label><div class="sel">電話</div></div><div class="field"><label>督促日</label><div class="inp">2026-12-02</div></div></div><div class="field"><label>ひとこと（相手の反応・次の約束）</label><div class="ta"><span class="type" data-in="10.7" data-dur="1.8" data-type="経理ご担当者様。12/5 に残額を振込予定とのこと。"></span></div></div><div class="row"><span class="btn" data-click="12.7">📣 督促を記録</span><span class="small muted">記録は消せません（誰がいつ連絡したかの証跡）。</span></div><div class="cue" data-in="13.6"><h3>これまでの督促　1回</h3><table class="tbl"><thead><tr><th>日付</th><th>手段</th><th>ひとこと</th><th>記録者</th></tr></thead><tbody><tr><td>2026-12-02</td><td>電話</td><td>12/5 に残額を振込予定</td><td>misaki.takahashi</td></tr></tbody></table></div></div>')
put(c,dun)
dun['data-out']='13.6'
hist=dun.select_one('[data-in="13.6"]');hist.attrs.pop('data-in');hist['class']=[]
hist.clear();put(hist,'<h3>これまでの督促　0回</h3>','<p class="small muted">まだ督促の記録はありません。</p>')
ledger=c.select_one('table')
put(ledger.select_one('thead tr'),'<th>督促</th>','<th></th>')
put(ledger.select_one('tbody tr'),'<td><span class="show" data-in="0" data-out="13.6">なし</span><span class="show" data-in="13.6">1回<br><span class="small muted">最終 2026-12-02（電話）</span></span></td>','<td><span class="btn secondary sm" data-click="10.0">📣 督促</span></td>')
fx(dun,10.55,13.55,'相手の反応・次の約束を記録',1.04)
fx(ledger,13.7,17.4,'最終の督促と回数を共有',1.05)
toast(s,'I20261031-001 の督促（電話・2026-12-02）を記録しました。通算 1 回。',13.6,17.6);add(s)

# エンディングの11工程はv1の部品を流用し、誤っていた工程5/6の名前を補正。
s=deepcopy(original[-1]);s['data-start']='220.1';s['data-end']='227.91';remove(s,'.end-title')
board=s.select_one('.end-board');board['data-out']='7.81';strip_fx(board)
for i,(el,name) in enumerate(zip(board.select('.eb'),names)):
    el.clear();put(el,f'<i>{i+1}</i>');el.append(name);el['data-in']=str(round(.35+i*.3,2))
board.select_one('.eb-note').string='対話に集中し、少人数で売上を拡大'
board.select_one('.eb-note')['data-in']='4.0';add(s)

# 追加指示: 4321版のオープニングとエンディングを採用。
# 参照版を毎回読み直さず、取り込み時のスナップショットで再現する。
reference=json.loads((ROOT/'_docs/reference_4321/snapshot.json').read_text())
new=[s for s in new if 16.96<=float(s['data-start'])<220.1]
for raw in reference['scenes']:
    s=html(raw);cls(s,'reference-bookend')
    if float(s['data-end'])==17:s['data-end']='16.96'  # 中間の開始は動かさない。
    add(s)

# 時系列DOMにまとめる。サイドバーは旧エンジンが生成し、通常画面はその右に置く。
frame=doc.select_one('#frame');app=frame.select_one('.app').extract()
app.select_one('.app-main').clear();frame.clear();frame.append(app)
for s in sorted(new,key=lambda s:float(s['data-start'])):frame.append(s)
doc.select_one('title').string='ASUMO 営業ジャーニー — 新作 v2'
doc.select_one('title').insert_before(html('<meta name="viewport" content="width=device-width,initial-scale=1">'))
doc.select_one('.masthead h1').string='営業ジャーニー — 新作 v2'
idxbtn=doc.select_one('#idxbtn').extract()
doc.select_one('.masthead .meta').clear()
put(doc.select_one('.masthead .meta'),'<span>232.2秒 / 実装準拠のHTMLデモ / 操作の経過を短縮して表示</span>',idxbtn)
for el in doc.select('#poster .pm,.poster .ps'):
    if '213' in textof(el) or '3分' in textof(el):el.string='3分52秒・音声付き'
doc.select_one('#ttot').string='3:52'
doc.select_one('#scrub')['aria-valuemax']=str(tl['total'])
doc.select_one('#index .note').string='字幕・音声は最新台本 v2。章を選ぶと、その位置から再生します。'
script=doc.select_one('script')
js=script.string
js=re.sub(r'const TOTAL = 213',f'const TOTAL = {tl["total"]}',js)
chapter_labels={1:'オープニング',2:'人は対話に集中',4:'リード作成・テレアポ準備',14:'テレアポ',23:'日程調整',27:'商談・提案資料',34:'受注から掲載・請求へ',44:'入金・督促',50:'エンディング'}
chap=[[r['start'],chapter_labels[r['no']],r['cap'].replace('\n','　'),''] for r in tl['rows'] if r['kind']=='title']
caps=[[r['start'],r['end'],r['cap'],r.get('read','')] for r in tl['rows'] if r['kind']=='cut']
js=re.sub(r'const CH = \[.*?\n  \];','const CH = '+json.dumps(chap,ensure_ascii=False)+';',js,flags=re.S)
js=re.sub(r'const CAPS = \[.*?\n  \];','const CAPS = '+json.dumps(caps,ensure_ascii=False).replace('\\','\\\\')+';',js,flags=re.S)
script.string=js
style=html('<style id="v2-styles"></style>');style.string=(ROOT/'_docs/video_v2.css').read_text();doc.select_one('style').insert_after(style)
reference_style=html('<style id="reference-bookend-styles"></style>')
reference_style.string=reference['css'];style.insert_after(reference_style)
doc.select_one('#narr')['src']='narration-bookends.wav'
out='<!doctype html>\n<html lang="ja">\n'+str(doc)+'\n</html>\n'
(ROOT/'index.html').write_text(out)
(ROOT/'_docs/scenes_codex_v2.json').write_text(json.dumps([dict(id=i,nav=s.get('data-nav'),start=float(s['data-start']),end=float(s['data-end'])) for i,s in enumerate(sorted(new,key=lambda s:float(s['data-start'])))],ensure_ascii=False,indent=2)+'\n')
print(f'Built {len(new)} scenes / {len(caps)} captions / {len(chap)} title cards / {tl["total"]} seconds')
