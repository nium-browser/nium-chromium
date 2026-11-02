'use strict';
// Nium — barra lateral com as abas de verdade da janela (TabStripModel do Chromium).
// O C++ manda a lista inteira a cada mudança (evento "nium-tabs"); aqui só desenhamos.
(() => {
  const list = document.getElementById('tabs');
  const status = document.getElementById('status');
  const nodes = new Map(); // id -> elemento da aba (reaproveitado entre atualizações)
  let tabs = [];
  let drag = null;

  const svg = (markup) => {
    const span = document.createElement('span');
    span.innerHTML = markup;
    return span.firstElementChild;
  };
  const CLOSE = '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1.5 1.5l7 7M8.5 1.5l-7 7"/></svg>';

  function call(method, params) {
    return window.niumNative.call(method, params).catch((error) => showStatus(error.message));
  }
  function showStatus(text) {
    status.textContent = text || '';
    status.hidden = !text;
  }

  function makeTab(tab) {
    const el = document.createElement('div');
    el.className = 'tab';
    el.setAttribute('role', 'tab');
    el.dataset.id = tab.id;
    const icon = document.createElement('span');
    icon.className = 'tab-icon';
    const title = document.createElement('span');
    title.className = 'tab-title';
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'tab-close';
    close.title = 'Fechar aba';
    close.append(svg(CLOSE));
    el.append(icon, title, close);
    return el;
  }

  function paintIcon(el, tab) {
    const icon = el.querySelector('.tab-icon');
    const key = tab.loading ? 'loading' : (tab.favicon || 'none');
    if (icon.dataset.key === key) return;
    icon.dataset.key = key;
    icon.replaceChildren();
    if (tab.loading) {
      icon.append(Object.assign(document.createElement('span'), { className: 'spinner' }));
    } else if (tab.favicon) {
      icon.append(Object.assign(document.createElement('img'), { src: tab.favicon, alt: '' }));
    } else {
      icon.append(Object.assign(document.createElement('span'), { className: 'globe' }));
    }
  }

  function render(next) {
    tabs = Array.isArray(next) ? next : [];
    if (drag) return; // não mexe na lista no meio de um arraste; a próxima atualização redesenha
    const seen = new Set();
    const ordered = [];
    let pinnedCount = 0;
    for (const tab of tabs) {
      seen.add(tab.id);
      let el = nodes.get(tab.id);
      if (!el) { el = makeTab(tab); nodes.set(tab.id, el); }
      el.classList.toggle('active', !!tab.active);
      el.classList.toggle('pinned', !!tab.pinned);
      el.setAttribute('aria-selected', tab.active ? 'true' : 'false');
      el.title = tab.title + (tab.url && tab.url !== tab.title ? '\n' + tab.url : '');
      el.querySelector('.tab-title').textContent = tab.title;
      paintIcon(el, tab);
      if (tab.pinned) pinnedCount++;
      ordered.push(el);
    }
    for (const [id, el] of nodes) {
      if (!seen.has(id)) { el.remove(); nodes.delete(id); }
    }
    if (pinnedCount && pinnedCount < ordered.length) {
      const sep = document.createElement('div');
      sep.className = 'separator';
      ordered.splice(pinnedCount, 0, sep);
    }
    list.replaceChildren(...ordered);
    list.querySelector('.tab.active')?.scrollIntoView({ block: 'nearest' });
  }

  // Clique ativa, botão do meio ou o X fecha.
  list.addEventListener('click', (event) => {
    const el = event.target.closest('.tab');
    if (!el || el.dataset.justDragged) return;
    const id = Number(el.dataset.id);
    if (event.target.closest('.tab-close')) call('tabs.close', { id });
    else call('tabs.activate', { id });
  });
  list.addEventListener('auxclick', (event) => {
    const el = event.target.closest('.tab');
    if (el && event.button === 1) { event.preventDefault(); call('tabs.close', { id: Number(el.dataset.id) }); }
  });
  list.addEventListener('mousedown', (event) => { if (event.button === 1) event.preventDefault(); });

  // Arrastar para reordenar: só na vertical, sem sair da barra.
  list.addEventListener('pointerdown', (event) => {
    const el = event.target.closest('.tab');
    if (!el || event.button !== 0 || event.target.closest('.tab-close')) return;
    drag = { el, id: Number(el.dataset.id), startY: event.clientY, moved: false, pointer: event.pointerId };
  });
  window.addEventListener('pointermove', (event) => {
    if (!drag || event.pointerId !== drag.pointer) return;
    const dy = event.clientY - drag.startY;
    if (!drag.moved) {
      if (Math.abs(dy) < 5) return;
      drag.moved = true;
      drag.el.setPointerCapture(event.pointerId);
      drag.el.classList.add('dragging');
      drag.siblings = [...list.querySelectorAll('.tab')].filter((t) => t.classList.contains('pinned') === drag.el.classList.contains('pinned'));
      drag.rects = drag.siblings.map((t) => t.getBoundingClientRect());
      drag.from = drag.siblings.indexOf(drag.el);
    }
    const first = drag.rects[0], last = drag.rects[drag.rects.length - 1], own = drag.rects[drag.from];
    const clamped = Math.max(first.top - own.top, Math.min(last.top - own.top, dy));
    drag.el.style.transform = `translateY(${clamped}px)`;
    const center = own.top + own.height / 2 + clamped;
    let to = drag.siblings.length - 1;
    for (let i = 0; i < drag.rects.length; i++) {
      if (center < drag.rects[i].top + drag.rects[i].height) { to = i; break; }
    }
    drag.to = to;
    const step = own.height + 2;
    drag.siblings.forEach((t, i) => {
      if (t === drag.el) return;
      let shift = 0;
      if (drag.from < to && i > drag.from && i <= to) shift = -step;
      if (drag.from > to && i < drag.from && i >= to) shift = step;
      t.style.transform = shift ? `translateY(${shift}px)` : '';
    });
  });
  const endDrag = (event) => {
    if (!drag || event.pointerId !== drag.pointer) return;
    const d = drag;
    drag = null;
    if (!d.moved) { setTimeout(() => render(tabs), 0); return; } // depois do clique
    d.el.dataset.justDragged = '1';
    setTimeout(() => delete d.el.dataset.justDragged, 0);
    d.el.classList.remove('dragging');
    for (const t of d.siblings) t.style.transform = '';
    const to = d.to ?? d.from;
    if (to !== d.from) {
      // Índice no TabStripModel: as fixadas vêm primeiro.
      const offset = d.el.classList.contains('pinned') ? 0 : tabs.filter((t) => t.pinned).length;
      call('tabs.move', { id: d.id, index: offset + to });
    }
    render(tabs);
  };
  window.addEventListener('pointerup', endDrag);
  window.addEventListener('pointercancel', endDrag);

  document.getElementById('new-tab').addEventListener('click', () => call('tabs.new'));

  window.niumNative.on('nium-tabs', render);
  call('tabs.watch').then(render);
})();
