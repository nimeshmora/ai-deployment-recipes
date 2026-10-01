'use strict';
const byId = id => document.getElementById(id);
const mascot = byId('mascot');
const bubble = byId('bubble');
const photo = mascot ? mascot.querySelector('.photo') : null;

/* --- reactive face -------------------------------------------------------
   The page swaps between real photos of Nimesha when they exist. Drop these
   same-origin files into /static and they're used automatically (CSP stays
   clean — img-src 'self'):
     mascot.jpg        neutral / wave  (shipped)
     mascot-happy.jpg  success
     mascot-think.jpg  working
     mascot-oops.jpg   something was blocked
   Any that are missing fall back to the neutral photo; the emoji sticker
   always reacts, so the face is expressive even with a single photo. */
const FRAMES = {wave: 'mascot.png', happy: 'mascot-happy.png', think: 'mascot-think.png', oops: 'mascot-oops.png'};
const available = {wave: true};
Object.entries(FRAMES).forEach(([mood, file]) => {
  if (mood === 'wave') return;
  const probe = new Image();
  probe.onload = () => { available[mood] = true; };
  probe.src = '/static/' + file;
});
// Mood, sticker and speech are cosmetic; text is set via textContent only.
const say = (mood, line) => {
  if (mascot) mascot.dataset.mood = mood;
  if (photo) photo.src = '/static/' + FRAMES[available[mood] ? mood : 'wave'];
  if (bubble && line) bubble.textContent = line;
};

// Mock replies are near-instant, so hold the "thinking" face long enough to see.
const sleep = ms => new Promise(r => setTimeout(r, ms));
const THINK_MS = 650;
const holdThink = async since => { const e = performance.now() - since; if (e < THINK_MS) await sleep(THINK_MS - e); };

/* --- health banner -------------------------------------------------------- */
fetch('/health/ready', {signal: AbortSignal.timeout(5000)})
  .then(async response => { if (!response.ok) throw new Error(); return response.json(); })
  .then(data => {
    byId('health').textContent = data.mode === 'mock'
      ? 'kitchen open · mock mode (no model cooking)'
      : 'kitchen open · live mode (provider not checked)';
  })
  .catch(() => {
    byId('health').textContent = 'kitchen is closed — is the app running?';
    byId('health').classList.add('bad');
    say('oops', "Hmm, I can't reach the kitchen. Is the app actually up?");
  });

/* --- chat ----------------------------------------------------------------- */
byId('chat').addEventListener('submit', async event => {
  event.preventDefault();
  byId('send').disabled = true;
  byId('output').textContent = 'thinking…';
  byId('meta').textContent = '';
  say('think', 'Running it through the gauntlet — token, limits, timeouts…');
  const start = performance.now();
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${byId('token').value.trim()}`},
      body: JSON.stringify({message: byId('message').value}),
      signal: AbortSignal.timeout(35000)
    });
    const data = await response.json();
    await holdThink(start);   // let the thinking face register
    // Model output is untrusted: render as plain text, never HTML.
    byId('output').textContent = response.ok ? data.answer : `HTTP ${response.status}: ${data.detail}`;
    byId('meta').textContent = `request ${response.headers.get('x-request-id') || 'unknown'} · ${Math.round(performance.now() - start)} ms` + (data.finish_reason ? ` · finish: ${data.finish_reason}` : '') + (data.finish_reason === 'length' ? ' · output hit the model token limit.' : '');
    if (response.ok) say('happy', 'Boom — it made it past every checkpoint. 🦴');
    else say('oops', `Stopped at the door (HTTP ${response.status}). That's a safeguard doing its job.`);
  } catch {
    byId('output').textContent = 'the request failed or ran past the browser deadline. check application logs. the upstream service may still be processing the request.';
    say('oops', 'That one timed out or failed — peek at the logs.');
  } finally { byId('send').disabled = false; }
});

/* --- "Prove it yourself": run each safeguard live from the page ----------- */
const token = () => byId('token').value.trim();
const CHAT = '/api/chat';

async function status(opts) {
  const r = await fetch(CHAT, opts);
  return {code: r.status, headers: r.headers};
}

// Each check sends a deliberately wrong (or bursty) request and reports back.
const RUNNERS = {
  c1: {needsToken: false, expect: 401, run: () => status({
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: 'hi'})})},
  c2: {needsToken: false, expect: 401, run: () => status({
    method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer not-the-real-token'}, body: JSON.stringify({message: 'hi'})})},
  c3: {needsToken: true, expect: 415, run: () => status({
    method: 'POST', headers: {'Content-Type': 'text/plain', 'Authorization': `Bearer ${token()}`}, body: JSON.stringify({message: 'hi'})})},
  c4: {needsToken: true, expect: 422, run: () => status({
    method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token()}`}, body: JSON.stringify({message: 'a'.repeat(5000)})})},
  c5: {needsToken: true, expect: 413, run: () => status({
    method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token()}`}, body: '{"message":"' + 'a'.repeat(20000) + '"}'})},
  c6: {needsToken: true, expect: 422, run: () => status({
    method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token()}`}, body: JSON.stringify({message: 'hi', admin: true})})},
};

function setVerdict(id, text, state) {
  const row = document.querySelector(`.check[data-check="${id}"]`);
  if (!row) return;
  const v = row.querySelector('[data-role="v"]');
  v.textContent = text;
  v.className = 'verdict' + (state ? ' ' + state : '');
}

async function runCheck(id) {
  const row = document.querySelector(`.check[data-check="${id}"]`);
  const btn = row.querySelector('.run');
  const def = RUNNERS[id];
  if ((def && def.needsToken || id === 'c7' || id === 'c8') && !token()) {
    setVerdict(id, 'paste your token above first ↑', 'warn');
    say('oops', 'I need your token up top to try that one.');
    return;
  }
  btn.disabled = true;
  setVerdict(id, 'running…', '');
  say('think', 'Checking…');
  const t0 = performance.now();
  try {
    if (id === 'c7') {
      // Rate limit: send a quick burst, sequentially so concurrency never trips first.
      let ok = 0, blocked = 0;
      for (let i = 0; i < 35; i++) {
        const {code} = await status({method: 'POST',
          headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token()}`},
          body: JSON.stringify({message: 'hi'})});
        if (code === 200) ok++; else if (code === 429) blocked++;
      }
      await holdThink(t0);
      if (ok === 0 && blocked === 0) {
        setVerdict(id, 'all 35 came back 401 — the auth gate fires first. Is the token above correct?', 'warn');
        say('oops', 'Those never got past the token gate — paste a valid token up top.');
      } else {
        const pass = blocked >= 1;
        setVerdict(id, `sent 35 fast → ${ok} ok, ${blocked} blocked with 429 ${pass ? '✓ throttled as designed' : '✗'}`, pass ? 'pass' : 'fail');
        say(pass ? 'happy' : 'oops', pass ? 'See? One caller can only go so fast. 🦴' : 'Hm, no throttling — check the limit.');
      }
    } else if (id === 'c8') {
      const {headers} = await status({method: 'POST',
        headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token()}`},
        body: JSON.stringify({message: 'hi'})});
      const want = ['x-request-id', 'content-security-policy', 'x-content-type-options', 'referrer-policy', 'cache-control'];
      const have = want.filter(h => headers.get(h));
      const pass = have.length === want.length;
      await holdThink(t0);
      setVerdict(id, `response carried: ${have.join(', ')} ${pass ? '✓' : '✗ missing ' + want.filter(h => !headers.get(h)).join(', ')}`, pass ? 'pass' : 'fail');
      say(pass ? 'happy' : 'oops', pass ? 'Hardened headers + a request ID to trace it. 🦴' : 'Some headers are missing.');
    } else {
      const {code} = await def.run();
      const pass = code === def.expect;
      await holdThink(t0);
      if (!pass && code === 401 && def.expect !== 401) {
        // Auth is checked before everything else, so a bad token short-circuits
        // to 401 and this gate is never reached.
        setVerdict(id, `got HTTP 401 · expected ${def.expect} — the auth gate fires first. Is the token above correct?`, 'warn');
        say('oops', 'The token gate caught it first — paste a valid token up top.');
      } else {
        setVerdict(id, `got HTTP ${code} · expected ${def.expect} ${pass ? '✓ blocked as designed' : '✗ unexpected'}`, pass ? 'pass' : 'fail');
        say(pass ? 'happy' : 'oops', pass ? 'Blocked exactly as designed. 🦴' : 'That did not behave as expected.');
      }
    }
  } catch {
    setVerdict(id, 'the request failed — is the app running?', 'fail');
    say('oops', 'That request never landed — is the app up?');
  } finally { btn.disabled = false; }
}

document.querySelectorAll('.run').forEach(btn =>
  btn.addEventListener('click', () => runCheck(btn.dataset.check)));

// Live guidance: tell the user, up front, whether they're ready to run checks.
const guide = byId('guide');
function updateGuide() {
  if (!guide) return;
  const ready = token().length > 0;
  guide.dataset.ready = ready ? 'yes' : 'no';
  guide.textContent = ready
    ? '✓ Token set — press any run below to fire a broken request and watch it get stopped.'
    : 'Paste your app token in the box above ↑ to unlock checks 3–8, then press any run.';
}
const tokenInput = byId('token');
if (tokenInput) tokenInput.addEventListener('input', updateGuide);
updateGuide();
