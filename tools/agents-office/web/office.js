// Agents Office page: the Status, Overview, Chat and Debug panels, the Hall of Fame and the zoom around
// the pixel office that scene.js draws. It polls /api/status while the tab is
// visible; the server only reads status files, so nothing here spends tokens except a sent chat message.
'use strict'
const TOKEN = document.querySelector('meta[name="office-token"]').content
const api = (path, body) => fetch(path, body === undefined ? { headers: { 'x-office-token': TOKEN } }
  : { method: 'POST', headers: { 'x-office-token': TOKEN, 'content-type': 'application/json' }, body: JSON.stringify(body) })

const { STATE_COLOR } = Scene

// ---------- state ----------
let snap = null
let selected = null // { project, id }
const canvas = document.getElementById('office')
const $ = id => document.getElementById(id)
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs)) k === 'class' ? (n.className = v) : k.startsWith('on') ? n.addEventListener(k.slice(2), v) : n.setAttribute(k, v)
  for (const k of kids) n.append(k instanceof Node ? k : document.createTextNode(String(k ?? '')))
  return n
}
const ago = t => { if (!t) return '—'; const s = Math.max(0, (Date.now() - Date.parse(t)) / 1000); return s < 60 ? `${s | 0}s ago` : s < 3600 ? `${(s / 60) | 0}m ago` : `${(s / 3600) | 0}h ago` }
function shown(a) { // a running state that stopped updating long ago is shown as stale
  const live = ['starting', 'thinking', 'working', 'waiting'].includes(a.state)
  return live && Date.now() - Date.parse(a.updatedAt) > (snap?.staleMinutes ?? 10) * 60e3 ? 'stale' : a.state
}
const pill = st => el('span', { class: 'pill', style: `background:${STATE_COLOR[st] || '#888'}` }, st)
const findAgent = () => {
  if (!snap || !selected) return null
  const p = snap.projects.find(x => x.path === selected.project)
  const a = p?.agents.find(x => x.id === selected.id)
  return a ? { p, a } : null
}

// ---------- office view: drawing, clicks and zoom ----------
function draw(t) {
  Scene.render(canvas, snap?.projects ?? [], selected, t)
  applyZoom()
  requestAnimationFrame(draw)
}
canvas.addEventListener('click', ev => {
  const r = canvas.getBoundingClientRect()
  const h = Scene.hitAt((ev.clientX - r.left) * (canvas.width / r.width), (ev.clientY - r.top) * (canvas.height / r.height))
  if (h) { selected = { project: h.project, id: h.id }; show('status') }
})
let zoom = 0 // 0 fits every room in the window width; otherwise screen pixels per art pixel
function applyZoom() {
  const width = zoom ? `${(canvas.width / Scene.S) * zoom}px` : '100%'
  if (canvas.style.width !== width) canvas.style.width = width
  $('zoom-label').textContent = zoom ? `${zoom}x` : 'fit'
}
function zoomBy(step) {
  const now = zoom || Math.round((canvas.clientWidth / (canvas.width / Scene.S)) * 2) / 2
  zoom = Math.min(6, Math.max(1, now + step))
}
$('zoom-in').addEventListener('click', () => zoomBy(0.5))
$('zoom-out').addEventListener('click', () => zoomBy(-0.5))
$('zoom-fit').addEventListener('click', () => { zoom = 0 })
$('view').addEventListener('wheel', ev => { if (ev.ctrlKey) { ev.preventDefault(); zoomBy(ev.deltaY < 0 ? 0.5 : -0.5) } }, { passive: false })

// ---------- Hall of Fame: the subagents that finished last ----------
const FAME = 8
const lasted = a => { const s = Math.max(0, (Date.parse(a.endedAt) - Date.parse(a.startedAt)) / 1000) || 0; return s < 60 ? `${s | 0}s` : `${(s / 60) | 0}m ${(s % 60) | 0}s` }
const short = n => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}k` : String(n))
const tokenLine = t => t && `in ${short(t.input)} · out ${short(t.output)} · cache read ${short(t.cacheRead)} · cache write ${short(t.cacheWrite)}`
function renderFame() {
  const done = (snap?.projects ?? []).flatMap(p => p.agents.filter(a => a.kind !== 'main' && a.state === 'finished' && a.endedAt).map(a => ({ p, a })))
    .sort((x, y) => Date.parse(y.a.endedAt) - Date.parse(x.a.endedAt)).slice(0, FAME)
  const box = $('fame-list'); box.replaceChildren()
  if (!done.length) return box.append(el('p', { class: 'hint' }, 'No subagent has finished yet.'))
  const t = el('table', {}, el('tr', {}, ...['Agent', 'Task', 'Project', 'Took', 'Output', 'Finished'].map(h => el('th', {}, h))))
  for (const { p, a } of done) {
    t.append(el('tr', { class: 'pick', onclick: () => { selected = { project: p.path, id: a.id }; show('status') } },
      el('td', {}, `${a.errorCount ? '' : '★ '}${a.role}`), el('td', {}, a.task || '—'), el('td', {}, p.name), el('td', {}, lasted(a)),
      el('td', {}, a.tokens ? short(a.tokens.output) : '—'), el('td', {}, ago(a.endedAt))))
  }
  box.append(t)
}

// ---------- panels ----------
function kv(pairs) { const d = el('dl', { class: 'kv' }); for (const [k, v] of pairs) if (v !== undefined && v !== null && v !== '') d.append(el('dt', {}, k), el('dd', {}, v)); return d }
function renderStatus() {
  const box = $('tab-status'); box.replaceChildren()
  const f = findAgent()
  if (!f) return box.append(el('p', { class: 'hint' }, 'Click an agent in the office, or a row in Overview.'))
  const { p, a } = f
  const st = shown(a)
  const card = el('div', { class: 'card' }, el('h3', {}, `${a.kind === 'main' ? 'Main agent' : a.role} `, pill(st)))
  card.append(kv([
    ['Project', p.name], ['Role', a.role], ['Task', a.task || (a.kind === 'main' ? '(prompt text hidden: AGENTS_STATUS_PROMPT=on shows it)' : '—')],
    ['Last tool', a.lastTool ? `${a.lastTool.name} ${a.lastTool.summary}${a.lastTool.ok === false ? ' (failed)' : ''}` : '—'],
    ['Waiting for', st === 'waiting' ? a.waitingFor : ''], ['Tools', a.toolCount], ['Errors', a.errorCount],
    ['Last error', a.lastError ? `${a.lastError.message} (${ago(a.lastError.at)})` : ''],
    ['Tokens', tokenLine(a.tokens) || (a.where === 'cloud' ? 'not on this computer' : 'no transcript found')],
    ['Where', a.where], ['Model', a.model], ['Started', ago(a.startedAt)], ['Updated', ago(a.updatedAt)], ['Ended', a.endedAt ? ago(a.endedAt) : ''],
    ['Session', a.sessionId],
  ]))
  if (a.where === 'cloud' && a.link) card.append(el('p', {}, el('a', { href: a.link, target: '_blank', rel: 'noopener' }, 'Open this cloud session')))
  if (a.recentTools?.length) {
    const t = el('table', {}, el('tr', {}, el('th', {}, 'Recent tools'), el('th', {}, ''), el('th', {}, '')))
    for (const r of [...a.recentTools].reverse()) t.append(el('tr', {}, el('td', {}, r.name), el('td', {}, r.summary), el('td', {}, r.ok === false ? 'failed' : ago(r.at))))
    card.append(t)
  }
  box.append(card)
}
function renderOverview() {
  const box = $('tab-overview'); box.replaceChildren()
  for (const p of snap?.projects ?? []) {
    const counts = {}
    for (const a of p.agents) { const s = shown(a); counts[s] = (counts[s] || 0) + 1 }
    const card = el('div', { class: 'card' }, el('h3', {}, p.name), el('div', { class: 'hint' }, p.ok ? `updated ${ago(p.updatedAt)}` : p.error))
    const line = el('p', {}); for (const [s, n] of Object.entries(counts)) line.append(pill(`${s} ${n}`), ' ')
    card.append(line)
    const t = el('table', {})
    for (const a of p.agents) {
      const tr = el('tr', { class: 'pick', onclick: () => { selected = { project: p.path, id: a.id }; show('status') } },
        el('td', {}, a.kind === 'main' ? 'main' : a.role), el('td', {}, pill(shown(a))), el('td', {}, a.lastTool?.name || ''), el('td', {}, ago(a.updatedAt)))
      if (a.where === 'cloud' && a.link) tr.append(el('td', {}, el('a', { href: a.link, target: '_blank', rel: 'noopener', onclick: e => e.stopPropagation() }, 'cloud')))
      t.append(tr)
    }
    card.append(t); box.append(card)
  }
  if (!snap?.projects.length) box.append(el('p', { class: 'hint' }, 'No projects in the list yet. Add one in Debug, or start a session in a kit project.'))
}
function chatTarget() {
  const f = findAgent(); if (!f) return null
  const main = f.a.kind === 'main' ? f.a : f.p.agents.find(x => x.id === f.a.parentId)
  return main ? { p: f.p, a: main } : null
}
function renderChat() {
  const head = $('chat-head'); head.replaceChildren()
  const c = chatTarget()
  const ok = c && c.a.where !== 'cloud'
  $('chat-send').disabled = !ok || chatting; $('open-terminal').disabled = !ok; $('chat-text').disabled = !ok
  if (!c) return head.append(el('p', { class: 'hint' }, 'Select an agent: the chat goes to its session.'))
  if (c.a.where === 'cloud') {
    return head.append(el('div', { class: 'card' }, el('h3', {}, 'Cloud session'), el('p', {}, 'Cloud sessions are not reachable from this computer. '),
      c.a.link ? el('a', { href: c.a.link, target: '_blank', rel: 'noopener' }, 'Open it on claude.ai/code') : el('span', { class: 'hint' }, 'no link recorded')))
  }
  head.append(el('div', { class: 'card' }, el('h3', {}, `${c.p.name} `, pill(shown(c.a))), kv([['Session', c.a.sessionId], ['Updated', ago(c.a.updatedAt)]]),
    ['working', 'thinking', 'waiting'].includes(shown(c.a)) ? el('p', { class: 'hint' }, 'This session is busy in its terminal: sending now starts a second run of it.') : ''))
}
function renderDebug() {
  const info = $('debug-info'); info.replaceChildren()
  info.append(kv([['Config', snap?.config], ['Poll', `${snap?.pollMs ?? '?'} ms`], ['Server time', snap?.now]]))
  for (const p of snap?.projects ?? []) {
    info.append(el('div', { class: 'card' }, el('h3', {}, p.name), kv([['Path', p.path], ['File', p.file], ['Read', p.ok ? 'ok' : p.error], ['File time', p.fileUpdatedAt], ['Agents', p.agents.length]]),
      el('button', { class: 'ghost', onclick: () => api('/api/projects', { action: 'remove', path: p.path }).then(poll) }, 'Remove from the office')))
  }
  const f = findAgent()
  $('debug-raw').textContent = f ? JSON.stringify(f.a, null, 2) : 'Select an agent to see its raw status entry.'
}
function renderPanels() { renderStatus(); renderOverview(); renderChat(); renderDebug(); renderFame() }
function show(tab) {
  document.querySelectorAll('nav button').forEach(b => b.classList.toggle('on', b.dataset.tab === tab))
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.id === `tab-${tab}`))
  renderPanels()
}
document.querySelectorAll('nav button').forEach(b => b.addEventListener('click', () => show(b.dataset.tab)))

// ---------- chat ----------
let chatting = false
const say = (cls, text) => { const log = $('chat-log'); log.append(el('div', { class: `msg ${cls}` }, text)); log.scrollTop = log.scrollHeight }
$('chat-form').addEventListener('submit', async ev => {
  ev.preventDefault()
  const c = chatTarget(); const text = $('chat-text').value.trim()
  if (!c || !text || chatting) return
  chatting = true; renderChat(); say('me', text); $('chat-text').value = ''
  try {
    const r = await api('/api/chat', { project: c.p.path, sessionId: c.a.sessionId, text })
    if (!r.ok || !r.body) { say('error', (await r.json().catch(() => ({}))).error || `HTTP ${r.status}`); return }
    const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = ''
    for (;;) {
      const { done, value } = await reader.read(); if (done) break
      buf += dec.decode(value, { stream: true })
      const lines = buf.split('\n'); buf = lines.pop()
      for (const l of lines) {
        if (!l) continue
        const e = JSON.parse(l)
        if (e.type === 'text') say('text', e.text)
        else if (e.type === 'tool') say('tool', `tool: ${e.text}`)
        else if (e.type === 'error') say('error', e.text)
        else if (e.type === 'done') say('tool', e.cost ? `done · $${Number(e.cost).toFixed(4)}` : 'done')
      }
    }
  } catch (err) { say('error', String(err)) } finally { chatting = false; renderChat() }
})
$('open-terminal').addEventListener('click', async () => {
  const c = chatTarget(); if (!c) return
  const r = await (await api('/api/open-terminal', { project: c.p.path, sessionId: c.a.sessionId })).json()
  say(r.ok ? 'tool' : 'error', r.ok ? `Terminal opened: ${r.manual}` : `${r.error || 'could not open a terminal'}. Run: ${r.manual || ''}`)
})
$('project-form').addEventListener('submit', async ev => {
  ev.preventDefault()
  const path = $('project-path').value.trim(); if (!path) return
  const r = await (await api('/api/projects', { action: 'add', path })).json()
  if (r.error) alert(r.error); else $('project-path').value = ''
  poll()
})

// ---------- polling (only while the tab is visible) ----------
async function poll() {
  if (document.visibilityState !== 'visible') return
  try {
    const r = await api('/api/status')
    if (r.status === 401) { $('summary').textContent = 'The office restarted: reload the page.'; return }
    snap = await r.json()
    Scene.sync(snap.projects, shown)
    const all = snap.projects.flatMap(p => p.agents)
    const busy = all.filter(a => ['thinking', 'working'].includes(shown(a))).length
    const wait = all.filter(a => shown(a) === 'waiting').length
    const err = all.filter(a => shown(a) === 'error').length
    $('summary').textContent = `${snap.projects.length} project(s) · ${busy} working · ${wait} waiting for you · ${err} in error`
    renderPanels()
  } catch { $('summary').textContent = 'Office server not reachable: start it again with the launcher.' }
}
setInterval(() => { $('clock').textContent = new Date().toLocaleTimeString() }, 1000)
const loop = () => poll().finally(() => setTimeout(loop, Math.max(500, Number(snap?.pollMs) || 2000))) // pollMs from the config
loop()
document.addEventListener('visibilitychange', poll)
requestAnimationFrame(draw)
Scene.loadSkin().catch(err => { $('summary').textContent = `Art not loaded: ${err.message}` })
