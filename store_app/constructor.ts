/* The constructor is a local, read-only presentation. No API calls or runtime dependencies. */
type ConstructorOptions = {
  t: (key: string) => string;
  copy: (text: string, button: HTMLButtonElement, idle: string, done: string) => void;
};

type ConstructorMemory = {
  assembled: boolean;
  tabs: Record<string, string>;
  dialog: string;
};

type ConstructorInstance = {
  dispose: () => void;
  deactivate: () => void;
};

type ConstructorAPI = {
  mount: (root: HTMLElement, options: ConstructorOptions) => void;
  unmount: (root: HTMLElement) => void;
  deactivate: (root: HTMLElement) => void;
};

interface Window {
  ExtellaConstructor: ConstructorAPI;
}

(function () {
  const instances = new WeakMap<HTMLElement, ConstructorInstance>();
  const memories = new WeakMap<HTMLElement, ConstructorMemory>();
  const svgNS = 'http://www.w3.org/2000/svg';
  const bricks = [
    { id: 'agent', color: '#b9a5e4', light: '#dbcef8', dark: '#9077c0', ink: '#473666', exploded: [224, 42], connected: [224, 50] },
    { id: 'icon', color: '#c5df87', light: '#e6f6b9', dark: '#9db65f', ink: '#4b6130', exploded: [422, 166], connected: [320, 148] },
    { id: 'integrations', color: '#8cafe5', light: '#bdd3f6', dark: '#628cc5', ink: '#304b76', exploded: [25, 170], connected: [128, 148] },
    { id: 'platform', color: '#4665ec', light: '#7490ff', dark: '#2949c7', ink: '#ffffff', exploded: [224, 270], connected: [224, 250] },
    { id: 'devices', color: '#f49781', light: '#ffc2ad', dark: '#d57361', ink: '#6e382f', exploded: [422, 350], connected: [320, 348] },
    { id: 'evolution', color: '#8798a9', light: '#b0bdcc', dark: '#62798e', ink: '#ffffff', exploded: [29, 365], connected: [128, 348] },
  ];

  function svgElement<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string> = {}): SVGElementTagNameMap[K] {
    const element = document.createElementNS(svgNS, tag);
    Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
    return element;
  }

  function renderScene(root: HTMLElement, t: ConstructorOptions['t']): void {
    const scene = root.querySelector<HTMLElement>('[data-xtl-scene]');
    if (!scene || scene.querySelector('svg')) return;
    const svg = svgElement('svg', {
      class: 'xtl-brick-scene-canvas', viewBox: '0 0 660 540', role: 'group',
      'aria-label': t('constructor.sceneLabel'),
    });
    const connections = svgElement('g', { class: 'xtl-scene-connections', fill: 'none', stroke: '#aebcd1', 'stroke-width': '1.3', 'stroke-dasharray': '4 6' });
    connections.append(svgElement('path', { d: 'M319 190V251 M213 245L270 276 M421 255L382 278 M215 397L269 367 M421 420L380 397' }));
    svg.append(connections);
    bricks.forEach((brick, index) => {
      const card = root.querySelector<HTMLElement>('.xtl-part-card[data-xtl-part="' + brick.id + '"]');
      const label = card?.querySelector('h3')?.textContent?.trim() || brick.id;
      const position = svgElement('g', {
        'data-xtl-brick': brick.id,
        'data-exploded': brick.exploded.join(' '),
        'data-connected': brick.connected.join(' '),
        class: 'xtl-brick-position',
        style: '--xtl-brick-delay:' + index * 28 + 'ms',
      });
      const group = svgElement('g', {
        class: 'xtl-brick-scene-piece', role: 'button', tabindex: '0',
        'data-xtl-part': brick.id, 'aria-label': t('constructor.partDetails') + ': ' + label,
        'aria-haspopup': 'dialog',
      });
      // Geometry and colors are constants. Labels from content use textContent below.
      group.innerHTML =
        '<path d="M3 56 96 107 189 56V100Q189 104 185 106L100 152Q96 154 92 152L7 106Q3 104 3 100Z" fill="' + brick.dark + '"/>' +
        '<path d="M3 56 96 107V153L7 106Q3 104 3 100Z" fill="' + brick.color + '"/>' +
        '<path d="M7 50 91 4Q96 1 101 4L185 50Q192 54 185 58L101 104Q96 107 91 104L7 58Q0 54 7 50Z" fill="' + brick.light + '"/>' +
        '<path d="M7 58 91 104Q96 107 101 104L185 58" stroke="#fff" stroke-opacity=".28" stroke-width="1.3" fill="none"/>' +
        [[96, 27], [53, 51], [139, 51], [96, 75]].map(([x, y]) =>
          '<g><path d="M' + (x - 18) + ' ' + (y - 10) + 'v9a18 9.7 0 0 0 36 0v-9Z" fill="' + brick.color + '"/>' +
          '<ellipse cx="' + x + '" cy="' + (y - 10) + '" rx="18" ry="9.7" fill="' + brick.light + '" stroke="' + brick.color + '" stroke-width=".9"/></g>'
        ).join('') +
        '<path class="xtl-brick-scene-focus" d="M7 50 91 4Q96 1 101 4L185 50Q189 52 189 56V100Q189 104 185 106L100 152Q96 154 92 152L7 106Q3 104 3 100V56Q3 52 7 50Z" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="4 4"/>';
      const title = svgElement('title');
      title.textContent = label;
      const text = svgElement('text', { transform: 'translate(15 86) rotate(28.5)', fill: brick.ink, 'font-size': label.length > 12 ? '11' : '14', 'font-weight': '600' });
      text.textContent = label;
      group.append(title, text);
      position.append(group);
      svg.append(position);
    });
    scene.append(svg);
  }

  function unmount(root: HTMLElement): void {
    instances.get(root)?.dispose();
    instances.delete(root);
  }

  function deactivate(root: HTMLElement): void {
    instances.get(root)?.deactivate();
  }

  function mount(root: HTMLElement, options: ConstructorOptions): void {
    unmount(root);
    const { t, copy } = options;
    const memory = memories.get(root) || { assembled: false, tabs: {}, dialog: '' };
    memories.set(root, memory);
    const cleanup: Array<() => void> = [];
    const triggers = new WeakMap<HTMLDialogElement, HTMLElement | SVGElement>();
    let disposing = false;

    function listen(target: EventTarget, type: string, listener: EventListener, capture = false): void {
      target.addEventListener(type, listener, capture);
      cleanup.push(() => target.removeEventListener(type, listener, capture));
    }

    function labelElements(): void {
      root.querySelectorAll<HTMLElement>('[data-t]').forEach(element => {
        const text = t(element.getAttribute('data-t') || '');
        if (text) element.textContent = text;
      });
      root.querySelectorAll<HTMLElement>('[data-xtl-label]').forEach(element => {
        const text = t(element.getAttribute('data-xtl-label') || '');
        if (text) element.setAttribute('aria-label', text);
      });
    }

    function setAssembly(announce: boolean): void {
      root.classList.toggle('xtl-is-assembled', memory.assembled);
      root.querySelectorAll<SVGElement>('[data-xtl-brick]').forEach(brick => {
        const coordinates = (brick.getAttribute(memory.assembled ? 'data-connected' : 'data-exploded') || '0 0').split(/\s+/).map(Number);
        const x = Number.isFinite(coordinates[0]) ? coordinates[0] : 0;
        const y = Number.isFinite(coordinates[1]) ? coordinates[1] : 0;
        brick.style.transform = 'translate(' + x + 'px,' + y + 'px)';
      });
      root.querySelectorAll<HTMLButtonElement>('[data-xtl-action="assemble"]').forEach(button => {
        button.textContent = t(memory.assembled ? 'constructor.disassemble' : 'constructor.assemble');
        button.setAttribute('aria-pressed', String(memory.assembled));
      });
      const status = root.querySelector<HTMLElement>('[data-xtl-assembly-status]');
      if (status && announce) status.textContent = t(memory.assembled ? 'constructor.assembled' : 'constructor.exploded');
    }

    function setTab(scope: HTMLElement, value: string, focus = false): void {
      const tabs = Array.from(scope.querySelectorAll<HTMLButtonElement>('[data-xtl-tab]'));
      const selected = tabs.find(tab => tab.getAttribute('data-xtl-tab') === value) || tabs[0];
      if (!selected) return;
      value = selected.getAttribute('data-xtl-tab') || '';
      const name = scope.getAttribute('data-xtl-tabs-scope') || '';
      memory.tabs[name] = value;
      tabs.forEach(tab => {
        const active = tab === selected;
        tab.setAttribute('aria-selected', String(active));
        tab.tabIndex = active ? 0 : -1;
        tab.classList.toggle('active', active);
        tab.classList.toggle('is-active', active);
        tab.classList.toggle('xtl-active', active);
        tab.classList.toggle('xtl-is-active', active);
      });
      scope.querySelectorAll<HTMLElement>('[data-xtl-panel]').forEach(panel => {
        const active = panel.getAttribute('data-xtl-panel') === value;
        panel.hidden = !active;
        if (!active) pauseMedia(panel);
      });
      if (focus) selected.focus();
    }

    function closeDialog(dialog: HTMLDialogElement): void {
      if (dialog.open) dialog.close();
    }

    function openDialog(id: string, trigger?: HTMLElement | SVGElement): void {
      const dialog = Array.from(root.querySelectorAll<HTMLDialogElement>('dialog[data-xtl-dialog]')).find(item => item.getAttribute('data-xtl-dialog') === id);
      if (!dialog) return;
      const parentDialog = trigger?.closest<HTMLDialogElement>('dialog');
      const externalTrigger = parentDialog ? triggers.get(parentDialog) : trigger;
      root.querySelectorAll<HTMLDialogElement>('dialog[open]').forEach(item => {
        if (item !== dialog) { triggers.delete(item); closeDialog(item); }
      });
      const returnTarget = externalTrigger || Array.from(root.querySelectorAll<HTMLElement>('.xtl-part-card[data-xtl-part]')).find(card => card.getAttribute('data-xtl-part') === id);
      if (returnTarget) triggers.set(dialog, returnTarget);
      memory.dialog = id;
      if (!dialog.open) dialog.showModal();
      dialog.scrollTop = 0;
      const heading = dialog.querySelector<HTMLElement>('h2');
      if (heading) { heading.tabIndex = -1; heading.focus({ preventScroll: true }); }
    }

    function mediaStatus(element: Element, text: string): void {
      const panel = element.closest('[data-xtl-panel]') || element.parentElement;
      if (!panel) return;
      let status = panel.querySelector<HTMLElement>('[data-xtl-media-status]');
      if (!status) {
        status = document.createElement('p');
        status.className = 'xtl-media-status';
        status.setAttribute('data-xtl-media-status', '');
        status.setAttribute('role', 'status');
        panel.append(status);
      }
      status.textContent = text;
    }

    function pauseMedia(container: Element): void {
      container.querySelectorAll<HTMLVideoElement>('video').forEach(video => video.pause());
      container.querySelectorAll<HTMLImageElement>('[data-xtl-chat-image]').forEach(img => {
        const poster = img.dataset.xtlPoster;
        if (poster && img.getAttribute('src') !== poster) img.src = poster;
        const button = img.closest('[data-xtl-panel]')?.querySelector<HTMLButtonElement>('[data-xtl-media="chat"]');
        if (button) {
          if (button.getAttribute('aria-pressed') === 'true') mediaStatus(img, '');
          button.setAttribute('aria-pressed', 'false');
          button.textContent = t('constructor.mediaPlay');
        }
      });
    }

    function toggleMedia(button: HTMLButtonElement): void {
      const panel = button.closest('[data-xtl-panel]');
      const img = panel?.querySelector<HTMLImageElement>('[data-xtl-chat-image]');
      if (!img) return;
      const playing = button.getAttribute('aria-pressed') === 'true';
      if (!img.dataset.xtlPoster) img.dataset.xtlPoster = img.getAttribute('src') || '';
      const source = button.getAttribute('data-xtl-gif') || img.getAttribute('data-xtl-gif') || '';
      if (!playing && !/^https:\/\/(?:extella\.dev|extella\.ai)\//.test(source)) {
        mediaStatus(button, t('constructor.mediaUnavailable'));
        return;
      }
      img.src = playing ? img.dataset.xtlPoster : source;
      button.setAttribute('aria-pressed', String(!playing));
      button.textContent = t(playing ? 'constructor.mediaPlay' : 'constructor.mediaPause');
      mediaStatus(button, playing ? '' : t('constructor.mediaLoading'));
    }

    labelElements();
    renderScene(root, t);
    if (!root.querySelector('[data-xtl-assembly-status]')) {
      const status = document.createElement('p');
      status.className = 'xtl-visually-hidden';
      status.setAttribute('role', 'status');
      status.setAttribute('data-xtl-assembly-status', '');
      root.querySelector('[data-xtl-scene]')?.append(status);
    }
    setAssembly(false);
    root.querySelectorAll<HTMLElement>('[data-xtl-tabs-scope]').forEach(scope => {
      const name = scope.getAttribute('data-xtl-tabs-scope') || '';
      const active = scope.querySelector('[data-xtl-tab][aria-selected="true"]');
      setTab(scope, memory.tabs[name] || active?.getAttribute('data-xtl-tab') || '');
    });

    listen(root, 'click', event => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;
      const close = target.closest('[data-xtl-close]');
      if (close) { const dialog = close.closest('dialog'); if (dialog) closeDialog(dialog); return; }
      const dialog = target instanceof HTMLDialogElement ? target : null;
      if (dialog) {
        const rect = dialog.getBoundingClientRect();
        const mouse = event as MouseEvent;
        if (mouse.clientX < rect.left || mouse.clientX > rect.right || mouse.clientY < rect.top || mouse.clientY > rect.bottom) closeDialog(dialog);
        return;
      }
      const part = target.closest<HTMLElement | SVGElement>('[data-xtl-part]');
      if (part) { openDialog(part.getAttribute('data-xtl-part') || '', part); return; }
      const assemble = target.closest('[data-xtl-action="assemble"]');
      if (assemble) { memory.assembled = !memory.assembled; setAssembly(true); return; }
      const tab = target.closest<HTMLButtonElement>('[data-xtl-tab]');
      if (tab) { const scope = tab.closest<HTMLElement>('[data-xtl-tabs-scope]'); if (scope) setTab(scope, tab.getAttribute('data-xtl-tab') || ''); return; }
      const copyButton = target.closest<HTMLButtonElement>('[data-xtl-copy]');
      if (copyButton) {
        const code = copyButton.closest('[data-xtl-panel]')?.querySelector('[data-xtl-code]');
        if (code?.textContent) copy(code.textContent, copyButton, t('constructor.copy'), t('constructor.copied'));
        return;
      }
      const media = target.closest<HTMLButtonElement>('[data-xtl-media="chat"]');
      if (media) { toggleMedia(media); return; }
      const anchor = target.closest<HTMLAnchorElement>('a[href^="#xtl-"]');
      if (anchor) {
        const id = anchor.getAttribute('href')?.slice(1);
        const destination = id ? Array.from(root.querySelectorAll<HTMLElement>('[id]')).find(element => element.id === id) : null;
        if (destination) {
          event.preventDefault();
          destination.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
          destination.tabIndex = -1;
          destination.focus({ preventScroll: true });
        }
      }
    });

    listen(root, 'keydown', event => {
      const keyboard = event as KeyboardEvent;
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;
      const svgPart = target.closest<SVGElement>('.xtl-brick-scene-piece');
      if (svgPart && (keyboard.key === 'Enter' || keyboard.key === ' ')) {
        keyboard.preventDefault();
        openDialog(svgPart.getAttribute('data-xtl-part') || '', svgPart);
        return;
      }
      const tab = target.closest<HTMLButtonElement>('[data-xtl-tab]');
      const scope = tab?.closest<HTMLElement>('[data-xtl-tabs-scope]');
      if (!tab || !scope || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(keyboard.key)) return;
      keyboard.preventDefault();
      const tabs = Array.from(scope.querySelectorAll<HTMLButtonElement>('[data-xtl-tab]'));
      const current = tabs.indexOf(tab);
      const next = keyboard.key === 'Home' ? 0 : keyboard.key === 'End' ? tabs.length - 1 :
        (current + (keyboard.key === 'ArrowRight' || keyboard.key === 'ArrowDown' ? 1 : -1) + tabs.length) % tabs.length;
      setTab(scope, tabs[next].getAttribute('data-xtl-tab') || '', true);
    });

    root.querySelectorAll<HTMLDialogElement>('dialog[data-xtl-dialog]').forEach(dialog => {
      listen(dialog, 'close', () => {
        if (disposing) return;
        if (memory.dialog === dialog.getAttribute('data-xtl-dialog')) memory.dialog = '';
        const trigger = triggers.get(dialog);
        if (trigger?.isConnected) trigger.focus({ preventScroll: true });
      });
    });
    root.querySelectorAll<HTMLImageElement>('[data-xtl-chat-image]').forEach(img => {
      listen(img, 'load', () => {
        const playing = img.closest('[data-xtl-panel]')?.querySelector('[data-xtl-media="chat"][aria-pressed="true"]');
        if (playing) mediaStatus(img, '');
      });
      listen(img, 'error', () => {
        const panel = img.closest('[data-xtl-panel]');
        const button = panel?.querySelector<HTMLButtonElement>('[data-xtl-media="chat"]');
        if (button) { button.setAttribute('aria-pressed', 'false'); button.textContent = t('constructor.mediaPlay'); }
        const poster = img.dataset.xtlPoster;
        if (poster && img.getAttribute('src') !== poster) img.src = poster;
        mediaStatus(img, t('constructor.mediaUnavailable'));
      });
    });
    root.querySelectorAll<HTMLVideoElement>('video').forEach(video => {
      const failed = () => mediaStatus(video, t('constructor.mediaUnavailable'));
      listen(video, 'error', failed);
      video.querySelectorAll('source').forEach(source => listen(source, 'error', failed));
    });

    instances.set(root, {
      deactivate: () => {
        pauseMedia(root);
        memory.dialog = '';
        root.querySelectorAll<HTMLDialogElement>('dialog[open]').forEach(dialog => { triggers.delete(dialog); closeDialog(dialog); });
      },
      dispose: () => {
        disposing = true;
        cleanup.forEach(remove => remove());
        pauseMedia(root);
        root.querySelectorAll<HTMLDialogElement>('dialog[open]').forEach(closeDialog);
      },
    });
    if (memory.dialog) openDialog(memory.dialog);
  }

  window.ExtellaConstructor = { mount, unmount, deactivate };
})();
