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
console.log('SMOKE OK');
await browser.close(); server.close();
