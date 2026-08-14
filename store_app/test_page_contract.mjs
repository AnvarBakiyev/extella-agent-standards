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
  assert.match(
    template,
    /\['preflight', 'prepare', 'install', 'credentials', 'bridge', 'verify'\]/,
  );
  assert.match(template, /params: \{action: action\}/);
});
