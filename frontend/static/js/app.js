'use strict';
/* Task Manager SPA — vanilla JS, hash routing. All user text is escaped via esc(). */
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const getCookie = n => (document.cookie.split('; ').find(r => r.startsWith(n + '=')) || '').split('=')[1] || '';
const S = {user: null, tab: 'all', page: 1, q: '', priority: '', status: '', category: '', sort: 'due_date'};
const cache = {};

async function api(path, {method = 'GET', body} = {}) {
  const headers = {'Content-Type': 'application/json'};
  if (method !== 'GET') headers['X-CSRFToken'] = getCookie('csrftoken');
  const r = await fetch('/api' + path, {method, headers, credentials: 'same-origin', body: body ? JSON.stringify(body) : undefined});
  if (r.status === 204) return null;
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(data.error?.message || 'Request failed'); e.status = r.status; e.details = data.error?.details; throw e; }
  return data;
}
function fmtErr(e) {
  if (e.details && typeof e.details === 'object')
    return Object.entries(e.details).map(([k, v]) => `${k}: ${[].concat(v).join(' ')}`).join(' | ');
  return e.message;
}
const setView = h => { $('#view').innerHTML = h; };
const errorBox = e => `<p class="state error" role="alert">${esc(e.message)}</p>`;
const empty = t => `<p class="state">${t}</p>`;
const fld = (l, n, v = '', t = 'text', x = '') => `<label>${l}<input name="${n}" type="${t}" value="${esc(v)}" ${x}></label>`;
const area = (l, n, v = '') => `<label>${l}<textarea name="${n}" rows="3" maxlength="2000">${esc(v)}</textarea></label>`;
const sel = (l, n, opts, v) => `<label>${l}<select name="${n}">${opts.map(([a, b]) => `<option value="${a}" ${String(a) === String(v) ? 'selected' : ''}>${b}</option>`).join('')}</select></label>`;
const PRI = [['low','Low'],['medium','Medium'],['high','High']];
const STAT = [['todo','To do'],['in_progress','In progress'],['done','Done']];

/* ---------- theme ---------- */
function applyTheme(t) { document.documentElement.dataset.theme = t; localStorage.setItem('theme', t); }
applyTheme(localStorage.getItem('theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

/* ---------- modal ---------- */
function modal(title, body, onSubmit) {
  const d = document.createElement('dialog');
  d.innerHTML = `<form novalidate><h2>${title}</h2>${body}<p class="err" role="alert"></p><div class="row end"><button type="button" class="btn">Cancel</button><button class="btn primary">Save</button></div></form>`;
  document.body.append(d); d.showModal();
  d.onclose = () => d.remove();
  $('button[type=button]', d).onclick = () => d.close();
  $('form', d).onsubmit = async e => {
    e.preventDefault();
    try { await onSubmit(Object.fromEntries(new FormData(e.target))); d.close(); }
    catch (err) { $('.err', d).textContent = fmtErr(err); }
  };
}

/* ---------- shell / reminders ---------- */
function shell(route) {
  const links = ['dashboard', 'tasks', 'goals'].map(r => `<a href="#/${r}" ${route === r || (r === 'goals' && route === 'goal') ? 'aria-current="page"' : ''}>${r[0].toUpperCase() + r.slice(1)}</a>`).join('');
  $('#nav').innerHTML = `<a class="brand" href="#/dashboard">✅ Task Manager</a>` + (S.user
    ? `<button id="bell" class="btn" aria-label="Reminders">🔔 <span id="bc">0</span></button><button id="th" class="btn" aria-label="Toggle dark mode">🌓</button><button id="lo" class="btn">Logout</button><nav aria-label="Main">${links}</nav>`
    : `<button id="th" class="btn" aria-label="Toggle dark mode">🌓</button>`);
  $('#th').onclick = () => applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  if (S.user) {
    $('#lo').onclick = async () => { await api('/auth/logout/', {method: 'POST'}).catch(() => {}); S.user = null; location.hash = '#/login'; };
    $('#bell').onclick = showReminders;
  }
}
async function reminders() {
  try { cache.rem = await api('/reminders/'); const c = $('#bc'); if (c) c.textContent = cache.rem.length; } catch {}
}
function showReminders() {
  const d = document.createElement('dialog');
  const r = cache.rem || [];
  d.innerHTML = `<h2>Reminders</h2>${r.length ? `<ul class="list">${r.map(x => `<li class="item"><span class="grow">${esc(x.title)}</span><span class="${x.overdue ? 'od' : ''}">${x.overdue ? 'Overdue · ' : 'Due today · '}${x.due_date}</span></li>`).join('')}</ul>` : empty('Nothing due. 🎉')}<div class="row end"><button class="btn">Close</button></div>`;
  document.body.append(d); d.showModal(); d.onclose = () => d.remove(); $('button', d).onclick = () => d.close();
}

/* ---------- auth pages ---------- */
function authPage(route) {
  const reg = route === 'register';
  setView(`<form class="card auth" novalidate><h1>${reg ? 'Create account' : 'Log in'}</h1>${fld('Username', 'username', '', 'text', 'required autocomplete="username"')}${reg ? fld('Email', 'email', '', 'email', 'required autocomplete="email"') : ''}${fld('Password', 'password', '', 'password', `required minlength="8" autocomplete="${reg ? 'new' : 'current'}-password"`)}<p class="err" role="alert"></p><button class="btn primary" style="width:100%">${reg ? 'Register' : 'Login'}</button><p><a href="#/${reg ? 'login' : 'register'}">${reg ? 'Have an account? Log in' : 'New here? Register'}</a></p></form>`);
  $('form').onsubmit = async e => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(e.target)), err = $('.err');
    if (d.username.trim().length < 3) return err.textContent = 'Username must be at least 3 characters.';
    if (reg && !/^\S+@\S+\.\S+$/.test(d.email)) return err.textContent = 'Enter a valid email.';
    if (d.password.length < 8) return err.textContent = 'Password must be at least 8 characters.';
    try { S.user = await api(reg ? '/auth/register/' : '/auth/login/', {method: 'POST', body: d}); location.hash = '#/dashboard'; }
    catch (x) { err.textContent = fmtErr(x); }
  };
}

/* ---------- tasks ---------- */
const taskRow = t => { cache[t.id] = t; return `<li class="item ${t.status === 'done' ? 'done' : ''}" data-id="${t.id}">
  <input type="checkbox" class="chk" aria-label="Mark ${esc(t.title)} done" ${t.status === 'done' ? 'checked' : ''}>
  <div class="grow"><strong>${esc(t.title)}</strong><div class="meta"><span class="badge p-${t.priority}">${t.priority}</span>${t.category ? `<span class="badge">${esc(t.category)}</span>` : ''}<span class="badge">${t.status.replace('_', ' ')}</span>${t.due_date ? `<span class="${t.is_overdue ? 'od' : ''}">Due ${t.due_date}</span>` : ''}${t.recurrence !== 'none' ? `<span>↻ ${t.recurrence}</span>` : ''}${t.goal_title ? `<span>🎯 ${esc(t.goal_title)}</span>` : ''}</div></div>
  <button class="btn sm" data-act="edit">Edit</button><button class="btn sm danger" data-act="del">Delete</button></li>`; };

function bindTasks(root, reload) {
  root.onclick = async e => {
    const li = e.target.closest('li[data-id]'); if (!li) return;
    const t = cache[li.dataset.id];
    try {
      if (e.target.dataset.act === 'edit') taskForm(t, reload);
      else if (e.target.dataset.act === 'del') { if (confirm('Delete this task?')) { await api(`/tasks/${t.id}/`, {method: 'DELETE'}); reload(); } }
      else if (e.target.classList.contains('chk')) { await api(`/tasks/${t.id}/`, {method: 'PATCH', body: {status: e.target.checked ? 'done' : 'todo'}}); reload(); }
    } catch (x) { alert(fmtErr(x)); reload(); }
  };
}

async function taskForm(t = {}, done = () => {}) {
  const goals = (await api('/goals/?page_size=100')).results;
  modal(t.id ? 'Edit task' : 'New task',
    fld('Title', 'title', t.title, 'text', 'required maxlength="200"') + area('Description', 'description', t.description) +
    fld('Due date', 'due_date', t.due_date || '', 'date') + sel('Priority', 'priority', PRI, t.priority || 'medium') +
    fld('Category / tag', 'category', t.category, 'text', 'maxlength="50"') + sel('Status', 'status', STAT, t.status || 'todo') +
    sel('Repeats', 'recurrence', [['none','Never'],['daily','Daily'],['weekly','Weekly'],['custom','Custom']], t.recurrence || 'none') +
    fld('Custom interval (days)', 'recurrence_interval', t.recurrence_interval || '', 'number', 'min="1"') +
    sel('Goal', 'goal', [['', '— none —'], ...goals.map(g => [g.id, esc(g.title)])], t.goal ?? ''),
    async d => {
      if (!d.title.trim()) throw new Error('Title is required.');
      if (d.recurrence === 'custom' && !(+d.recurrence_interval > 0)) throw new Error('Enter a custom interval of 1+ days.');
      const body = {...d, due_date: d.due_date || null, goal: d.goal || null, recurrence_interval: d.recurrence === 'custom' ? +d.recurrence_interval : null};
      await api(t.id ? `/tasks/${t.id}/` : '/tasks/', {method: t.id ? 'PATCH' : 'POST', body});
      done();
    });
}

async function tasks() {
  const p = new URLSearchParams({page: S.page, ordering: S.sort});
  if (S.tab !== 'all') p.set('view', S.tab);
  [['search', S.q], ['priority', S.priority], ['status', S.status], ['category', S.category]].forEach(([k, v]) => v && p.set(k, v));
  const res = await api('/tasks/?' + p);
  setView(`<div class="row between"><h1>Tasks</h1><button id="new" class="btn primary">+ New task</button></div>
   <div class="row" role="tablist">${['all','today','upcoming','overdue'].map(t => `<button class="btn ${S.tab === t ? 'on' : ''}" data-tab="${t}" role="tab" aria-selected="${S.tab === t}">${t[0].toUpperCase() + t.slice(1)}</button>`).join('')}</div>
   <div class="card"><div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr))">
     <label>Search<input id="q" type="search" value="${esc(S.q)}"></label>
     ${sel('Priority', 'priority', [['', 'Any'], ...PRI], S.priority)}${sel('Status', 'status', [['', 'Any'], ...STAT], S.status)}
     <label>Tag<input id="cat" value="${esc(S.category)}"></label>
     ${sel('Sort', 'sort', [['due_date','Due date'],['-priority_rank','Priority'],['-created_at','Newest'],['title','Title']], S.sort)}</div></div>
   <div class="card">${res.results.length ? `<ul class="list" id="tl">${res.results.map(taskRow).join('')}</ul>` : empty('No tasks here yet. Create one to get started.')}
   <div class="row between"><button class="btn sm" id="prev" ${res.previous ? '' : 'disabled'}>← Prev</button><span>Page ${S.page} · ${res.count} total</span><button class="btn sm" id="next" ${res.next ? '' : 'disabled'}>Next →</button></div></div>`);
  const reload = () => { render(); };
  $('#new').onclick = () => taskForm({}, reload);
  document.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => { S.tab = b.dataset.tab; S.page = 1; render(); });
  const bind = (id, key, ev = 'change') => $(id).addEventListener(ev, e => { S[key] = e.target.value; S.page = 1; render(); });
  bind('#q', 'q'); bind('[name=priority]', 'priority'); bind('[name=status]', 'status'); bind('#cat', 'category'); bind('[name=sort]', 'sort');
  $('#prev').onclick = () => { S.page--; render(); }; $('#next').onclick = () => { S.page++; render(); };
  if ($('#tl')) bindTasks($('#tl'), reload);
}

/* ---------- dashboard ---------- */
async function dashboard() {
  const d = await api('/dashboard/');
  const max = Math.max(1, ...d.weekly.map(w => w.count));
  setView(`<h1>Hello, ${esc(S.user.username)} 👋</h1>
  <div class="grid"><div class="card"><div class="stat ${d.overdue_count ? 'od' : ''}">${d.overdue_count}</div>Overdue tasks</div>
   <div class="card"><div class="stat">🔥 ${d.streak}</div>Day streak</div>
   <div class="card"><div class="stat">${d.today_tasks.filter(t => t.status === 'done').length}/${d.today_tasks.length}</div>Done today</div></div>
  <div class="card"><div class="row between"><h2>Today</h2><button id="new" class="btn sm primary">+ Task</button></div>${d.today_tasks.length ? `<ul class="list" id="tl">${d.today_tasks.map(taskRow).join('')}</ul>` : empty('Nothing due today.')}</div>
  <div class="card"><h2>Active goals</h2>${d.active_goals.length ? d.active_goals.map(g => `<p><a href="#/goal/${g.id}">${esc(g.title)}</a> — ${g.progress.percent}%</p><div class="bar" role="progressbar" aria-valuenow="${g.progress.percent}" aria-valuemin="0" aria-valuemax="100"><i style="width:${g.progress.percent}%"></i></div>`).join('') : empty('No active goals. Create one on the Goals page.')}</div>
  <div class="card"><h2>Completed this week</h2><div class="chart">${d.weekly.map(w => `<div><span>${w.count}</span><i style="height:${w.count / max * 80}%"></i>${new Date(w.date + 'T00:00').toLocaleDateString(undefined, {weekday: 'short'})}</div>`).join('')}</div></div>`);
  $('#new').onclick = () => taskForm({}, render);
  if ($('#tl')) bindTasks($('#tl'), render);
}

/* ---------- goals ---------- */
function goalForm(g = {}, done) {
  modal(g.id ? 'Edit goal' : 'New goal',
    fld('Title', 'title', g.title, 'text', 'required maxlength="200"') + area('Description', 'description', g.description) +
    fld('Target date', 'target_date', g.target_date || '', 'date') + fld('Category', 'category', g.category, 'text', 'maxlength="50"') +
    sel('Status', 'status', [['active','Active'],['paused','Paused'],['completed','Completed']], g.status || 'active'),
    async d => {
      if (!d.title.trim()) throw new Error('Title is required.');
      await api(g.id ? `/goals/${g.id}/` : '/goals/', {method: g.id ? 'PATCH' : 'POST', body: {...d, target_date: d.target_date || null}});
      done();
    });
}
const bar = p => `<div class="bar" role="progressbar" aria-valuenow="${p}" aria-valuemin="0" aria-valuemax="100"><i style="width:${p}%"></i></div>`;

async function goals() {
  const res = await api('/goals/?page_size=50');
  setView(`<div class="row between"><h1>Goals</h1><button id="new" class="btn primary">+ New goal</button></div>${res.results.length ? res.results.map(g => `<a class="card" style="display:block;color:inherit;text-decoration:none" href="#/goal/${g.id}"><div class="row between"><strong>${esc(g.title)}</strong><span class="badge">${g.status}</span></div><div class="meta">${g.category ? esc(g.category) + ' · ' : ''}${g.target_date ? 'Target ' + g.target_date : 'No target date'} · ${g.progress.done}/${g.progress.total} items</div>${bar(g.progress.percent)}</a>`).join('') : empty('No goals yet. Set your first goal!')}`);
  $('#new').onclick = () => goalForm({}, render);
}

async function goalDetail(_, id) {
  const [g, tk] = await Promise.all([api(`/goals/${id}/`), api(`/tasks/?goal=${id}&page_size=100`)]);
  setView(`<p><a href="#/goals">← Goals</a></p><div class="card"><div class="row between"><h1>${esc(g.title)}</h1><span class="badge">${g.status}</span></div><p>${esc(g.description)}</p>${bar(g.progress.percent)}<p>${g.progress.percent}% (${g.progress.done}/${g.progress.total})</p><div class="row"><button id="edit" class="btn">Edit</button><button id="del" class="btn danger">Delete</button></div></div>
  <div class="card"><div class="row between"><h2>Milestones</h2><button id="addm" class="btn sm primary">+ Milestone</button></div>${g.milestones.length ? `<ul class="list" id="ml">${g.milestones.map(m => `<li class="item" data-mid="${m.id}"><input type="checkbox" class="chk" aria-label="Toggle ${esc(m.title)}" ${m.is_done ? 'checked' : ''}><span class="grow">${esc(m.title)}${m.due_date ? ` <small class="meta">due ${m.due_date}</small>` : ''}</span><button class="btn sm danger" data-act="del">Delete</button></li>`).join('')}</ul>` : empty('No milestones yet.')}</div>
  <div class="card"><div class="row between"><h2>Linked tasks</h2><button id="addt" class="btn sm primary">+ Task</button></div>${tk.results.length ? `<ul class="list" id="tl">${tk.results.map(taskRow).join('')}</ul>` : empty('No tasks linked to this goal.')}</div>`);
  $('#edit').onclick = () => goalForm(g, render);
  $('#del').onclick = async () => { if (confirm('Delete this goal? Tasks are kept but unlinked.')) { await api(`/goals/${id}/`, {method: 'DELETE'}); location.hash = '#/goals'; } };
  $('#addt').onclick = () => taskForm({goal: +id}, render);
  $('#addm').onclick = () => modal('New milestone', fld('Title', 'title', '', 'text', 'required maxlength="200"') + fld('Due date', 'due_date', '', 'date'),
    async d => { if (!d.title.trim()) throw new Error('Title is required.'); await api('/milestones/', {method: 'POST', body: {goal: +id, title: d.title, due_date: d.due_date || null}}); render(); });
  if ($('#ml')) $('#ml').onclick = async e => {
    const li = e.target.closest('li[data-mid]'); if (!li) return;
    try {
      if (e.target.dataset.act === 'del') await api(`/milestones/${li.dataset.mid}/`, {method: 'DELETE'});
      else if (e.target.classList.contains('chk')) await api(`/milestones/${li.dataset.mid}/`, {method: 'PATCH', body: {is_done: e.target.checked}});
      else return;
      render();
    } catch (x) { alert(fmtErr(x)); }
  };
  if ($('#tl')) bindTasks($('#tl'), render);
}

/* ---------- router ---------- */
async function render() {
  const [route, arg] = (location.hash.replace(/^#\//, '') || 'dashboard').split('/');
  if (!S.user && !['login', 'register'].includes(route)) { location.hash = '#/login'; return; }
  if (S.user && ['login', 'register'].includes(route)) { location.hash = '#/dashboard'; return; }
  shell(route); setView('<p class="state" role="status">Loading…</p>');
  try { await ({login: authPage, register: authPage, dashboard, tasks, goals, goal: goalDetail}[route] || dashboard)(route, arg); }
  catch (e) { if (e.status === 401) { S.user = null; location.hash = '#/login'; } else setView(errorBox(e)); }
  if (S.user) reminders();
}
addEventListener('hashchange', render);
(async () => {
  await fetch('/api/auth/csrf/', {credentials: 'same-origin'});
  try { S.user = await api('/auth/me/'); } catch { S.user = null; }
  render(); setInterval(() => S.user && reminders(), 60000);
})();
