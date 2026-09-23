/* H106: scoped app_token transport for an Extella OS page.

   Measured inside a live OS window 22.09.2026: the OS does not listen to 'etb_run_expert',
   parent.extellaDesktop is blocked by the sandbox, localStorage throws. The page calls
   /api/app-agent/run with its {{app_token}}; the device is named by the app's own
   dispatcher expert and every next call is pinned to it with targets:[device]. */
class ExtellaBridge {
  constructor({ timeoutMs = 90000, allowedExperts = [], routeExpert = '' } = {}) {
    this.timeoutMs = timeoutMs;
    this.allowedExperts = new Set(allowedExperts);
    this.routeExpert = routeExpert;
    if (routeExpert) this.allowedExperts.add(routeExpert);
    this.appToken = String(window.EXTELLA_APP?.appToken || '');
    this.device = null;
    this.discovery = null;
    this.calls = [];
  }

  get embedded() { return Boolean(this.appToken) && !this.appToken.startsWith('{{'); }

  static isDevice(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(value || '').trim());
  }

  static executionError(value, depth = 0) {
    if (!value || depth > 8) return '';
    if (typeof value === 'string') {
      if (value.startsWith('[Execution Error]')) return value;
      try { return ExtellaBridge.executionError(JSON.parse(value), depth + 1); } catch { return ''; }
    }
    if (typeof value !== 'object') return '';
    for (const key of ['result', 'data', 'response', 'payload']) {
      const found = ExtellaBridge.executionError(value[key], depth + 1);
      if (found) return found;
    }
    return '';
  }

  static accountMismatch(text) {
    return /^\[Execution Error\][\s\S]*\(<container>, line 1\)/.test(String(text || ''));
  }

  static codedError(message, code) {
    const error = new Error(message);
    error.code = code;
    return error;
  }

  static deferred(value, depth = 0) {
    if (!value || depth > 8) return false;
    if (typeof value === 'string') {
      if (value.startsWith('deferred')) return true;
      try { return ExtellaBridge.deferred(JSON.parse(value), depth + 1); } catch { return false; }
    }
    if (typeof value !== 'object') return false;
    return ['result', 'data', 'response', 'payload'].some(key => ExtellaBridge.deferred(value[key], depth + 1));
  }

  targetFrom(value, depth = 0) {
    if (!value || depth > 8) return '';
    if (typeof value === 'string') {
      try { return this.targetFrom(JSON.parse(value), depth + 1); } catch { return ''; }
    }
    if (typeof value !== 'object') return '';
    const direct = value.pageRoute?.targetId || value.device || value.device_id || value.targetId;
    // Only a real device id counts: once a storefront handed out "[object Promise]" as a device.
    if (ExtellaBridge.isDevice(direct)) return String(direct).trim();
    for (const key of ['result', 'data', 'response', 'payload']) {
      const found = this.targetFrom(value[key], depth + 1);
      if (found) return found;
    }
    return '';
  }

  unwrap(value) {
    let current = value;
    for (let depth = 0; depth < 8; depth += 1) {
      if (typeof current === 'string') {
        try { current = JSON.parse(current); continue; } catch { return current; }
      }
      if (!current || typeof current !== 'object') return current;
      const platform = 'expert_name' in current || 'execution_log' in current || 'agent_id' in current;
      if (platform && current.result !== undefined) { current = current.result; continue; }
      if (typeof current.result === 'string') { current = current.result; continue; }
      return current;
    }
    return current;
  }

  async request(expert, params = {}, targets = null, timeoutMs = this.timeoutMs) {
    if (!this.embedded) throw new Error('Открой приложение с рабочего стола Extella и обнови окно.');
    const now = Date.now();
    this.calls = this.calls.filter(at => now - at < 60000);
    if (this.calls.length >= 30) throw new Error('Слишком много действий за минуту. Подожди и повтори.');
    const body = { app_token:this.appToken, expert_name:expert, params:params || {} };
    if (targets?.length) body.targets = targets;
    const encoded = JSON.stringify(body);
    if (new TextEncoder().encode(encoded).length > 65536) throw new Error('Запрос больше 64 КБ. Уменьши объём данных.');
    this.calls.push(now);
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch('https://os.extella.ai/api/app-agent/run', {
        method:'POST', headers:{'Content-Type':'application/json'}, body:encoded, signal:controller.signal,
      });
      let payload = {};
      try { payload = await response.json(); } catch { /* error below */ }
      if (!response.ok) {
        if (response.status === 401) throw new Error('Ключ приложения истёк. Обнови окно Extella и повтори.');
        if (response.status === 403) throw new Error('Разреши приложению запуск экспертов на устройстве.');
        const text = String(payload.message || payload.detail || '');
        if (/is unavailable/i.test(text)) {
          const gone = new Error('Компьютер, на котором работало приложение, сейчас не на связи. Открой на нём Extella и повтори.');
          gone.deviceGone = true;
          throw gone;
        }
        throw new Error(text || `Extella вернула HTTP ${response.status}`);
      }
      const executionError = ExtellaBridge.executionError(payload);
      if (executionError) {
        if (ExtellaBridge.accountMismatch(executionError)) {
          throw ExtellaBridge.codedError(
            'Extella отправила задание на компьютер, который вошёл в другой аккаунт. ' +
            'Скопируй Device ID нужного компьютера из нижней панели Extella.',
            'DEVICE_REQUIRED',
          );
        }
        throw ExtellaBridge.codedError(
          `Код не выполнился на устройстве: ${executionError.replace('[Execution Error]', '').trim().slice(0, 200)}`,
          'EXECUTION_ERROR',
        );
      }
      if (ExtellaBridge.deferred(payload)) {
        throw new Error('Работа идёт дольше обычного и продолжается в фоне. Подожди минуту и нажми ещё раз.');
      }
      return payload;
    } catch (error) {
      if (error?.name === 'AbortError') throw new Error('Extella не подтвердила выполнение за отведённое время.');
      throw error;
    } finally { window.clearTimeout(timer); }
  }

  async discover() {
    if (this.device) return this.device;
    if (!this.routeExpert) throw new Error('В приложении не задан эксперт-диспетчер устройства.');
    if (!this.discovery) this.discovery = (async () => {
      const payload = await this.request(this.routeExpert, {}, null);
      const target = this.targetFrom(payload);
      if (!target) throw new Error('Extella выполнила первый вызов, но не сообщила устройство. Перезапусти Extella на нужном компьютере.');
      this.device = target;
      return target;
    })().catch(error => { this.discovery = null; throw error; });
    return this.discovery;
  }

  async connectDevice(value) {
    const target = String(value || '').trim();
    if (!ExtellaBridge.isDevice(target)) {
      throw ExtellaBridge.codedError(
        'Device ID должен быть UUID из 36 символов. Нажми строку Device ID в нижней панели Extella, чтобы скопировать его.',
        'INVALID_DEVICE',
      );
    }
    if (!this.routeExpert) throw new Error('В приложении не задан эксперт-диспетчер устройства.');
    try {
      const payload = await this.request(this.routeExpert, {}, [target]);
      const reported = this.targetFrom(payload);
      if (reported !== target) {
        throw ExtellaBridge.codedError(
          reported ? 'Эксперт ответил с другого устройства. Проверь Device ID и повтори.'
                   : 'Устройство ответило, но не подтвердило свой Device ID. Повтори или выбери другой компьютер.',
          'DEVICE_MISMATCH',
        );
      }
      this.device = target;
      this.discovery = Promise.resolve(target);
      return { device:target, data:this.unwrap(payload) };
    } catch (error) {
      if (error?.code === 'DEVICE_REQUIRED') {
        throw ExtellaBridge.codedError(
          'Указанный компьютер вошёл в другой аккаунт Extella. Войди на нём тем же аккаунтом, что и в этом окне.',
          'DEVICE_REQUIRED',
        );
      }
      throw error;
    }
  }

  async run(expert, params = {}, { timeoutMs = this.timeoutMs } = {}) {
    if (!this.allowedExperts.has(expert)) return { ok:false, error:'Этот маршрут не разрешён приложению.' };
    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        const target = await this.discover();
        const payload = await this.request(expert, params, [target], timeoutMs);
        const data = this.unwrap(payload);
        if (data && typeof data === 'object' && data.status === 'error') return { ok:false, error:data.message || 'Эксперт вернул ошибку.' };
        return { ok:true, data, device:target };
      } catch (error) {
        // The machine was removed or went offline: forget it and ask the dispatcher once more.
        if (error?.deviceGone && attempt === 0) { this.device = null; this.discovery = null; continue; }
        return { ok:false, error:error?.message || String(error), code:error?.code || '' };
      }
    }
    return { ok:false, error:'Не удалось найти компьютер для работы.' };
  }
}

window.ExtellaBridge = ExtellaBridge;
