"""前回v2の中間と参照版の指定部分が、意図せず変わっていないか検算。"""
from pathlib import Path
import json, subprocess, hashlib
from bs4 import BeautifulSoup as BS
from import_reference_bookends import decode, RATE, FRAME_BYTES

ROOT = Path(__file__).resolve().parents[1]
meta = json.loads((ROOT/'_docs/reference_4321/snapshot.json').read_text())
before = BS(subprocess.check_output(['git','show',meta['middle_base_commit']+':index.html'], cwd=ROOT), 'html.parser')
after = BS((ROOT/'index.html').read_text(), 'html.parser')
def middle(doc):
    return [str(s) for s in doc.select('.scene') if 16.96<=float(s['data-start'])<220.1]
assert middle(before) == middle(after)
assert before.select_one('script').string == after.select_one('script').string
assert before.select_one('#v2-styles').string == after.select_one('#v2-styles').string
for scene, raw in zip(after.select('.reference-bookend'), meta['scenes'], strict=True):
    scene['class'].remove('reference-bookend')
    expected = BS(raw, 'html.parser').select_one('.scene')
    if float(expected['data-end']) == 17: expected['data-end'] = '16.96'
    assert str(scene) == str(expected)
current = decode(ROOT/'narration-bookends.wav')
original = decode(ROOT/'narration.mp3')
a,b = [round(t*RATE)*FRAME_BYTES for t in [16.96,220.1]]
assert current[a:b] == original[a:b]
for segment in meta['audio']:
    a,b = [round(segment[k]*RATE)*FRAME_BYTES for k in ['start','end']]
    assert hashlib.sha256(current[a:b]).hexdigest() == segment['pcm_sha256']
print(f'PASS: 中間{len(middle(before))}シーン・CSS・JS不変 / 参照4シーン一致（末尾0.04秒のみ調整） / 音声3区間PCM一致')
