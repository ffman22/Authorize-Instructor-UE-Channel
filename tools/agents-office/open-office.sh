#!/bin/sh
# Agents Office launcher (Linux): double-click, or run it. Starts the viewer for this project and opens the browser.
cd "$(dirname "$0")/../.." || exit 1
PATH="$PATH:/opt/homebrew/bin:/usr/local/bin" # a double-click does not load the login shell PATH
if ! command -v node >/dev/null 2>&1; then
  echo "Agents Office needs Node.js 18 or newer: https://nodejs.org"
  command -v xdg-open >/dev/null 2>&1 && xdg-open https://nodejs.org >/dev/null 2>&1
  exit 1
fi
node tools/agents-office/office.mjs start --open --project "$PWD"
