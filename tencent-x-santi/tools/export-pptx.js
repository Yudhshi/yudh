// slides.html → Keynote / PowerPoint で開ける pptx（export/santi-deck.pptx）
// 文字はそのまま編集できるテキストボックス（字体・字号・色・位置は Chromium の実測値）。
// 図・墨・印章・章扉の筆文字・紙の質感は、そのページの背景画像（文字だけ消して撮った 1920×1080 の JPEG）。
// 講演者ノート（speaker-notes.md）はノート欄に入る。
// 使い方: node tools/export-pptx.js   （playwright と Chromium、pptxgenjs が要る。無ければ npm install pptxgenjs）
// Keynote で同じ見た目にするには、Google Fonts の Shippori Mincho B1・Noto Sans JP・Noto Serif SC・Ma Shan Zheng・JetBrains Mono を Mac に入れておく。
const fs = require('fs');
const path = require('path');
let chromium; try { chromium = require('playwright').chromium; } catch (e) { chromium = require('/opt/node22/lib/node_modules/playwright').chromium; }
let pptxgen; try { pptxgen = require('pptxgenjs'); } catch (e) { pptxgen = require(path.join(__dirname, '..', 'node_modules', 'pptxgenjs')); }

const ROOT = path.resolve(__dirname, '..');
const SL = path.join(ROOT, 'slides');
const OUT = path.join(ROOT, 'export');
const BG = path.join(OUT, 'bg');
fs.mkdirSync(BG, { recursive: true });
const PX = 13.333 / 1920;                 // 1px → inch（1920px = 13.333in、字は 1px = 0.5pt）
const r2 = v => Math.round(v * 100) / 100;

// ---- 講演者ノート（tools/build-rehearsal.py と同じ読み方） ---------------------------
function readNotes() {
  const deck = fs.readFileSync(path.join(SL, 'slides.html'), 'utf8');
  const slides = [...deck.matchAll(/SLIDE (\d+) \/ ([^\n]*)/g)].map(m => [parseInt(m[1]), m[2].trim()]);
  const md = fs.readFileSync(path.join(SL, 'speaker-notes.md'), 'utf8');
  const per = {}; slides.forEach(([n]) => per[n] = []);
  let cur = null;
  for (const ln of md.split('\n')) {
    if (ln.startsWith('## ')) { cur = null; continue; }
    const m = ln.match(/^- \*\*(s\d+(?:[〜～\-–]s?\d+)?)[^*]*\*\*[:：]?\s*(.*)$/);
    if (m) {
      const nums = [...m[1].matchAll(/\d+/g)].map(x => parseInt(x[0]));
      const t = nums.length > 1 ? Array.from({ length: nums[nums.length - 1] - nums[0] + 1 }, (_, i) => nums[0] + i) : [nums[0]];
      cur = t.filter(x => x in per); cur.forEach(x => per[x].push(m[2])); continue;
    }
    const m2 = ln.match(/^\s{2,}- (.*)$/);
    if (m2 && cur) cur.forEach(x => per[x].push('・' + m2[1]));
  }
  const plain = t => t.replace(/\*\*(.+?)\*\*/g, '$1');
  return slides.map(([n, title]) => {
    const body = [`s${String(n).padStart(2, '0')} ${title}`, ...per[n].map(plain)];
    if (body.length === 1) body.push('（この枚のノートは無い。画面の字を読むだけ）');
    return body.join('\n');
  });
}

// ---- ブラウザ側：そのページの文字を全部拾う ------------------------------------------
async function collect(i) {
  const slides = [...document.querySelectorAll('.slide')];
  slides.forEach(s => s.classList.remove('active'));
  const sl = slides[i]; sl.classList.add('active');
  await document.fonts.ready;
  const st = document.getElementById('stage').getBoundingClientRect(); const k = 1920 / st.width;
  const rel = r => ({ x: (r.left - st.left) * k, y: (r.top - st.top) * k, w: r.width * k, h: r.height * k });
  const EXEMPT = '.seal, .vwm, .slide-header-bar';      // 印章と章扉の筆文字は画像のまま
  const cs = el => getComputedStyle(el);
  const toHex = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return { hex: '000000', a: 1 }; const p = m[1].split(',').map(parseFloat); return { hex: p.slice(0, 3).map(v => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase(), a: p.length > 3 ? p[3] : 1 }; };
  const styleOf = el => { const s = cs(el); const c = toHex(s.color); return { fontFace: s.fontFamily.split(',')[0].replace(/["']/g, '').trim(), fontSize: parseFloat(s.fontSize), bold: parseInt(s.fontWeight) >= 600, italic: s.fontStyle === 'italic', color: c.hex, alpha: c.a, ls: s.letterSpacing === 'normal' ? 0 : parseFloat(s.letterSpacing) }; };
  const frags = []; const tagged = new Set();
  const walker = document.createTreeWalker(sl, NodeFilter.SHOW_TEXT); let n;
  while ((n = walker.nextNode())) {
    if (!n.textContent.trim()) continue;
    const p = n.parentElement; if (!p || p.closest(EXEMPT) || p.closest('svg') || p.closest('.vquote, .thanks')) continue;
    if (cs(p).display === 'none' || cs(p).visibility === 'hidden') continue;
    const style = styleOf(p); const t = n.textContent; let cur = null;
    const push = c => { if (c.text.trim()) frags.push({ text: c.text.replace(/\s+/g, ' '), rect: rel({ left: c.left, top: c.top, width: c.right - c.left, height: c.bottom - c.top }), style }); };
    for (let c = 0; c < t.length; c++) {            // 1文字ずつ位置を見て、行ごとに分ける
      const r = document.createRange(); r.setStart(n, c); r.setEnd(n, c + 1); const rr = r.getClientRects()[0];
      if (!rr || rr.width === 0) { if (cur && t[c] !== '\n') cur.text += t[c]; continue; }
      if (cur && Math.abs(rr.top - cur.top) < 2) { cur.text += t[c]; cur.right = Math.max(cur.right, rr.right); cur.bottom = Math.max(cur.bottom, rr.bottom); cur.left = Math.min(cur.left, rr.left); }
      else { if (cur) push(cur); cur = { text: t[c], left: rr.left, top: rr.top, right: rr.right, bottom: rr.bottom }; }
    }
    if (cur) push(cur);
    tagged.add(p);
  }
  frags.sort((a, b) => (Math.abs(a.rect.y - b.rect.y) < 12 ? a.rect.x - b.rect.x : a.rect.y - b.rect.y));
  const boxes = [];
  for (const f of frags) {                             // 同じ行で続いている断片は1つの箱に（色違いの run になる）
    const last = boxes[boxes.length - 1];
    if (last && Math.abs(last.rect.y - f.rect.y) < 12 && Math.abs((last.rect.x + last.rect.w) - f.rect.x) < 4) {
      last.runs.push({ text: f.text, style: f.style });
      const bottom = Math.max(last.rect.y + last.rect.h, f.rect.y + f.rect.h); last.rect.y = Math.min(last.rect.y, f.rect.y); last.rect.h = bottom - last.rect.y;
      last.rect.w = (f.rect.x + f.rect.w) - last.rect.x;
    } else boxes.push({ rect: { ...f.rect }, runs: [{ text: f.text, style: f.style }], align: 'left' });
  }
  for (const t of sl.querySelectorAll('svg text')) {   // 図の中の字
    const r = t.getBoundingClientRect(); if (r.width === 0) continue;
    const s = cs(t); const ctm = t.getScreenCTM(); const scale = Math.hypot(ctm.a, ctm.b) * k; const c = toHex(s.fill);
    const rr = rel(r); const slack = Math.max(60, rr.w * 0.4); let x = rr.x, w = rr.w, align = 'left';
    if (s.textAnchor === 'middle') { x = rr.x - slack; w = rr.w + 2 * slack; align = 'center'; } else if (s.textAnchor === 'end') { x = rr.x - 2 * slack; w = rr.w + 2 * slack; align = 'right'; }
    boxes.push({ rect: { x, y: rr.y, w, h: rr.h }, runs: [{ text: t.textContent.trim(), style: { fontFace: s.fontFamily.split(',')[0].replace(/["']/g, '').trim(), fontSize: parseFloat(s.fontSize) * scale, bold: parseInt(s.fontWeight) >= 600, italic: false, color: c.hex, alpha: c.a, ls: 0 } }], align, svg: true });
    t.setAttribute('data-xt', '1');
  }
  for (const col of sl.querySelectorAll('.vquote .vcol, .thanks .vcol')) {   // 縦書きは1列を1つの縦書き箱に
    const is = [...col.querySelectorAll('i')]; if (!is.length) continue;
    const r = rel(col.getBoundingClientRect()); const s = styleOf(is[0]); const lh = parseFloat(cs(is[0]).lineHeight) / s.fontSize;
    boxes.push({ rect: r, runs: [{ text: is.map(i => i.textContent).join(''), style: { ...s, ls: (lh - 1) * s.fontSize } }], align: 'left', vert: true });
    is.forEach(i => tagged.add(i));
  }
  tagged.forEach(el => el.setAttribute('data-xt', '1'));
  return boxes;
}

(async () => {
  const notes = readNotes();
  const opts = {}; if (fs.existsSync('/opt/pw-browsers/chromium')) opts.executablePath = '/opt/pw-browsers/chromium';
  const browser = await chromium.launch(opts);
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.join(SL, 'slides.html'), { waitUntil: 'load' });
  await page.addStyleTag({ content: `.slide.active .anim{animation:none!important}.slide.active .on-splat .splat{animation:none!important}[data-xhide]{color:transparent!important}text[data-xhide]{fill:transparent!important}` });
  await page.evaluate(() => document.fonts.ready);
  const n = await page.$$eval('.slide', e => e.length);
  const pres = new pptxgen(); pres.layout = 'LAYOUT_WIDE'; pres.title = '黒暗森林と競馬場'; pres.author = 'Yudi Shi';
  let total = 0;
  for (let i = 0; i < n; i++) {
    const boxes = await page.evaluate(collect, i);
    await page.waitForTimeout(250);
    await page.evaluate(() => document.querySelectorAll('[data-xt]').forEach(e => e.setAttribute('data-xhide', '1')));
    const bg = path.join(BG, `s${String(i + 1).padStart(2, '0')}.jpg`);
    await page.screenshot({ path: bg, type: 'jpeg', quality: 92 });
    await page.evaluate(() => document.querySelectorAll('[data-xt]').forEach(e => { e.removeAttribute('data-xt'); e.removeAttribute('data-xhide'); }));
    const s = pres.addSlide(); s.background = { path: bg };
    for (const bx of boxes) {
      const runs = bx.runs.map(r => { const o = { fontFace: r.style.fontFace, fontSize: r2(r.style.fontSize / 2), bold: r.style.bold, italic: r.style.italic, color: r.style.color }; if (r.style.ls) o.charSpacing = r2(r.style.ls / 2); if (r.style.alpha < 1) o.transparency = Math.round((1 - r.style.alpha) * 100); return { text: r.text, options: o }; });
      const o = { x: r2(bx.rect.x * PX), y: r2(bx.rect.y * PX), w: r2((bx.rect.w + (bx.svg ? 0 : 8)) * PX), h: r2(bx.rect.h * PX), margin: 0, isTextBox: true, valign: 'top', align: bx.align, wrap: false, fit: 'none', lineSpacingMultiple: 1 };
      if (bx.vert) { o.vert = 'eaVert'; o.w = r2(bx.rect.w * PX); }
      s.addText(runs, o); total++;
    }
    s.addNotes(notes[i]);
  }
  const out = path.join(OUT, 'santi-deck.pptx');
  await pres.writeFile({ fileName: out });
  console.log('wrote', out, '| slides', n, '| text boxes', total);
  await browser.close();
})();
