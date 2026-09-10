"""参照版の冒頭・末尾と、新作の中間をPCM単位で無劣化結合する。"""
from pathlib import Path
import json, subprocess, hashlib
from import_reference_bookends import decode, RATE, FRAME_BYTES, FFMPEG

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / '_docs/reference_4321'
meta = json.loads((REF / 'snapshot.json').read_text())
original = decode(ROOT / 'narration.mp3')
pcm = bytearray(original)
for segment in meta['audio']:
    part = decode(REF / segment['file'])
    assert hashlib.sha256(part).hexdigest() == segment['pcm_sha256']
    a, b = [round(segment[k] * RATE) * FRAME_BYTES for k in ['start', 'end']]
    assert len(part) == b - a
    pcm[a:b] = part
out = ROOT / 'narration-bookends.wav'
subprocess.run([FFMPEG, '-v', 'error', '-y', '-f', 's16le', '-ar', str(RATE),
    '-ac', '2', '-i', '-', '-c:a', 'pcm_s16le', str(out)], input=bytes(pcm), check=True)
actual = decode(out)
assert actual == pcm, '結合後のPCMが不一致'
a, b = [round(t * RATE) * FRAME_BYTES for t in [16.96, 220.1]]
assert actual[a:b] == original[a:b], '中間の音声が変更された'
print(f'PASS: 音声{len(actual)/FRAME_BYTES/RATE}秒 / 中間PCM完全一致 / 冒頭・末尾は参照版と完全一致 / {out.stat().st_size:,} bytes')
