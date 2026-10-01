'use strict';
const byId = id => document.getElementById(id);
const CHAT = '/api/chat';
const token = () => byId('token').value.trim();
const sleep = ms => new Promise(r => setTimeout(r, ms));
const guardEl = id => document.querySelector(`.guard[data-check="${id}"]`);

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

// effect: 'blocked' = a bad request should bounce off the gate; 'allowed' = a good one passes through.
const TESTS = {
  c1: {needsToken: false, effect: 'blocked', label: 'no-token request', run: () =>
    status({method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: 'hi'})})
      .then(r => r.code === 401
        ? {state: 'pass', text: 'stopped → HTTP 401 ✓'}
        : {state: 'fail', text: `got HTTP ${r.code}, expected 401`})},

  c5: {needsToken: true, effect: 'blocked', label: '~20 KB body', run: () =>
    status({method: 'POST', headers: auth(), body: '{"message":"' + 'a'.repeat(20000) + '"}'})
      .then(r => report(r.code, 413))},

  c7: {needsToken: true, effect: 'blocked', label: '35 fast requests', run: async () => {
    let ok = 0, blocked = 0;
    for (let i = 0; i < 35; i++) {
      const {code} = await status({method: 'POST', headers: auth(), body: JSON.stringify({message: 'hi'})});
      if (code === 200) ok++; else if (code === 429) blocked++;
    }
    if (ok === 0 && blocked === 0) return {state: 'warn', text: 'all came back 401 — token correct?'};
    return blocked >= 1
      ? {state: 'pass', text: `${ok} through, ${blocked} throttled → 429 ✓`}
      : {state: 'fail', text: `${ok} ok, ${blocked} throttled — no limit hit`};
  }},

  c8: {needsToken: true, effect: 'allowed', label: 'normal request', run: () =>
    status({method: 'POST', headers: auth(), body: JSON.stringify({message: 'hi'})})
      .then(({headers}) => {
        const want = ['x-request-id', 'content-security-policy', 'x-content-type-options', 'referrer-policy', 'cache-control'];
        const missing = want.filter(h => !headers.get(h));
        return missing.length === 0
          ? {state: 'pass', text: 'passed, carrying hardened headers ✓'}
          : {state: 'fail', text: `missing: ${missing.join(', ')}`};
      })},
};

function report(code, expect) {
  if (code === expect) return {state: 'pass', text: `stopped → HTTP ${code} ✓`};
  if (code === 401 && expect !== 401) return {state: 'warn', text: 'got HTTP 401 — the auth gate fires first; token correct?'};
  return {state: 'fail', text: `got HTTP ${code}, expected ${expect}`};
}

// Build the little animated "request → gate" lane inside a result slot.
function buildLane(container) {
  container.textContent = '';
  const mk = (cls, txt) => { const e = document.createElement('span'); e.className = cls; if (txt) e.textContent = txt; return e; };
  const lane = mk('lane');
  const track = mk('track');
  track.appendChild(mk('packet'));
  const gate = mk('gate', '🛡');
  const stamp = mk('stamp');
  lane.append(mk('who', 'request'), track, gate, stamp);
  container.appendChild(lane);
  return {lane, stamp};
}

async function runTest(id) {
  const def = TESTS[id];
  const row = guardEl(id);
  const btn = row.querySelector('.test');
  const res = row.querySelector('[data-role="v"]');
  if (def.needsToken && !token()) { res.textContent = 'paste your token above first ↑'; res.className = 'g-result show warn'; return; }

  btn.disabled = true;
  const {lane, stamp} = buildLane(res);
  res.className = 'g-result show';
  requestAnimationFrame(() => lane.classList.add('sending'));   // packet races toward the gate

  const t0 = performance.now();
  let r;
  try { r = await def.run(); }
  catch { r = {state: 'fail', text: 'the request failed — is the app running?'}; }
  const wait = 850 - (performance.now() - t0);
  if (wait > 0) await sleep(wait);                              // let the race be seen

  lane.classList.remove('sending');
  lane.classList.add(def.effect, r.state);                     // bounce (blocked) or pass (allowed) + colour
  stamp.textContent = (def.label ? def.label + ' ' : '') + r.text;
  stamp.classList.add('pop', r.state);
  btn.disabled = false;
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
