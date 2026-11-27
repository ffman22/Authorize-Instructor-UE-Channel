#!/usr/bin/env node
// PreToolUse hook (Bash): rewrites noisy commands (installs, builds, test runs,
// downloads with progress bars) so they run through quiet-run.mjs, which keeps
// only errors, failures and the final summary when the output is long.
// Short output still comes back whole. Commands that already pipe or redirect
// their output, or that carry the marker "# full-output", are left alone.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const NOISY = [
  // installs
  /\b(npm|pnpm)\s+(install|i|ci|add|update|rebuild)\b/,
  /\byarn(\s+(install|add|upgrade))?\s*$/,
  /\byarn\s+(install|add|upgrade)\b/,
  /\b(pip3?|python3?\s+-m\s+pip)\s+install\b/,
  /\buv\s+(sync|add|pip\s+install)\b/,
  /\bapt(-get)?\s+(install|update|upgrade|dist-upgrade)\b/,
  /\bbrew\s+(install|upgrade)\b/,
  /\bgem\s+install\b/,
  /\bbundle(\s+install)?\s*$/,
  /\bcomposer\s+(install|update)\b/,
  // builds
  /\b(npm|pnpm|yarn)\s+(run\s+)?build\b/,
  /\bcargo\s+(build|install|test|check)\b/,
  /\bdotnet\s+(build|restore|test|publish)\b/,
  /\bgo\s+(build|test|get|install|mod\s+download)\b/,
  /(^|[\s;&|])(\.\/)?gradlew?\b/,
  /\bmvn\b/,
  /(^|[\s;&|])make(\s|$)/,
  /\bcmake\s+--build\b/,
  /\bdocker\s+(build|pull)\b/,
  /-batchmode\b/, // Unity command-line builds
  /\bRunUAT\b|\bUnrealEditor-Cmd\b/, // Unreal command-line builds
  /\btsc\b(?!.*--version)/,
  // test runs
  /\b(npm|pnpm|yarn)\s+(run\s+)?test\b/,
  /\b(python3?\s+-m\s+)?pytest\b/,
  /\bpython3?\s+-m\s+unittest\b/,
  /\b(jest|vitest|mocha)\b/,
  /\bplaywright\s+test\b/,
  /\bnode\s+--test\b/,
  // progress bars
  /\bgit\s+clone\b/,
  /\bwget\b/,
];

const PASS = /# *full-output\b/;
const HANDLES_OUTPUT = /\||(^|[^0-9&<])>(?!&)|\s1?>&?\s*\S|--quiet\b|\s-q\b|--silent\b|\s-s\b/;

function main() {
  let input;
  try { input = JSON.parse(readFileSync(0, 'utf8')); } catch { return; }
  if (input.tool_name !== 'Bash') return;
  const ti = input.tool_input || {};
  const cmd = ti.command;
  if (typeof cmd !== 'string' || !cmd.trim()) return;
  if (ti.run_in_background) return;
  if (PASS.test(cmd) || HANDLES_OUTPUT.test(cmd)) return;
  if (cmd.includes('quiet-run.mjs')) return;
  if (!NOISY.some((re) => re.test(cmd))) return;

  const runner = join(dirname(fileURLToPath(import.meta.url)), 'quiet-run.mjs').replace(/\\/g, '/');
  let tag = 'QUIET_CMD_EOF';
  while (cmd.includes(tag)) tag += '_X';
  const wrapped = `node "${runner}" <<'${tag}'\n${cmd}\n${tag}`;

  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      updatedInput: { ...ti, command: wrapped },
      additionalContext: 'quiet-output: this command runs through .claude/hooks/quiet-run.mjs (long output is cut to errors, failures and the summary; the full log path is printed). Add "# full-output" to the command to get everything.',
    },
  }));
}

main();
