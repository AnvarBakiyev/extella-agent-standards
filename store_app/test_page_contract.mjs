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
  // Срез до следующего обработчика, а не до codex-connect: между ними теперь
  // живёт карточка локальной модели со своими этапами.
  const handler = page.slice(
    page.indexOf("getElementById('claude-reprovision')"),
    page.indexOf("function подключитьЛокальную"),
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

test('в установщик проходят только action, два числа порции и профиль из белого списка', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  const тело = page.slice(page.indexOf('params: (function()'), page.indexOf('}).then(function(r){'));
  // Копирование ключей означало бы, что подменённая страница передаёт
  // установщику произвольные поля.
  assert.equal(/for \(var k in/.test(тело), false, 'ключи не копируются');
  assert.ok(тело.includes('parseInt(ещё.offset'));
  assert.ok(тело.includes('Math.min(64'), 'порция ограничена сверху');
  // Числа приводятся к числу, а не берутся сырыми.
  assert.equal(/p\.(offset|limit) = ещё\./.test(тело), false, 'числа не берутся сырыми');
  // Единственное сырое присваивание — profile, и только внутри проверки на
  // два точных литерала: подстановка мимо них не проходит вообще.
  assert.ok(тело.includes("ещё.profile === 'quality' || ещё.profile === 'fast'"),
    'профиль ограничен двумя литералами');
  const после = тело.slice(тело.indexOf("ещё.profile === 'quality'"));
  assert.ok(после.includes('p.profile = ещё.profile'), 'профиль присваивается только после проверки');
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

test('страница живёт по замеренному контракту app-agent/run', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  // Замер 18.08.2026 probe-экспертом со сном: поле timeout НЕ соблюдается
  // (20, 150, без поля — идентично, отсечка ~51 с), а пути ожидания task_id
  // для app_token не существует. Поле в запросе было бы ложным обещанием.
  assert.equal(/timeout:/.test(page.slice(page.indexOf("fetch('/api/app-agent/run'"),
    page.indexOf('}).then(function(r){'))), false, 'поле timeout — плацебо, его быть не должно');
  const parser = page.slice(page.indexOf('BEGIN_H17_PARSER'), page.indexOf('END_H17_PARSER'));
  assert.ok(parser.includes("indexOf('deferred') === 0"), 'отложенная задача распознаётся');
  assert.ok(parser.includes('отложено.отложено = true'), 'отложенность помечается для повтора');
  assert.ok(parser.indexOf("indexOf('deferred')") < parser.indexOf('value = value.result'));
  // Рабочая стратегия — повтор идемпотентного шага, ограниченный сверху.
  const retry = page.slice(page.indexOf('function шагСПовтором'), page.indexOf('function установитьЧерезКанал'));
  assert.ok(retry.includes('осталось = 3'), 'повторы ограничены');
  assert.ok(retry.includes('error.отложено !== true'), 'повторяется только отложенность');
});

test('канал приложения кормит этапы, а тишина лечится чтением статуса', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  const канал = page.slice(page.indexOf('function установитьЧерезКанал'), page.indexOf('function подключить'));
  // Чужие сообщения не принимаются: только свой reqId.
  assert.ok(канал.includes('m.reqId !== reqId) return'), 'сообщения фильтруются по reqId');
  assert.ok(канал.includes('etb_claude_install_progress'));
  assert.ok(канал.includes('etb_claude_install_result'));
  // installer_unavailable — не ошибка, а сигнал идти прямым путём.
  assert.ok(канал.includes("m.code === 'installer_unavailable'"));
  // Переинъекция рамки съедает события без повтора: итог перечитывается
  // этапом status, а не ожиданием сообщения.
  assert.ok(канал.includes("'status'"), 'дозор перечитывает статус');
  assert.ok(канал.includes('ready_to_verify === true'), 'восстановление требует измеренной готовности');
  // Прямой путь показывает этапы по именам.
  assert.ok(page.includes('ИМЕНА_ЭТАПОВ'), 'этапы названы словами');
  assert.ok(page.includes("'Этап ' + (номер + 1)"), 'виден номер этапа');
});

test('три уровня разработки идут по порядку с заголовками', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  const i1 = page.indexOf('УРОВЕНЬ 1');
  const i2 = page.indexOf('УРОВЕНЬ 2');
  const i3 = page.indexOf('УРОВЕНЬ 3');
  assert.ok(i1 > 0 && i2 > i1 && i3 > i2, 'уровни идут 1→2→3 по порядку');
  // Уровень 1 — разработка (мосты) прежде запуска: пока агента нет, запускать нечего.
  assert.ok(page.slice(i1, i2).includes('codex-connect') &&
            page.slice(i1, i2).includes('claude-connect'), 'уровень 1 держит оба моста');
  // Уровень 2 — сложные задачи (качество), уровень 3 — ежедневные (поток).
  assert.ok(page.slice(i2, i3).includes('local-llm-quality'), 'уровень 2 — кнопка качества');
  assert.ok(page.slice(i3).includes('local-llm-fast'), 'уровень 3 — кнопка потока');
  // Уровень 3 называет типы задач: пользователь должен видеть, что запускать.
  for (const t of ['классификация', 'извлечение', 'маршрутизация']) {
    assert.ok(page.slice(i3).includes(t), `уровень 3 называет тип задачи: ${t}`);
  }
});

test('локальная модель: два профиля, свой список этапов, скачивание опросом', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  // Два профиля — две разные экономики (качество медленное, поток быстрый).
  assert.ok(page.includes('id="local-llm-quality"'), 'кнопка качества есть');
  assert.ok(page.includes('id="local-llm-fast"'), 'кнопка потока есть');
  // Своя строка состояния на профиль: прогресс качества и потока не смешивается.
  assert.ok(page.includes('id="local-llm-state-quality"') && page.includes('id="local-llm-state-fast"'),
    'у каждого профиля своя строка состояния');
  assert.ok(page.includes("'local-llm-state-' + профиль"), 'строка выбирается по профилю');
  const маршрут = page.slice(page.indexOf('function подключитьЛокальную'),
                             page.indexOf("getElementById('codex-connect')"));
  assert.ok(маршрут.includes("подключитьЛокальную('quality'") ||
            page.includes("подключитьЛокальную('quality'"), 'профиль quality передаётся');
  assert.ok(page.includes("подключитьЛокальную('fast'"), 'профиль fast передаётся');
  // Мостовые этапы сюда не относятся: у продукта свой список.
  for (const чужой of ['credentials', 'РАЗДАЧА', 'bridge']) {
    assert.equal(маршрут.includes(`'${чужой}'`), false, `этап ${чужой} чужой для локальной модели`);
  }
  assert.ok(маршрут.includes("'ОПРОС:model'"), 'скачивание идёт опросом');
  // profile проходит в установщик белым списком: ровно два значения, не строка.
  const тело = page.slice(page.indexOf('params: (function()'), page.indexOf('}).then(function(r){'));
  assert.ok(тело.includes("ещё.profile === 'quality'") && тело.includes("ещё.profile === 'fast'"),
    'профиль ограничен двумя значениями');
  assert.equal(/p\.profile = ещё\.profile\b(?![^]*['"]quality)/.test(тело), true, 'профиль присваивается только после проверки');
  // Опрос долгого этапа: мгновенные ответы с finished/прогрессом, пауза между
  // опросами, и тот же контракт расхода — иначе долгий этап уходит в
  // отложенную задачу (~51 с), дождаться которую страница не может.
  const опрос = page.slice(page.indexOf('function опроситьДолгий'), page.indexOf('function подключить'));
  assert.ok(опрос.includes('r.finished === true'));
  assert.ok(опрос.includes('подождать(20000)'));
  assert.ok(опрос.includes('model_called !== false'));
  assert.ok(опрос.includes('paid !== false'));
});
