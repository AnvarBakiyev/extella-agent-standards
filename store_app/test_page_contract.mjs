import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const template = await readFile(new URL("./page.template.html", import.meta.url), "utf8");

const строкиОболочки = JSON.parse(
  await readFile(new URL("./shell.json", import.meta.url), "utf8")).строки;

// Разборщик теперь берёт текст отказов из таблицы строк (H117), поэтому ему
// передаётся настоящий помощник т() на выбранном языке.
function parser(язык = "ru") {
  const source = template.match(
    /\/\/ BEGIN_H17_PARSER([\s\S]*?)\/\/ END_H17_PARSER/,
  )?.[1];
  assert.ok(source, "H17 parser must remain marked in the page shell");
  return Function("т", "тф", `${source}; return разобрать_ответ_эксперта;`)(
    (ключ) => (строкиОболочки[ключ] || {})[язык] || "",
    (ключ, знач) => String((строкиОболочки[ключ] || {})[язык] || "").replace(
      /\{([A-Za-zА-Яа-яЁё0-9_]+)\}/g,
      (всё, имя) => (знач && знач[имя] !== undefined ? String(знач[имя]) : всё)),
  );
}

test("page unwraps both Extella result envelopes", () => {
  const parse = parser();
  assert.deepEqual(
    parse({ result: { result: JSON.stringify({ status: "success", code: "ready" }) } }),
    { status: "success", code: "ready" },
  );
});

test("отказ платформы переводится словами в ОБОИХ путях вызова и на ОБОИХ языках", async () => {
  // Копий обработки отказов было две; расходясь, витрина показала
  // покупательнице сырой ответ ядра (замер 23.08.2026). Контракт держит
  // единственность: одна функция, оба пути зовут её, сырого текста нет.
  const источник = template.match(
    /function отказПлатформы\(статус, сырое, роль\)\{([\s\S]*?)\n  \}/);
  assert.ok(источник, "функция отказов обязана быть одна и с этим именем");
  assert.equal((template.match(/function отказПлатформы/g) || []).length, 1,
    "вторая копия обработки отказов запрещена");
  // Витринный путь принимает роль от вызывающего (кнопка подключения передаёт
  // свою), поэтому допустимо «роль || 'витрина'» — умолчание остаётся буквальным.
  const зовы = template.match(/отказПлатформы\(r\.status, raw, (роль \|\| )?'(установщик|витрина)'\)/g) || [];
  assert.equal(зовы.length, 2, "оба пути вызова обязаны звать общую функцию");
  assert.ok(!template.includes("'ОС ответила '"),
    "сырой ответ платформы человеку не показывается");

  // Текст отказов живёт в store_app/shell.json на двух языках (H117), поэтому
  // функция собирается с настоящим помощником т() и проверяется в двух языках.
  // Прежняя редакция проверяла только русский: английский отказ мог быть пустым,
  // и покупатель увидел бы пустое место вместо причины.
  const строки = JSON.parse(
    await readFile(new URL("./shell.json", import.meta.url), "utf8")).строки;
  const собрать = (язык) => new Function("т", `${источник[0]}; return отказПлатформы;`)(
    (ключ) => (строки[ключ] || {})[язык] || "");

  const недоступно = JSON.stringify({detail:
    "core /api/expert/run failed: HTTP 500: {'status': 'error', 'message': " +
    "'Target 00000000-0000-0000-0000-000000000000 is unavailable'}"});
  // Кнопка подключения новее старой установки: «не найден» ведёт в магазин.
  const нетЭксперта = JSON.stringify({detail: "core /api/expert/run failed: Expert not found"});
  assert.match(собрать('ru')(502, нетЭксперта, 'подключение'), /добавь заново из магазина/);
  assert.match(собрать('en')(502, нетЭксперта, 'подключение'), /add it again from the store/);
  const ждём = {ru: /Extella на этом компьютере не отвечает/,
                en: /Extella on this computer is not responding/};
  const шаг = {ru: /повтори/i, en: /try again/i};

  for (const язык of ["ru", "en"]) {
    const отказ = собрать(язык);
    for (const роль of ["установщик", "витрина"]) {
      const слова = отказ(502, недоступно, роль);
      assert.match(слова, ждём[язык],
        `${язык}/${роль}: «устройство недоступно» обязано переводиться`);
      assert.ok(!/HTTP 500|'status'|Target /.test(слова),
        `${язык}/${роль}: сырой ответ платформы не показывается`);
    }
    // Незнакомая причина тоже говорит словами и даёт следующий шаг.
    const чужое = отказ(500, JSON.stringify({detail: "kaboom {'x': 1}"}), "витрина");
    assert.ok(!чужое.includes("kaboom"), `${язык}: незнакомая деталь не идёт в лицо`);
    assert.match(чужое, шаг[язык], `${язык}: у отказа обязан быть следующий шаг`);
    // Пустой отказ хуже сырого: человек не понимает, что произошло.
    for (const код of [403, 401, 429, 500, 418]) {
      assert.ok(отказ(код, "{}", "витрина").trim().length > 20,
        `${язык}: отказ ${код} не должен быть пустым`);
    }
  }
});

test("промпт живёт в одном месте, и кнопка берёт его оттуда", async () => {
  // Раньше промпт лежал ДВАЖДЫ: массивом ПРОМПТ_АГЕНТУ в шаблоне и разделом в
  // content.json. Копии разошлись дважды — 26.08.2026 (H81) и 24.09.2026 (H110):
  // во второй раз кнопка отдавала неверный текст про ключ, а проверки были
  // зелёными. Теперь источник один, и договор охраняет именно это.
  const содержимое = JSON.parse(
    await readFile(new URL("./content.json", import.meta.url), "utf8"));
  const раздел = (содержимое["разделы"] || []).find(
    (р) => р["роль"] === "промпт-агенту");
  assert.ok(раздел, "раздел с ролью «промпт-агенту» обязан существовать");

  assert.equal(template.includes("var ПРОМПТ_АГЕНТУ"), false,
    "второй копии промпта в шаблоне быть не должно");
  assert.match(template, /промпт_агенту\(текущее\)/,
    "кнопка обязана читать промпт из содержимого");
  assert.match(template, /роль[^\n]*промпт-агенту/,
    "раздел находится по роли, а не по заголовку: заголовок переводится");
  // Пустой промпт — отказ словами, а не молча скопированная пустота. Текст отказа
  // переехал в store_app/shell.json: оболочка двуязычна (H117), поэтому договор
  // проверяет не русскую строку в шаблоне, а что отказ есть на ОБОИХ языках и что
  // шаблон его зовёт.
  const оболочка = JSON.parse(
    await readFile(new URL("./shell.json", import.meta.url), "utf8")).строки;
  assert.match(template, /т\('промпт\.нет'\)/,
    "у кнопки обязан быть видимый отказ, когда промпта нет");
  for (const язык of ["ru", "en"]) {
    assert.ok((оболочка["промпт.нет"] || {})[язык],
      `отказ «промпта нет» обязан быть на языке ${язык}`);
  }

  for (const [где, текст] of [["русский", раздел["тело"]], ["английский", раздел["тело_en"]]]) {
    assert.ok(!/Токен я дам сам|пришлёт строку тебе|Сгенерируй мне API-токен/.test(текст),
      `${где}: просить ключ у человека нельзя`);
    assert.match(текст, /не создавай своих|do not create tokens of your own/,
      `${где}: запрет заводить свои токены обязан остаться`);
    assert.match(текст, /connect_mcp\.py/,
      `${где}: обязана быть команда подключения, а не поиск ключа руками`);
    assert.match(текст, /AGENT_START\.md/, `${где}: назван вход для агента`);
    assert.match(текст, /raw\.githubusercontent\.com/,
      `${где}: ссылки сырые — страница GitHub не читается целиком`);
    assert.match(текст, /api\.html/,
      `${где}: сказано, что публичная справка не источник правды`);
    assert.equal(/START_HERE/.test(текст), false, `${где}: устаревший вход не упоминается`);
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

test("page rejects Python repr and an unexpected result shape, in both languages", () => {
  // Номер правила H17 в тексте отказа language-independent и обязан остаться в
  // обоих языках: по нему человек находит разбор поломки.
  const ждём = {ru: /не той формой/, en: /shape/i};
  for (const язык of ["ru", "en"]) {
    const parse = parser(язык);
    assert.throws(() => parse({ result: { result: "{'status': 'success'}" } }), /H17/,
      `${язык}: отказ обязан назвать H17`);
    assert.throws(() => parse({ result: { result: JSON.stringify({ ok: true }) } }),
      ждём[язык], `${язык}: отказ про чужую форму обязан быть на этом языке`);
  }
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
  // Конец ищется ПОСЛЕ начала главной кнопки: перед ней в ряду стоит кнопка
  // подключения редактора, и первый </button> в блоке принадлежит ей.
  const начало = действия.indexOf('class="btn main"');
  const главная = действия.slice(начало, действия.indexOf('</button>', начало));
  assert.ok(главная.includes('промпт'), 'главная кнопка — промпт, а не копия текста');

  const содержимое = JSON.parse(
    await readFile(new URL('./content.json', import.meta.url), 'utf8'));
  const раздел = (содержимое['разделы'] || []).find((р) => р['роль'] === 'промпт-агенту');
  const промпт = раздел['тело'];
  assert.ok(промпт.includes('extella-agent-standards'), 'адрес источника есть');
  assert.ok(промпт.includes('Не копируй правила к себе'), 'запрет копии повторён ассистенту');
  // Промпт короткий: человек видит, что это не простыня. Меряем знаками, а не
  // строками — текст теперь абзацами, строк в нём нет.
  const код = промпт.slice(промпт.indexOf('<code>') + 6, промпт.indexOf('</code>'));
  assert.ok(код.length <= 2600, `промпт должен быть коротким, а в нём ${код.length} знаков`);
  // Копия всего текста остаётся, но второстепенной и честно названной снимком.
  // Подписи живут в shell.json (H117), поэтому сверяем таблицу на двух языках.
  const оболочка = JSON.parse(
    await readFile(new URL('./shell.json', import.meta.url), 'utf8')).строки;
  for (const ключ of ['всё.кнопка', 'всё.готово']) {
    assert.ok((оболочка[ключ] || {}).ru, `${ключ}: нет русского текста`);
    assert.ok((оболочка[ключ] || {}).en, `${ключ}: нет английского перевода`);
  }
  assert.match(оболочка['всё.готово'].ru, /снимок/, 'копия честно названа снимком');
  assert.match(оболочка['всё.готово'].en, /snapshot/i, 'the English copy says snapshot too');
});

test("подстановка в строках оболочки работает с кириллическими именами", async () => {
  // Первая редакция тф() брала имя метки как \w — а \w в JavaScript это
  // [A-Za-z0-9_], кириллицы в нём нет. Метки {сек}, {всего}, {гб} не подставлялись
  // вовсе: в исходе оставались фигурные скобки, и ни одной ошибки в консоли.
  // Подставилась только латинская {n} (замер 27.09.2026).
  const источник = template.match(/function тф\(ключ, значения\)\{[\s\S]*?\n  \}/);
  assert.ok(источник, "форматтер строк обязан быть и называться тф");
  const строки = JSON.parse(
    await readFile(new URL("./shell.json", import.meta.url), "utf8")).строки;

  for (const язык of ["ru", "en"]) {
    const тф = new Function("т", `${источник[0]}; return тф;`)(
      (ключ) => (строки[ключ] || {})[язык] || "");
    // Все метки во всех строках таблицы обязаны подставляться на обоих языках.
    for (const [ключ, з] of Object.entries(строки)) {
      const метки = [...String(з[язык] || "").matchAll(/\{([^}]+)\}/g)].map((м) => м[1]);
      if (!метки.length) continue;
      const значения = {};
      for (const м of метки) значения[м] = "42";
      const вышло = тф(ключ, значения);
      assert.ok(!/[{}]/.test(вышло),
        `${язык}/${ключ}: метка не подставилась — «${вышло}»`);
    }
    // Явная проба на кириллицу: она и была дефектом.
    assert.equal(тф("дп.сек", {сек: "1.4"}).includes("1.4"), true,
      `${язык}: кириллическое имя метки обязано подставляться`);
    // Неизвестное имя остаётся меткой, а не превращается в пустоту.
    const источник2 = new Function("т", `${источник[0]}; return тф;`)(() => "{чего_нет}");
    assert.match(источник2("любой", {}), /\{чего_нет\}/,
      "неизвестная метка остаётся видимой, а не съедается");
  }
});

test("скрипт собранной страницы разбирается: битый JS не проходит молча", async () => {
  // Замена строк по якорю «до ближайшей ;» однажды оставила висячий обрывок
  // выражения — `показать(тф('уст.сверяю', {…},\n ' из ' + итог.total + '…');`.
  // Страница собиралась, гейты были зелёными, а скрипт не разбирался вовсе:
  // в окне не работала бы ни одна кнопка (замер 28.09.2026). Разбор собранной
  // страницы — самая дешёвая проверка из возможных, и её не было.
  const собрано = await readFile(new URL("./index.html", import.meta.url), "utf8");
  const скрипты = [...собрано.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  assert.ok(скрипты.length >= 1, "в собранной странице обязан быть скрипт");
  for (const [, код] of скрипты) {
    assert.doesNotThrow(() => new Function(код),
      "скрипт собранной страницы обязан разбираться");
  }
});

test("каждая запись «что нового» показывает текст, а не только номер версии", async () => {
  // Рисовальщик читал только поле «строки». У трёх новейших записей текст лежит
  // в «текст», у трёх — в «пункты»: под номером версии выводился ПУСТОЙ список.
  // Номер видно, изменения нет — панель выглядела рабочей и молчала (28.09.2026).
  const содержимое = JSON.parse(
    await readFile(new URL("./content.json", import.meta.url), "utf8"));
  const записи = содержимое["что_нового"] || [];
  assert.ok(записи.length, "список изменений обязан быть непустым");
  for (const в of записи) {
    const есть = (в["строки"] && в["строки"].length) ||
                 (в["пункты"] && в["пункты"].length) ||
                 (в["текст"] && String(в["текст"]).trim());
    assert.ok(есть, `запись ${в["версия"]}: нет ни строк, ни пунктов, ни текста`);
  }
  // Рисовальщик обязан знать все три формы, иначе запись покажется пустой.
  for (const поле of ["строки", "пункты", "текст"]) {
    assert.ok(template.includes(`поле(в, "${поле}")`),
      `рисовальщик новостей обязан читать поле «${поле}»`);
  }
});

test("умолчание — английский, а выбор человека сильнее умолчания", async () => {
  // Решение 27.09.2026: английский по умолчанию, переключатель на русский.
  // Умолчание переключается ТОЛЬКО когда оболочка переведена целиком (H117),
  // иначе англичанин получает английские разделы внутри русского окна.
  const выбор = template.match(/var ЯЗЫК = \(function\(\)\{[\s\S]*?\}\)\(\);/);
  assert.ok(выбор, "выбор языка обязан быть в одном месте");
  const язык = (сохранено) => new Function("localStorage", `${выбор[0]}; return ЯЗЫК;`)(
    {getItem: () => сохранено});
  assert.equal(язык(null), "en", "без выбора человека язык английский");
  assert.equal(язык("ru"), "ru", "выбранный русский сохраняется");
  assert.equal(язык("en"), "en", "выбранный английский сохраняется");
  assert.equal(язык("клингонский"), "en", "чужое значение не ломает страницу");

  // Оболочка обязана быть переведена целиком, иначе умолчание врёт.
  const строки = JSON.parse(
    await readFile(new URL("./shell.json", import.meta.url), "utf8")).строки;
  const без = Object.entries(строки).filter(([, з]) => !String(з.en || "").trim());
  assert.deepEqual(без.map(([к]) => к), [],
    "английское умолчание требует английского у КАЖДОЙ строки оболочки");

  // И у каждого раздела руководства, и у каждой записи «что нового».
  const содержимое = JSON.parse(
    await readFile(new URL("./content.json", import.meta.url), "utf8"));
  for (const р of содержимое["разделы"] || []) {
    assert.ok(String(р["тело_en"] || "").trim(), `раздел ${р["номер"]}: нет английского`);
  }
  for (const в of содержимое["что_нового"] || []) {
    const есть = в["текст_en"] || (в["строки_en"] || []).length || (в["пункты_en"] || []).length;
    assert.ok(есть, `запись ${в["версия"]}: нет английского`);
  }
});

test("имя продукта одно во всех трёх местах, на каждом языке", async () => {
  // Имя живёт в трёх файлах: карточка магазина (listing.json), заголовок окна
  // (shell.json) и шапка страницы (content.json). Смена английского имени
  // 28.09.2026 показала это: два места я поправил, третье нашёл только поиском —
  // на экране и в карточке были бы разные имена (H112: копии расходятся молча).
  const карточка = JSON.parse(
    await readFile(new URL("./listing.json", import.meta.url), "utf8"));
  const оболочка = JSON.parse(
    await readFile(new URL("./shell.json", import.meta.url), "utf8")).строки;
  const содержимое = JSON.parse(
    await readFile(new URL("./content.json", import.meta.url), "utf8"));

  const окно = оболочка["окно.заголовок"];
  const шапка = содержимое["шапка"];
  assert.equal(окно.ru, шапка["заголовок"], "русское имя окна и шапки обязано совпадать");
  assert.equal(окно.en, шапка["заголовок_en"], "английское имя окна и шапки обязано совпадать");

  const предложено = (карточка["карточка_предлагается"] || {})["имя"];
  if (предложено) {
    assert.equal(предложено, окно.en,
      "предложенное имя карточки обязано совпадать с английским именем на экране");
  }
});

test("проверка выкладки узнаёт заголовок с атрибутами", async () => {
  // Проверка перед отправкой искала «<title>Разработка на Extella</title>» точной
  // строкой. У тега появился атрибут ключа перевода — и выкладка отказала на
  // ИСПРАВНОЙ странице со словами «это не тот файл» (28.09.2026). Проверка нужная:
  // она не пускает битый файл покупателям. Ломким был способ сравнения.
  const выкладка = await readFile(new URL("./update.py", import.meta.url), "utf8");
  assert.ok(!выкладка.includes('маркер = "<title>'),
    "заголовок нельзя искать точной строкой: атрибут тега ломает сравнение");
  assert.match(выкладка, /<title\[\^>\]\*>/,
    "заголовок ищется регуляркой, терпимой к атрибутам");

  // И собранная страница обязана этой проверке удовлетворять.
  const собрано = await readFile(new URL("./index.html", import.meta.url), "utf8");
  const з = собрано.match(/<title[^>]*>\s*([^<]+?)\s*<\/title>/);
  assert.ok(з, "у собранной страницы обязан быть заголовок");
  assert.match(з[1], /Extella/, "заголовок обязан называть Extella");
});

test("переключатель языка виден на главном экране, а не спрятан в «Ещё»", () => {
  // Замечание владельца 28.09.2026 на Windows 11: английское окно открылось, а
  // перейти на русский было нечем — кнопка жила на четвёртом экране «Ещё».
  const меню = template.slice(template.indexOf('<nav class="меню"'),
                              template.indexOf("</nav>", template.indexOf('<nav class="меню"')));
  assert.match(меню, /id="язык"/, "кнопка языка обязана стоять в строке вкладок");
  const ещё = template.slice(template.indexOf('data-экран="ещё">'),
                             template.indexOf("<footer>"));
  assert.ok(!ещё.includes('id="язык"'), "второй кнопки языка в «Ещё» быть не должно");
  // Класс свой: код экранов разбирает клик через closest('.вкладка') и принял бы
  // кнопку языка с классом вкладки за экран.
  const кнопка = меню.match(/<button[^>]*id="язык"[^>]*>/)[0];
  assert.ok(!/class="[^"]*вкладка/.test(кнопка), "у кнопки языка не класс вкладки");
});

test('кнопка подключения редактора: на главном экране, без адреса, ключа в окне нет', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  // Экран, а не вкладка меню: у вкладки тот же атрибут data-экран.
  const экран = '<div class="экран" data-экран="начало">';
  const начало = page.slice(page.indexOf(экран), page.indexOf('<div class="экран" data-экран="проба">'));
  assert.ok(начало.includes('id="подключить"'), 'кнопка стоит на экране «Начало», рядом с промптом');

  const обработчик = page.slice(page.indexOf("function подключениеРедактора("),
                                page.indexOf("getElementById('всё').onclick"));
  assert.ok(обработчик.includes("зовСценария('dev_connect_assistant', {app_token: APP_TOKEN}, 'подключение', адрес)"),
            'эксперту уходит только пропуск окна');
  // Главная кнопка зовёт без адреса; Device ID — только запасной путь H106.
  assert.ok(обработчик.includes("подключениеРедактора(this, '');"), 'главная кнопка — без адреса');
  assert.ok(обработчик.includes("if (e && e.не_туда && !адрес)"), 'поле Device ID открывается только при «не туда»');
  // Старая установка не знает нового эксперта: совет обязан вести в магазин, а не
  // к перезагрузке окна — она агента не меняет (Windows, 29.09.2026).
  assert.ok(page.includes("if (роль === 'подключение') return т('отказ.нет_подключения');"),
            'отказ «эксперт не найден» у кнопки подключения ведёт к переустановке');
  // Адрес попадает в targets только из поля запасного пути (H106).
  const зов = page.slice(page.indexOf('function зовСценария('), page.indexOf('(function деньПервый'));
  assert.ok(зов.includes('if (адрес) тело.targets = [адрес];'), 'targets — только когда адрес дан');
  // Ключ выпускает эксперт на компьютере; странице его неоткуда взять и нечего показать.
  assert.ok(!/\{\{token\}\}|\.token\b/.test(обработчик), 'окно не держит и не показывает ключ');
  assert.ok(обработчик.includes('кнопка.disabled = true') && обработчик.includes('кнопка.disabled = false'),
            'кнопка гаснет на время вызова и загорается в любом исходе');

  const эксперт = await readFile(new URL('../experts/dev_connect_assistant.py', import.meta.url), 'utf8');
  const коды = [...эксперт.matchAll(/код="([^"]+)"/g)].map((м) => м[1]);
  const оболочка = JSON.parse(await readFile(new URL('./shell.json', import.meta.url), 'utf8'))['строки'];
  for (const к of коды) {
    assert.ok(обработчик.includes(`'подкл.код.${к}'`), `исход ${к} есть в таблице окна`);
    assert.ok(оболочка[`подкл.код.${к}`]?.en, `исход ${к} переведён`);
  }
});

test('приёмка выпуска ищет кнопку, которая есть в странице', async () => {
  const page = await readFile(new URL('./page.template.html', import.meta.url), 'utf8');
  const выпуск = await readFile(new URL('./product/deploy_prerelease_claude.py', import.meta.url), 'utf8');
  // Приёмка ждала снятую кнопку claude-connect и роняла исправный выпуск 3.8.0.
  const ids = [...выпуск.matchAll(/'id="([^"]+)"' not in page/g)].map((м) => м[1]);
  assert.ok(ids.length > 0, 'приёмка проверяет хотя бы одну кнопку');
  for (const id of ids) {
    assert.ok(page.includes(`id="${id}"`), `приёмка ждёт id="${id}", а в шаблоне его нет`);
  }
});
