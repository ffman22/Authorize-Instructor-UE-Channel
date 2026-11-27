#!/usr/bin/env node
// Runner used by quiet-output.mjs. Reads a shell command on stdin, runs it with
// bash (stderr merged into stdout), saves the full log, and prints:
//   - everything, when the cleaned output is short (<= SHORT_LIMIT lines);
//   - otherwise only error and failure lines plus the last TAIL lines (the
//     summary), with the path of the full log.
// The exit code of the command is kept.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const SHORT_LIMIT = 40;
const TAIL = 15;
const MAX_MATCHES = 60;
const KEEP = /\b(error|errors|err!|failed|failure|failures|fail|fatal|exception|traceback|panic|cannot|could not|not found|denied|refused|segmentation fault|assert\w*)\b|✗|✘|×/i;
const DROP = /\b(0 (errors?|failed|failures))\b|--no-error|error-?handling/i; // lines that only look like errors

const cmd = readFileSync(0, 'utf8').replace(/\n$/, '');

const child = spawn('bash', ['-c', `{ ${cmd}\n} 2>&1`], { stdio: ['ignore', 'pipe', 'inherit'] });
const chunks = [];
child.stdout.on('data', (c) => chunks.push(c));
child.on('error', (e) => { console.log(`quiet-run: could not start bash: ${e.message}`); process.exit(127); });
child.on('close', (code, signal) => {
  const raw = Buffer.concat(chunks).toString('utf8');
  const lines = raw
    .replace(/\x1b\[[0-9;?]*[A-Za-z]/g, '') // ANSI colors and cursor moves
    .split('\n')
    .map((l) => l.split('\r').filter((s) => s.trim()).pop() ?? '') // progress bars: keep the last redraw
    .filter((l, i, a) => !(l === '' && a[i - 1] === ''));
  while (lines.length && lines[lines.length - 1] === '') lines.pop();

  const exit = code ?? (signal ? 128 : 1);
  if (lines.length <= SHORT_LIMIT) {
    if (lines.length) console.log(lines.join('\n'));
    process.exit(exit);
  }

  let log = '';
  try {
    const dir = join(tmpdir(), 'claude-quiet-output');
    mkdirSync(dir, { recursive: true });
    log = join(dir, `${new Date().toISOString().replace(/[:.]/g, '-')}.log`);
    writeFileSync(log, raw);
  } catch { log = '(could not save)'; }

  const tailStart = lines.length - TAIL;
  const seen = new Set();
  const matches = [];
  for (let i = 0; i < tailStart; i++) {
    const l = lines[i];
    if (KEEP.test(l) && !DROP.test(l) && !seen.has(l)) { seen.add(l); matches.push(l); }
  }
  const out = [`[quiet-output] ${lines.length} lines, exit ${exit}; showing errors/failures and the last ${TAIL} lines. Full log: ${log}`];
  if (matches.length) {
    out.push('--- errors and failures ---');
    out.push(...matches.slice(0, MAX_MATCHES));
    if (matches.length > MAX_MATCHES) out.push(`... ${matches.length - MAX_MATCHES} more in the full log`);
  }
  out.push('--- summary (last lines) ---', ...lines.slice(tailStart));
  console.log(out.join('\n'));
  process.exit(exit);
});
