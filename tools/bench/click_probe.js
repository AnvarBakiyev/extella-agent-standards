/* Клик-робот приёмки: прокликивает панель ВНУТРИ живой страницы на настоящем
   origin ОС и отчитывается на /probe-report (тот же origin — CORS не мешает).
   Внедряется прокси-пробой в HTML приложения, поэтому не нужен ни playwright,
   ни CDP: работает тем же безголовым Chrome, что уже стоит на стенде.

   ПРЕДОХРАНИТЕЛЬ. Робот жмёт ТОЛЬКО элементы с явными крючками data-testid и
   никогда — кнопки с опасными словами (удалить/провести/отправить/оплатить...).
   Приложение без крючков не прокликивается: это честный вердикт «нечем», а не
   попытка угадать кнопки на живых данных покупателя.

   Панели ОС рисуют UI в Shadow DOM, поэтому обход идёт сквозь теневые корни. */
(function () {
  var ТАКТ = 300;             // шаг ожидания
  var ТАКТОВ_МОНТАЖА = 150;   // ждём появления интерфейса тактами, не по часам
  var ПОСЛЕ_КЛИКА = 1200;     // сколько ждём отклика после нажатия
  var МАКС_КЛИКОВ = 6;

  var ОПАСНЫЕ = ['удал', 'удаление', 'delete', 'remove', 'провести', 'провед',
                 'отправ', 'send', 'оплат', 'pay', 'куп', 'buy', 'списать',
                 'очист', 'сброс', 'publish', 'опублик', 'выложить'];

  function всеУзлы(корень, накопитель) {
    накопитель = накопитель || [];
    var обход = корень.querySelectorAll ? корень.querySelectorAll('*') : [];
    for (var i = 0; i < обход.length; i++) {
      var у = обход[i];
      накопитель.push(у);
      if (у.shadowRoot) всеУзлы(у.shadowRoot, накопитель);   // сквозь тень
    }
    return накопитель;
  }

  function крючки() {
    return всеУзлы(document).filter(function (у) {
      return у.getAttribute && у.getAttribute('data-testid');
    });
  }

  function кнопки() {
    return всеУзлы(document).filter(function (у) {
      var т = (у.tagName || '').toLowerCase();
      return т === 'button' || (т === 'a' && у.getAttribute('href')) ||
             у.getAttribute && у.getAttribute('role') === 'button';
    });
  }

  function видно(у) {
    if (!у.getBoundingClientRect) return false;
    var r = у.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function опасно(у) {
    var т = ((у.textContent || '') + ' ' + (у.getAttribute('data-testid') || '') +
             ' ' + (у.getAttribute('aria-label') || '')).toLowerCase();
    for (var i = 0; i < ОПАСНЫЕ.length; i++) if (т.indexOf(ОПАСНЫЕ[i]) > -1) return true;
    return false;
  }

  function слепок() {
    // Текст всего живого интерфейса, включая теневые корни — чтобы увидеть отклик.
    return всеУзлы(document).map(function (у) {
      return у.shadowRoot ? '' : (у.textContent || '').slice(0, 40);
    }).join('|').length + ':' + (document.body ? document.body.innerHTML.length : 0);
  }

  function ждать(мс) { return new Promise(function (r) { setTimeout(r, мс); }); }

  function послать(отчёт) {
    try {
      fetch('/probe-report', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(отчёт)
      });
    } catch (e) { /* отчёт не ушёл — проба это увидит по его отсутствию */ }
  }

  function отчитаться(отчёт) {
    try { window.__проклик = отчёт; } catch (e) { /* карман для отладки */ }
    // Панель живёт во ВЛОЖЕННОЙ рамке песочницы ОС, у неё пустой origin: fetch
    // наружу оттуда не проходит (та же грабля «Origin: null → Failed to fetch»).
    // Поэтому изнутри отдаём отчёт наверх сообщением — как это делает и сама
    // платформа, — а верхний кадр уже передаёт его пробе.
    try {
      if (window.parent !== window) {
        window.parent.postMessage({ type: 'probe_report_ext', отчёт: отчёт }, '*');
      }
    } catch (e) { /* наверх не доложить — останется карман и fetch ниже */ }
    послать(отчёт);
  }

  // Верхний кадр: принимаем отчёт вложенной панели и передаём его пробе.
  try {
    if (window.parent === window) {
      window.addEventListener('message', function (e) {
        var d = e.data || {};
        if (d && d.type === 'probe_report_ext' && d.отчёт) послать(d.отчёт);
      });
    }
  } catch (e) { /* нет доступа к сообщениям — не беда */ }

  function монтаж() {
    // Ждём ТАКТАМИ, а не по часам: в безголовом браузере виртуальное время
    // сжато, и Date.now() перескакивает отведённый срок мгновенно — робот
    // отчитывался «0 кнопок» ещё до отрисовки панели (замер 23.08 на Агенте 1С).
    // Такт отдаёт управление циклу событий, давая догрузиться сети и мониться UI.
    var осталось = ТАКТОВ_МОНТАЖА;
    return new Promise(function (готово) {
      (function тик() {
        if (крючки().length > 0 || кнопки().length > 0 || --осталось <= 0) return готово();
        setTimeout(тик, ТАКТ);
      })();
    });
  }

  monkey();

  async function monkey() {
    var отчёт = { стадия: 'старт', крючков: 0, кнопок: 0, клики: [], пропущено: [] };
    try {
      await монтаж();
      var к = крючки().filter(видно);
      var б = кнопки().filter(видно);
      отчёт.крючков = к.length;
      отчёт.кнопок = б.length;
      отчёт.стадия = 'смонтировано';

      // Дубли крючков — молчаливая ложь приёмки: робот жмёт первый попавшийся
      // элемент и отчитывается, что кнопка нажата, тогда как соседние с тем же
      // именем не проверялись ни разу. Поймано на живой панели 24.08: три
      // кнопки перехода к реестру несли один крючок. Считаем и называем.
      var счёт = {};
      к.forEach(function (у) {
        var имя = у.getAttribute('data-testid');
        счёт[имя] = (счёт[имя] || 0) + 1;
      });
      отчёт.дубли = Object.keys(счёт).filter(function (имя) { return счёт[имя] > 1; })
        .map(function (имя) { return имя + '×' + счёт[имя]; });

      // Крючок, собранный из подписи с числом, завтра сменится вместе с числом.
      отчёт.шаткие = к.map(function (у) { return у.getAttribute('data-testid'); })
        .filter(function (имя) { return /\d/.test(имя); });

      if (!к.length) {
        отчёт.стадия = 'нечем прокликать';
        отчёт.почему = 'в панели нет data-testid — машине не за что взяться';
        return отчитаться(отчёт);
      }

      // Сперва заполняем поля: иначе нажатие уходит в проверку «пусто» и
      // настоящий путь приложения не проверяется (замер 23.08 на каркасе-рецепте:
      // клик по пустой форме дал только «Сначала опиши задачу»).
      отчёт.заполнено = 0;
      к.forEach(function (у) {
        var т = (у.tagName || '').toLowerCase();
        var тип = (у.getAttribute('type') || 'text').toLowerCase();
        if (т !== 'input' && т !== 'textarea') return;
        if (['button', 'submit', 'checkbox', 'radio', 'file'].indexOf(тип) > -1) return;
        try {
          у.focus();
          у.value = (тип === 'number') ? '1' : 'проверка приёмки';
          у.dispatchEvent(new Event('input', { bubbles: true }));
          у.dispatchEvent(new Event('change', { bubbles: true }));
          отчёт.заполнено++;
        } catch (e) { /* поле не принимает — не беда */ }
      });

      var жать = к.filter(function (у) {
        var т = (у.tagName || '').toLowerCase();
        var кликабельно = т === 'button' || т === 'a' ||
                          (у.getAttribute && у.getAttribute('role') === 'button');
        if (!кликабельно) return false;
        if (опасно(у)) { отчёт.пропущено.push(у.getAttribute('data-testid')); return false; }
        return true;
      }).slice(0, МАКС_КЛИКОВ);

      for (var i = 0; i < жать.length; i++) {
        var у = жать[i];
        var имя = у.getAttribute('data-testid');
        var было = слепок();
        try { у.click(); } catch (e) { отчёт.клики.push({ id: имя, ошибка: String(e).slice(0, 80) }); continue; }
        await ждать(ПОСЛЕ_КЛИКА);
        отчёт.клики.push({ id: имя, откликнулось: слепок() !== было });
      }
      отчёт.стадия = 'прокликано';
    } catch (e) {
      отчёт.стадия = 'сорвалось';
      отчёт.ошибка = String(e).slice(0, 160);
    }
    отчитаться(отчёт);
  }
})();
