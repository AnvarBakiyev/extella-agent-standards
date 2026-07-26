// Рендер кабинета агента Extella — образец базовой технологии.
// Вход: объект от tools/build_agent_cabinet.py (schema extella.agent_cabinet.v1).
// Три вкладки: Паспорт · Как работает фактически · Эволюция. Двуязычно (правило §3.26).
// Кабинет НЕ пишется руками под каждого агента: данные приходят из паспорта агента.

var CAB_T = {
  ru: { tabs: ['Паспорт', 'Как работает фактически', 'Эволюция'],
        state: 'Agent Genome — геном агента', attention: 'Требует внимания',
        own: 'только этот агент', shared: 'Shared Gene — затронет класс',
        declared: 'Как должен работать (заявлено)', sources: 'Источники доказательств',
        limits: 'Чего кабинет НЕ показывает', cycle: 'Цикл изменения',
        guard: 'Защита от массовой поломки', version: 'Активная версия', owner: 'Владелец',
        est: 'оценка', limitsCol: 'Границы' },
  en: { tabs: ['Passport', 'How it actually works', 'Evolution'],
        state: 'Agent Genome', attention: 'Needs attention',
        own: 'this agent only', shared: 'Shared Gene — affects the class',
        declared: 'How it is supposed to work (declared)', sources: 'Evidence sources',
        limits: 'What this cabinet does NOT show', cycle: 'Change cycle',
        guard: 'Protection against mass breakage', version: 'Active version', owner: 'Owner',
        est: 'estimate', limitsCol: 'Limits' }
};

function cabLang(){ return (typeof WLANG !== 'undefined' && WLANG === 'en') ? 'en' : 'ru'; }

function renderCabinet(cab, hostId, tab){
  var host = document.getElementById(hostId); if(!host || !cab) return;
  var L = cabLang(), T = CAB_T[L], p = cab.passport, i = p.identity;
  tab = tab || 'passport';
  var h = '<div style="display:flex;gap:8px;margin-bottom:14px">';
  ['passport','actual','evolution'].forEach(function(k, n){
    h += '<button class="btn ' + (tab===k?'gold':'ghost') + ' sm" onclick="renderCabinet(window._cab,\'' + hostId + '\',\'' + k + '\')">' + T.tabs[n] + '</button>';
  });
  h += '</div>';
  h += '<div style="font:700 18px var(--sans)">' + (i.name||'—') + '</div>' +
       '<div style="font-size:12.5px;color:var(--silver,#889);margin-bottom:12px">' +
       T.owner + ': ' + (i.owner||'—') + ' · ' + T.version + ': ' + (i.active_version||'—') +
       ' · ' + (i.model_profile||'—') + ' · ' + ((i.languages||[]).join(', ')||'—') + '</div>';

  if(tab === 'passport'){
    h += '<div class="card" style="margin-bottom:12px"><div style="font-weight:700;margin-bottom:8px">' + T.state + '</div><table style="width:100%;font-size:12px;border-collapse:collapse">';
    (p.genome||[]).forEach(function(s){
      h += '<tr style="border-top:1px solid var(--line,#e4decf)"><td style="padding:5px 4px"><b>' + s.capability + '</b> <span style="color:var(--silver)">v' + s.version + '</span></td>' +
           '<td style="padding:5px 4px">' + s.autonomy + '</td>' +
           '<td style="padding:5px 4px;color:' + (s.provenance==='global'?'#b8862f':'var(--silver)') + '">' + (s.provenance==='global'?T.shared:T.own) + '</td>' +
           '<td style="padding:5px 4px">' + s.side_effects + ' / ' + s.confirmation + '</td>' +
           '<td style="padding:5px 4px">' + T.limitsCol + ': ' + (s.limits||[]).length + '</td></tr>';
    });
    h += '</table></div>';
    var a = p.attention || {};
    h += '<div class="card" style="border-left:3px solid #b8862f"><div style="font-weight:700;margin-bottom:8px">' + T.attention + '</div><div style="font-size:12.5px;line-height:1.7">' +
         '• ' + T.shared + ': ' + ((a.shared_genes||[]).join(', ')||'—') + '<br>' +
         '• ' + (L==='en'?'outward or physical actions':'действия наружу или с техникой') + ': ' + ((a.external_or_physical||[]).join(', ')||'—') + '<br>' +
         '• ' + (L==='en'?'human required':'обязателен человек') + ': ' + ((a.human_required||[]).join(', ')||'—') + '</div></div>';
  }

  if(tab === 'actual'){
    var d = cab.declared_behaviour || {}, ac = cab.actual_behaviour || {};
    h += '<div class="card" style="margin-bottom:12px"><div style="font-weight:700;margin-bottom:8px">' + T.declared + '</div><div style="font-size:12.5px;line-height:1.7">' +
         (d.steps||[]).map(function(s,n){ return (n+1) + '. ' + s.capability + ' (' + s.autonomy + ', ' + s.side_effects + ')'; }).join('<br>') + '</div></div>';
    h += '<div class="card" style="margin-bottom:12px"><div style="font-weight:700;margin-bottom:8px">' + T.sources + '</div><div style="font-size:12.5px;line-height:1.7">• ' +
         (ac.evidence_sources||[]).map(function(s){ return s.what; }).join('<br>• ') + '</div></div>';
    h += '<div class="card" style="border-left:3px solid #b8862f"><div style="font-weight:700;margin-bottom:8px">' + T.limits + '</div><div style="font-size:12.5px;line-height:1.7">• ' +
         ((ac.limits||{})[L]||[]).join('<br>• ') + '</div></div>';
  }

  if(tab === 'evolution'){
    var e = cab.evolution || {}, g = e.shared_change_guard || {};
    h += '<div class="card" style="margin-bottom:12px"><div style="font-weight:700;margin-bottom:8px">' + T.cycle + '</div><div style="font-size:12.5px;line-height:1.7">' +
         (e.cycle||[]).map(function(s,n){ return '<b>' + (n+1) + '.</b> ' + s.what; }).join('<br>') + '</div></div>';
    var q = (L==='en' ? g.prompt_en : g.prompt_ru) || '';
    var ch = (L==='en' ? g.choices_en : g.choices_ru) || [];
    // N подставляет продукт из живых данных: сколько агентов реально используют механизм
    q = q.replace('{N}', String(g.affected_count != null ? g.affected_count : 'N'));
    h += '<div class="card" style="border-left:3px solid #b8862f"><div style="font-weight:700;margin-bottom:8px">' + T.guard + '</div>' +
         '<div style="font-size:13px;line-height:1.6;margin-bottom:10px">' + q + '</div>' +
         '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">' +
         ch.map(function(c,n){ return '<button class="btn ' + (n===0?'gold':'ghost') + ' sm" disabled title="' + (L==='en'?'wired by the product':'подключает продукт') + '">' + c + '</button>'; }).join('') +
         '</div><div style="font-size:12px;color:var(--silver,#889)">' + g.must_show +
         '<br><b>' + (L==='en'?'Shared Genes of this agent':'Shared Genes этого агента') + ':</b> ' + ((g.candidates||[]).join(', ')||'—') + '</div></div>';
  }
  window._cab = cab;
  host.innerHTML = h;
}
