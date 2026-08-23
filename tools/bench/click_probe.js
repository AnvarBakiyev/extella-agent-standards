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
  var ЖДАТЬ_МОНТАЖ = 20000;   // сколько ждём появления интерфейса
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

  function отчитаться(отчёт) {
    try { window.__проклик = отчёт; } catch (e) { /* карман для отладки */ }
    try {
      fetch('/probe-report', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(отчёт)
      });
    } catch (e) { /* отчёт не ушёл — проба это увидит по его отсутствию */ }
  }

  function монтаж() {
    var до = Date.now() + ЖДАТЬ_МОНТАЖ;
    return new Promise(function (готово) {
      (function тик() {
        if (крючки().length > 0 || кнопки().length > 0 || Date.now() > до) return готово();
        setTimeout(тик, 400);
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
