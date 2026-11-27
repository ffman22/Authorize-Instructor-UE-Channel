#!/usr/bin/env node
// Routes heavy mechanical work to Gemini (docs/model_routing.md) to save Claude tokens.
// UserPromptSubmit: one-line reminder when the request looks like Gemini work.
// PreToolUse: asks the owner before Claude watches a video or reads a long transcript itself.
import { readFileSync, statSync } from 'node:fs';

const BIG_TEXT_BYTES = 30_000;
const PROMPT_WORDS = /analiz|analy[sz]|transcri|subtitl|resum|summar|competi|benchmark|gemini|audio|sonido|miniatura|thumbnail|imagen|(ve|mira|revisa|watch).{0,30}v[ií]deo/i;
const VIDEO_TOOLS = /vidiq_(video_watch|watch_shortform_content|video_transcript)$/;
const HOW = 'Use tools/gemini_task.py "<task>" --youtube <url> | --file <text> --out out/gemini/<name>.md, ' +
  'tools/gemini_review.py for video or audio files, tools/gemini_image.py for images, or tools/find_moments.py for an own local video (docs/model_routing.md).';

let input = {};
try { input = JSON.parse(readFileSync(0, 'utf8')); } catch { process.exit(0); }

if (input.hook_event_name === 'UserPromptSubmit') {
  if (PROMPT_WORDS.test(input.prompt || '')) console.log(`Gemini routing: video analysis, transcripts and long summaries go to Gemini first. ${HOW}`);
  process.exit(0);
}

function ask(reason) {
  console.log(JSON.stringify({
    hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'ask', permissionDecisionReason: `${reason} ${HOW}` },
  }));
  process.exit(0);
}

const tool = input.tool_name || '';
if (VIDEO_TOOLS.test(tool)) ask('This spends Claude tokens on video work that belongs to Gemini.');

if (tool === 'Read') {
  const file = input.tool_input?.file_path || '';
  if (/\.(srt|vtt|txt)$/i.test(file) && !input.tool_input?.limit) {
    let size = 0;
    try { size = statSync(file).size; } catch { process.exit(0); }
    if (size > BIG_TEXT_BYTES) ask(`Long text (${Math.round(size / 1000)} KB): let Gemini summarize it.`);
  }
}
