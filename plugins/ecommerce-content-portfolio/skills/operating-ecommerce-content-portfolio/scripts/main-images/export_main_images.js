#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('url');

function fail(message) { throw new Error(message); }

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key || !key.startsWith('--') || !value) fail(`Invalid argument near ${key || '(empty)'}`);
    if (key === '--html') options.html = value;
    else if (key === '--output-dir') options.outputDir = value;
    else if (key === '--chrome') options.chrome = value;
    else fail(`Unknown argument: ${key}`);
  }
  if (!options.html || !options.outputDir) fail('Required arguments: --html and --output-dir');
  return options;
}

function loadPlaywright() {
  const candidates = [
    'playwright',
    process.env.PLAYWRIGHT_MODULE,
    '/Applications/ChatGPT.app/Contents/Resources/cua_node/lib/node_modules/playwright',
  ].filter(Boolean);
  const roots = [
    path.join(os.homedir(), '.cache', 'codex-runtimes', 'codex-primary-runtime', 'dependencies', 'node', 'node_modules', '.pnpm'),
  ];
  for (const root of roots) {
    if (!fs.existsSync(root)) continue;
    for (const name of fs.readdirSync(root).filter((item) => item.startsWith('playwright@')).sort().reverse()) {
      candidates.push(path.join(root, name, 'node_modules', 'playwright'));
    }
  }
  for (const candidate of candidates) {
    try { return require(candidate); } catch (_) { /* try next */ }
  }
  fail('Playwright is unavailable. Install it or set PLAYWRIGHT_MODULE.');
}

function findChrome(explicit) {
  const candidates = [
    explicit,
    process.env.CHROME_PATH,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
  ].filter(Boolean);
  const found = candidates.find((candidate) => fs.existsSync(candidate));
  if (!found) fail('Chrome or Chromium was not found. Pass --chrome or set CHROME_PATH.');
  return found;
}

function pngSize(filePath) {
  const buffer = fs.readFileSync(filePath);
  if (buffer.length < 24 || buffer.toString('ascii', 1, 4) !== 'PNG') fail(`Invalid PNG: ${filePath}`);
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

function safeFileName(value, fallback) {
  const cleaned = String(value || fallback).replace(/[\\/:*?"<>|\u0000-\u001F]/g, '-').trim();
  return cleaned || fallback;
}

async function waitForAssets(page) {
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
  const failures = await page.evaluate(() => Array.from(document.images)
    .filter((image) => image.naturalWidth === 0)
    .map((image) => image.getAttribute('src')));
  if (failures.length) fail(`Images failed to load: ${failures.join(', ')}`);
}

async function exportProfile(browser, html, outputDir, profile) {
  const context = await browser.newContext({ viewport: { width: 750, height: 750 }, deviceScaleFactor: profile.size / 750, locale: 'zh-CN' });
  const page = await context.newPage();
  try {
    await page.goto(pathToFileURL(html).href, { waitUntil: 'load', timeout: 30000 });
    await waitForAssets(page);
    const root = page.locator('[data-export-width]').first();
    const box = await root.boundingBox();
    if (!box || Math.abs(box.width - 750) > 1) fail(`Preview width must be 750 CSS px; got ${box && box.width}`);
    const cards = page.locator('[data-export-section]');
    if (await cards.count() !== 5) fail('Expected exactly five export cards.');
    const imageCounts = await page.locator('[data-platform-card]').evaluateAll((nodes) => nodes.map((node) => node.querySelectorAll('img.primary-photo').length));
    if (imageCounts.length !== 5 || imageCounts.some((count) => count !== 1)) fail(`Each card needs one primary photo: ${imageCounts.join(', ')}`);
    fs.mkdirSync(outputDir, { recursive: true });
    const outputs = [];
    for (let index = 0; index < 5; index += 1) {
      const rawName = await cards.nth(index).getAttribute('data-export-name');
      const baseName = safeFileName(rawName, `${String(index + 1).padStart(2, '0')}_主图`);
      const fileName = `${baseName}_${profile.size}.png`;
      const filePath = path.join(outputDir, fileName);
      await cards.nth(index).screenshot({ path: filePath, type: 'png', scale: 'device', animations: 'disabled' });
      const size = pngSize(filePath);
      if (size.width !== profile.size || size.height !== profile.size) fail(`${fileName} is ${size.width}x${size.height}`);
      outputs.push({ file: fileName, ...size });
    }
    return outputs;
  } finally {
    await context.close();
  }
}

async function run() {
  const options = parseArgs(process.argv.slice(2));
  const html = path.resolve(options.html);
  const outputRoot = path.resolve(options.outputDir);
  if (!fs.existsSync(html)) fail(`HTML does not exist: ${html}`);
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ executablePath: findChrome(options.chrome), headless: true });
  const profiles = [
    { key: '1500x1500', size: 1500, dir: path.join(outputRoot, 'master-1500') },
    { key: '1000x1000', size: 1000, dir: path.join(outputRoot, 'platform_exports', '1000x1000') },
    { key: '800x800', size: 800, dir: path.join(outputRoot, 'platform_exports', '800x800') },
  ];
  const report = { html, moduleCount: 5, profiles: {}, generatedAt: new Date().toISOString() };
  try {
    for (const profile of profiles) report.profiles[profile.key] = await exportProfile(browser, html, profile.dir, profile);
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(outputRoot, 'export-report.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

run().catch((error) => {
  process.stderr.write(`ERROR: ${error.message}\n`);
  process.exit(1);
});
