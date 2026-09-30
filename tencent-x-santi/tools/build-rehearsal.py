# 通し稽古シートを作る：slides/rehearsal.html
# 左に縮小画（rehearsal/thumbs/sNN.jpg）、右に speaker-notes.md のその枚のノート。A4 横で印刷できる。
# 使い方: node tools/shoot-thumbs.js && python3 tools/build-rehearsal.py
import re, os, html as H
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SL = os.path.join(ROOT, 'slides')
notes_md = open(os.path.join(SL, 'speaker-notes.md'), encoding='utf-8').read()
outline = open(os.path.join(SL, 'outline.md'), encoding='utf-8').read()
deck = open(os.path.join(SL, 'slides.html'), encoding='utf-8').read()

# 枚数とタイトル（slides.html のコメント "SLIDE NN / タイトル" を出所にする）
slides = [(int(m.group(1)), m.group(2).strip()) for m in re.finditer(r'SLIDE (\d+) / ([^\n]*)', deck)]
titles = {n: t for n, t in slides}
N = len(slides)

# Part ごとの時間（outline.md の全体ストラクチャ表）
part_time = {}
for m in re.finditer(r'^\| (Part \d) \| ([^|]+) \| (\d+)分 \|', outline, flags=re.M):
    part_time[m.group(1)] = (m.group(2).strip(), int(m.group(3)))

# ノートを枚に振る。「- **sNN 〜**：」「- **sNN〜sMM**」「- **sNN**：」の形。範囲は全部の枚に同じ文を付ける。
def md_inline(t):
    t = H.escape(t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    return t
per = {n: [] for n, _ in slides}
general = []          # 枚に紐づかない段（冒頭の方針・質問が出たら）
section = ''
lines = notes_md.split('\n')
i = 0
cur_targets = None
while i < len(lines):
    ln = lines[i]
    if ln.startswith('## '):
        section = ln[3:].strip(); cur_targets = None; i += 1; continue
    m = re.match(r'^- \*\*(s\d+(?:[〜～\-–]s?\d+)?)[^*]*\*\*[:：]?\s*(.*)$', ln)
    if m:
        rng = m.group(1); body = m.group(2)
        nums = [int(x) for x in re.findall(r'\d+', rng)]
        targets = list(range(nums[0], nums[-1] + 1)) if len(nums) > 1 else [nums[0]]
        cur_targets = [t for t in targets if t in per]
        for t in cur_targets: per[t].append(('p', body))
        i += 1; continue
    m2 = re.match(r'^\s{2,}- (.*)$', ln)     # 子の箸条
    if m2 and cur_targets:
        for t in cur_targets: per[t].append(('sub', m2.group(1)))
        i += 1; continue
    if ln.startswith('- ') and not cur_targets:
        general.append((section, ln[2:]))
    elif ln.startswith('> '):
        general.append((section or '前提', ln[2:]))
    i += 1

def render_notes(items):
    if not items: return '<p class="none">（この枚のノートは無い。画面の字を読むだけ）</p>'
    out = []
    for kind, t in items:
        out.append(f'<p class="{kind}">{md_inline(t)}</p>')
    return '\n'.join(out)

def part_of(n):
    # outline の Layer 2 表から Part を引く
    for m in re.finditer(r'^## (Part \d): ([^（]+)（(\d+)枚）\n\n\|.*?\n\|[-| ]+\n((?:\|.*\n)+)', outline, flags=re.M):
        nums = [int(x) for x in re.findall(r'^\| (\d+) \|', m.group(4), flags=re.M)]
        if n in nums: return m.group(1), m.group(2).strip()
    return '', ''

rows = []
last_part = None
for n, title in slides:
    part, pname = part_of(n)
    if part != last_part and part:
        pt = part_time.get(part, ('', 0))
        rows.append(f'<h2 class="part"><span>{H.escape(part)}</span>{H.escape(pname)}<em>{pt[1]}分</em></h2>')
        last_part = part
    rows.append(f'''<section class="row">
  <div class="thumb"><img src="rehearsal/thumbs/s{n:02d}.jpg" alt="s{n:02d}" loading="lazy"><div class="no">s{n:02d}</div></div>
  <div class="notes"><h3>{H.escape(title)}</h3>{render_notes(per[n])}</div>
  <div class="clock"><span>実測</span></div>
</section>''')

gen_html = ''.join(f'<p><span class="sec">{H.escape(s)}</span>{md_inline(t)}</p>' for s, t in general if t.strip())

out = f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<title>通し稽古シート｜黒暗森林と競馬場</title>
<style>
  @page{{size:A4 landscape;margin:12mm 12mm}}
  :root{{--ink:#24292A;--sub:#5A5E57;--rule:#C9C2B3;--hair:#E3DED2;--gold:#75530F;--blue:#0052D9;
        --sans:"Noto Sans JP","Hiragino Sans","Yu Gothic",sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,monospace}}
  *{{box-sizing:border-box}}
  body{{margin:0;padding:24px 28px;background:#fff;color:var(--ink);font-family:var(--sans);font-size:12px;line-height:1.65;
       -webkit-print-color-adjust:exact;print-color-adjust:exact}}
  h1{{margin:0;font-size:19px;font-weight:600;letter-spacing:.04em}}
  .sub{{margin-top:6px;font-family:var(--mono);font-size:11px;letter-spacing:.1em;color:var(--sub)}}
  .hr{{height:2px;background:var(--ink);margin:12px 0 4px}}
  .general{{columns:2;column-gap:28px;margin:10px 0 6px;font-size:11px;color:var(--sub)}}
  .general p{{margin:0 0 6px;break-inside:avoid}}
  .general .sec{{display:inline-block;margin-right:8px;font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;color:var(--gold)}}
  h2.part{{display:flex;align-items:baseline;gap:14px;margin:22px 0 6px;padding-top:8px;border-top:1px solid var(--rule);
          font-size:13px;font-weight:600;letter-spacing:.06em;break-after:avoid}}
  h2.part span{{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;color:var(--blue)}}
  h2.part em{{margin-left:auto;font-style:normal;font-family:var(--mono);font-size:11px;color:var(--sub)}}
  .row{{display:grid;grid-template-columns:300px 1fr 64px;gap:0 18px;padding:9px 0;border-bottom:1px solid var(--hair);break-inside:avoid}}
  .thumb{{position:relative}} .thumb img{{display:block;width:300px;height:auto;border:1px solid var(--rule)}}
  .thumb .no{{position:absolute;left:0;bottom:-2px;transform:translateY(100%);font-family:var(--mono);font-size:10px;letter-spacing:.12em;color:var(--sub)}}
  .notes h3{{margin:0 0 4px;font-size:12.5px;font-weight:600}}
  .notes p{{margin:0 0 4px}} .notes p.sub{{margin-left:14px;font-size:11px;color:var(--sub)}}
  .notes p.none{{color:var(--sub);font-size:11px}}
  .notes b{{font-weight:600}}
  .clock{{border-left:1px solid var(--rule);padding-left:8px}} .clock span{{font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;color:var(--sub)}}
  .how{{margin-top:14px;font-size:11px;line-height:1.7;color:var(--sub);border-left:2px solid var(--rule);padding-left:12px}}
</style></head><body>
<h1>通し稽古シート</h1>
<div class="sub">黒暗森林と競馬場 ／ {N}枚 ／ 目安 {sum(t for _, t in part_time.values())}分（Part 別の配分は outline.md） ／ 左：画面　右：話すこと　端：実測</div>
<div class="hr"></div>
<div class="general">{gen_html}</div>
{''.join(rows)}
<p class="how"><b>使い方</b>｜ストップウォッチを持って通しで一度話す。枚が変わるたびに右端へ通過時刻を書く。Part の合計を outline.md の配分（2／11／4／15／3分）と見比べ、どの Part で伸びたかを見る。
話の中身はこのシートの右側が原稿代わり。台本にはしない。<br>
<b>作り直し</b>｜node tools/shoot-thumbs.js（縮小画）→ python3 tools/build-rehearsal.py（このファイル）。ノートを書き足したら作り直す。</p>
</body></html>
'''
open(os.path.join(SL, 'rehearsal.html'), 'w', encoding='utf-8').write(out)
print('rehearsal.html', N, 'slides;', sum(1 for n in per if per[n]), 'with notes;', len(general), 'general lines')
