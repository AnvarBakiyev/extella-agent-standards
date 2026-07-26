// Canonical Agent Cabinet renderer for Extella Evolution.
// Input: tools/build_agent_cabinet.py output (schema extella.agent_cabinet.v1.1).
// Three tabs: Agent Passport · Actual behaviour · Evolution Loop.
// Agent Cabinet is generated from Agent Passport; do not hand-write one per agent.

var CAB_T = {
  ru: {
    tabs: ['Agent Passport', 'Фактическое поведение', 'Evolution Loop'],
    state: 'Agent Genome — геном агента', attention: 'Требует внимания',
    own: 'только этот агент', shared: 'Shared Gene — затронет класс',
    declared: 'Как должен работать (заявлено)', sources: 'Источники доказательств',
    limits: 'Чего Agent Cabinet НЕ показывает', cycle: 'Evolution Loop — цикл управляемого изменения',
    create: 'Создать в Extella', createGuards: 'Правила создания (обязательны)', createNo: 'Здесь НЕ создаётся',
    guard: 'Защита от массовой поломки', version: 'Активная версия', owner: 'Владелец',
    agentId: 'Platform Agent ID', provider: 'Поставщик / модель', limitsCol: 'Границы', type: 'Тип',
    legacy: 'Legacy capability.global (не используется для точного N)',
    outward: 'действия наружу или с техникой', human: 'обязателен человек',
    sharedOfAgent: 'Shared Genes этого агента', wired: 'подключает продукт'
  },
  en: {
    tabs: ['Agent Passport', 'Actual behaviour', 'Evolution Loop'],
    state: 'Agent Genome', attention: 'Needs attention',
    own: 'this agent only', shared: 'Shared Gene — affects the class',
    declared: 'How it is supposed to work (declared)', sources: 'Evidence sources',
    limits: 'What Agent Cabinet does NOT show', cycle: 'Evolution Loop',
    create: 'Create in Extella', createGuards: 'Creation rules (mandatory)', createNo: 'NOT created here',
    guard: 'Protection against mass breakage', version: 'Active version', owner: 'Owner',
    agentId: 'Platform Agent ID', provider: 'Provider / model', limitsCol: 'Limits', type: 'Type',
    legacy: 'Legacy capability.global (not used for the exact consumer count)',
    outward: 'outward or physical actions', human: 'human required',
    sharedOfAgent: 'Shared Genes of this agent', wired: 'wired by the product'
  }
};

function cabLang(){
  return (typeof WLANG !== 'undefined' && WLANG === 'en') ? 'en' : 'ru';
}

function cabEsc(value){
  return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
  });
}

function cabLocalized(row, field, lang){
  row = row || {};
  var localized = row[field + '_' + lang];
  if(localized != null) return localized;
  return row[field] == null ? '' : row[field];
}

function cabList(values){
  return (Array.isArray(values) ? values : []).map(cabEsc).join(', ');
}

function cabGeneLabel(gene){
  if(typeof gene === 'string') return cabEsc(gene);
  gene = gene || {};
  var kind = gene.kind || gene.element_type || 'gene';
  var name = gene.name || gene.capability || '—';
  var id = gene.gene_id || '—';
  return cabEsc(name) + ' <span style="color:var(--silver,#8c8c8c)">[' +
    cabEsc(kind) + ' · ' + cabEsc(id) + ']</span>';
}

function renderCabinet(cab, hostId, tab){
  var host = document.getElementById(hostId); if(!host || !cab) return;
  var L = cabLang(), T = CAB_T[L], p = cab.passport || {}, i = p.identity || {};
  tab = tab || 'passport';
  var h = '<div style="display:flex;gap:8px;margin-bottom:14px">';
  ['passport','actual','evolution'].forEach(function(k, n){
    h += '<button type="button" data-cab-tab="' + k + '" class="btn ' +
      (tab===k?'gold':'ghost') + ' sm">' + cabEsc(T.tabs[n]) + '</button>';
  });
  h += '</div>';
  h += '<div style="font:700 18px var(--sans)">' + cabEsc(i.name || '—') + '</div>' +
       '<div style="font-size:12.5px;color:var(--silver,#8c8c8c);margin-bottom:12px">' +
       cabEsc(T.owner) + ': ' + cabEsc(i.owner || '—') + ' · ' +
       cabEsc(T.agentId) + ': ' + cabEsc(i.platform_agent_id || '—') + ' · ' +
       cabEsc(T.version) + ': ' + cabEsc(i.active_version || '—') + ' · ' +
       cabEsc(T.provider) + ': ' + cabEsc(i.platform_provider || '—') + ' / ' +
       cabEsc(i.model_profile || '—') + ' · ' + (cabList(i.languages) || '—') + '</div>';

  if(tab === 'passport'){
    h += '<div class="card" style="margin-bottom:12px"><div style="font-weight:700;margin-bottom:8px">' +
      cabEsc(T.state) + '</div><table style="width:100%;font-size:12px;border-collapse:collapse">';
    (p.genome || []).forEach(function(s){
      var shared = s.provenance === 'global';
      var effect = s.side_effects ?
        cabEsc(s.side_effects) + ' / ' + cabEsc(s.confirmation || '—') : '—';
      h += '<tr style="border-top:1px solid var(--line,#ebe8e1)">' +
           '<td style="padding:5px 4px"><b>' + cabEsc(s.name || s.capability || '—') +
           '</b> <span style="color:var(--silver)">v' + cabEsc(s.version || '—') + '</span>' +
           (s.gene_id ? '<br><span style="color:var(--silver)">' + cabEsc(s.gene_id) + '</span>' : '') +
           '</td><td style="padding:5px 4px">' + cabEsc(T.type) + ': ' +
           cabEsc(s.element_type || 'capability') + '</td>' +
           '<td style="padding:5px 4px">' + cabEsc(s.autonomy || '—') + '</td>' +
           '<td style="padding:5px 4px;color:' + (shared?'#a5632a':'var(--silver)') + '">' +
           cabEsc(shared ? T.shared : T.own) + '</td>' +
           '<td style="padding:5px 4px">' + effect + '</td>' +
           '<td style="padding:5px 4px">' + cabEsc(T.limitsCol) + ': ' +
           (Array.isArray(s.limits) ? s.limits.length : 0) + '</td></tr>';
    });
    h += '</table></div>';
    var a = p.attention || {};
    var genes = (a.shared_genes || []).map(cabGeneLabel).join(', ') || '—';
    h += '<div class="card" style="border-left:3px solid #a5632a"><div style="font-weight:700;margin-bottom:8px">' +
         cabEsc(T.attention) + '</div><div style="font-size:12.5px;line-height:1.7">' +
         '• ' + cabEsc(T.shared) + ': ' + genes + '<br>' +
         '• ' + cabEsc(T.legacy) + ': ' + (cabList(a.legacy_global_capabilities) || '—') + '<br>' +
         '• ' + cabEsc(T.outward) + ': ' + (cabList(a.external_or_physical) || '—') + '<br>' +
         '• ' + cabEsc(T.human) + ': ' + (cabList(a.human_required) || '—') + '</div></div>';
  }

  if(tab === 'actual'){
    var d = cab.declared_behaviour || {}, ac = cab.actual_behaviour || {};
    h += '<div class="card" style="margin-bottom:12px"><div style="font-weight:700;margin-bottom:8px">' +
         cabEsc(T.declared) + '</div><div style="font-size:12.5px;line-height:1.7">' +
         (d.steps || []).map(function(s,n){
           return (n+1) + '. ' + cabEsc(s.capability || '—') + ' (' +
             cabEsc(s.autonomy || '—') + ', ' + cabEsc(s.side_effects || '—') + ')';
         }).join('<br>') + '</div></div>';
    h += '<div class="card" style="margin-bottom:12px"><div style="font-weight:700;margin-bottom:8px">' +
         cabEsc(T.sources) + '</div><div style="font-size:12.5px;line-height:1.7">• ' +
         (ac.evidence_sources || []).map(function(s){
           return cabEsc(cabLocalized(s, 'what', L));
         }).join('<br>• ') + '</div></div>';
    h += '<div class="card" style="border-left:3px solid #a5632a"><div style="font-weight:700;margin-bottom:8px">' +
         cabEsc(T.limits) + '</div><div style="font-size:12.5px;line-height:1.7">• ' +
         ((ac.limits || {})[L] || []).map(cabEsc).join('<br>• ') + '</div></div>';
  }

  if(tab === 'evolution'){
    var e = cab.evolution || {}, g = e.shared_change_guard || {};
    h += '<div class="card" style="margin-bottom:12px"><div style="font-weight:700;margin-bottom:8px">' +
         cabEsc(T.cycle) + '</div><div style="font-size:12.5px;line-height:1.7">' +
         (e.cycle || []).map(function(s,n){
           return '<b>' + (n+1) + '.</b> ' + cabEsc(cabLocalized(s, 'what', L));
         }).join('<br>') + '</div></div>';
    var cr = e.creation || {};
    if(cr.required){
      var kinds = (cr.kinds || []).map(function(k){
        return '<button type="button" class="btn ghost sm" disabled title="' + cabEsc(T.wired) + '">+ ' +
               cabEsc(cabLocalized(k, 'what', L)) + '</button>';
      }).join('');
      var guards = (cr.guards || []).map(function(x){
        return '• ' + cabEsc(cabLocalized(x, 'must', L));
      }).join('<br>');
      var nope = ((L==='en' ? cr.forbidden_en : cr.forbidden_ru) || []).map(cabEsc).join(' · ');
      h += '<div class="card" style="margin-bottom:12px"><div style="font-weight:700;margin-bottom:8px">' +
           cabEsc((L==='en' ? cr.title_en : cr.title_ru) || T.create) + '</div>' +
           '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">' + kinds + '</div>' +
           '<div style="font-size:12px;line-height:1.7;color:var(--silver,#8c8c8c)"><b>' +
           cabEsc(T.createGuards) + ':</b><br>' + guards + '<br><b>' + cabEsc(T.createNo) + ':</b> ' +
           nope + '</div></div>';
    }
    var q = String((L==='en' ? g.prompt_en : g.prompt_ru) || '');
    var ch = (L==='en' ? g.choices_en : g.choices_ru) || [];
    q = q.replace('{N}', String(g.affected_count != null ? g.affected_count : 'N'));
    var candidates = (g.candidates || []).map(cabGeneLabel).join(', ') || '—';
    h += '<div class="card" style="border-left:3px solid #a5632a"><div style="font-weight:700;margin-bottom:8px">' +
         cabEsc(T.guard) + '</div><div style="font-size:13px;line-height:1.6;margin-bottom:10px">' +
         cabEsc(q) + '</div><div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">' +
         ch.map(function(c,n){
           return '<button type="button" class="btn ' + (n===0?'gold':'ghost') +
             ' sm" disabled title="' + cabEsc(T.wired) + '">' + cabEsc(c) + '</button>';
         }).join('') + '</div><div style="font-size:12px;color:var(--silver,#8c8c8c)">' +
         cabEsc(cabLocalized(g, 'must_show', L)) + '<br><b>' +
         cabEsc(T.sharedOfAgent) + ':</b> ' + candidates + '</div></div>';
  }

  host.innerHTML = h;
  Array.prototype.forEach.call(host.querySelectorAll('[data-cab-tab]'), function(button){
    button.addEventListener('click', function(){
      renderCabinet(cab, hostId, button.getAttribute('data-cab-tab'));
    });
  });
}
