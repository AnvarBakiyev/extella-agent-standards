/* Run after: npm i -D playwright && npx playwright install chromium
   Then: node tests/smoke.mjs  (from this folder) */
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, resolve } from 'node:path';
import { chromium } from 'playwright';

const root = resolve('app');
const types = { '.html':'text/html', '.css':'text/css', '.js':'application/javascript' };
const server = createServer(async (req, res) => {
  const path = join(root, req.url === '/' ? 'index.html' : req.url);
  try { await stat(path); res.writeHead(200, {'Content-Type':types[extname(path)] || 'text/plain'}); res.end(await readFile(path)); }
  catch { res.writeHead(404); res.end('not found'); }
}).listen(4173);

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('http://127.0.0.1:4173');
await page.getByTestId('task-input').fill('Проверить запуск');
await page.getByTestId('run-button').click();
await page.getByTestId('result').waitFor();
if (!(await page.getByTestId('result').textContent()).includes('Проверить запуск')) throw new Error('Не появился локальный результат');
await page.getByRole('button', {name:'Риск'}).click();
if (!(await page.getByTestId('result').textContent()).includes('Риск')) throw new Error('Сценарий не пересчитал результат');

// H104/§46: незакреплённый вызов ушёл на устройство другого аккаунта. Поле
// появляется только на этой подписи; ручной Device ID проверяется целевым вызовом.
const device = '24f37e45-8c9f-4896-b64f-0dcd0cd8b0e4';
await page.route('https://os.extella.ai/api/app-agent/run', async route => {
  const body = JSON.parse(route.request().postData() || '{}');
  if (!body.targets?.length) {
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
      status:'ok', result:{status:'success',expert_name:'my_app_where',
        result:'[Execution Error] invalid decimal literal (<container>, line 1)'},
    })});
  }
  const result = body.expert_name === 'my_app_where'
    ? {status:'success',device,pageRoute:{targetId:device},host:'test-mac.local'}
    : {status:'success',text:'Ответ с выбранного устройства'};
  return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
    status:'ok', result:{status:'success',expert_name:body.expert_name,result:JSON.stringify(result)},
  })});
});
await page.evaluate(() => { window.__APP_TEST__.bridge.appToken='test-app-token'; window.__APP_TEST__.bridge.device=null; window.__APP_TEST__.bridge.discovery=null; });
await page.getByTestId('task-input').fill('Проверить H104');
await page.getByTestId('run-button').click();
await page.locator('#device-connect').waitFor({state:'visible'});
await page.locator('#device-id').fill(device);
await page.getByRole('button', {name:'Работать через это устройство'}).click();
await page.getByText('Ответ с выбранного устройства').waitFor();
console.log('SMOKE OK');
await browser.close(); server.close();
