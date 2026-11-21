const $ = (s) => document.querySelector(s);
const el = (tag, props = {}, ...kids) => { const e = document.createElement(tag); Object.assign(e, props); e.append(...kids); return e; };
let KEY = sessionStorage.getItem('key') || '';
const view = $('#view'), msg = $('#msg');
const say = (t, err = false) => { msg.textContent = t || ''; msg.className = err ? 'err' : ''; };

async function api(path, opts = {}) {
  const headers = { 'X-API-Key': KEY };
  let body = opts.body;
  if (body && !(body instanceof FormData)) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(body); }
  const r = await fetch(path, { method: opts.method || 'GET', headers, body });
  if (r.status === 401) { lock(); throw new Error('Wrong API key'); }
  if (!r.ok) { let t = await r.text(); try { t = JSON.parse(t).detail || t; } catch (e) {} throw new Error(typeof t === 'string' ? t : JSON.stringify(t)); }
  return r.json();
}
const guard = (fn) => async (...a) => { say(''); try { await fn(...a); } catch (e) { say(e.message, true); } };

function lock() { sessionStorage.removeItem('key'); KEY = ''; $('#nav').hidden = $('#logout').hidden = true; $('#login').hidden = false; view.replaceChildren(); }
$('#go').onclick = () => { KEY = $('#key').value.trim(); sessionStorage.setItem('key', KEY); start(); };
$('#key').onkeydown = (e) => { if (e.key === 'Enter') $('#go').click(); };
$('#logout').onclick = lock;

const TABS = { Approvals: approvals, Skills: skillsView, Chat: chatView, Knowledge: knowledge, Persona: persona, History: history };
function start() {
  $('#login').hidden = true; $('#nav').hidden = $('#logout').hidden = false;
  const nav = $('#nav'); nav.replaceChildren();
  for (const [name, fn] of Object.entries(TABS)) {
    const b = el('button', { textContent: name });
    b.onclick = guard(async () => { [...nav.children].forEach((x) => x.classList.remove('on')); b.classList.add('on'); view.replaceChildren(); await fn(); });
    nav.append(b);
  }
  nav.children[1].click();
}

function resultCard(run, onDone) {
  const ta = el('textarea', { value: run.output, style: 'min-height:220px' });
  const card = el('div', { className: 'card' }, ta);
  if (run.sources && run.sources.length) card.append(el('div', { className: 'mut', textContent: 'Used notes from: ' + run.sources.join(', ') }));
  const good = el('button', { textContent: 'Good: remember this style' });
  good.onclick = guard(async () => { await api(`/runs/${run.run_id}/feedback`, { method: 'POST', body: { action: 'accept', edited: ta.value } }); say('Saved. Future drafts will learn from this.'); });
  const copy = el('button', { className: 'ghost', textContent: 'Copy' });
  copy.onclick = () => navigator.clipboard.writeText(ta.value).then(() => say('Copied'));
  const drop = el('button', { className: 'ghost', textContent: 'Discard' });
  drop.onclick = guard(async () => { await api(`/runs/${run.run_id}/feedback`, { method: 'POST', body: { action: 'reject' } }); card.remove(); });
  card.append(el('div', { className: 'row' }, good, copy, drop));
  return card;
}

async function skillsView() {
  const list = await api('/skills');
  const pick = el('select'); list.forEach((s) => pick.append(el('option', { value: s.name, textContent: s.title })));
  const form = el('div'), out = el('div');
  const draw = () => {
    form.replaceChildren(); out.replaceChildren();
    const s = list.find((x) => x.name === pick.value);
    form.append(el('p', { className: 'mut', textContent: s.description || '' }));
    const fields = {};
    for (const i of s.inputs) {
      let f;
      if (i.type === 'textarea') f = el('textarea');
      else if (i.type === 'select') { f = el('select'); (i.options || []).forEach((o) => f.append(el('option', { value: o, textContent: o }))); }
      else f = el('input');
      fields[i.name] = f;
      form.append(el('label', { textContent: i.label || i.name }), f);
    }
    const run = el('button', { textContent: 'Draft it' });
    run.onclick = guard(async () => {
      const inputs = {}; for (const k in fields) inputs[k] = fields[k].value;
      run.disabled = true; say('Thinking...');
      try { const r = await api('/run/' + s.name, { method: 'POST', body: { inputs } }); out.replaceChildren(resultCard(r)); say(''); }
      finally { run.disabled = false; }
    });
    form.append(el('div', { className: 'row' }, run));
  };
  pick.onchange = draw; view.append(el('h2', { textContent: 'Run a skill' }), pick, form, out); draw();
}

async function approvals() {
  const items = await api('/pending');
  view.append(el('h2', { textContent: 'Emails waiting for your approval' }));
  if (!items.length) view.append(el('p', { className: 'mut', textContent: 'Nothing pending. Drafts from the email automation appear here.' }));
  for (const it of items) {
    const ta = el('textarea', { value: it.draft, style: 'min-height:200px' });
    const card = el('div', { className: 'card' },
      el('div', { className: 'mut', textContent: `${it.sender} | ${it.subject} | ${it.category}` }),
      el('pre', { className: 'mut', textContent: (it.body || '').slice(0, 600) }), ta);
    if ((it.sources || []).length) card.append(el('div', { className: 'mut', textContent: 'Used notes from: ' + it.sources.join(', ') }));
    const act = (action) => guard(async () => { await api('/approve/' + it.thread_id, { method: 'POST', body: { action, edited: ta.value } }); card.remove(); say(action === 'approve' ? 'Approved' : 'Rejected'); });
    const yes = el('button', { textContent: 'Approve and send' }); yes.onclick = act('approve');
    const no = el('button', { className: 'ghost', textContent: 'Reject' }); no.onclick = act('reject');
    card.append(el('div', { className: 'row' }, yes, no)); view.append(card);
  }
}

async function chatView() {
  const hist = [], box = el('div');
  const input = el('textarea', { style: 'min-height:70px', placeholder: 'Ask anything about your work, clients, past projects...' });
  const send = el('button', { textContent: 'Send' });
  const add = (role, text, src) => { const b = el('div', { className: 'bubble ' + role, textContent: text }); if (src && src.length) b.append(el('div', { className: 'mut', textContent: 'Sources: ' + src.join(', ') })); box.append(b); };
  send.onclick = guard(async () => {
    const m = input.value.trim(); if (!m) return; input.value = ''; add('user', m); send.disabled = true;
    try { const r = await api('/chat', { method: 'POST', body: { message: m, history: hist.slice(-10) } }); hist.push({ role: 'user', content: m }, { role: 'assistant', content: r.answer }); add('assistant', r.answer, r.sources); }
    finally { send.disabled = false; }
  });
  view.append(el('h2', { textContent: 'Chat with your clone' }), box, input, el('div', { className: 'row' }, send));
}

async function knowledge() {
  const list = el('div');
  const refresh = guard(async () => {
    const items = await api('/knowledge'); list.replaceChildren();
    if (!items.length) list.append(el('p', { className: 'mut', textContent: 'Empty. Upload your CV, project write-ups, pricing, past replies.' }));
    for (const s of items) {
      const del = el('button', { className: 'danger', textContent: 'Delete' });
      del.onclick = guard(async () => { await api('/knowledge/' + encodeURIComponent(s.source), { method: 'DELETE' }); refresh(); });
      list.append(el('div', { className: 'row' }, el('span', { textContent: `${s.source} (${s.chunks} chunks)` }), del));
    }
  });
  const file = el('input', { type: 'file', multiple: true, accept: '.pdf,.md,.txt,.csv,.json' });
  const up = el('button', { textContent: 'Upload' });
  up.onclick = guard(async () => {
    const fd = new FormData(); [...file.files].forEach((f) => fd.append('upload', f)); if (!file.files.length) return;
    say('Indexing...'); const r = await api('/ingest/files', { method: 'POST', body: fd });
    say(r.map((x) => x.error ? `${x.file}: ${x.error}` : `${x.file}: ${x.chunks} chunks`).join(' | ')); file.value = ''; refresh();
  });
  const name = el('input', { placeholder: 'Name, e.g. pricing-2026' }), text = el('textarea', { placeholder: 'Or paste text here' });
  const save = el('button', { textContent: 'Add text' });
  save.onclick = guard(async () => { if (!name.value || !text.value) return; await api('/ingest', { method: 'POST', body: { source: name.value, text: text.value } }); name.value = text.value = ''; refresh(); });
  view.append(el('h2', { textContent: 'Knowledge' }), el('p', { className: 'mut', textContent: 'Do not upload credentials or unredacted client data.' }), file, el('div', { className: 'row' }, up), name, text, el('div', { className: 'row' }, save), el('h3', { textContent: 'Indexed' }), list);
  refresh();
}

async function persona() {
  const p = await api('/persona'); const ta = el('textarea', { value: p.persona, style: 'min-height:320px' });
  const save = el('button', { textContent: 'Save' });
  save.onclick = guard(async () => { await api('/persona', { method: 'PUT', body: { persona: ta.value } }); say('Saved'); });
  view.append(el('h2', { textContent: 'Persona' }), el('p', { className: 'mut', textContent: 'Who you are, your voice and hard rules. Every draft starts from this.' }), ta, el('div', { className: 'row' }, save));
}

async function history() {
  const rows = await api('/runs'); const t = el('table');
  t.append(el('tr', {}, ...['When', 'Skill', 'Status'].map((h) => el('th', { textContent: h }))));
  for (const r of rows) t.append(el('tr', {}, el('td', { textContent: new Date(r.ts * 1000).toLocaleString() }), el('td', { textContent: r.skill }), el('td', { textContent: r.status })));
  view.append(el('h2', { textContent: 'History' }), t);
}

if (KEY) start();
