// Agents Office scene: rooms, desks and characters drawn from the skin in web/skin/ (CC0, see
// skin/LICENSES.md). One actor per agent walks in through the door, works at a desk, and a finished
// subagent delivers its report at the lead desk and leaves. Positions are in art pixels.
// Ideas (not code) from ailtonloures/agents-office (MIT).
'use strict'
const Scene = (() => {
  const S = 3 // canvas pixels per art pixel
  const ROOM_W = 208, ROOM_H = 188, GAP = 6
  const SPEED = 60 // art pixels per second
  const MIN_DESK_MS = 2500, REPORT_MS = 2200, FRESH_MS = 20e3
  const STATE_COLOR = { starting: '#93c5fd', thinking: '#60a5fa', working: '#22c55e', waiting: '#eab308', error: '#ef4444', idle: '#94a3b8', finished: '#a78bfa', ended: '#475569', stale: '#f97316' }
  const DOOR = { x: 22, y: 56 }, CORRIDOR_X = 9
  const LEAD = { desk: { x: 80, y: 66 }, seat: { x: 104, y: 80 }, aisle: 90, report: { x: 132, y: 90 } }
  const DESKS = [0, 1, 2, 3, 4, 5].map(i => {
    const x = 24 + (i % 3) * 64, y = 118 + ((i / 3) | 0) * 46
    return { desk: { x, y }, seat: { x: x + 9, y: y + 14 }, aisle: y + 19 }
  })

  const hash = s => { let h = 2166136261; for (const c of String(s)) h = Math.imul(h ^ c.charCodeAt(0), 16777619) >>> 0; return h }
  // The outfit and accessory say what the agent does; the first match wins.
  const professionOf = a => {
    if (a.kind === 'main') return 'tech-lead'
    const r = String(a.role).toLowerCase()
    if (/valid|check|review|test|qa|audit|verif/.test(r)) return 'qa'
    if (/architect|director|plan/.test(r)) return 'architect'
    if (/program|engineer|develop|executor|coder|code/.test(r)) return 'developer'
    if (/design|analy|explore|research|strateg|search|guide/.test(r)) return 'analyst'
    return 'support'
  }
  // What the character does at its desk and what the bubble says, from the last tool.
  function activityOf(a, state) {
    if (state === 'waiting') return { pose: 'phone', say: '? waiting for you' }
    if (state === 'error') return { pose: 'idle', say: `! ${a.lastError?.tool || 'error'} failed` }
    if (state === 'stale') return { pose: 'idle', say: '? no news' }
    if (state === 'idle' || state === 'ended') return { pose: 'sleep', say: 'z z' }
    if (state === 'thinking' || state === 'starting') return { pose: 'idle', say: '…' }
    const tool = a.lastTool?.name || ''
    const what = String(a.lastTool?.summary || '').split(/[\\/]/).pop()
    if (/^(Edit|Write|NotebookEdit|MultiEdit)$/.test(tool)) return { pose: 'type', say: `edit ${what}` }
    if (/^(Read|Grep|Glob|LS)$/.test(tool)) return { pose: 'read', say: `read ${what}` }
    if (/^(Bash|PowerShell|Monitor)$/.test(tool)) return { pose: 'command', say: `$ ${what}` }
    if (/^Web/.test(tool)) return { pose: 'phone', say: `web ${what}` }
    if (/^(Agent|Task)$/.test(tool)) return { pose: 'phone', say: 'calling help' }
    return { pose: 'type', say: tool.replace(/^mcp__.*__/, '') }
  }

  // ---------- skin ----------
  let skin = null
  const images = {}
  const load = src => new Promise((ok, fail) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => fail(new Error(src)); i.src = `/skin/${src}` })
  async function loadSkin() {
    const meta = await (await fetch('/skin/skin.json')).json()
    const c = meta.characters
    const files = [meta.props.image, meta.tileset.image, c.body, ...c.hair, ...Object.values(c.outfit), ...Object.values(c.accessory)]
    await Promise.all(files.map(async f => { images[f] = await load(f) }))
    skin = meta
  }
  const sheets = new Map() // appearance key -> composed and recolored sheet
  const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16))
  const toned = (c, f) => c.map(v => Math.round(f < 1 ? v * f : v + (255 - v) * (f - 1)))
  function sheetFor(a) {
    const c = skin.characters
    const h = hash(a.id)
    const job = professionOf(a)
    const pick = (list, shift) => list[(h >>> shift) % list.length]
    const look = { hair: (h >>> 3) % c.hair.length, skin: pick(c.palettes.skin, 7), hairColor: pick(c.palettes.hair, 11), shirt: pick(c.palettes.shirt, 15), pants: pick(c.palettes.pants, 19) }
    const key = `${job}|${Object.values(look).join('|')}`
    if (sheets.has(key)) return sheets.get(key)
    const base = images[c.body]
    const canvas = document.createElement('canvas')
    canvas.width = base.width; canvas.height = base.height
    const g = canvas.getContext('2d', { willReadFrequently: true })
    for (const f of [c.body, c.outfit[job], c.hair[look.hair], c.accessory[job]]) g.drawImage(images[f], 0, 0)
    const map = new Map()
    for (const [part, color] of [['skin', look.skin], ['hair', look.hairColor], ['shirt', look.shirt], ['pants', look.pants]]) {
      for (const [suffix, f] of [['', 1], ['Shade', 0.72], ['Light', 1.3]]) {
        const from = c.baseColors[part + suffix]
        if (from) map.set(rgb(from).join(), toned(rgb(color), f))
      }
    }
    const data = g.getImageData(0, 0, canvas.width, canvas.height)
    const p = data.data
    for (let i = 0; i < p.length; i += 4) {
      const to = p[i + 3] && map.get(`${p[i]},${p[i + 1]},${p[i + 2]}`)
      if (to) [p[i], p[i + 1], p[i + 2]] = to
    }
    g.putImageData(data, 0, 0)
    sheets.set(key, canvas)
    return canvas
  }

  // ---------- actors ----------
  const rooms = new Map() // project path -> Map(agent id -> actor)
  const seenRooms = new Set()
  const pathIn = d => [{ x: CORRIDOR_X, y: DOOR.y }, { x: CORRIDOR_X, y: d.aisle }, { x: d.seat.x, y: d.aisle }, d.seat]
  const pathToReport = d => [{ x: d.seat.x, y: d.aisle }, { x: CORRIDOR_X, y: d.aisle }, { x: CORRIDOR_X, y: LEAD.report.y }, LEAD.report]
  const pathOut = from => [{ x: CORRIDOR_X, y: from.aisle ?? LEAD.report.y }, { x: CORRIDOR_X, y: DOOR.y }, DOOR]
  const pathLeaveDesk = d => [{ x: d.seat.x, y: d.aisle }, ...pathOut(d)]
  const present = (a, state) => state !== 'ended' && state !== 'finished'

  function sync(projects, shownState) {
    for (const p of projects) {
      const first = !seenRooms.has(p.path)
      seenRooms.add(p.path)
      if (!rooms.has(p.path)) rooms.set(p.path, new Map())
      const actors = rooms.get(p.path)
      const order = [...p.agents].sort((a, b) => (b.kind === 'main') - (a.kind === 'main') || Date.parse(b.updatedAt) - Date.parse(a.updatedAt))
      for (const a of order) {
        const state = shownState(a)
        let actor = actors.get(a.id)
        if (actor) { actor.agent = a; actor.state = state; if (actor.phase === 'gone' && present(a, state)) { actors.delete(a.id); actor = null } }
        if (actor) continue
        // A subagent that started and finished between two polls still walks in and delivers.
        const justDone = !first && state === 'finished' && Date.now() - Date.parse(a.endedAt || a.updatedAt) < FRESH_MS
        if (!present(a, state) && !justDone) { actors.set(a.id, { agent: a, state, phase: 'gone' }); continue }
        const slot = freeSlot(actors, a)
        if (slot === null) continue // office full: counted in the room's "+N" label
        const d = slot < 0 ? LEAD : DESKS[slot]
        const start = first ? d.seat : DOOR
        actors.set(a.id, { agent: a, state, slot, d, x: start.x, y: start.y, phase: first ? 'desk' : 'in', path: first ? [] : pathIn(d).slice(), since: performance.now(), dir: 'up' })
      }
      for (const id of actors.keys()) if (!p.agents.some(a => a.id === id)) actors.delete(id)
    }
    for (const key of rooms.keys()) if (!projects.some(p => p.path === key)) { rooms.delete(key); seenRooms.delete(key) }
  }
  function freeSlot(actors, a) {
    const taken = new Set([...actors.values()].filter(x => x.phase !== 'gone').map(x => x.slot))
    if (a.kind === 'main' && !taken.has(-1)) return -1
    const i = DESKS.findIndex((_, k) => !taken.has(k))
    return i < 0 ? null : i
  }

  function walk(actor, dt) {
    let step = SPEED * dt
    while (step > 0 && actor.path.length) {
      const to = actor.path[0]
      const dx = to.x - actor.x, dy = to.y - actor.y
      const dist = Math.hypot(dx, dy)
      if (dist > 0.01) actor.dir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up')
      if (dist <= step) { actor.x = to.x; actor.y = to.y; actor.path.shift(); step -= dist } else { actor.x += (dx / dist) * step; actor.y += (dy / dist) * step; step = 0 }
    }
    return actor.path.length === 0
  }
  function update(actor, dt, now) {
    if (actor.phase === 'gone') return
    const done = !present(actor.agent, actor.state)
    const to = phase => { actor.phase = phase; actor.since = now }
    if (actor.phase === 'in') { if (walk(actor, dt)) to('desk') } else if (actor.phase === 'desk') {
      if (!done || now - actor.since < MIN_DESK_MS) return
      if (actor.agent.kind === 'main') { actor.path = pathLeaveDesk(actor.d); to('out') } else { actor.path = pathToReport(actor.d).slice(); to('to-lead') }
    } else if (actor.phase === 'to-lead') { if (walk(actor, dt)) to('report') } else if (actor.phase === 'report') {
      actor.dir = 'left'
      if (now - actor.since > REPORT_MS) { actor.path = pathOut({}); to('out') }
    } else if (actor.phase === 'out') { if (walk(actor, dt)) to('gone') }
  }

  // ---------- drawing ----------
  let ctx = null
  const px = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(Math.round(x * S), Math.round(y * S), Math.round(w * S), Math.round(h * S)) }
  const img = (image, sx, sy, sw, sh, x, y) => ctx.drawImage(image, sx, sy, sw, sh, Math.round(x) * S, Math.round(y) * S, sw * S, sh * S)
  function prop(name, x, y) { const f = skin.props.frames[name]; if (f) img(images[skin.props.image], f.x, f.y, f.w, f.h, x - f.ax, y - f.ay) }
  function tile(name, x, y, w = 16, h = 16) {
    const t = skin.tileset, i = t.tiles[name], n = skin.tileSize
    img(images[t.image], (i % t.columns) * n, ((i / t.columns) | 0) * n, w, h, x, y)
  }
  function text(s, x, y, size, color, align = 'left') {
    ctx.fillStyle = color; ctx.font = `bold ${size * S}px ui-monospace, Consolas, monospace`; ctx.textBaseline = 'top'; ctx.textAlign = align
    ctx.fillText(s, x * S, y * S)
    ctx.textAlign = 'left'
  }
  function ring(x, y, color, selected) {
    ctx.beginPath(); ctx.ellipse(x * S, (y - 2) * S, 10 * S, 4 * S, 0, 0, Math.PI * 2)
    ctx.globalAlpha = 0.28; ctx.fillStyle = color; ctx.fill(); ctx.globalAlpha = 1
    ctx.lineWidth = (selected ? 2 : 1) * S; ctx.strokeStyle = color; ctx.stroke()
    if (selected) { ctx.beginPath(); ctx.ellipse(x * S, (y - 2) * S, 13 * S, 6 * S, 0, 0, Math.PI * 2); ctx.lineWidth = S; ctx.strokeStyle = '#ffffff'; ctx.stroke() }
  }
  function bubble(s, x, y, color) {
    const label = s.length > 16 ? `${s.slice(0, 15)}…` : s
    ctx.font = `bold ${5 * S}px ui-monospace, Consolas, monospace`
    const w = ctx.measureText(label).width / S + 5
    const left = Math.max(1, Math.min(x - w / 2, ROOM_W - w - 1))
    px(left - 0.6, y - 0.6, w + 1.2, 9.2, color); px(left, y, w, 8, '#f8fafc'); px(x - 1, y + 8.6, 2, 1.5, color)
    text(label, left + 2.5, y + 1.3, 5, '#111827')
  }
  function frameOf(actor, act, t) {
    const c = skin.characters
    const step = (ms, n) => ((t / ms) | 0) % n
    if (actor.phase === 'report') return c.poses[step(250, 2) ? 'celebrate-b' : 'celebrate']
    if (actor.phase !== 'desk') return c.walk[actor.dir][[0, 1, 2, 1][step(140, 4)]]
    if (act.pose === 'type') return c.poses[['sit-type', 'sit-type-b', 'sit-type-c'][step(170, 3)]]
    if (act.pose === 'command') return c.poses[step(110, 2) ? 'sit-type-c' : 'sit-type']
    if (act.pose === 'read') return c.poses[step(800, 2) ? 'read-b' : 'read']
    if (act.pose === 'phone') return c.poses.phone
    if (act.pose === 'sleep') return c.poses[step(1100, 2) ? 'sleep-b' : 'sleep']
    return c.idle.up[step(700, 2)]
  }
  function drawActor(actor, t, selected) {
    const { width: w, height: h } = skin.characters.frame
    const act = activityOf(actor.agent, actor.state)
    const f = frameOf(actor, act, t)
    const cols = skin.characters.columns
    ring(actor.x, actor.y, STATE_COLOR[actor.phase === 'report' || actor.phase === 'out' ? 'finished' : actor.state] || '#94a3b8', selected)
    img(sheetFor(actor.agent), (f % cols) * w, ((f / cols) | 0) * h, w, h, actor.x - w / 2, actor.y - h)
    if (actor.agent.where === 'cloud') { px(actor.x + 8, actor.y - 26, 7, 3, '#e2e8f0'); px(actor.x + 10, actor.y - 28, 4, 2, '#e2e8f0') }
    if (actor.phase === 'report') { px(actor.x - 15, actor.y - 20, 6, 8, '#f8fafc'); for (let i = 0; i < 3; i++) px(actor.x - 14, actor.y - 18 + i * 2, 4, 0.7, '#475569') }
  }
  function sayOf(actor) {
    if (actor.phase === 'report') return 'report ✓'
    if (actor.phase !== 'desk') return ''
    return activityOf(actor.agent, actor.state).say
  }
  function screenGlow(d, slotName, actor, t) {
    const sc = skin.props.frames[slotName].screens[0]
    const color = actor && actor.phase === 'desk' ? STATE_COLOR[actor.state] : null
    if (!color) return
    ctx.globalAlpha = 0.35; px(d.desk.x + sc.x + 1, d.desk.y + sc.y + 1, sc.w - 2, sc.h - 2, color); ctx.globalAlpha = 1
    if (actor.state === 'working') for (let i = 0; i < 3; i++) px(d.desk.x + sc.x + 3, d.desk.y + sc.y + 3 + i * 2.5, 3 + ((((t / 150) | 0) + i * 3) % 8), 0.8, '#f8fafc')
  }

  function drawRoom(p, t, selectedId) {
    const hue = hash(p.path)
    px(0, 0, ROOM_W, ROOM_H, '#0b0d13')
    for (let y = 44; y < ROOM_H - 2; y += 16) for (let x = 2; x < ROOM_W - 2; x += 16) tile(hue % 2 ? 'wood' : 'floor', x, y, Math.min(16, ROOM_W - 2 - x), Math.min(16, ROOM_H - 2 - y))
    for (let x = 2; x < ROOM_W - 2; x += 16) { const w = Math.min(16, ROOM_W - 2 - x); tile('wall-top', x, 12, w); tile('wall-mid', x, 28, w) }
    px(2, 2, ROOM_W - 4, 10, `hsl(${hue % 360} 30% 24%)`)
    text(p.name.slice(0, 34), 44, 4, 6, '#f8fafc')
    prop('door-0', DOOR.x - 8, 49)
    prop('kanban', 46, 50); prop('bookshelf', 152, 52); prop(['plant', 'plant-fig', 'plant-tall'][hue % 3], 190, 58)
    if (!p.ok) { text('no status yet', ROOM_W / 2, 100, 7, '#1f2937', 'center'); return [] }
    const actors = [...(rooms.get(p.path)?.values() ?? [])].filter(a => a.phase !== 'gone')
    const at = slot => actors.find(a => a.slot === slot)
    const layers = [] // painted from the back of the room to the front
    const station = (d, name, slot) => layers.push({ y: d.desk.y, paint: () => { prop(name, d.desk.x, d.desk.y); screenGlow(d, name, at(slot), t) } })
    station(LEAD, 'lead-desk', -1)
    DESKS.forEach((d, i) => station(d, ['workstation', 'workstation-b', 'workstation-c'][(hue + i) % 3], i))
    for (const a of actors) layers.push({ y: a.y, paint: () => drawActor(a, t, a.agent.id === selectedId) })
    layers.sort((a, b) => a.y - b.y).forEach(l => l.paint())
    // Bubbles go over everything else.
    for (const a of actors) { const s = sayOf(a); if (s) bubble(s, a.x, a.y - 41, STATE_COLOR[a.phase === 'report' ? 'finished' : a.state] || '#94a3b8') }
    const hidden = p.agents.filter(a => a.state !== 'finished' && a.state !== 'ended' && !rooms.get(p.path)?.has(a.id)).length
    if (hidden) text(`+${hidden} more`, ROOM_W - 6, ROOM_H - 9, 6, '#111827', 'right')
    return actors
  }

  let hits = []
  let last = 0
  function render(canvas, projects, selected, t) {
    ctx = canvas.getContext('2d')
    const cols = projects.length <= 1 ? 1 : projects.length <= 4 ? 2 : 3
    const rows = Math.max(1, Math.ceil(projects.length / cols))
    const w = (cols * (ROOM_W + GAP) + GAP) * S, h = (rows * (ROOM_H + GAP) + GAP) * S
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h }
    ctx.imageSmoothingEnabled = false
    px(0, 0, w / S, h / S, '#0d0f15')
    const dt = Math.min(1.5, last ? (t - last) / 1000 : 0) // a slowed-down tab keeps the walking pace
    last = t
    hits = []
    if (!skin) return text('loading art…', 8, 8, 7, '#94a3b8')
    if (!projects.length) return text('No projects yet: start a Claude Code session in a kit project.', 8, 20, 6, '#94a3b8')
    projects.forEach((p, i) => {
      const rx = GAP + (i % cols) * (ROOM_W + GAP), ry = GAP + ((i / cols) | 0) * (ROOM_H + GAP)
      for (const a of rooms.get(p.path)?.values() ?? []) update(a, dt, performance.now())
      ctx.save(); ctx.translate(rx * S, ry * S)
      for (const a of drawRoom(p, t, selected?.project === p.path ? selected.id : null)) hits.push({ x: rx + a.x - 10, y: ry + a.y - 34, w: 20, h: 36, z: a.y, id: a.agent.id, project: p.path })
      ctx.restore()
    })
  }
  // Canvas coordinates in, the agent in front at that point out.
  const hitAt = (cx, cy) => hits.filter(b => cx / S >= b.x && cx / S < b.x + b.w && cy / S >= b.y && cy / S < b.y + b.h).sort((a, b) => b.z - a.z)[0]
  // For tests: where every actor is and what it is doing.
  const debug = () => [...rooms].flatMap(([project, actors]) => [...actors.values()].filter(a => a.phase !== 'gone').map(a => ({ project, id: a.agent.id, phase: a.phase, slot: a.slot, x: Math.round(a.x), y: Math.round(a.y), job: professionOf(a.agent), say: sayOf(a) })))

  return { S, STATE_COLOR, loadSkin, sync, render, hitAt, debug, professionOf, activityOf }
})()
globalThis.Scene = Scene
