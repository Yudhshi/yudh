# 字体を自前配信するための取得スクリプト。
# Google Fonts の text= で必要な字だけ切り出して woff2 を落とし、unicode-range 付きの @font-face を書く。
import re, os, sys, json, subprocess, urllib.parse, unicodedata, concurrent.futures as cf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, 'slides/assets/fonts')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
os.makedirs(OUT, exist_ok=True)

def read(rel): return open(os.path.join(ROOT, rel), encoding='utf-8').read()
html = read('slides/slides.html')
jp_text = html + read('slides/speaker-notes.md') + read('slides/outline.md')

def printable(chars):
    return {c for c in chars if ord(c) >= 0x20 and unicodedata.category(c)[0] not in 'CZ'}

# 日本語の基本セット：JIS 第1水準漢字 + かな + ASCII + 記号
jp = set()
for hi in range(0x88, 0x99):
    for lo in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
        if (hi, lo) < (0x88, 0x9F) or (hi, lo) > (0x98, 0x72): continue
        try: jp.add(bytes([hi, lo]).decode('cp932'))
        except UnicodeDecodeError: pass
for a, b in [(0x20, 0x7E), (0x3000, 0x303F), (0x3041, 0x309F), (0x30A0, 0x30FF), (0xFF01, 0xFF5E), (0xFF61, 0xFF9F)]:
    jp.update(chr(c) for c in range(a, b + 1))
jp.update('―—…‥′″℃％＆＋－×÷＝≠≒∞°○●◎△▲▽▼□■◇◆☆★→←↑↓⇒⇔∴∵※〒〔〕〈〉《》【】Ⅰ Ⅱ Ⅲ Ⅳ Ⅴ Ⅵ Ⅶ Ⅷ Ⅸ Ⅹ ①②③④⑤⑥⑦⑧⑨⑩「」『』（）・〜')
jp |= printable(jp_text)
jp = printable(jp)

ascii_set = printable({chr(c) for c in range(0x20, 0x7F)} | set('—–·×'))

# 中国語（印章・縦書き・章扉）：lang="zh-CN" の中の字 + 元の text= に入っていた字
zh = set()
for m in re.finditer(r'lang="zh-CN"[^>]*>(.*?)</(?:span|div|h1|p)>', html, flags=re.S):
    zh |= set(re.sub(r'<[^>]+>', '', m.group(1)))
zh |= set('一三不个中们住体公另可司国在外就我挡文是本根现能语谢赛马')
zh = printable(zh)
brush = printable(set('三体开暗林森篇赛马黑谢'))

FAMILIES = [
    ('Shippori Mincho B1', 'shippori-mincho-b1', [500, 700, 800], jp),
    ('Noto Sans JP',       'noto-sans-jp',       [400, 500, 700], jp),
    ('JetBrains Mono',     'jetbrains-mono',     [500, 700],      ascii_set),
    ('Noto Serif SC',      'noto-serif-sc',      [700],           zh),
    ('Ma Shan Zheng',      'ma-shan-zheng',      [400],           brush),
]
CHUNK = 300

def uranges(chars):
    cps = sorted(ord(c) for c in chars); out = []; i = 0
    while i < len(cps):
        j = i
        while j + 1 < len(cps) and cps[j + 1] == cps[j] + 1: j += 1
        out.append(f'U+{cps[i]:04X}' if i == j else f'U+{cps[i]:04X}-{cps[j]:04X}'); i = j + 1
    return ', '.join(out)

jobs = []
for fam, slug, weights, chars in FAMILIES:
    ordered = sorted(chars)
    chunks = [ordered[i:i + CHUNK] for i in range(0, len(ordered), CHUNK)]
    for w in weights:
        for k, ch in enumerate(chunks):
            jobs.append((fam, slug, w, k, ''.join(ch)))
print(len(jobs), 'requests;', {slug: len(chars) for _, slug, _, chars in FAMILIES}, file=sys.stderr)

def fetch(job):
    fam, slug, w, k, text = job
    fn = f'{slug}-{w}-{k:02d}.woff2'
    path = os.path.join(OUT, fn)
    url = 'https://fonts.googleapis.com/css2?family=' + urllib.parse.quote(fam).replace('%20', '+') + f':wght@{w}&text=' + urllib.parse.quote(text, safe='') + '&display=swap'
    css = subprocess.run(['curl', '-sS', '-A', UA, url], capture_output=True, text=True, check=True).stdout
    m = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)
    if not m: return (job, None, css[:200])
    if not (os.path.exists(path) and os.path.getsize(path) > 0):
        subprocess.run(['curl', '-sS', '-o', path, m.group(1)], check=True)
    return (job, fn, None)

with cf.ThreadPoolExecutor(8) as ex:
    results = list(ex.map(fetch, jobs))

fails = [r for r in results if r[1] is None]
for r in fails: print('FAIL', r[0][:4], r[2], file=sys.stderr)

faces = []
for (fam, slug, w, k, text), fn, _ in results:
    if not fn: continue
    faces.append(f'''@font-face {{
  font-family: "{fam}";
  font-style: normal;
  font-weight: {w};
  font-display: block;
  src: url("{fn}") format("woff2");
  unicode-range: {uranges(set(text))};
}}''')
header = '''/* 黒暗森林と競馬場 — 自前配信の字体（v4.3）
   Google Fonts から text= で必要な字だけ切り出した woff2。ネットワークが無くても同じ字体で出る。
   収録：日本語 2書体は JIS 第1水準の漢字＋かな＋ASCII＋記号＋この資料に出てくる全部の字。
        Noto Serif SC は lang="zh-CN" の字、Ma Shan Zheng は章扉と最後の筆文字だけ。
   収録外の字は unicode-range に無いので、その1字だけ Mac のヒラギノに落ちる（他の字は変わらない）。
   作り直し：python3 tools/build-fonts.py（このファイルと woff2 を全部書き直す）。 */
'''
open(os.path.join(OUT, 'fonts.css'), 'w', encoding='utf-8').write(header + '\n'.join(faces) + '\n')
total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print(json.dumps({'faces': len(faces), 'fails': len(fails), 'total_bytes': total}))
