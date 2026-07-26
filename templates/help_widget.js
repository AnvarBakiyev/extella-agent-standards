// Готовое окно «? Как это работает» — образец из продукта Extella (Конструктор процессов).
// Скопируй файл в свой продукт, заполни HELP на ДВУХ языках (правило §3.26) и поставь на экране
// кнопку: <button onclick="openHelp('мой_экран')">? Как это работает</button>
// Плюс вызов helpFirstTime('мой_экран') при открытии экрана — первый раз человек увидит сам.
//
// Требуется: функция el(id) → document.getElementById, и в разметке контейнер:
//   <div id="xtl_help" style="display:none;position:fixed;inset:0;z-index:9996;background:rgba(12,14,18,.55);overflow:auto;padding:34px 18px">
//     <div style="max-width:720px;margin:0 auto;background:#f5f3ee;border-radius:16px;padding:26px 28px 22px">
//       <div id="xtl_help_body"></div>
//       <button onclick="closeHelp()">Понятно / Got it</button>
//     </div>
//   </div>

var LANG = (typeof WLANG !== 'undefined' && WLANG === 'en') ? 'en' : 'ru';

// ОБЯЗАТЕЛЬНАЯ структура записи. nope (границы) — не опционален: возможность без честно
// названного предела к выпуску не допускается (проверялка паспорта это тоже требует).
var HELP = {
  my_surface: {
    ru: {
      icon: '\u2699\uFE0F', title: 'Как работает <моя возможность>',
      sub: 'Одна фраза: какую боль снимает',
      steps: ['Человек делает …', 'Система делает …', 'На выходе …'],
      sure: ['Что реально проверено и можно показать'],
      nope: ['ЧЕГО НЕ ОБЕЩАЕМ — минимум одна честная граница'],
      who: { title: 'Кто может раскрыть или откатить', items: ['…'] },   // можно опустить
      extra: 'Ссылка на подробный документ для службы безопасности — при необходимости'
    },
    en: {
      icon: '\u2699\uFE0F', title: 'How <my capability> works',
      sub: 'One line: which pain it removes',
      steps: ['The person does …', 'The system does …', 'The result is …'],
      sure: ['What is actually verified and can be demonstrated'],
      nope: ['WHAT WE DO NOT PROMISE — at least one honest limit'],
      who: { title: 'Who can reveal the data or roll the change back', items: ['…'] },
      extra: 'Link to the detailed document for the security team, if needed'
    }
  }
};

var T = {
  ru: { how: 'Как это работает', sure: 'Что гарантировано', nope: 'Чего мы НЕ обещаем — важно знать', ok: 'Понятно' },
  en: { how: 'How it works', sure: 'What is guaranteed', nope: 'What we do NOT promise — important', ok: 'Got it' }
};

function _helpCard(color){
  return '<div class="card" style="' + (color ? 'border-left:3px solid ' + color + ';' : '') + 'margin-bottom:12px">';
}
function openHelp(key){
  var d = (HELP[key]||{})[LANG], box = el('xtl_help_body'), wrap = el('xtl_help');
  if(!d || !box || !wrap) return;
  var h = '<div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:14px">' +
      '<div style="font-size:26px;line-height:1">' + d.icon + '</div><div>' +
      '<div style="font:700 19px var(--sans);color:var(--ink,#0a0a0a)">' + d.title + '</div>' +
      '<div style="font-size:12.5px;color:var(--silver,#8c8c8c)">' + d.sub + '</div></div>' +
      '<button class="btn ghost sm" style="margin-left:auto" onclick="closeHelp()">✕</button></div>';
  h += _helpCard('') + '<div style="font-weight:700;font-size:13.5px;margin-bottom:8px">Как это работает</div>' +
       '<div style="font-size:12.5px;line-height:1.65;color:var(--ink,#0a0a0a)">' +
       d.steps.map(function(s,i){ return '<b>' + (i+1) + '.</b> ' + s; }).join('<br>') + '</div></div>';
  h += _helpCard('#2f6b66') + '<div style="font-weight:700;font-size:13.5px;margin-bottom:8px">Что гарантировано</div>' +
       '<div style="font-size:12.5px;line-height:1.7;color:var(--ink,#0a0a0a)">• ' + d.sure.join('<br>• ') + '</div></div>';
  h += _helpCard('#c57e33') + '<div style="font-weight:700;font-size:13.5px;margin-bottom:8px">Чего мы НЕ обещаем — важно знать</div>' +
       '<div style="font-size:12.5px;line-height:1.7;color:var(--ink,#0a0a0a)">• ' + d.nope.join('<br>• ') + '</div></div>';
  if(d.who) h += _helpCard('') + '<div style="font-weight:700;font-size:13.5px;margin-bottom:8px">' + d.who.title + '</div>' +
       '<div style="font-size:12.5px;line-height:1.7;color:var(--ink,#0a0a0a)">• ' + d.who.items.join('<br>• ') + '</div></div>';
  if(d.extra) h += '<div style="font-size:11.5px;color:var(--silver,#8c8c8c);line-height:1.6;margin-bottom:14px">' + d.extra + '</div>';
  box.innerHTML = h; wrap.style.display = 'block';
}
function closeHelp(){ var h=el('xtl_help'); if(h) h.style.display='none'; }
function helpFirstTime(key){
  try{
    if(localStorage.getItem('xtl_help_seen_'+key)==='1') return;
    localStorage.setItem('xtl_help_seen_'+key,'1');
  }catch(e){}   // приватный режим/запрет хранилища — показываем, но не падаем
  openHelp(key);
}
