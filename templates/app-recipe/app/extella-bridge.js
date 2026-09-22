/* H106: scoped app_token transport for an Extella OS page. */
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

  targetFrom(value, depth = 0) {
    if (!value || depth > 8) return '';
    if (typeof value === 'string') {
      try { return this.targetFrom(JSON.parse(value), depth + 1); } catch { return ''; }
    }
    if (typeof value !== 'object') return '';
    const direct = value.pageRoute?.targetId || value.device || value.device_id || value.targetId;
    if (typeof direct === 'string' && direct.trim()) return direct.trim();
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
        throw new Error(payload.message || payload.detail || `Extella вернула HTTP ${response.status}`);
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

  async run(expert, params = {}, { timeoutMs = this.timeoutMs } = {}) {
    if (!this.allowedExperts.has(expert)) return { ok:false, error:'Этот маршрут не разрешён приложению.' };
    try {
      const target = await this.discover();
      const payload = await this.request(expert, params, [target], timeoutMs);
      return { ok:true, data:this.unwrap(payload), device:target };
    } catch (error) {
      return { ok:false, error:error?.message || String(error) };
    }
  }
}

window.ExtellaBridge = ExtellaBridge;
