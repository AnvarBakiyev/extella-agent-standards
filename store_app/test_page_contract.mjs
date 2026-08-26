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

test("отказ платформы переводится словами в ОБОИХ путях вызова", () => {
  // Копий обработки отказов было две; расходясь, витрина показала
  // покупательнице сырой ответ ядра (замер 23.08.2026). Контракт держит
  // единственность: одна функция, оба пути зовут её, сырого текста нет.
  const источник = template.match(
    /function отказПлатформы\(статус, сырое, роль\)\{([\s\S]*?)\n  \}/);
  assert.ok(источник, "функция отказов обязана быть одна и с этим именем");
  assert.equal((template.match(/function отказПлатформы/g) || []).length, 1,
    "вторая копия обработки отказов запрещена");
  const зовы = template.match(/отказПлатформы\(r\.status, raw, '(установщик|витрина)'\)/g) || [];
  assert.equal(зовы.length, 2, "оба пути вызова обязаны звать общую функцию");
  assert.ok(!template.includes("'ОС ответила '"),
    "сырой ответ платформы человеку не показывается");

  const отказ = new Function(`${источник[0]}; return отказПлатформы;`)();
  const недоступно = JSON.stringify({detail:
    "core /api/expert/run failed: HTTP 500: {'status': 'error', 'message': " +
    "'Target 00000000-0000-0000-0000-000000000000 is unavailable'}"});
  for (const роль of ["установщик", "витрина"]) {
    const слова = отказ(502, недоступно, роль);
    assert.match(слова, /Extella на этом компьютере не отвечает/,
      `${роль}: «устройство недоступно» обязано переводиться`);
    assert.ok(!/HTTP 500|'status'|Target /.test(слова),
      `${роль}: сырой ответ платформы не показывается`);
  }
  // Незнакомая причина тоже говорит словами и даёт следующий шаг.
  const чужое = отказ(500, JSON.stringify({detail: "kaboom {'x': 1}"}), "витрина");
  assert.ok(!чужое.includes("kaboom"), "незнакомая деталь не идёт в лицо");
  assert.match(чужое, /повтори/i, "у отказа обязан быть следующий шаг");
});

test("промпт кнопки и промпт руководства не расходятся в правиле про ключ", async () => {
  // Промпт живёт в ДВУХ местах: массив ПРОМПТ_АГЕНТУ (его копирует кнопка) и
  // раздел «Готовый промпт для агента» в content.json (его читают на экране
  // «Найти ответ»). Копии уже разошлись однажды: README велел просить ключ в
  // чате, а промпт это запрещал, и человек упирался в тупик (H81, 26.08.2026).
  // Договор держит согласие по самому опасному пункту — что делать с ключом.
  const содержимое = JSON.parse(
    await readFile(new URL("./content.json", import.meta.url), "utf8"));
  const раздел = (содержимое["разделы"] || []).find(
    (р) => String(р["заголовок"] || "").includes("промпт для агента"));
  assert.ok(раздел, "раздел с промптом обязан существовать");

  for (const [где, текст] of [["кнопка", template], ["руководство", раздел["тело"]]]) {
    assert.ok(!/Токен я дам сам|пришлёт строку тебе|Сгенерируй мне API-токен/.test(текст),
      `${где}: просить ключ у человека больше нельзя — он уже на машине`);
    assert.match(текст, /не создавай своих/,
      `${где}: запрет заводить свои токены обязан остаться`);
    assert.match(текст, /connect_mcp\.py/,
      `${где}: обязана быть команда подключения, а не поиск ключа руками`);
  }
});

test("H72: доменная проверка не слепнет на конвертах покупательского пути", () => {
  // Дословная форма ответа /api/app-agent/run от 22.08.2026: транспортный
  // конверт несёт status:"ok", конверт исполнения — status:"success" вместе
  // с expert_name, а сам ответ лежит в нём СТРОКОЙ. Парсер, который считает
  // доменом первый же строковый status, возвращает конверт — и у покупателя
  // молча мертвеют все кнопки при зелёных проверках на локальном мосте.
  const parse = parser();
  assert.deepEqual(
    parse({ status: "ok", agent_id: "agent_x", result: {
      status: "success", expert_name: "journey_capabilities",
      result: JSON.stringify({ status: "success", code: "ready" }) } }),
    { status: "success", code: "ready" },
  );
  // Доменный ответ с собственным полем result снимать по-прежнему нельзя.
  assert.deepEqual(
    parse({ status: "error", code: "boom", result: "подробности" }),
    { status: "error", code: "boom", result: "подробности" },
  );
});

test("каждый самоповтор страницы конечен, а дозор умирает с запасным выходом", () => {
  // Замер 22.08.2026: бессмертный дозор поставил 78 задач за 232 минуты при
  // трёх нажатиях. Пределы и смерть дозора при передаче работы прямому
  // пути — не стиль, а контракт.
  assert.match(template, /дозор\(10\);/);
  const дозор = template.slice(template.indexOf("function дозор"), template.indexOf("дозор(10);"));
  assert.ok(дозор.includes("осталось <= 0"), "у дозора обязан быть предел");
  const долгий = template.slice(template.indexOf("function опроситьДолгий"),
                                template.indexOf("function подключить"));
  assert.ok(долгий.includes("осталось <= 0"), "у долгого опроса обязан быть предел");
  const запасной = template.slice(template.indexOf("подождать(8000)"),
                                  template.indexOf("function дозор"));
  assert.ok(запасной.includes("завершено = true"),
    "запасной выход обязан убивать дозор, иначе он бессмертен");
  const раздача = template.slice(template.indexOf("function раздать"),
                                 template.indexOf("function вызватьSetup"));
  assert.match(раздача, /порция\(0, \d+\)/, "у раздачи обязан быть предел порций");
  assert.ok(раздача.includes("дальше <= offset"),
    "застывший offset обязан останавливать раздачу");
  // Полоса-маршрут вместо холста (решение владельца 22.08.2026): вечного
  // requestAnimationFrame больше нет, а завершение акта не двигает экран —
  // прокрутка только от руки («Дальше» или станция полосы).
  assert.ok(!template.includes("requestAnimationFrame(кадр"),
    "вечный цикл отрисовки холста убран");
  const открыть = template.slice(template.indexOf("function открыть(н"),
                                 template.indexOf("document.getElementById('дп-старт')"));
  assert.ok(!открыть.includes("scrollIntoView"),
    "завершение акта не прокручивает экран само");
  assert.match(template, /дп-полоса\{position:sticky/,
    "полоса-маршрут липнет к верху окна");
  const канал = template.slice(template.indexOf("function установитьЧерезКанал"),
                               template.indexOf("function опроситьДолгий"));
  assert.ok(канал.includes("снять_обёртки(m.result)"),
    "канальный результат обязан сниматься той же функцией, что прямой (H72)");
  assert.ok(канал.includes("e.source !== window.parent"),
    "приёмник результата обязан принимать сообщения только от родителя");
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

test('кнопки установки на паузе: экранов нет, машинерия цела, висячих привязок нет', () => {
  // Владелец 23.08.2026 снял с продукта установку агентов и локальных
  // моделей: обе связки работали ненадёжно и держали выход. Контракт держит
  // ровно это состояние — не «кнопок нет никогда», а «кнопок нет, а код,
  // который их вернёт, на месте и не разложился».
  for (const экран of ['агент', 'модели']) {
    assert.ok(!template.includes(`data-экран="${экран}"`),
      `экран «${экран}» снят с продукта`);
  }
  for (const id of ['codex-connect', 'claude-connect', 'claude-reprovision',
                    'local-llm-quality', 'local-llm-fast']) {
    assert.ok(!template.includes(`getElementById('${id}')`),
      `привязка к ${id} обязана уйти вместе с разметкой: иначе скрипт падает на null`);
  }
  // Машинерия установки остаётся: возврат кнопок — это разметка, а не переписывание.
  for (const кусок of ['function подключить(', 'function установитьЧерезКанал(',
                       'function раздать(', 'function вызватьSetup(']) {
    assert.ok(template.includes(кусок), `${кусок} обязана пережить паузу`);
  }
  // Знание про мосты и модели не пропало — оно ищется на экране «Найти ответ».
  assert.ok(template.includes('data-экран="поиск"'), 'экран поиска на месте');
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



test('хвостов от убранных экранов не осталось', () => {
  // Сравнение локальной и облачной модели объясняло выбор на экране
  // «Локальные модели». Экран сняли 23.08.2026, а блок остался висеть под
  // «Днём первым», где ему нечего объяснять (замер владельца). Вместе с ним
  // ушёл и его CSS: мёртвые правила в выложенном продукте вводят в
  // заблуждение того, кто будет читать страницу следующим.
  for (const след of ['class="compare"', 'class="cbody"', 'class="tasktypes"',
                      'Когда вдумчивость', '.compare{', '.tasktypes{']) {
    assert.ok(!template.includes(след), `хвост «${след}» обязан уйти`);
  }
});

test('главное действие — промпт со ссылкой на источник, а не снимок текста', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  // Правило раздела 10: «источник правил один… не копируй текст гида». Кнопка,
  // копирующая весь текст, ему противоречила: снимок устаревает в тот же день,
  // а агент не знает, что читает снимок.
  const действия = page.slice(page.indexOf('<div class="actions">'), page.indexOf('</div>', page.indexOf('<div class="actions">')));
  const главная = действия.slice(действия.indexOf('class="btn main"'), действия.indexOf('</button>'));
  assert.ok(главная.includes('промпт'), 'главная кнопка — промпт, а не копия текста');
  const промпт = page.slice(page.indexOf('var ПРОМПТ_АГЕНТУ'), page.indexOf("].join('\\n')"));
  // Ссылка на живой источник и вход обязаны быть в промпте.
  assert.ok(промпт.includes('github.com/AnvarBakiyev/extella-agent-standards'), 'адрес источника есть');
  // Вход — README.md. START_HERE.md сам объявляет себя историей: «вход один и
  // находится в README». Тест раньше требовал устаревший файл — и промпт вместе
  // с английским переводом уводил ассистента не туда.
  assert.ok(промпт.includes('README.md'), 'назван единственный вход');
  assert.equal(промпт.includes('START_HERE'), false, 'устаревший вход не упоминается');
  assert.ok(промпт.includes('Не копируй правила к себе'), 'запрет копии повторён ассистенту');
  // Промпт короткий: человек видит, что это не простыня.
  const строк = промпт.split('\n').filter(s => s.trim().startsWith("'")).length;
  assert.ok(строк <= 20, `промпт должен быть коротким, а в нём ${строк} строк`);
  // Копия всего текста остаётся, но второстепенной и честно названной снимком.
  assert.ok(page.includes('Скопировать весь текст'));
  assert.ok(page.includes('снимок, он устареет'), 'копия честно названа снимком');
});
