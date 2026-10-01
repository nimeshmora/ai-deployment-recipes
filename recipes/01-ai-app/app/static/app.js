'use strict';
const byId = id => document.getElementById(id);
const CHAT = '/api/chat';
const token = () => byId('token').value.trim();

/* --- health banner -------------------------------------------------------- */
fetch('/health/ready', {signal: AbortSignal.timeout(5000)})
  .then(async r => { if (!r.ok) throw new Error(); return r.json(); })
  .then(d => { byId('health').textContent = d.mode === 'mock'
      ? 'mock mode · no model called'
      : 'live mode · provider not checked'; })
  .catch(() => { const h = byId('health'); h.textContent = 'app not ready'; h.classList.add('bad'); });

/* --- token guidance ------------------------------------------------------- */
const guide = byId('guide');
function updateGuide() {
  const ready = token().length > 0;
  guide.dataset.ready = ready ? 'yes' : 'no';
  guide.textContent = ready
    ? '✓ Token set — run any test, or send a request.'
    : 'Paste your token above to unlock the live tests.';
}
byId('token').addEventListener('input', updateGuide);
updateGuide();

/* --- live safeguard tests ------------------------------------------------- */
async function status(opts) {
  const r = await fetch(CHAT, opts);
  return {code: r.status, headers: r.headers};
}
const auth = () => ({'Content-Type': 'application/json', 'Authorization': `Bearer ${token()}`});

const TESTS = {
  // Authentication: no token at all must be rejected. Needs no valid token.
  c1: {needsToken: false, label: 'sent a request with no token', run: () =>
    status({method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: 'hi'})})
      .then(r => r.code === 401
        ? {state: 'pass', text: `got HTTP 401 ✓ blocked as designed`}
        : {state: 'fail', text: `got HTTP ${r.code} · expected 401`})},

  // Oversized body: > 16 KB is dropped before parsing. Needs a valid token.
  c5: {needsToken: true, label: 'sent a ~20 KB body (limit is 16 KB)', run: () =>
    status({method: 'POST', headers: auth(), body: '{"message":"' + 'a'.repeat(20000) + '"}'})
      .then(r => report(r.code, 413))},

  // Rate limit: a quick burst past the budget must get throttled. Needs a valid token.
  c7: {needsToken: true, label: 'sent 35 requests fast (budget 30/min)', run: async () => {
    let ok = 0, blocked = 0;
    for (let i = 0; i < 35; i++) {
      const {code} = await status({method: 'POST', headers: auth(), body: JSON.stringify({message: 'hi'})});
      if (code === 200) ok++; else if (code === 429) blocked++;
    }
    if (ok === 0 && blocked === 0) return {state: 'warn', text: 'all came back 401 — is the token correct?'};
    return blocked >= 1
      ? {state: 'pass', text: `${ok} ok, ${blocked} throttled with 429 ✓`}
      : {state: 'fail', text: `${ok} ok, ${blocked} throttled — no limit hit`};
  }},

  // Security headers: a normal response must carry the hardened set. Needs a valid token.
  c8: {needsToken: true, label: 'inspected a normal response', run: () =>
    status({method: 'POST', headers: auth(), body: JSON.stringify({message: 'hi'})})
      .then(({headers}) => {
        const want = ['x-request-id', 'content-security-policy', 'x-content-type-options', 'referrer-policy', 'cache-control'];
        const missing = want.filter(h => !headers.get(h));
        return missing.length === 0
          ? {state: 'pass', text: `all present: ${want.join(', ')} ✓`}
          : {state: 'fail', text: `missing: ${missing.join(', ')}`};
      })},
};

// For token-gated checks, a 401 means the auth gate fired first — explain, don't just "fail".
function report(code, expect) {
  if (code === expect) return {state: 'pass', text: `got HTTP ${code} ✓ blocked as designed`};
  if (code === 401 && expect !== 401) return {state: 'warn', text: `got HTTP 401 — the auth gate fires first; is the token correct?`};
  return {state: 'fail', text: `got HTTP ${code} · expected ${expect}`};
}

function setResult(id, text, state) {
  const row = document.querySelector(`.guard[data-check="${id}"]`);
  const el = row.querySelector('[data-role="v"]');
  el.textContent = (TESTS[id].label ? TESTS[id].label + ' → ' : '') + text;
  el.className = 'g-result show ' + state;
}

async function runTest(id) {
  const def = TESTS[id];
  const btn = document.querySelector(`.guard[data-check="${id}"] .test`);
  if (def.needsToken && !token()) { setResult(id, 'paste your token above first ↑', 'warn'); return; }
  btn.disabled = true;
  setResult(id, 'running…', 'run');
  try { const r = await def.run(); setResult(id, r.text, r.state); }
  catch { setResult(id, 'the request failed — is the app running?', 'fail'); }
  finally { btn.disabled = false; }
}
document.querySelectorAll('.test').forEach(b => b.addEventListener('click', () => runTest(b.dataset.check)));

/* --- try a real request --------------------------------------------------- */
byId('send').addEventListener('click', async () => {
  if (!token()) { byId('output').textContent = 'paste your token above first ↑'; return; }
  byId('send').disabled = true;
  byId('output').textContent = 'sending…';
  byId('meta').textContent = '';
  const start = performance.now();
  try {
    const r = await fetch(CHAT, {method: 'POST', headers: auth(),
      body: JSON.stringify({message: byId('message').value || 'Hello'}), signal: AbortSignal.timeout(35000)});
    const data = await r.json();
    // Model output is untrusted: render as plain text, never HTML.
    byId('output').textContent = r.ok
      ? data.answer + '\n\n— your request passed every checkpoint.'
      : `HTTP ${r.status}: ${data.detail}`;
    byId('meta').textContent = `request ${r.headers.get('x-request-id') || 'unknown'} · ${Math.round(performance.now() - start)} ms`
      + (data.finish_reason ? ` · finish: ${data.finish_reason}` : '');
  } catch {
    byId('output').textContent = 'the request failed or exceeded the browser deadline. check the app logs.';
  } finally { byId('send').disabled = false; }
});
