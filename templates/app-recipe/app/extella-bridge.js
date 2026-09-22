/* One route from an Extella OS window to the app's own experts (canon H106).

   HOW THE OS WINDOW WORKS (measured inside a live window 22.09.2026):
   - the OS does NOT listen to postMessage 'etb_run_expert' — that protocol belonged to the
     toolbar retired on 12.08.2026, and a call sent that way goes nowhere;
   - the window is a sandbox (origin null): parent.extellaDesktop is blocked, and the OS
     does not put the device into etb_init either;
   - what works (Agent 1C, Recruiter): the OS fills {{app_token}} into index.html, and the
     page calls POST https://os.extella.ai/api/app-agent/run itself.

   DEVICE. The platform's answer does not say where the code ran, so the app's expert
   reports it itself (field "device", read from ~/.extella/device.txt). The bridge
   remembers it and pins every next call with targets:[device]. The first call goes
   unpinned: the platform picks the machine, and if it picks one logged into another
   account the bridge says so in words instead of showing a "syntax error" (H104). */
class ExtellaBridge {
  constructor({ timeoutMs = 90000, allowedExperts = [] } = {}) {
    this.timeoutMs = timeoutMs;
    this.allowedExperts = new Set(allowedExperts);
    const token = String(window.EXTELLA_APP_TOKEN || '');
    this.token = token && !token.startsWith('{{') ? token : '';
    this.device = ExtellaBridge.recall();
  }

  static get API() { return 'https://os.extella.ai/api/app-agent/run'; }
  static isDevice(v) { return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(v || '')); }

  // Storage throws inside the sandboxed window — then the device lives for this session only.
  static recall() {
    try { const v = localStorage.getItem('extella-app-device'); return ExtellaBridge.isDevice(v) ? v : null; }
    catch (_) { return null; }
  }
  remember(v) {
    if (!ExtellaBridge.isDevice(v)) return;
    this.device = String(v);
    try { localStorage.setItem('extella-app-device', this.device); } catch (_) { /* session only */ }
  }
  forget() {
    this.device = null;
    try { localStorage.removeItem('extella-app-device'); } catch (_) { /* nothing stored */ }
  }

  // "Embedded" means the OS handed this page its key; outside Extella app.js uses local demo mode.
  get embedded() { return Boolean(this.token); }

  async run(expert, params = {}, { timeoutMs = this.timeoutMs } = {}) {
    if (!this.allowedExperts.has(expert)) return { ok:false, error:'Этот маршрут не разрешён приложению.' };
    if (!this.embedded) return { ok:false, error:'Эксперт доступен только в окне Extella OS — открой приложение с рабочего стола.' };
    const pinned = this.device;
    const answer = await this.call(expert, params, pinned, timeoutMs);
    // The remembered machine was removed or is offline: forget it and let the platform choose once.
    if (!answer.ok && pinned && answer.deviceGone) {
      this.forget();
      return this.call(expert, params, null, timeoutMs);
    }
    return answer;
  }

  async call(expert, params, device, timeoutMs) {
    const body = { app_token:this.token, expert_name:expert, params };
    if (device) body.targets = [device];
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), timeoutMs);
    let status = 0, raw = '';
    try {
      const response = await fetch(ExtellaBridge.API, {
        method:'POST', headers:{ 'Content-Type':'application/json' }, body:JSON.stringify(body), signal:abort.signal,
      });
      status = response.status;
      raw = await response.text();
    } catch (error) {
      return { ok:false, error: error.name === 'AbortError'
        ? `Extella не ответила за ${Math.round(timeoutMs / 1000)} с. Задание могло продолжиться на компьютере — повтори через минуту.`
        : 'Нет связи с Extella. Проверь интернет и повтори.' };
    } finally { clearTimeout(timer); }

    if (status === 401 || status === 403) {
      return { ok:false, error:'Ключ окна устарел или приложению не выданы права запуска. Закрой окно и открой приложение с рабочего стола заново.' };
    }
    if (status === 429) return { ok:false, error:'Слишком много запросов подряд. Подожди минуту и повтори.' };
    if (status >= 400) {
      const deviceGone = /is unavailable/i.test(raw);
      return { ok:false, deviceGone, error: deviceGone
        ? 'Компьютер, на котором работало приложение, сейчас не на связи. Открой на нём Extella и повтори.'
        : /Expert not found/i.test(raw)
          ? `У приложения нет эксперта ${expert}. Его нужно сохранить в агента приложения.`
          : `Extella ответила ошибкой ${status}. Повтори; если повторится — пришли этот текст в поддержку.` };
    }

    let value;
    try { value = ExtellaBridge.unwrap(JSON.parse(raw)); }
    catch (error) { return { ok:false, error:error.message || 'Extella ответила не по форме.' }; }
    if (value && typeof value === 'object') {
      if (value.status === 'error') return { ok:false, error:value.message || 'Эксперт вернул ошибку.' };
      this.remember(value.device || (value.pageRoute && value.pageRoute.targetId));
    }
    return { ok:true, data:value };
  }

  // Transport wrappers come off here; what is inside belongs to the caller (H17, H56).
  static unwrap(value) {
    for (let depth = 0; depth < 10; depth++) {
      if (typeof value === 'string') {
        if (value.startsWith('[Execution Error]')) throw new Error(ExtellaBridge.explain(value));
        if (value.startsWith('deferred')) throw new Error('Работа идёт дольше обычного и продолжается в фоне. Подожди минуту и нажми ещё раз.');
        try { value = JSON.parse(value); continue; }
        catch (_) { throw new Error('Эксперт ответил не JSON-строкой (H17): «' + value.slice(0, 120) + '»'); }
      }
      const transport = value && typeof value === 'object' && value.result !== undefined &&
                        (value.status === 'ok' || value.expert_name !== undefined);
      if (!transport) break;
      value = value.result;
    }
    return value;
  }

  // A "syntax error" on line 1 of <container> is not syntax: the machine is logged into
  // another Extella account and the expert code arrives unreadable (H104). The wording
  // changes from run to run (decimal / imaginary literal, invalid syntax), the line does not.
  static explain(text) {
    if (/\(<container>, line 1\)/.test(text)) {
      return 'Extella отправила задание на компьютер, который вошёл в другой аккаунт Extella. ' +
             'Открой Extella на нужном компьютере тем же аккаунтом, что и это окно, или отвяжи лишний компьютер от аккаунта.';
    }
    return 'Код не выполнился на компьютере: ' + text.replace('[Execution Error]', '').trim().slice(0, 200);
  }
}

window.ExtellaBridge = ExtellaBridge;
