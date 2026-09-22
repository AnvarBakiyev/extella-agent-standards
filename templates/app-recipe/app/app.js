(() => {
  const el = id => document.getElementById(id);
  const bridge = new ExtellaBridge({ routeExpert:'my_app_where', allowedExperts:['my_app_expert'] });
  let lastTask = '', scenario = 'base';

  const scenarios = { base:['Базовый',100,'Текущие условия'], risk:['Риск',64,'Спрос ниже, затраты выше'], upside:['Рост',145,'Спрос выше ожиданий'] };
  function renderScenarios() {
    el('scenario-table').innerHTML = Object.entries(scenarios).map(([key,[name,value,note]]) => `<tr><td>${name}</td><td class="num">${value}</td><td>${note}</td></tr>`).join('');
    document.querySelectorAll('[data-scenario]').forEach(button => button.classList.toggle('active', button.dataset.scenario === scenario));
  }
  function status(message, type='') { const node=el('status'); node.textContent=message; node.className=`status ${type}`; }
  function view(name) { ['empty','waiting','error','result'].forEach(id => el(id).classList.toggle('hidden', id !== name)); }
  function setBusy(busy) { el('run').disabled=busy; el('run').textContent=busy?'Считаю…':'Сделать'; }
  function showDeviceConnect(error) {
    const visible = error?.code === 'DEVICE_REQUIRED';
    el('device-connect').classList.toggle('hidden', !visible);
    if (visible) {
      el('device-status').textContent = error.message || '';
      el('device-status').className = 'status error';
      el('device-id').focus();
    }
  }
  function localResult(task) { const factor=scenarios[scenario][1]; return `Готово локально\n\nЗадача: ${task}\nСценарий: ${scenarios[scenario][0]}\nИтоговый ориентир: ${factor}\n\nПодключи my_app_expert, чтобы заменить этот demo-расчёт реальным.`; }

  async function run() {
    const task = el('task').value.trim();
    if (!task) { status('Сначала опиши задачу.', 'error'); el('task').focus(); return; }
    lastTask=task; setBusy(true); view('waiting'); status('Считаю результат…', 'wait');
    try {
      // In a browser the local calculation keeps development and visual tests fast.
      // Inside Extella replace this condition with the real expert call immediately.
      const answer = bridge.embedded ? await bridge.run('my_app_expert', { task, scenario }) : { ok:true, data:{ text:localResult(task), mode:'локально' } };
      if (!answer.ok) { const error=new Error(answer.error); error.code=answer.code; throw error; }
      showDeviceConnect(null);
      el('result').textContent = answer.data.text || answer.data.message || JSON.stringify(answer.data, null, 2);
      el('mode').textContent = bridge.embedded ? 'Extella' : 'локально'; view('result'); status('Готово — результат подтверждён.', 'ok');
    } catch (error) {
      showDeviceConnect(error);
      el('error-text').textContent=error.message || 'Повтори попытку.'; view('error'); status('Результат не подтверждён.', 'error');
    } finally { setBusy(false); }
  }

  async function connectDevice() {
    const button=el('device-use'); button.disabled=true; button.textContent='Проверяю устройство…';
    el('device-status').textContent='Проверяю ответ на выбранном компьютере…'; el('device-status').className='status wait';
    try {
      const proof=await bridge.connectDevice(el('device-id').value);
      el('device-status').textContent=`Устройство ${proof.device.slice(0,8)} подтверждено. Работает только до закрытия окна.`;
      el('device-status').className='status ok';
      if (lastTask) await run();
    } catch (error) {
      el('device-status').textContent=error.message || String(error); el('device-status').className='status error';
    } finally { button.disabled=false; button.textContent='Работать через это устройство'; }
  }

  el('run').addEventListener('click', run);
  el('retry').addEventListener('click', () => { el('task').value=lastTask; run(); });
  el('example').addEventListener('click', () => { el('task').value='Собери список рисков запуска'; el('task').focus(); });
  el('device-use').addEventListener('click', connectDevice);
  el('device-id').addEventListener('keydown', event => { if (event.key === 'Enter') connectDevice(); });
  el('scenarios').addEventListener('click', event => { const button=event.target.closest('[data-scenario]'); if (!button) return; scenario=button.dataset.scenario; renderScenarios(); if (lastTask) run(); });
  window.__APP_TEST__ = { run, bridge, setEmbedded(value) { Object.defineProperty(bridge, 'embedded', { value, configurable:true }); } };
  renderScenarios();
})();
