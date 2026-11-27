# Agents Office

A local web page that shows every agent of every listed project as a 2D pixel office: one room per project, one desk per agent, and four panels (Status, Overview, Chat, Debug). Managed by the project kit; `kit.py update` installs and updates it.

## Open it
- **Windows:** double-click `tools/agents-office/open-office.cmd`.
- **macOS:** double-click `tools/agents-office/open-office.command` (the first time: right-click, Open, Open, because the file is not signed).
- **Linux:** double-click `tools/agents-office/open-office.sh` (choose "Run" if the file manager asks).
- **Inside Claude Code:** `/agentes-office`.
- **Command:** `node tools/agents-office/office.mjs start --open` (also `stop`, `status`, `list`, `add <folder>`, `remove <folder>`).

The browser opens `http://127.0.0.1:4780/` (the next free port when 4780 is taken). Needs Node.js 18 or newer; the launcher opens nodejs.org when it is missing.

## What it shows
| Panel | Content |
|---|---|
| Office | One room per project. A new subagent walks in through the door and sits at a desk; when it finishes it takes its report to the lead and leaves. Its pose and speech bubble follow the last tool (edit, read, command, web), outfit and accessory follow its role, and the ring under it takes the state color. A small cloud marks a cloud session. `−`, `Fit all`, `+` or Ctrl + wheel zoom |
| Hall of Fame | Below the office: the last 8 finished subagents (task, project, time taken, output tokens; `★` = no errors) |
| Status | The agent clicked in the office: role, state, task, last tool, last 5 tools, errors, tokens, timestamps, session id |
| Overview | Every project: counts per state and the agent list (click a row to select) |
| Chat | Sends a message to the selected session, or opens it in a new terminal window |
| Debug | Config file, each status file and its read result, the raw entry of the selected agent; add or remove projects |

States: starting, thinking, working, waiting, idle, error, finished (subagent), ended (session); `stale` when a running state has not changed for 10 minutes.

## How it works
- The hook `.claude/hooks/agents-status.mjs` writes `.claude/agents-status.json` (git-ignored) in each project, and lists the project in the viewer config at each local session start. The page reads those files every 2 seconds while it is visible. No model is called to show status: zero tokens at rest.
- Tokens are not in hook events: the viewer reads the local transcripts in `~/.claude/projects` (`AGENTS_OFFICE_TRANSCRIPTS` points elsewhere) and keeps only the usage numbers; no transcript text is stored or sent to the page. Cloud sessions show none.
- One config file lists the projects: `~/.claude/agents-office/config.json` (`projects`, `port`, `pollMs`, `staleMinutes`, `chatTimeoutMinutes`); `AGENTS_OFFICE_CONFIG` points elsewhere.
- Chat runs `claude -p --resume <session> --output-format stream-json` in the project folder; only that message costs tokens. A terminal that already shows the session does not see these turns until it resumes again, and tools that need a permission prompt are refused there. "Open in a terminal" starts `claude --resume <session>` in a new window instead.
- Cloud sessions run on another machine: their status file is not on this computer. When an entry is marked cloud, the page shows its `claude.ai/code` link instead of chat.
- Privacy: the page binds `127.0.0.1` only, needs a per-start token, and refuses other host names. Prompt text is not stored unless `AGENTS_STATUS_PROMPT=on`; tool inputs are reduced to a short summary with obvious secrets masked. `AGENTS_STATUS=off` stops the hook.
- Art: `web/skin/` is the default skin of [ailtonloures/agents-office](https://github.com/ailtonloures/agents-office), CC0 1.0 ([LICENSES.md](web/skin/LICENSES.md); its bitmap fonts are not included). The walk-in, desk, report and exit idea comes from that project (MIT); the code here is written for the kit.
