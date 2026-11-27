#!/usr/bin/env node
// Agents Office viewer, managed by the project kit (tools/kit/kit.py update). A local web page that shows
// every agent of every listed project as a 2D pixel office, with status, overview, debug and chat panels.
// Zero tokens at rest: the page only reads the .claude/agents-status.json files the kit hook writes; a model
// is called only when the person sends a chat message. Node standard library only, bound to 127.0.0.1.
//
//   node tools/agents-office/office.mjs start [--open] [--project <dir>]   start in the background (or reuse)
//   node tools/agents-office/office.mjs serve [--port <n>]                   run in the foreground
//   node tools/agents-office/office.mjs stop | status
//   node tools/agents-office/office.mjs add <dir> | remove <dir> | list    the project list (one config file)
import { spawn } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { closeSync, existsSync, mkdirSync, openSync, readdirSync, readFileSync, readSync, renameSync, statSync, unlinkSync, writeFileSync, chmodSync } from 'node:fs'
import { createServer } from 'node:http'
import { homedir, tmpdir } from 'node:os'
import { basename, delimiter, dirname, extname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const WEB = join(HERE, 'web')
export const STATUS_FILE = join('.claude', 'agents-status.json')
export const SCHEMA = 1
export const configPath = () => process.env.AGENTS_OFFICE_CONFIG || join(homedir(), '.claude', 'agents-office', 'config.json')
const runtimePath = () => join(dirname(configPath()), 'server.json')
const DEFAULTS = { projects: [], port: 4780, pollMs: 2000, staleMinutes: 10, chatTimeoutMinutes: 10 }
const SESSION_ID = /^[A-Za-z0-9_-]{6,80}$/
const MAX_BODY = 64 * 1024

// ---------- config: one file lists every project the office shows ----------

const readJson = p => { try { return JSON.parse(readFileSync(p, 'utf8')) } catch { return undefined } }
const writeJson = (p, data) => {
  mkdirSync(dirname(p), { recursive: true })
  const tmp = `${p}.${process.pid}.tmp`
  writeFileSync(tmp, `${JSON.stringify(data, null, 2)}\n`)
  renameSync(tmp, p)
}
export function loadConfig(p = configPath()) {
  const c = { ...DEFAULTS, ...(readJson(p) ?? {}) }
  c.projects = [...new Set((Array.isArray(c.projects) ? c.projects : []).filter(x => typeof x === 'string').map(x => resolve(x)))]
  return c
}
export function editProjects(action, dir, p = configPath()) {
  const c = loadConfig(p)
  const abs = resolve(dir)
  if (action === 'add') {
    if (!existsSync(abs) || !statSync(abs).isDirectory()) throw new Error(`not a folder: ${abs}`)
    if (!c.projects.includes(abs)) c.projects.push(abs)
  } else c.projects = c.projects.filter(x => x !== abs)
  writeJson(p, { ...(readJson(p) ?? {}), projects: c.projects })
  return c.projects
}

// ---------- status files ----------

export function readProject(dir) {
  const file = join(dir, STATUS_FILE)
  const out = { path: dir, name: basename(dir), file, ok: false, error: '', fileUpdatedAt: null, agents: [] }
  if (!existsSync(file)) { out.error = 'no status file yet (no session has run here since the kit update)'; return out }
  try {
    out.fileUpdatedAt = statSync(file).mtime.toISOString()
    const st = JSON.parse(readFileSync(file, 'utf8'))
    if (st.schema !== SCHEMA || typeof st.agents !== 'object' || !st.agents) throw new Error(`unknown schema ${st.schema}`)
    out.ok = true
    out.name = String(st.project || out.name)
    out.updatedAt = st.updatedAt
    out.agents = Object.values(st.agents)
  } catch (err) { out.error = `unreadable: ${err.message}` }
  return out
}
export const snapshot = cfg => ({ now: new Date().toISOString(), config: configPath(), staleMinutes: cfg.staleMinutes, projects: cfg.projects.map(dir => withTokens(readProject(dir))) })

// ---------- tokens: hook events carry none, so the usage numbers come from the local transcripts ----------

// Only the numbers of message.usage are kept; no transcript text is stored, sent or logged.
const transcriptsDir = () => process.env.AGENTS_OFFICE_TRANSCRIPTS || join(homedir(), '.claude', 'projects')
const usageCache = new Map() // file -> { offset, rest, byId: Map(message id -> [input, output, cacheRead, cacheWrite]) }
const paths = new Map() // agent id -> transcript path
export function readUsage(file) {
  const size = statSync(file).size
  let c = usageCache.get(file)
  if (!c || size < c.offset) usageCache.set(file, (c = { offset: 0, rest: Buffer.alloc(0), byId: new Map() }))
  if (size > c.offset) { // transcripts only grow: read the new bytes
    const chunk = Buffer.alloc(size - c.offset)
    const fd = openSync(file, 'r')
    let read = 0
    try { read = readSync(fd, chunk, 0, chunk.length, c.offset) } finally { closeSync(fd) }
    c.offset += read
    const all = Buffer.concat([c.rest, chunk.subarray(0, read)])
    const end = all.lastIndexOf(10) + 1 // keep a half-written last line (and its characters) for the next read
    c.rest = all.subarray(end)
    for (const line of all.subarray(0, end).toString('utf8').split(/\r?\n/)) {
      if (!line.includes('"usage"')) continue
      try {
        const m = JSON.parse(line).message
        if (!m?.usage) continue
        const n = k => Number(m.usage[k]) || 0
        // one reply spans several lines with the same id: the last one wins, never a sum
        c.byId.set(m.id || c.byId.size, [n('input_tokens'), n('output_tokens'), n('cache_read_input_tokens'), n('cache_creation_input_tokens')])
      } catch {}
    }
  }
  const t = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }
  for (const [i, o, r, w] of c.byId.values()) { t.input += i; t.output += o; t.cacheRead += r; t.cacheWrite += w }
  return c.byId.size ? t : null
}
export function transcriptPath(a, root = transcriptsDir()) {
  const [sid, sub] = String(a.id).split('/')
  if (!SESSION_ID.test(sid) || (sub !== undefined && !/^[A-Za-z0-9_-]{1,80}$/.test(sub))) return null
  const rel = sub === undefined ? `${sid}.jsonl` : join(sid, 'subagents', `agent-${sub}.jsonl`)
  const key = join(root, rel)
  if (paths.has(key)) return paths.get(key)
  let folders = []
  try { folders = readdirSync(root) } catch { return null }
  for (const f of folders) {
    const file = join(root, f, rel)
    if (existsSync(file)) { paths.set(key, file); return file }
  }
  return null
}
function withTokens(project) {
  for (const a of project.agents) {
    if (a.where === 'cloud') continue
    try { const file = transcriptPath(a); if (file) a.tokens = readUsage(file) } catch {}
  }
  return project
}

// The session must be a local main agent listed in a configured project: nothing else can be resumed.
function findSession(cfg, project, sessionId) {
  const dir = resolve(String(project || ''))
  if (!cfg.projects.includes(dir) || !SESSION_ID.test(String(sessionId || ''))) return null
  const a = readProject(dir).agents.find(x => x.id === sessionId && x.kind === 'main')
  return a ? { dir, agent: a } : null
}

// ---------- chat: the existing session, resumed ----------

const claudeBin = () => process.env.AGENTS_OFFICE_CLAUDE || 'claude'
// A claude started from inside a Claude Code session would inherit its variables and skip its transcript.
export function cleanEnv(env = process.env) {
  const out = {}
  for (const [k, v] of Object.entries(env)) {
    if (k === 'CLAUDECODE' || k === 'CLAUDE_PID' || k === 'CLAUDE_EFFORT') continue
    if (k.startsWith('CLAUDE_CODE_') && !k.startsWith('CLAUDE_CODE_USE_') && !k.startsWith('CLAUDE_CODE_SKIP_')) continue
    out[k] = v
  }
  return out
}
const onPath = name => (process.env.PATH || '').split(delimiter).some(d => d && existsSync(join(d, name)))

// How to open `claude --resume <id>` in a new terminal window on each system (pure, tested).
export function terminalPlan(platform, dir, id, bin = claudeBin(), has = onPath) {
  const manual = `cd "${dir}" && ${bin} --resume ${id}`
  if (platform === 'win32') return { cmd: 'cmd.exe', args: ['/c', 'start', 'Agents Office', '/D', dir, 'cmd.exe', '/k', bin, '--resume', id], manual }
  if (platform === 'darwin') {
    const q = s => `'${String(s).replace(/'/g, `'\\''`)}'`
    return { script: `#!/bin/sh\ncd ${q(dir)} && exec ${q(bin)} --resume ${id}\n`, cmd: 'open', args: ['-a', 'Terminal'], manual }
  }
  const candidates = [
    [process.env.TERMINAL, ['-e', bin, '--resume', id]],
    ['x-terminal-emulator', ['-e', bin, '--resume', id]],
    ['gnome-terminal', ['--', bin, '--resume', id]],
    ['konsole', ['-e', bin, '--resume', id]],
    ['xfce4-terminal', ['-x', bin, '--resume', id]],
    ['xterm', ['-e', bin, '--resume', id]],
  ]
  for (const [cmd, args] of candidates) if (cmd && has(cmd)) return { cmd, args, cwd: dir, manual }
  return { manual }
}
function openTerminal(dir, id) {
  const plan = terminalPlan(process.platform, dir, id)
  if (!plan.cmd) return { ok: false, manual: plan.manual, error: 'no terminal program found: run the command by hand' }
  const args = [...plan.args]
  if (plan.script) {
    const f = join(tmpdir(), `agents-office-${id}.command`)
    writeFileSync(f, plan.script)
    chmodSync(f, 0o755)
    args.push(f)
  }
  const child = spawn(plan.cmd, args, { cwd: plan.cwd || dir, detached: true, stdio: 'ignore', env: cleanEnv(), windowsHide: false })
  child.on('error', () => {})
  child.unref()
  return { ok: true, manual: plan.manual }
}

// Simplifies one stream-json line of `claude -p` for the page.
export function chatEvent(line) {
  let m
  try { m = JSON.parse(line) } catch { return null }
  if (m.type === 'assistant') {
    return (m.message?.content ?? []).map(c => (c.type === 'text' ? { type: 'text', text: c.text }
      : c.type === 'tool_use' ? { type: 'tool', text: c.name } : null)).filter(Boolean)
  }
  if (m.type === 'result') return [{ type: m.is_error ? 'error' : 'done', text: m.is_error ? String(m.result || m.subtype) : '', cost: m.total_cost_usd }]
  return null
}
const busy = new Set()
function chat(cfg, dir, id, text, res) {
  if (busy.has(id)) return send(res, 409, { error: 'a message to this session is still running' })
  busy.add(id)
  res.writeHead(200, { 'content-type': 'application/x-ndjson; charset=utf-8', 'cache-control': 'no-store' })
  const line = o => res.write(`${JSON.stringify(o)}\n`)
  // Fixed flags and a checked id only; the message goes through stdin, never through a shell.
  const child = spawn(claudeBin(), ['-p', '--resume', id, '--output-format', 'stream-json', '--verbose'], {
    cwd: dir, env: cleanEnv(), stdio: ['pipe', 'pipe', 'pipe'], shell: process.platform === 'win32', windowsHide: true,
  })
  let buf = ''; let err = ''
  const timer = setTimeout(() => child.kill(), cfg.chatTimeoutMinutes * 60e3)
  child.stdout.on('data', d => {
    buf += d
    const lines = buf.split('\n'); buf = lines.pop()
    for (const l of lines) for (const ev of chatEvent(l) ?? []) line(ev)
  })
  child.stderr.on('data', d => { err = (err + d).slice(-2000) })
  child.on('error', e => { line({ type: 'error', text: `could not start claude: ${e.message}` }) })
  child.on('close', code => {
    clearTimeout(timer); busy.delete(id)
    for (const ev of chatEvent(buf) ?? []) line(ev)
    if (code) line({ type: 'error', text: `claude exited with ${code}${err ? `: ${err.trim().split('\n').pop()}` : ''}` })
    res.end()
  })
  res.on('close', () => { if (child.exitCode === null) child.kill() })
  child.stdin.end(text)
}

// ---------- http ----------

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.png': 'image/png' }
const ROLES = ['tech-lead', 'analyst', 'architect', 'developer', 'qa', 'support']
// The page may load these files and nothing else.
export const WEB_FILES = new Set(['index.html', 'office.js', 'scene.js', 'style.css', 'skin/skin.json', 'skin/props.png', 'skin/tileset.png',
  'skin/characters/body.png', ...[0, 1, 2, 3, 4, 5, 6].map(i => `skin/characters/hair-${i}.png`),
  ...ROLES.flatMap(r => [`skin/characters/outfit-${r}.png`, `skin/characters/accessory-${r}.png`])])
function send(res, code, body) {
  res.writeHead(code, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' })
  res.end(JSON.stringify(body))
}
const readBody = req => new Promise((ok, fail) => {
  let b = ''
  req.on('data', d => { b += d; if (b.length > MAX_BODY) { fail(new Error('body too large')); req.destroy() } })
  req.on('end', () => { try { ok(b ? JSON.parse(b) : {}) } catch { fail(new Error('body is not JSON')) } })
})

export function makeServer({ token = randomBytes(24).toString('hex'), cfgPath = configPath() } = {}) {
  const server = createServer(async (req, res) => {
    const port = server.address()?.port
    const host = String(req.headers.host || '')
    // Only this machine, by its own address: blocks DNS rebinding and pages of other sites.
    if (host !== `127.0.0.1:${port}` && host !== `localhost:${port}`) return send(res, 403, { error: 'host not allowed' })
    const url = new URL(req.url, `http://${host}`)
    if (url.pathname === '/api/health') return send(res, 200, { ok: true, app: 'agents-office', schema: SCHEMA })
    if (!url.pathname.startsWith('/api/')) {
      const name = url.pathname === '/' ? 'index.html' : url.pathname.slice(1)
      if (!WEB_FILES.has(name) || !existsSync(join(WEB, name))) return send(res, 404, { error: 'not found' })
      let body = readFileSync(join(WEB, name))
      if (name === 'index.html') body = body.toString('utf8').replace('__OFFICE_TOKEN__', token)
      res.writeHead(200, { 'content-type': TYPES[extname(name)], 'cache-control': 'no-store', 'x-frame-options': 'DENY' })
      return res.end(body)
    }
    // Every other call needs the token the page was served with (a custom header other sites cannot send).
    if (req.headers['x-office-token'] !== token) return send(res, 401, { error: 'missing token: reload the page' })
    const cfg = loadConfig(cfgPath)
    try {
      if (req.method === 'GET' && url.pathname === '/api/status') return send(res, 200, { ...snapshot(cfg), config: cfgPath, pollMs: cfg.pollMs })
      if (req.method !== 'POST') return send(res, 405, { error: 'method not allowed' })
      const body = await readBody(req)
      if (url.pathname === '/api/projects') {
        if (!['add', 'remove'].includes(body.action)) return send(res, 400, { error: 'action is add or remove' })
        return send(res, 200, { projects: editProjects(body.action, String(body.path || ''), cfgPath) })
      }
      const found = findSession(cfg, body.project, body.sessionId)
      if (!found) return send(res, 404, { error: 'unknown session or project' })
      if (found.agent.where === 'cloud') return send(res, 400, { error: 'cloud sessions open from their link', link: found.agent.link })
      if (url.pathname === '/api/open-terminal') return send(res, 200, openTerminal(found.dir, body.sessionId))
      if (url.pathname === '/api/chat') {
        const text = String(body.text || '').trim()
        if (!text) return send(res, 400, { error: 'empty message' })
        return chat(cfg, found.dir, body.sessionId, text, res)
      }
      return send(res, 404, { error: 'not found' })
    } catch (err) { return send(res, 400, { error: err.message }) }
  })
  server.token = token
  return server
}

// ---------- CLI ----------

async function health(port) {
  try { const r = await fetch(`http://127.0.0.1:${port}/api/health`, { signal: AbortSignal.timeout(800) }); return (await r.json()).app === 'agents-office' } catch { return false }
}
function openBrowser(url) {
  const [cmd, args] = process.platform === 'win32' ? ['cmd.exe', ['/c', 'start', '', url]] : process.platform === 'darwin' ? ['open', [url]] : ['xdg-open', [url]]
  const c = spawn(cmd, args, { detached: true, stdio: 'ignore' }); c.on('error', () => {}); c.unref()
}
function listen(server, first) {
  return new Promise((ok, fail) => {
    let port = first
    const tryPort = () => {
      server.once('error', e => { if (e.code === 'EADDRINUSE' && port < first + 10) { port++; tryPort() } else fail(e) })
      server.listen(port, '127.0.0.1', () => ok(server.address().port))
    }
    tryPort()
  })
}
async function serve(port) {
  const server = makeServer()
  const p = await listen(server, port)
  const url = `http://127.0.0.1:${p}/`
  writeJson(runtimePath(), { pid: process.pid, port: p, url, startedAt: new Date().toISOString() })
  const bye = () => { try { if (readJson(runtimePath())?.pid === process.pid) unlinkSync(runtimePath()) } catch {} process.exit(0) }
  process.on('SIGINT', bye); process.on('SIGTERM', bye)
  console.log(`Agents Office: ${url} (Ctrl+C stops it)`)
}
async function start(open, port) {
  const rt = readJson(runtimePath())
  if (rt && (await health(rt.port))) { console.log(`Agents Office is running: ${rt.url}`); if (open) openBrowser(rt.url); return }
  const child = spawn(process.execPath, [fileURLToPath(import.meta.url), 'serve', '--port', String(port)], { detached: true, stdio: 'ignore', windowsHide: true })
  child.unref()
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 100))
    const now = readJson(runtimePath())
    if (now && now.pid === child.pid && (await health(now.port))) { console.log(`Agents Office started: ${now.url}`); if (open) openBrowser(now.url); return }
  }
  console.log('Agents Office did not start: run `node tools/agents-office/office.mjs serve` to see the error.')
  process.exitCode = 1
}

async function main(argv) {
  const [cmd = 'start', ...rest] = argv
  const flag = n => rest.includes(n)
  const val = n => { const i = rest.indexOf(n); return i >= 0 ? rest[i + 1] : undefined }
  const cfg = loadConfig()
  if (process.env.CLAUDE_CODE_REMOTE === 'true' && (cmd === 'start' || cmd === 'serve')) {
    console.log('Agents Office runs on your own computer: cloud sessions show there as a card with their claude.ai/code link.')
    return
  }
  if (cmd === 'serve') return serve(Number(val('--port')) || cfg.port)
  if (cmd === 'start') {
    if (val('--project')) editProjects('add', val('--project'))
    return start(flag('--open'), Number(val('--port')) || cfg.port)
  }
  if (cmd === 'stop') {
    const rt = readJson(runtimePath())
    if (!rt) return console.log('Agents Office is not running.')
    try { process.kill(rt.pid) } catch {}
    try { unlinkSync(runtimePath()) } catch {}
    return console.log('Agents Office stopped.')
  }
  if (cmd === 'status') { const rt = readJson(runtimePath()); return console.log(rt && (await health(rt.port)) ? `running: ${rt.url}` : 'not running') }
  if (cmd === 'add' || cmd === 'remove') return console.log(editProjects(cmd, rest[0] || process.cwd()).join('\n') || '(no projects)')
  if (cmd === 'list') return console.log(`${configPath()}\n${cfg.projects.join('\n') || '(no projects)'}`)
  console.log('usage: office.mjs start [--open] [--project <dir>] | serve [--port <n>] | stop | status | add <dir> | remove <dir> | list')
  process.exitCode = 2
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main(process.argv.slice(2)).catch(err => { console.error(`Agents Office: ${err.message}`); process.exitCode = 1 })
}
