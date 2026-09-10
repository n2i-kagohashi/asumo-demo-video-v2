"""4321 の指定部分を一度だけ保存。元フォルダは読み取り専用で扱う。"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, subprocess
from bs4 import BeautifulSoup as BS
import tinycss2

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'asumo-demo'
DEST = ROOT / '_docs/reference_4321'
FFMPEG = '/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg'
RATE = 48000
FRAME_BYTES = 4  # stereo / signed 16 bit


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode(path):
    return subprocess.check_output([FFMPEG, '-v', 'error', '-i', str(path),
        '-f', 's16le', '-acodec', 'pcm_s16le', '-ar', str(RATE), '-ac', '2', '-'])


if __name__ == '__main__':
    # 既存スナップショットの無断更新を防止。
    if DEST.exists():
        raise SystemExit(f'保存済みのため再取り込みしません: {DEST}')
    raw = (SOURCE / 'index.html').read_bytes()
    audio_hash = sha((SOURCE / 'narration.mp3').read_bytes())
    doc = BS(raw, 'html.parser')
    scenes = [s for s in doc.select('.scene')
              if float(s['data-start']) < 17 or float(s['data-start']) >= 220.1]
    assert [(float(s['data-start']), float(s['data-end'])) for s in scenes] == [
        (0, 9.7), (9.7, 12.7), (12.7, 17), (220.1, 232.2)]
    # 共通のロゴ演出は既存の475de1fにある。追加CSSのみ取り出して局所化。
    css = doc.select_one('style').string
    extra = css[css.index('.scene.tcard{'):css.index('/* 提案書の実物。')]
    scoped = []
    for rule in tinycss2.parse_stylesheet(extra, skip_whitespace=True, skip_comments=True):
        assert rule.type == 'qualified-rule'
        selectors = tinycss2.serialize(rule.prelude).strip().split(',')
        selectors = [(s.strip().replace('.scene', '.frame .scene.reference-bookend', 1)
                      if s.strip().startswith('.scene') else '.reference-bookend ' + s.strip())
                     for s in selectors]
        scoped.append(','.join(selectors) + '{' + tinycss2.serialize(rule.content) + '}')
    # v2 全体の簡略演出から、この4シーンだけ参照版の演出に戻す。
    scoped += [
        '.frame .scene.reference-bookend{background:transparent;transform:scale(1.012)!important;transition:opacity .6s var(--ease),transform .9s var(--ease)}',
        '.frame .scene.reference-bookend.on{transform:none!important}',
        '.frame .scene.reference-bookend.tcard{background:var(--theater)}',
        '@media(prefers-reduced-motion:reduce){.frame .scene.reference-bookend{transition:none!important}}',
    ]
    pcm = decode(SOURCE / 'narration.mp3')
    assert len(pcm) == round(232.2 * RATE) * FRAME_BYTES
    DEST.mkdir()
    segments = []
    for name, start, end in [('opening', 0, 16.96), ('ending', 220.1, 232.2)]:
        data = pcm[round(start * RATE) * FRAME_BYTES:round(end * RATE) * FRAME_BYTES]
        out = DEST / (name + '.flac')
        subprocess.run([FFMPEG, '-v', 'error', '-n', '-f', 's16le', '-ar', str(RATE),
            '-ac', '2', '-i', '-', '-c:a', 'flac', str(out)], input=data, check=True)
        assert decode(out) == data
        segments.append(dict(file=out.name, start=start, end=end, pcm_sha256=sha(data)))
    manifest = dict(source_url='http://localhost:4321/', source_path=str(SOURCE),
        captured_at=datetime.now(timezone.utc).isoformat(), source_html_sha256=sha(raw),
        source_audio_sha256=audio_hash, middle_base_commit='3d1498d',
        sample_rate=RATE, channels=2, sample_format='s16le',
        scenes=[str(s) for s in scenes], css='\n'.join(scoped), audio=segments)
    (DEST / 'snapshot.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    assert sha((SOURCE / 'index.html').read_bytes()) == manifest['source_html_sha256']
    assert sha((SOURCE / 'narration.mp3').read_bytes()) == audio_hash
    print(f'保存: {len(scenes)}シーン / 音声2区間 / 元ファイル変更なし')
