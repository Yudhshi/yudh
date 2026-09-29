# assets/sprite.svg の中身を slides.html の <!-- sprite:start --> 〜 <!-- sprite:end --> に埋め込む。
# 外部 SVG の <use href="file#id"> は file:// で開くと Chrome が拒むことがあるので、埋め込みにしている。
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_p = os.path.join(ROOT, 'slides/slides.html'); svg_p = os.path.join(ROOT, 'slides/assets/sprite.svg')
html = open(html_p, encoding='utf-8').read(); svg = open(svg_p, encoding='utf-8').read().strip()
svg = re.sub(r'^<\?xml[^>]*>\s*', '', svg)
svg = re.sub(r'<svg\b([^>]*)>', lambda m: '<svg id="sprite" aria-hidden="true"' + re.sub(r'\s(id|style|aria-hidden)="[^"]*"', '', m.group(1)) + '>', svg, count=1)
new = re.sub(r'<!-- sprite:start -->.*?<!-- sprite:end -->', '<!-- sprite:start -->\n  ' + svg + '\n  <!-- sprite:end -->', html, flags=re.S)
assert new != html or '<symbol' in html, 'sprite slot not found'
open(html_p, 'w', encoding='utf-8').write(new)
print('inlined', svg.count('<symbol'), 'symbols')
