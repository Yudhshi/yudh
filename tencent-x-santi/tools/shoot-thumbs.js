// 44枚を 1920×1080 で描いて、通し稽古シート用の縮小 JPEG（480×270）を rehearsal/thumbs/ に書く。
// 使い方: node tools/shoot-thumbs.js   （playwright と Chromium が要る。無い機械では既存の thumbs をそのまま使う）
const path = require('path');
const fs = require('fs');
let chromium;
try { chromium = require('playwright').chromium; } catch (e) { chromium = require('/opt/node22/lib/node_modules/playwright').chromium; }
(async () => {
  const root = path.resolve(__dirname, '..');
  const out = path.join(root, 'slides/rehearsal/thumbs');
  fs.mkdirSync(out, { recursive: true });
  const opts = {}; if (fs.existsSync('/opt/pw-browsers/chromium')) opts.executablePath = '/opt/pw-browsers/chromium';
  const browser = await chromium.launch(opts);
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 0.25 });
  await page.goto('file://' + path.join(root, 'slides/slides.html'), { waitUntil: 'load' });
  await page.evaluate(async () => { await document.fonts.ready; });
  const n = await page.$$eval('.slide', els => els.length);
  for (let i = 0; i < n; i++) {
    await page.evaluate((i) => {
      const s = document.querySelectorAll('.slide'); s.forEach(x => x.classList.remove('active')); s[i].classList.add('active');
    }, i);
    await page.evaluate(async () => { await document.fonts.ready; });
    await page.waitForTimeout(700);
    await page.screenshot({ path: path.join(out, `s${String(i + 1).padStart(2, '0')}.jpg`), type: 'jpeg', quality: 78 });
  }
  await browser.close();
  console.log('thumbs', n);
})();
