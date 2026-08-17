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
    /\['preflight', 'install', 'credentials', 'agents', 'bridge', 'verify'\]/,
  );
  assert.match(template, /params: \{action: action\}/);
});

// Пересверка раздачи: кнопка обязана быть отдельной от установки, гонять только
// безмодельный этап agents и показывать числа, а не слово «готово».
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
  assert.ok(handler.includes("'agents'"));
  // Тот же контракт расхода, что у установки.
  assert.ok(handler.includes('model_called !== false'));
  assert.ok(handler.includes('paid !== false'));
  // Зелёным только когда без моста никого не осталось.
  assert.ok(handler.includes('r.not_runnable'));
  assert.ok(handler.includes("Number(r.not_runnable) > 0 ? 'bad' : 'ok'"));
});
