/* One safe route from an iframe app to Extella experts. */
class ExtellaBridge {
  constructor({ timeoutMs = 90000, allowedExperts = [] } = {}) {
    this.timeoutMs = timeoutMs;
    this.allowedExperts = new Set(allowedExperts);
    this.pending = new Map();
    this.device = null;
    window.addEventListener('message', event => this.onMessage(event));
  }

  get embedded() { return window.parent !== window; }
  id() { return `app-${Date.now()}-${crypto.getRandomValues(new Uint32Array(1))[0].toString(36)}`; }

  run(expert, params = {}, { timeoutMs = this.timeoutMs } = {}) {
    if (!this.allowedExperts.has(expert)) return Promise.resolve({ ok:false, error:'Этот маршрут не разрешён приложению.' });
    if (!this.embedded) return Promise.resolve({ ok:false, error:'Эксперт доступен только внутри OS XTEL.' });
    const reqId = this.id();
    return new Promise(resolve => {
      const timer = window.setTimeout(() => {
        this.pending.delete(reqId);
        resolve({ ok:false, error:'Extella не подтвердила выполнение за отведённое время.' });
      }, timeoutMs);
      this.pending.set(reqId, { resolve, timer });
      window.parent.postMessage({ type:'etb_run_expert', reqId, name:expert, params }, '*');
    });
  }

  onMessage(event) {
    if (event.source !== window.parent) return;
    const data = event.data || {};
    if (data.type === 'etb_init') { this.device = data.device || null; return; }
    if (data.type !== 'etb_expert_result' || !this.pending.has(data.reqId)) return;
    const pending = this.pending.get(data.reqId);
    this.pending.delete(data.reqId); window.clearTimeout(pending.timer);
    pending.resolve(data.ok === false ? { ok:false, error:data.error || data.message || 'Эксперт вернул ошибку.' } : { ok:true, data:data.result ?? data });
  }
}

window.ExtellaBridge = ExtellaBridge;
