'use strict';
// Nium — ponte entre a interface (chrome://nium) e o C++ (nium_handler.cc).
//   window.niumNative.call('metodo', {params}) -> Promise   (resposta via cr.webUIResponse)
//   window.niumNative.on('evento', fn)                      (avisos do C++ via cr.webUIListenerCallback)
(() => {
  let seq = 0;
  const pending = new Map();
  const listeners = new Map();
  window.cr = window.cr || {};
  window.cr.webUIResponse = (id, ok, value) => {
    const p = pending.get(id);
    if (!p) return;
    pending.delete(id);
    if (ok) p.resolve(value);
    else p.reject(new Error(typeof value === 'string' ? value : 'Falha na ponte do Nium.'));
  };
  window.cr.webUIListenerCallback = (event, ...args) => {
    for (const fn of listeners.get(event) || []) {
      try { fn(...args); } catch (error) { console.error(error); }
    }
  };
  function call(method, params = null) {
    return new Promise((resolve, reject) => {
      if (typeof chrome === 'undefined' || typeof chrome.send !== 'function') {
        reject(new Error('Abra esta página como chrome://nium dentro do Nium.'));
        return;
      }
      const id = 'n' + (++seq);
      pending.set(id, { resolve, reject });
      chrome.send('nium.call', [id, method, params]);
    });
  }
  function on(event, fn) {
    if (!listeners.has(event)) listeners.set(event, new Set());
    listeners.get(event).add(fn);
    return () => listeners.get(event)?.delete(fn);
  }
  window.niumNative = Object.freeze({ call, on });
})();
