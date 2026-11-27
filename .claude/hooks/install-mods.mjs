// SessionStart hook, managed by the project kit (tools/kit/kit.py update). The kit's mods (session-reset,
// model-router, task-tracker, kit-agents) live once, in the kit repository's marketplace "project-kit";
// this project enables the ones it wants in .claude/settings.json ("enabledPlugins": "<mod>@project-kit")
// next to the marketplace source ("extraKnownMarketplaces"), and reads its own settings from
// .claude/kit.json. On startup and resume this hook adds the marketplace when this machine lacks it,
// pulls it (claude plugin marketplace update), and installs or updates each enabled mod at project scope
// when its version changed. They load at the next start or resume (cloud sessions have no
// /reload-plugins). Silent when everything is current; never blocks the session.
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join, resolve } from 'node:path'

const MARKET = 'project-kit'
const cwd = process.env.CLAUDE_PROJECT_DIR || process.cwd()
const readJson = p => { try { return JSON.parse(readFileSync(p, 'utf8')) } catch { return undefined } }

let source = ''
try {
  const input = await new Promise(done => {
    let data = ''
    process.stdin.on('data', c => (data += c))
    process.stdin.on('end', () => done(data))
    setTimeout(() => done(data), 2000)
  })
  source = JSON.parse(input || '{}').source ?? ''
} catch {}
if (source === 'clear' || source === 'compact') process.exit(0) // same process: nothing new to load

const settings = readJson(join(cwd, '.claude', 'settings.json')) ?? {}
const market = settings.extraKnownMarketplaces?.[MARKET]?.source
const mods = Object.entries(settings.enabledPlugins ?? {}).filter(([id, on]) => on && id.endsWith(`@${MARKET}`)).map(([id]) => id.slice(0, -MARKET.length - 1))
if (!market || !mods.length) process.exit(0)

const win = process.platform === 'win32'
const claude = (...args) => execFileSync('claude', ['plugin', ...(win ? args.map(a => `"${a}"`) : args)], { cwd, shell: win, stdio: 'pipe', timeout: 90000 })
const pluginsDir = join(homedir(), '.claude', 'plugins')
const same = (a, b) => Boolean(a && b) && resolve(a).toLowerCase() === resolve(b).toLowerCase()
const notes = []
try {
  if (!readJson(join(pluginsDir, 'known_marketplaces.json'))?.[MARKET]) {
    const where = market.repo ?? market.url ?? market.path
    claude('marketplace', 'add', where, '--scope', 'project')
  } else {
    claude('marketplace', 'update', MARKET)
  }
  const loc = readJson(join(pluginsDir, 'known_marketplaces.json'))?.[MARKET]?.installLocation
  const catalog = readJson(join(loc, '.claude-plugin', 'marketplace.json'))?.plugins ?? []
  const installed = readJson(join(pluginsDir, 'installed_plugins.json'))?.plugins ?? {}
  for (const mod of mods) {
    try {
      const entry = catalog.find(p => p.name === mod)
      if (!entry) { notes.push(`${mod} is not in the ${MARKET} marketplace`); continue }
      const want = readJson(join(loc, entry.source, '.claude-plugin', 'plugin.json'))?.version ?? ''
      const list = [installed[`${mod}@${MARKET}`] ?? []].flat()
      const here = list.find(e => e.scope === 'project' && same(e.projectPath, cwd)) ?? list.find(e => e.scope === 'user')
      if (!here) {
        claude('install', `${mod}@${MARKET}`, '--scope', 'project')
        notes.push(`${mod} ${want} installed`)
      } else if (want && here.version !== want) {
        claude('update', `${mod}@${MARKET}`, '--scope', here.scope)
        notes.push(`${mod} updated ${here.version} → ${want}`)
      }
    } catch {
      notes.push(`${mod}: automatic install failed; run once: claude plugin install ${mod}@${MARKET} --scope project`)
    }
  }
} catch {
  notes.push(`the ${MARKET} marketplace could not be reached (offline, or no access to the kit repository); the installed mods stay as they are`)
}
if (notes.length) console.log(`${MARKET}: ${notes.join('; ')}. They load at the next start or resume.`)
