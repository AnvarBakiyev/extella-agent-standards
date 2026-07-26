// Canonical «? Как это работает / How it works» widget for Extella Evolution.
// Fill HELP on BOTH languages and add:
//   <button type="button" onclick="openHelp('my_surface')">? Как это работает</button>
// Call helpFirstTime('my_surface') when the surface first opens.
//
// Requires el(id) -> document.getElementById and this container:
//   <div id="xtl_help" style="display:none;position:fixed;inset:0;z-index:9996;background:rgba(12,14,18,.55);overflow:auto;padding:34px 18px">
//     <div style="max-width:720px;margin:0 auto;background:#f4f1ea;border-radius:16px;padding:26px 28px 22px">
//       <div id="xtl_help_body"></div>
//     </div>
//   </div>

// nope (honest limits) is mandatory. Agent Passport checker enforces limits
// and help_surface for every capability.
var HELP = {
  my_surface: {
    ru: {
      icon: '\u2699\uFE0F', title: 'Как работает <моя возможность>',
      sub: 'Одна фраза: какую боль снимает',
      steps: ['Человек делает …', 'Система делает …', 'На выходе …'],
      sure: ['Что реально проверено и можно показать'],
      nope: ['ЧЕГО НЕ ОБЕЩАЕМ — минимум одна честная граница'],
      who: { title: 'Кто может раскрыть или откатить', items: ['…'] },
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

var HELP_T = {
  ru: {
    how: 'Как это работает', sure: 'Что гарантировано',
    nope: 'Чего мы НЕ обещаем — важно знать', ok: 'Понятно'
  },
  en: {
    how: 'How it works', sure: 'What is guaranteed',
    nope: 'What we do NOT promise — important', ok: 'Got it'
  }
};

function helpLang(){
  return (typeof WLANG !== 'undefined' && WLANG === 'en') ? 'en' : 'ru';
}

function helpEsc(value){
  return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
  });
}

function helpItems(values){
  return (Array.isArray(values) ? values : []).map(helpEsc);
}

function _helpCard(color){
  return '<div class="card" style="' +
    (color ? 'border-left:3px solid ' + color + ';' : '') +
    'margin-bottom:12px">';
}

function openHelp(key){
  var L = helpLang(), T = HELP_T[L];
  var d = (HELP[key] || {})[L], box = el('xtl_help_body'), wrap = el('xtl_help');
  if(!d || !box || !wrap) return;
  var steps = helpItems(d.steps), sure = helpItems(d.sure), nope = helpItems(d.nope);
  var h = '<div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:14px">' +
      '<div style="font-size:26px;line-height:1">' + helpEsc(d.icon) + '</div><div>' +
      '<div style="font:700 19px var(--sans);color:var(--ink,#0a0a0a)">' +
      helpEsc(d.title) + '</div><div style="font-size:12.5px;color:var(--silver,#889)">' +
      helpEsc(d.sub) + '</div></div><button type="button" data-help-close ' +
      'class="btn ghost sm" style="margin-left:auto" aria-label="' + helpEsc(T.ok) +
      '">✕</button></div>';
  h += _helpCard('') + '<div style="font-weight:700;font-size:13.5px;margin-bottom:8px">' +
       helpEsc(T.how) + '</div><div style="font-size:12.5px;line-height:1.65;color:var(--ink,#0a0a0a)">' +
       steps.map(function(s,i){ return '<b>' + (i+1) + '.</b> ' + s; }).join('<br>') + '</div></div>';
  h += _helpCard('#4b7f52') + '<div style="font-weight:700;font-size:13.5px;margin-bottom:8px">' +
       helpEsc(T.sure) + '</div><div style="font-size:12.5px;line-height:1.7;color:var(--ink,#0a0a0a)">• ' +
       sure.join('<br>• ') + '</div></div>';
  h += _helpCard('#b8862f') + '<div style="font-weight:700;font-size:13.5px;margin-bottom:8px">' +
       helpEsc(T.nope) + '</div><div style="font-size:12.5px;line-height:1.7;color:var(--ink,#0a0a0a)">• ' +
       nope.join('<br>• ') + '</div></div>';
  if(d.who){
    h += _helpCard('') + '<div style="font-weight:700;font-size:13.5px;margin-bottom:8px">' +
      helpEsc(d.who.title) + '</div><div style="font-size:12.5px;line-height:1.7;color:var(--ink,#0a0a0a)">• ' +
      helpItems(d.who.items).join('<br>• ') + '</div></div>';
  }
  if(d.extra){
    h += '<div style="font-size:11.5px;color:var(--silver,#889);line-height:1.6;margin-bottom:14px">' +
      helpEsc(d.extra) + '</div>';
  }
  h += '<button type="button" data-help-close class="btn gold">' + helpEsc(T.ok) + '</button>';
  box.innerHTML = h;
  Array.prototype.forEach.call(box.querySelectorAll('[data-help-close]'), function(button){
    button.addEventListener('click', closeHelp);
  });
  wrap.style.display = 'block';
}

function closeHelp(){
  var h = el('xtl_help'); if(h) h.style.display = 'none';
}

function helpFirstTime(key){
  try{
    if(localStorage.getItem('xtl_help_seen_' + key) === '1') return;
    localStorage.setItem('xtl_help_seen_' + key, '1');
  }catch(e){} // private mode/storage denial: show help without failing
  openHelp(key);
}
