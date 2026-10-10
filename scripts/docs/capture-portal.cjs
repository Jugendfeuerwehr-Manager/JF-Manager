/* Portal, participation and drag-and-drop images for the handbook (DOC-01.5).
 * Run only against backend/demo.py's isolated database, like capture-screenshots.cjs.
 * Animated GIFs need ffmpeg on the PATH. */
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const demoDir = process.env.JF_SCREENSHOT_DEMO_DIR;
if (!demoDir || !path.basename(demoDir).startsWith('jf-manager-demo-')) {
  throw new Error('JF_SCREENSHOT_DEMO_DIR must be the temporary directory created by demo.py.');
}
const env = Object.fromEntries(fs.readFileSync(path.join(demoDir, 'demo.env'), 'utf8')
  .trim().split('\n').map(line => [line.slice(0, line.indexOf('=')), line.slice(line.indexOf('=') + 1)]));
if (env.DJANGO_SETTINGS_MODULE !== 'jf_manager_backend.demo_settings' ||
    path.resolve(env.JF_DEMO_DATABASE) !== path.join(path.resolve(demoDir), 'demo.sqlite3')) {
  throw new Error('Refusing non-isolated database.');
}
const base = process.env.JF_SCREENSHOT_URL || 'http://127.0.0.1:5174';
if (!['localhost', '127.0.0.1'].includes(new URL(base).hostname)) throw new Error('Local demo only.');
const out = path.resolve('docs/handbook/images');
// The dev server adds a Vue devtools button; it does not belong in handbook images.
const HIDE_DEVTOOLS = `addEventListener('DOMContentLoaded', () => {
  const style = document.createElement('style');
  style.textContent = '[id*="vue-devtools"], [class*="vue-devtools"] { display: none !important; }';
  document.head.append(style);
});`;
const login = JSON.parse(fs.readFileSync(path.join(demoDir, 'login.json'), 'utf8'));
const python = process.env.JF_DEMO_PYTHON || 'python';
const djangoShell = code => execFileSync(python, ['manage.py', 'shell', '-c', code], {
  cwd: path.resolve('backend'), env: {...process.env, ...env}, encoding: 'utf8',
}).trim().split('\n').pop();

// Demo services with positions (opt-in) and with the assignment board, both seeded by seed_demo.
const ids = JSON.parse(djangoShell(
  'import json; from participation.models import SessionParticipation as P; ' +
  'print(json.dumps({m: P.objects.filter(mode=m).values_list("session_id", flat=True).first() for m in ("opt_in", "assignment")}))'));

async function settle(page, text) {
  await page.getByText(text, {exact: false}).first().waitFor({timeout: 20000});
  await page.waitForTimeout(1200);
  if (/konnte[n]? nicht geladen|Netzwerkfehler/.test(await page.locator('body').innerText())) {
    throw new Error('Page contains a load error near: ' + text);
  }
}

async function shot(page, name, locator) {
  await (locator ?? page).screenshot({path: path.join(out, name + '.png')});
  console.log('Captured ' + name);
}

async function staffLogin(page) {
  await page.goto(base + '/login');
  await page.fill('#username', login.username);
  await page.fill('#password', login.password);
  await page.getByRole('button', {name: 'Anmelden', exact: true}).click();
  await page.locator('#mfa-code').waitFor();
  const code = execFileSync(python, ['manage.py', 'demo_totp', 'admin'], {
    cwd: path.resolve('backend'), env: {...process.env, ...env}, encoding: 'utf8',
  }).trim();
  await page.fill('#mfa-code', code);
  await page.getByRole('button', {name: 'Bestätigen', exact: true}).click();
  await page.waitForURL(base + '/');
}

async function openParticipation(page, sessionId) {
  await page.goto(`${base}/training/sessions/${sessionId}/plan`);
  await settle(page, 'Speichern');
  const direct = page.getByRole('button', {name: 'Teilnahme', exact: true});
  if (await direct.count()) await direct.first().click();
  else {
    await page.getByRole('button', {name: 'Weitere Aktionen'}).click();
    await page.getByRole('menuitem', {name: 'Teilnahme'}).click();
  }
  await page.getByRole('tablist', {name: 'Teilnahme'}).waitFor();
}

function toGif(video, name, width = 960) {
  const target = path.join(out, name + '.gif');
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', video, '-vf',
    `fps=8,scale=${width}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer`,
    target]);
  console.log('Captured ' + name + '.gif');
}

(async () => {
  const launched = await chromium.launch({headless: true,
    ...(process.env.CHROME_PATH ? {executablePath: process.env.CHROME_PATH} : {})});
  const browser = {
    newContext: async options => { const context = await launched.newContext(options); await context.addInitScript(HIDE_DEVTOOLS); return context; },
    close: () => launched.close(),
  };
  const videoDir = fs.mkdtempSync(path.join(os.tmpdir(), 'jf-handbook-video-'));
  try {
    // Staff views: inbox, change requests, positions, registrations and the assignment board.
    const staff = await browser.newContext({viewport: {width: 1440, height: 1000}});
    const page = await staff.newPage();
    await staffLogin(page);
    await page.goto(base + '/eingang');
    await settle(page, 'Eingang');
    await shot(page, 'inbox');
    await page.goto(base + '/portal-verwaltung?tab=antraege');
    await settle(page, 'Anträge');
    await shot(page, 'change-requests');
    await openParticipation(page, ids.opt_in);
    await page.waitForTimeout(800);
    await shot(page, 'participation-positions', page.getByRole('dialog'));
    await page.getByRole('tab', {name: /Meldungen/}).click();
    await page.waitForTimeout(1000);
    await shot(page, 'participation-registrations', page.getByRole('dialog'));
    // One TOTP code is valid once; later contexts reuse this signed-in session.
    const storageState = await staff.storageState();
    await staff.close();

    // Drag and drop on the assignment board, recorded as an animation.
    const boardContext = await browser.newContext({viewport: {width: 1280, height: 860},
      storageState, recordVideo: {dir: videoDir, size: {width: 1280, height: 860}}});
    const board = await boardContext.newPage();
    await openParticipation(board, ids.assignment);
    await board.getByRole('tab', {name: /Zuteilung/}).click();
    await settle(board, 'Bewerbungen');
    await shot(board, 'assignment-board', board.getByRole('dialog'));
    const card = board.locator('.board__applicants article.card').first();
    const zone = board.locator('.board__slots .zone:not([aria-disabled="true"])').first();
    await card.hover();
    await board.waitForTimeout(700);
    await card.dragTo(zone, {steps: 25});
    await board.waitForTimeout(1600);
    const boardVideo = await board.video().path();
    await boardContext.close();
    toGif(boardVideo, 'assignment-drag');

    // Drag a library block into the planner.
    const plannerContext = await browser.newContext({viewport: {width: 1440, height: 900},
      storageState, recordVideo: {dir: videoDir, size: {width: 1440, height: 900}}});
    const planner = await plannerContext.newPage();
    await planner.goto(`${base}/training/sessions/${ids.opt_in}/plan`);
    await planner.getByRole('button', {name: 'Weitere Aktionen'}).waitFor({timeout: 30000});
    await planner.waitForTimeout(1000);
    // The library may already be open (remembered per user); otherwise open it from the header.
    const opened = await planner.locator('.picker-item').first().waitFor({timeout: 5000}).then(() => true, () => false);
    if (!opened) await planner.locator('button', {hasText: 'Bibliothek'}).first().click();
    await planner.locator('.picker-item').first().waitFor();
    await planner.waitForTimeout(800);
    await planner.locator('.picker-item').first().dragTo(planner.locator('.lane-col').first(), {steps: 25, targetPosition: {x: 60, y: 160}});
    await planner.waitForTimeout(1600);
    const plannerVideo = await planner.video().path();
    await plannerContext.close();
    toGif(plannerVideo, 'planner-drag', 1024);

    // Parent portal on a phone: overview, sessions and choosing a position.
    const parent = await browser.newContext({viewport: {width: 390, height: 844}, deviceScaleFactor: 2, isMobile: true, hasTouch: true});
    const portal = await parent.newPage();
    await portal.goto(base + '/login');
    await portal.fill('#username', 'eltern@demo.example.invalid');
    await portal.fill('#password', login.password);
    await portal.getByRole('button', {name: 'Anmelden', exact: true}).click();
    await portal.waitForURL(/\/portal/);
    await settle(portal, 'Termine');
    await shot(portal, 'portal-home');
    await portal.goto(base + '/portal/termine');
    await settle(portal, 'Termine');
    await shot(portal, 'portal-sessions');
    await portal.goto(`${base}/portal/termine/${ids.opt_in}`);
    await settle(portal, 'Brandsicherheitswache');
    await shot(portal, 'portal-positions');
    await parent.close();
  } finally {
    await browser.close();
    fs.rmSync(videoDir, {recursive: true, force: true});
  }
})().catch(error => {
  console.error(error);
  process.exit(1);
});
