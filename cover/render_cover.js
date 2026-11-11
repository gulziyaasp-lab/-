// Рендер обложки рилса 1080x1920: node render_cover.js out.png [фото_лаунжа.jpg]
const { chromium } = require('playwright');
const path = require('path'), { pathToFileURL } = require('url');
(async () => {
  let url = pathToFileURL(path.join(__dirname, 'cover.html')).href;
  if (process.argv[3]) url += '?photo=' + encodeURIComponent(pathToFileURL(path.resolve(process.argv[3])).href);
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await pg.goto(url); await pg.waitForTimeout(300);
  await pg.screenshot({ path: process.argv[2] });
  await b.close();
})();
