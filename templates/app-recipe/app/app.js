(() => {
  const el = id => document.getElementById(id);
  const bridge = new ExtellaBridge({ allowedExperts:['my_app_expert'] });
  let lastTask = '', scenario = 'base';

  const scenarios = { base:['Базовый',100,'Текущие условия'], risk:['Риск',64,'Спрос ниже, затраты выше'], upside:['Рост',145,'Спрос выше ожиданий'] };
  function renderScenarios() {
    el('scenario-table').innerHTML = Object.entries(scenarios).map(([key,[name,value,note]]) => `<tr><td>${name}</td><td class="num">${value}</td><td>${note}</td></tr>`).join('');
    document.querySelectorAll('[data-scenario]').forEach(button => button.classList.toggle('active', button.dataset.scenario === scenario));
  }
  function status(message, type='') { const node=el('status'); node.textContent=message; node.className=`status ${type}`; }
  function view(name) { ['empty','waiting','error','result'].forEach(id => el(id).classList.toggle('hidden', id !== name)); }
  function setBusy(busy) { el('run').disabled=busy; el('run').textContent=busy?'Считаю…':'Сделать'; }
  function localResult(task) { const factor=scenarios[scenario][1]; return `Готово локально\n\nЗадача: ${task}\nСценарий: ${scenarios[scenario][0]}\nИтоговый ориентир: ${factor}\n\nПодключи my_app_expert, чтобы заменить этот demo-расчёт реальным.`; }

  async function run() {
    const task = el('task').value.trim();
    if (!task) { status('Сначала опиши задачу.', 'error'); el('task').focus(); return; }
    lastTask=task; setBusy(true); view('waiting'); status('Считаю результат…', 'wait');
    try {
      // In a browser the local calculation keeps development and visual tests fast.
      // Inside Extella replace this condition with the real expert call immediately.
      const answer = bridge.embedded ? await bridge.run('my_app_expert', { task, scenario }) : { ok:true, data:{ text:localResult(task), mode:'локально' } };
      if (!answer.ok) throw new Error(answer.error);
      el('result').textContent = answer.data.text || answer.data.message || JSON.stringify(answer.data, null, 2);
      el('mode').textContent = bridge.embedded ? 'Extella' : 'локально'; view('result'); status('Готово — результат подтверждён.', 'ok');
    } catch (error) {
      el('error-text').textContent=error.message || 'Повтори попытку.'; view('error'); status('Результат не подтверждён.', 'error');
    } finally { setBusy(false); }
  }

  el('run').addEventListener('click', run);
  el('retry').addEventListener('click', () => { el('task').value=lastTask; run(); });
  el('example').addEventListener('click', () => { el('task').value='Собери список рисков запуска'; el('task').focus(); });
  el('scenarios').addEventListener('click', event => { const button=event.target.closest('[data-scenario]'); if (!button) return; scenario=button.dataset.scenario; renderScenarios(); if (lastTask) run(); });
  window.__APP_TEST__ = { run, bridge, setEmbedded(value) { Object.defineProperty(bridge, 'embedded', { value, configurable:true }); } };
  renderScenarios();
})();
