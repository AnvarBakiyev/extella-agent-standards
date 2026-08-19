import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const template = await readFile(new URL("./page.template.html", import.meta.url), "utf8");

function parser() {
  const source = template.match(
    /\/\/ BEGIN_H17_PARSER([\s\S]*?)\/\/ END_H17_PARSER/,
  )?.[1];
  assert.ok(source, "H17 parser must remain marked in the page shell");
  return Function(`${source}; return разобрать_ответ_эксперта;`)();
}

test("page unwraps both Extella result envelopes", () => {
  const parse = parser();
  assert.deepEqual(
    parse({ result: { result: JSON.stringify({ status: "success", code: "ready" }) } }),
    { status: "success", code: "ready" },
  );
});

test("page rejects Python repr and an unexpected result shape", () => {
  const parse = parser();
  assert.throws(() => parse({ result: { result: "{'status': 'success'}" } }), /H17/);
  assert.throws(() => parse({ result: { result: JSON.stringify({ ok: true }) } }), /формой/);
});

test("shell contains one build-time app token marker", () => {
  assert.equal((template.match(/\/\*APP_TOKEN\*\/""/g) || []).length, 1);
});

test("one click runs every reviewed no-model setup step in order", () => {
  assert.match(template, /fetch\('\/api\/app-agent\/run'/);
  assert.match(
    template,
    // 'agents' заменён меткой РАЗДАЧА: он один идёт порциями.
    /\['preflight', 'install', 'credentials', 'РАЗДАЧА', 'bridge', 'verify'\]/,
  );
  // Раздача добавила два числовых поля порции; их форма проверяется отдельным
  // тестом ниже. Здесь важно, что action по-прежнему задаётся кодом страницы.
  assert.match(template, /var p = \{action: action\};/);
});

// Пересверка раздачи: кнопка обязана быть отдельной от установки, гонять только
// безмодельный этап agents и показывать числа, а не слово «готово».
test('раздача идёт порциями и складывает числа, а не берёт последнюю порцию', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  const helper = page.slice(page.indexOf('function раздать'), page.indexOf('function вызватьSetup'));
  // Один вызов на всех агентов платформа откладывает в задачу и отвечает
  // ссылкой на неё вместо результата — страница показывала это как отказ H17.
  assert.ok(helper.includes('limit: 8'));
  assert.ok(helper.includes('r.finished === true'), 'конец берётся у установщика');
  for (const поле of ['written', 'runnable', 'not_runnable', 'skipped_public']) {
    assert.ok(helper.includes(`итог.${поле} +=`), `${поле} должно складываться`);
  }
  assert.ok(helper.includes('model_called !== false'));
  assert.ok(helper.includes('paid !== false'));
});

test('кнопка пересверки раздачи гоняет только этап agents и не скрывает числа', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  assert.ok(page.includes('id="claude-reprovision"'), 'кнопка пересверки отсутствует');
  const handler = page.slice(
    page.indexOf("getElementById('claude-reprovision')"),
    page.indexOf("getElementById('codex-connect')"),
  );
  // Полная переустановка ради нового агента — лишние минуты и лишний риск.
  for (const шаг of ['preflight', 'install', 'credentials', 'bridge', 'verify']) {
    assert.equal(handler.includes(`'${шаг}'`), false, `пересверка не должна гонять ${шаг}`);
  }
  assert.ok(handler.includes('раздать('), 'пересверка обязана идти порциями');
  // Зелёным только когда без моста никого не осталось.
  assert.ok(handler.includes('r.not_runnable'));
  assert.ok(handler.includes("Number(r.not_runnable) > 0 ? 'bad' : 'ok'"));
});

test('в установщик проходят только action и два числа порции', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  const тело = page.slice(page.indexOf('params: (function()'), page.indexOf('}).then(function(r){'));
  // Копирование ключей означало бы, что подменённая страница передаёт
  // установщику произвольные поля.
  assert.equal(/for \(var k in/.test(тело), false, 'ключи не копируются');
  assert.ok(тело.includes('parseInt(ещё.offset'));
  assert.ok(тело.includes('Math.min(64'), 'порция ограничена сверху');
  assert.equal(/p\.[a-z_]+ = ещё\./.test(тело), false, 'сырые значения не проходят');
});

test('копирование пробует запасной путь, когда clipboard отклоняет запись', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  const тело = page.slice(page.indexOf('function скопировать'), page.indexOf('document.addEventListener'));
  // В рамке приложения clipboard существует и отклоняет — отказ без попытки
  // execCommand означает нерабочую кнопку ровно там, где ей пользуются.
  assert.ok(тело.includes('.then(ok, запасной)'), 'на отказ clipboard идёт запасной путь');
  assert.ok(тело.includes('execCommand'));
  // Сдаёмся словами только после того, как не сработали оба пути.
  assert.ok(тело.indexOf('запасной()') > 0);
});
