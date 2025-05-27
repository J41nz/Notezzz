const puppeteer = require('puppeteer');
const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:5000';
const FLAG = process.env.FLAG || 'test{flag}';
const sleep = ms => new Promise(res => setTimeout(res, ms));

const CONFIG = {
  APPNAME: process.env.APPNAME || 'Admin',
  APPURL: process.env.BASE_URL || 'http://127.0.0.1:8000',
  APPURLREGEX: process.env.APPURLREGEX || '^.*$',
  APPFLAG: process.env.FLAG || FLAG,
  APPLIMITTIME: Number(process.env.APPLIMITTIME || '60'),
  APPLIMIT: Number(process.env.APPLIMIT || '5'),
};

console.table(CONFIG);

const initBrowser = puppeteer.launch({
  executablePath: '/usr/bin/chromium-browser',
  headless: 'new',
  args: [
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-gpu',
    '--no-gpu',
    '--disable-default-apps',
    '--disable-translate',
    '--disable-device-discovery-notifications',
    '--proxy-server="direct://"',
    '--proxy-bypass-list=*',
    '--disable-software-rasterizer',
    '--disable-xss-auditor',
  ],
  ignoreHTTPSErrors: true,
});

console.log('Bot started...');

module.exports = {
  name: CONFIG.APPNAME,
  urlRegex: CONFIG.APPURLREGEX,
  rateLimit: {
    windowMs: CONFIG.APPLIMITTIME * 1000,
    max: CONFIG.APPLIMIT,
  },

  bot: async (urlToVisit) => {
    const browser = await initBrowser;
    const context = await browser.createIncognitoBrowserContext();
    const page = await context.newPage();

    page.on('request', req => {
      console.log(`[BOT] → ${req.method()} ${req.url()}`);
    });

    page.on('response', res => {
      console.log(`[BOT] ← ${res.status()} ${res.url()}`);
    });

    page.on('requestfailed', req => {
      console.error(`[BOT] ✗ ${req.url()} failed:`, req.failure());
    });

    try {
      const domain = new URL(BASE_URL).hostname;
      await page.setCookie({
        name: 'flag',
        value: CONFIG.APPFLAG,
        domain,
        httpOnly: false,
        secure: false,
      });

      console.log(`[BOT] Visiting: ${urlToVisit}`);
      await page.goto(urlToVisit, {
        timeout: 3000,
        waitUntil: 'domcontentloaded',
      });
      console.log('[BOT] DOMContentLoaded fired');

      await sleep(5000);

      console.log(`[BOT] Successfully visited ${urlToVisit}`);
      await context.close();
      return true;

    } catch (err) {
      console.error(`[BOT] ERROR visiting ${urlToVisit}:`, err.name, err.message);
      await context.close();
      return false;
    }
  },
};