'use strict';
const $ = s => document.querySelector(s);
const fail = e => { $('#error').textContent = e.message || String(e); };
(async () => {
  try {
    const v = await niumNative.call('version');
    $('#version').textContent = `Nium ${v.nium} · Chromium ${v.chromium}`;
    $('#status').textContent = 'ponte funcionando'; $('#status').classList.add('ok');
    const saved = await niumNative.call('storeGet', { key: 'teste' });
    $('#store-value').textContent = saved?.text || '(nada ainda)';
  } catch (e) { $('#status').textContent = 'sem ponte'; fail(e); }
})();
$('#open-form').addEventListener('submit', e => {
  e.preventDefault();
  niumNative.call('openTab', { url: $('#open-url').value.trim() }).catch(fail);
});
$('#store-form').addEventListener('submit', async e => {
  e.preventDefault();
  try {
    const text = $('#store-text').value;
    await niumNative.call('storeSet', { key: 'teste', value: { text, at: Date.now() } });
    $('#store-value').textContent = text || '(vazio)';
  } catch (err) { fail(err); }
});
