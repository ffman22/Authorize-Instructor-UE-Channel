// Lifecycle hook, managed by the project kit (tools/kit/kit.py update): keeps .claude/agents-status.json
// current for the Agents Office viewer (one main agent per session plus its subagents: state, task, last
// tool, errors, timestamps). Zero tokens: it never prints, never calls a model and always exits 0, so a
// broken status file or a slow disk never blocks the session. Tool inputs are reduced to a short summary
// and obvious secrets are masked before anything is written; prompt text is kept only with
// AGENTS_STATUS_PROMPT=on. A local session start also adds the project to the viewer's list.
import { closeSync, mkdirSync, openSync, readFileSync, renameSync, statSync, unlinkSync, writeFileSync } from 'node:fs'
import { basename, dirname, isAbsolute, join, relative, resolve } from 'node:path'
import { homedir } from 'node:os'
import { pathToFileURL } from 'node:url'

export const SCHEMA = 1
const FILE = join('.claude', 'agents-status.json')
const MAX_AGENTS = 60
const RECENT_TOOLS = 5
const KEEP_ENDED_MS = 24 * 3600e3 // ended sessions and finished subagents stay a day, then are pruned
const SPAWN_TOOLS = new Set(['Task', 'Agent'])

const now = () => new Date().toISOString()
const SECRET = /(sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[abpr]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+|(?:token|secret|password|passwd|api[_-]?key)\s*[=:]\s*\S+)/gi
export const redact = s => String(s ?? '').replace(SECRET, '[hidden]')
export const clip = (s, n) => {
  const t = redact(s).replace(/\s+/g, ' ').trim()
  return t.length > n ? `${t.slice(0, n - 1)}…` : t
}

// A short, safe line for a tool call: a path, a pattern or the call's own description, never the full input.
export function summarize(tool, input, root) {
  const i = input && typeof input === 'object' ? input : {}
  const rel = p => (isAbsolute(String(p)) && root ? relative(root, String(p)) || basename(String(p)) : String(p))
  if (i.file_path || i.notebook_path) return clip(rel(i.file_path || i.notebook_path), 100)
  if (tool === 'Bash') return clip(i.description || String(i.command ?? '').split(/\s+/)[0], 80)
  if (SPAWN_TOOLS.has(tool)) return clip(`${i.subagent_type || 'agent'}: ${i.description || ''}`, 100)
  if (i.pattern) return clip(i.pattern, 80)
  if (i.url) { try { return new URL(i.url).host } catch { return '' } }
  if (i.query) return clip(i.query, 80)
  return clip(i.description || i.path || '', 80)
}

// A cloud session opens at claude.ai/code/session_<id>; the environment knows it as cse_<id>.
export const cloudLink = id => `https://claude.ai/code/session_${String(id).replace(/^(cse|session)_/, '').replace(/[^A-Za-z0-9]/g, '')}`

// The viewer's single project list: a session start adds this project once (local sessions only).
const officeConfig = () => process.env.AGENTS_OFFICE_CONFIG || join(homedir(), '.claude', 'agents-office', 'config.json')
export function registerProject(root, file = officeConfig()) {
  let c = {}
  try { c = JSON.parse(readFileSync(file, 'utf8')) } catch {}
  const list = Array.isArray(c.projects) ? c.projects : []
  if (list.includes(root)) return false
  mkdirSync(dirname(file), { recursive: true })
  const tmp = `${file}.${process.pid}.tmp`
  writeFileSync(tmp, `${JSON.stringify({ ...c, projects: [...list, root] }, null, 2)}\n`)
  renameSync(tmp, file)
  return true
}

// Options: the environment wins, then the project's .claude/kit.json ("agentsOffice": { "enabled": true,
// "storePrompt": false }); a missing file or key gives the defaults (on, prompt text not stored).
export function options(root, env = process.env) {
  let k = {}
  try { k = JSON.parse(readFileSync(join(root, '.claude', 'kit.json'), 'utf8')).agentsOffice ?? {} } catch {}
  return {
    enabled: env.AGENTS_STATUS === 'off' ? false : k.enabled !== false,
    storePrompt: env.AGENTS_STATUS_PROMPT ? env.AGENTS_STATUS_PROMPT === 'on' : k.storePrompt === true,
  }
}

const blank = (root, at) => ({ schema: SCHEMA, project: basename(root), path: root, updatedAt: at, agents: {} })

function agent(st, id, fields, at) {
  const a = st.agents[id] ?? (st.agents[id] = {
    id, sessionId: '', parentId: null, kind: 'main', name: 'Main', role: 'lead', state: 'starting',
    task: '', lastTool: null, recentTools: [], toolCount: 0, errorCount: 0, lastError: null,
    where: process.env.CLAUDE_CODE_REMOTE === 'true' ? 'cloud' : 'local',
    startedAt: at, updatedAt: at, endedAt: null,
  })
  Object.assign(a, fields, { updatedAt: at })
  return a
}

// Pure update: one hook event in, the new status out (exported for the kit tests).
export function apply(st, e, root, at = now()) {
  const sid = String(e.session_id || 'unknown')
  const hook = e.hook_event_name
  st.pending ??= {} // spawn descriptions per session, waiting for their SubagentStart
  const main = agent(st, sid, { sessionId: sid }, at)
  // Tool events of a subagent carry its agent_id; without it they belong to the main agent.
  const actorId = e.agent_id ? `${sid}/${e.agent_id}` : sid
  const actor = () => {
    if (!e.agent_id) return main
    const known = st.agents[actorId]
    const type = e.agent_type || known?.role || 'agent' // later events may omit agent_type: keep the first one
    return agent(st, actorId, { sessionId: sid, parentId: sid, kind: 'subagent', role: type, name: known?.name || type }, at)
  }

  switch (hook) {
    case 'SessionStart':
      Object.assign(main, { state: 'idle', endedAt: null, source: e.source || 'startup' })
      if (e.model) main.model = clip(e.model, 60)
      if (process.env.CLAUDE_CODE_REMOTE_SESSION_ID) main.link = cloudLink(process.env.CLAUDE_CODE_REMOTE_SESSION_ID)
      break
    case 'UserPromptSubmit':
      // Prompt text stays out of the file unless AGENTS_STATUS_PROMPT=on or kit.json agentsOffice.storePrompt (privacy); subagent tasks are kept.
      Object.assign(main, { state: 'thinking', task: options(root).storePrompt ? clip(e.prompt, 140) : '', lastError: null })
      break
    case 'PreToolUse': {
      const a = actor()
      const summary = summarize(e.tool_name, e.tool_input, root)
      a.state = 'working'
      a.lastTool = { name: String(e.tool_name || ''), summary, ok: null, at }
      a.recentTools = [...a.recentTools, a.lastTool].slice(-RECENT_TOOLS)
      a.toolCount++
      if (SPAWN_TOOLS.has(e.tool_name)) {
        const i = e.tool_input || {}
        ;(st.pending[sid] ??= []).push({ type: i.subagent_type || '', task: clip(i.description || i.prompt, 140), at })
        st.pending[sid] = st.pending[sid].slice(-10)
      }
      break
    }
    case 'PostToolUse':
    case 'PostToolUseFailure': {
      const a = actor()
      const ok = hook === 'PostToolUse'
      if (a.lastTool && a.lastTool.name === e.tool_name) a.lastTool.ok = ok
      a.state = ok ? 'thinking' : 'error'
      if (!ok) { a.errorCount++; a.lastError = { message: clip(e.error || `${e.tool_name} failed`, 200), tool: String(e.tool_name || ''), at } }
      break
    }
    case 'Notification':
      // Waiting for the person: a permission prompt or an idle prompt.
      Object.assign(main, { state: 'waiting', waitingFor: clip(e.message || e.notification_type, 120) })
      break
    case 'SubagentStart': {
      const q = st.pending[sid] ?? []
      const k = q.findIndex(p => !p.type || p.type === e.agent_type)
      const spawn = k >= 0 ? q.splice(k, 1)[0] : null
      agent(st, actorId, { sessionId: sid, parentId: sid, kind: 'subagent', name: e.agent_type || 'agent', role: e.agent_type || 'agent', state: 'thinking', task: spawn?.task || '' }, at)
      break
    }
    case 'SubagentStop':
      agent(st, actorId, { sessionId: sid, parentId: sid, kind: 'subagent', state: 'finished', endedAt: at }, at)
      break
    case 'Stop':
      Object.assign(main, { state: 'idle', waitingFor: undefined })
      break
    case 'StopFailure':
      main.errorCount++
      Object.assign(main, { state: 'error', lastError: { message: clip(e.error || 'the turn ended with an API error', 200), tool: '', at } })
      break
    case 'SessionEnd':
      for (const a of Object.values(st.agents)) {
        if (a.sessionId === sid && !a.endedAt) Object.assign(a, { state: a.kind === 'main' ? 'ended' : 'finished', endedAt: at, updatedAt: at })
      }
      main.endReason = e.reason || ''
      delete st.pending[sid]
      break
    default:
      break
  }
  main.updatedAt = at
  st.updatedAt = at
  return prune(st, at)
}

function prune(st, at) {
  const t = Date.parse(at)
  for (const [id, a] of Object.entries(st.agents)) {
    if (a.endedAt && t - Date.parse(a.endedAt) > KEEP_ENDED_MS) delete st.agents[id]
  }
  const ids = Object.keys(st.agents)
  if (ids.length > MAX_AGENTS) {
    ids.sort((x, y) => Date.parse(st.agents[x].updatedAt) - Date.parse(st.agents[y].updatedAt))
    for (const id of ids.slice(0, ids.length - MAX_AGENTS)) delete st.agents[id]
  }
  for (const sid of Object.keys(st.pending ?? {})) if (!st.agents[sid]) delete st.pending[sid]
  return st
}

// Parallel tool calls run hooks at the same time: a short lock file keeps read-modify-write whole.
function withLock(lock, fn) {
  const until = Date.now() + 800
  for (;;) {
    try { closeSync(openSync(lock, 'wx')); break } catch {
      try { if (Date.now() - statSync(lock).mtimeMs > 3000) unlinkSync(lock) } catch {}
      if (Date.now() > until) return // give up quietly: one missed event is fine, a blocked session is not
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 15)
    }
  }
  try { fn() } finally { try { unlinkSync(lock) } catch {} }
}

export function record(root, e, when) {
  const file = join(root, FILE)
  mkdirSync(join(root, '.claude'), { recursive: true })
  withLock(`${file}.lock`, () => {
    const at = when ?? now() // taken inside the lock, so timestamps follow the write order
    let st
    try { st = JSON.parse(readFileSync(file, 'utf8')) } catch {}
    if (!st || st.schema !== SCHEMA || typeof st.agents !== 'object') st = blank(root, at)
    st.path = root
    apply(st, e, root, at)
    const tmp = `${file}.${process.pid}.tmp`
    writeFileSync(tmp, `${JSON.stringify(st, null, 1)}\n`)
    renameSync(tmp, file)
  })
}

const isMain = Boolean(process.argv[1]) && import.meta.url === pathToFileURL(resolve(process.argv[1])).href
if (isMain) {
  let raw = ''
  process.stdin.on('data', c => (raw += c))
  process.stdin.on('end', () => {
    try {
      const e = JSON.parse(raw || '{}')
      const root = resolve(process.env.CLAUDE_PROJECT_DIR || e.cwd || process.cwd())
      if (options(root).enabled) {
        record(root, e)
        if (e.hook_event_name === 'SessionStart' && process.env.CLAUDE_CODE_REMOTE !== 'true') registerProject(root)
      }
    } catch {} // never block the session
    process.exit(0)
  })
}
