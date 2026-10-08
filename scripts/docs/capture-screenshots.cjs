/* Run only against backend/demo.py's isolated database. See handbook/publishing.md. */
const fs = require('node:fs');
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
const login = JSON.parse(fs.readFileSync(path.join(demoDir, 'login.json'), 'utf8'));
(async () => {
  const browser = await chromium.launch({headless: true,
    ...(process.env.CHROME_PATH ? {executablePath: process.env.CHROME_PATH} : {})});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}, deviceScaleFactor: 1});
    const capture = async (name, route, text) => {
      await page.goto(base + route);
      await page.getByText(text, {exact: false}).first().waitFor().catch(async error => {
        console.error((await page.locator('body').innerText()).slice(0, 3500));
        throw error;
      });
      await page.waitForTimeout(1400); // settle asynchronous tables and fonts
      if (/konnte[n]? nicht geladen|Netzwerkfehler/.test(await page.locator('body').innerText())) {
        console.error((await page.locator('body').innerText()).slice(0, 4000));
        throw new Error('Page contains a load error: ' + route);
      }
      await page.screenshot({path: path.join(out, name + '.png'), fullPage: false});
      console.log('Captured ' + name);
    };
    await capture('login', '/login', 'Anmelden');
    await page.fill('#username', login.username);
    await page.fill('#password', login.password);
    await page.getByRole('button', {name: 'Anmelden', exact: true}).click();
    await page.locator('#mfa-code').waitFor();
    const code = execFileSync(process.env.JF_DEMO_PYTHON || 'python', ['manage.py', 'demo_totp', 'admin'], {
      cwd: path.resolve('backend'), env: {...process.env, ...env}, encoding: 'utf8'
    }).trim();
    await page.fill('#mfa-code', code);
    await page.getByRole('button', {name: 'Bestätigen', exact: true}).click();
    await page.waitForURL(base + '/');
    await capture('dashboard', '/', 'Dashboard');
    await capture('setup', '/settings/setup', 'Einrichtung');
    await capture('roles', '/roles', 'Rollen');
    const personOptions = await page.locator('#role-person option').evaluateAll(items => items.map(o => ({value:o.value, text:o.textContent})));
    await page.selectOption('#role-person', personOptions.find(p => p.text === 'Mira Brandt').value);
    await page.selectOption('#role-area', '1');
    await page.selectOption('#role-choice', {label:'Betreuer'});
    await page.getByRole('button', {name:'Wirkung prüfen', exact:true}).click();
    await page.getByRole('heading', {name:'Hinzu kommende Rechte', exact:true}).waitFor();
    await page.screenshot({path:path.join(out,'roles.png')});
    await page.getByRole('button', {name:'Vorschau verwerfen', exact:true}).click();
    await capture('role-templates', '/role-templates', 'Rollenvorlagen');
    await capture('report', '/servicebook/report', 'Anwesenheitsauswertung');
    await capture('profile', '/profile', 'Profil');
    await page.locator('#device-heading').evaluate(node => node.scrollIntoView({block:'start'}));
    await page.locator('.device-settings').screenshot({path:path.join(out,'devices.png')});
    const user = await (await page.request.get(base + '/api/v1/users/me/')).json();
    const scope = '?department=' + user.favorite_department;
    const services = await (await page.request.get(base + '/api/v1/servicebook/services/' + scope)).json();
    const service = services.results.find(s => s.id);
    if (!service) throw new Error('No seeded service.');
    await capture('attendance', `/servicebook/${service.id}/attendance`, 'Anwesend');
    const sessions = await (await page.request.get(base + '/api/v1/training/sessions/' + scope)).json();
    const session = sessions.results.find(s => s.status === 'published');
    if (!session) throw new Error('No published demo training.');
    await capture('planner', `/training/sessions/${session.id}/plan`, 'Speichern');
    await page.setViewportSize({width: 390, height: 844});
    await capture('execution-mobile', `/training/sessions/${session.id}/run`, 'Station');
    await page.getByRole('button', {name:'Nächster Abschnitt', exact:true}).click();
    await page.screenshot({path:path.join(out,'execution-mobile.png')});
    await capture('mobile', '/', 'Module');
    await page.getByRole('button', {name:'Alle Module', exact:true}).click();
    await page.waitForTimeout(300);
    await page.screenshot({path:path.join(out,'mobile.png')});
    fs.writeFileSync(path.join(out, 'provenance.json'), JSON.stringify({
      captured_on: '2026-10-08', source: 'backend/demo.py + seed_demo (isolated SQLite, fictitious data)',
      source_commit: execFileSync('git', ['rev-parse', 'HEAD'], {encoding:'utf8'}).trim(),
      viewports: {desktop: [1440,1000], mobile: [390,844]},
      accounts: ['admin (synthetic demo superuser)'],
      scope: 'Existing staff UI; portal changes in progress are not documented.'
    }, null, 2) + '\n');
  } finally { await browser.close(); }
})().catch(error => {console.error(error.message); process.exitCode = 1;});
