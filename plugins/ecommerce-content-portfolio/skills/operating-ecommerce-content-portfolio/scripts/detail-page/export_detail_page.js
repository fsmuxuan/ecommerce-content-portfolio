#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('url');

function fail(message) {
  throw new Error(message);
}

function parseArgs(argv) {
  const values = { width: 750, scale: 2, selector: '[data-export-width]', moduleSelector: '[data-export-section]' };
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith('--')) fail(`Unexpected argument: ${key}`);
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) fail(`Missing value for ${key}`);
    index += 1;
    if (key === '--html') values.html = value;
    else if (key === '--output-dir') values.outputDir = value;
    else if (key === '--width') values.width = Number(value);
    else if (key === '--scale') values.scale = Number(value);
    else if (key === '--selector') values.selector = value;
    else if (key === '--module-selector') values.moduleSelector = value;
    else if (key === '--chrome') values.chrome = value;
    else fail(`Unknown argument: ${key}`);
  }
  if (!values.html) fail('Required argument: --html');
  if (!values.outputDir) fail('Required argument: --output-dir');
  if (!Number.isInteger(values.width) || values.width < 320) fail('--width must be an integer of at least 320');
  if (!Number.isInteger(values.scale) || values.scale < 2) fail('--scale must be an integer of at least 2');
  return values;
}

function loadPlaywright() {
  const attempts = [];
  const tryLoad = (candidate) => {
    if (!candidate) return null;
    try { return require(candidate); } catch (error) { attempts.push(`${candidate}: ${error.message}`); return null; }
  };
  let loaded = tryLoad('playwright');
  if (loaded) return loaded;
  loaded = tryLoad(process.env.PLAYWRIGHT_MODULE);
  if (loaded) return loaded;
  loaded = tryLoad('/Applications/ChatGPT.app/Contents/Resources/cua_node/lib/node_modules/playwright');
  if (loaded) return loaded;

  const pnpmRoot = path.join(
    os.homedir(), '.cache', 'codex-runtimes', 'codex-primary-runtime',
    'dependencies', 'node', 'node_modules', '.pnpm'
  );
  if (fs.existsSync(pnpmRoot)) {
    const versions = fs.readdirSync(pnpmRoot).filter((name) => name.startsWith('playwright@')).sort().reverse();
    for (const version of versions) {
      loaded = tryLoad(path.join(pnpmRoot, version, 'node_modules', 'playwright'));
      if (loaded) return loaded;
    }
  }
  fail(`Playwright is unavailable. Install it or set PLAYWRIGHT_MODULE. Attempts: ${attempts.join(' | ')}`);
}

function findChrome(explicit) {
  const candidates = [
    explicit,
    process.env.CHROME_PATH,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ].filter(Boolean);
  const found = candidates.find((candidate) => fs.existsSync(candidate));
  if (!found) fail('Chrome or Chromium was not found. Pass --chrome /absolute/path/to/browser.');
  return found;
}

function pngSize(filePath) {
  const buffer = fs.readFileSync(filePath);
  if (buffer.length < 24 || buffer.toString('ascii', 1, 4) !== 'PNG') fail(`Not a valid PNG: ${filePath}`);
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

function safeName(value, fallback) {
  const cleaned = String(value || fallback).replace(/[^a-zA-Z0-9_-]+/g, '-').replace(/^-+|-+$/g, '');
  return cleaned || fallback;
}

async function run() {
  const options = parseArgs(process.argv.slice(2));
  const html = path.resolve(options.html);
  const outputDir = path.resolve(options.outputDir);
  if (!fs.existsSync(html) || !fs.statSync(html).isFile()) fail(`HTML file does not exist: ${html}`);
  fs.mkdirSync(outputDir, { recursive: true });

  const { chromium } = loadPlaywright();
  const chrome = findChrome(options.chrome);
  const browser = await chromium.launch({ executablePath: chrome, headless: true });
  const context = await browser.newContext({
    viewport: { width: options.width, height: 900 },
    deviceScaleFactor: options.scale,
    locale: 'zh-CN',
  });
  const page = await context.newPage();
  try {
    await page.goto(pathToFileURL(html).href, { waitUntil: 'load', timeout: 30000 });
    await page.evaluate(async () => {
      if (document.fonts && document.fonts.ready) await document.fonts.ready;
      await Promise.all(Array.from(document.images).map((image) => {
        if (image.complete) return Promise.resolve();
        return new Promise((resolve) => {
          image.addEventListener('load', resolve, { once: true });
          image.addEventListener('error', resolve, { once: true });
        });
      }));
    });

    const failedImages = await page.evaluate(() => Array.from(document.images)
      .filter((image) => !image.complete || image.naturalWidth === 0)
      .map((image) => image.getAttribute('src') || '(missing src)'));
    if (failedImages.length) fail(`Images failed to load: ${failedImages.join(', ')}`);

    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    if (overflow.scrollWidth > overflow.clientWidth + 1) {
      fail(`Horizontal overflow detected: ${overflow.scrollWidth}px > ${overflow.clientWidth}px`);
    }

    const root = page.locator(options.selector).first();
    if (await root.count() !== 1) fail(`Page root not found with selector: ${options.selector}`);
    const rootBox = await root.boundingBox();
    if (!rootBox) fail('Page root has no visible bounding box.');
    if (Math.abs(rootBox.width - options.width) > 1) {
      fail(`Page root width is ${rootBox.width}px; expected ${options.width}px.`);
    }

    const targetPixelWidth = options.width * options.scale;
    const outputs = [];
    const fullPath = path.join(outputDir, '00_完整详情页_2x.png');
    await root.screenshot({ path: fullPath, type: 'png', animations: 'disabled', scale: 'device' });
    const fullSize = pngSize(fullPath);
    if (fullSize.width !== targetPixelWidth) {
      fail(`Full PNG width is ${fullSize.width}px; expected ${targetPixelWidth}px.`);
    }
    outputs.push({ type: 'full', file: path.basename(fullPath), ...fullSize });

    const modules = page.locator(options.moduleSelector);
    const moduleCount = await modules.count();
    if (moduleCount === 0) fail(`No export modules found with selector: ${options.moduleSelector}`);
    for (let index = 0; index < moduleCount; index += 1) {
      const module = modules.nth(index);
      const box = await module.boundingBox();
      if (!box) fail(`Export module ${index + 1} has no visible bounding box.`);
      const name = await module.getAttribute('data-export-section');
      const fileName = `${String(index + 1).padStart(2, '0')}_${safeName(name, `module-${index + 1}`)}.png`;
      const filePath = path.join(outputDir, fileName);
      await module.screenshot({
        path: filePath,
        type: 'png',
        animations: 'disabled',
        scale: 'device',
      });
      const size = pngSize(filePath);
      if (size.width !== targetPixelWidth) {
        fail(`Module PNG ${fileName} width is ${size.width}px; expected ${targetPixelWidth}px.`);
      }
      outputs.push({ type: 'module', section: name || `module-${index + 1}`, file: fileName, ...size });
    }

    const report = {
      html,
      outputDir,
      cssWidth: options.width,
      scale: options.scale,
      targetPixelWidth,
      imageCount: await page.locator('img').count(),
      moduleCount,
      horizontalOverflow: false,
      outputs,
    };
    fs.writeFileSync(path.join(outputDir, 'export-report.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  process.stderr.write(`ERROR: ${error.message}\n`);
  process.exit(1);
});
