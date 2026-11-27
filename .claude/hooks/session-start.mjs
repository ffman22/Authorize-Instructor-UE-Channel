// SessionStart hook (startup, resume, clear, compact), managed by the project kit (tools/kit/kit.py update).
// Node, so it runs the same on Windows, macOS and Linux. It fast-forwards the main branch without risking a
// half-done rebase, and tells the session where the work stands (the handoff checkpoint) so a fresh session
// needs no file read before its first task. Project settings live in .claude/kit.json.
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const cwd = process.env.CLAUDE_PROJECT_DIR || process.cwd()
const readJson = p => { try { return JSON.parse(readFileSync(join(cwd, p), 'utf8')) } catch { return {} } }
const kit = readJson('.claude/kit.json')
const name = kit.projectName || 'Project'
const main = kit.mainBranch || 'main'
const keep = kit.sessionLogKeep || 3
const git = (...args) => execFileSync('git', args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 60000 }).trim()

let source = ''
try {
  const input = await new Promise(resolve => {
    let data = ''
    process.stdin.on('data', c => (data += c))
    process.stdin.on('end', () => resolve(data))
    setTimeout(() => resolve(data), 2000)
  })
  source = JSON.parse(input || '{}').source ?? ''
} catch {}

let state
try {
  const branch = git('branch', '--show-current')
  let hasRemote = true
  try { git('remote', 'get-url', 'origin') } catch { hasRemote = false }
  if (!hasRemote) state = `on branch ${branch || '(detached)'}, no remote`
  else if (branch === main) {
    git('fetch', '-q', 'origin', main) // FETCH_HEAD: shallow clones may have no remote-tracking ref
    try {
      git('merge', '--ff-only', '-q', 'FETCH_HEAD')
      const ahead = git('rev-list', '--count', `FETCH_HEAD..${main}`)
      state = `${main} is up to date with origin (HEAD ${git('log', '-1', '--format=%h %s')})${ahead !== '0' ? `; ${ahead} local commits not pushed yet` : ''}`
    } catch {
      state = `${main} could not fast-forward (local commits or changes in the way): run git pull --rebase and tell the owner if it conflicts`
    }
  } else {
    git('fetch', '-q', 'origin')
    state = `on branch ${branch || '(detached)'}, not ${main}: fetched only`
  }
} catch {
  state = 'git sync failed (offline or no git)'
}

let checkpoint = ''
try {
  const h = readFileSync(join(cwd, 'docs', 'pipeline', 'handoff.md'), 'utf8')
  const m = h.match(/<!-- CHECKPOINT -->\r?\n([\s\S]*?)<!-- \/CHECKPOINT -->/)
  if (m) checkpoint = m[1].trim()
} catch {}

let rotateNote = ''
try {
  const n = (readFileSync(join(cwd, 'docs', 'pipeline', 'session_log.md'), 'utf8').match(/^## /gm) || []).length
  if (n > keep) rotateNote = `- session_log.md has ${n} entries (keep ${keep}): run python3 tools/kit/rotate_session_log.py at the next recap.`
} catch {}

const lines = source === 'compact'
  ? [`${name}: repository state: ${state}. CLAUDE.md rules still apply.`]
  : [
      `${name} session start (source: ${source || 'unknown'}).`,
      `- Repository state: ${state}.`,
      '- CLAUDE.md and the checkpoint below are already loaded: read nothing else now. Open the rest of docs/pipeline/handoff.md only for the item the task needs, the latest session_log.md entry only when the task continues the last session, and only the matching section of lessons_learned.md.',
      `- The owner's first message is usually the task: start on it. With no task, summarize where the work stands in a few lines and propose the next handoff item. Chat in ${kit.chatLanguage || 'the owner\'s language'}.`,
      ...(rotateNote ? [rotateNote] : []),
    ]
if (checkpoint) lines.push('Checkpoint (docs/pipeline/handoff.md):', checkpoint)

process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext: lines.join('\n') } }))
