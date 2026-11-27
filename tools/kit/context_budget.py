#!/usr/bin/env python3
"""Context budget check for the repository's documentation.

Measures, in estimated tokens (characters / 4), the three things that decide
how much context a session spends before it starts working:

1. Always loaded: CLAUDE.md, .claude/rules/*.md and the
   handoff checkpoint. Each file has a budget and the set has a total budget.
2. Sections: every heading section of every tracked Markdown file. Sessions
   read sections, not files, so a section is the unit that must stay small.
3. Folder README candidates: tracked folders whose code and text reach the
   folder threshold and that have no README.md of their own.
4. CLAUDE.md files: the seven sections in order, line and token caps.

Rules and budgets: docs/pipeline/context_budget.md. Managed by the project kit
(tools/kit/kit.py update); project settings in .claude/kit.json ("budgetSkip").

Usage:
  python3 tools/kit/context_budget.py            # report
  python3 tools/kit/context_budget.py --strict   # exit 1 when over budget
  python3 tools/kit/context_budget.py --all      # also list every always-loaded file
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Budgets in estimated tokens (docs/pipeline/context_budget.md).
FILE_BUDGET = 4000          # one always-loaded file
ALWAYS_TOTAL_BUDGET = 8000  # every always-loaded file together
SECTION_BUDGET = 4000       # one heading section of any Markdown file
FOLDER_THRESHOLD = 20000    # folder size that calls for its own README.md
CHECKPOINT_MAX_LINES = 20   # handoff checkpoint rule
ROOT_CLAUDE_MAX_LINES = 300    # root CLAUDE.md (target about 150)
FOLDER_CLAUDE_MAX_LINES = 150  # a folder CLAUDE.md
FOLDER_CLAUDE_BUDGET = 2000    # tokens of a folder CLAUDE.md (loaded with that folder)

# Every CLAUDE.md carries these headings, in this order (context_budget.md).
CLAUDE_SECTIONS = [
    "Intent",
    "Non-obvious tooling",
    "Architecture map",
    "Rules (verifiable)",
    "Hard constraints and anti-patterns",
    "Deeper docs",
    "Gotchas",
]

ALWAYS_LOADED = ["CLAUDE.md", ".claude/CLAUDE.md"]  # the second one only if it comes back
RULES_GLOB = ".claude/rules/*.md"
HANDOFF = "docs/pipeline/handoff.md"

TEXT_EXT = {".md", ".py", ".cs", ".js", ".mjs", ".ts", ".sh", ".txt", ".lua", ".shader", ".hlsl"}

# Third-party or generated trees: never asked to carry a project README.
# Extra prefixes come from .claude/kit.json "budgetSkip".
def _skip_prefixes():
    base = ["node_modules/", ".claude/skills/", "graphify-out/"]
    try:
        extra = json.loads((ROOT / ".claude" / "kit.json").read_text(encoding="utf-8")).get("budgetSkip", [])
    except (OSError, ValueError):
        extra = []
    return tuple(dict.fromkeys(base + list(extra)))


SKIP_PREFIXES = _skip_prefixes()

HEADING = re.compile(r"^(#{1,6})\s+(.*)")


def tokens(text):
    return (len(text) + 3) // 4


def tracked_files():
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [p for p in out.split("\0") if p]


def read(rel):
    try:
        return (ROOT / rel).read_text(encoding="utf-8", errors="replace")
    except (FileNotFoundError, IsADirectoryError):
        return ""


def checkpoint_text():
    """Checkpoint block of the handoff: between the CHECKPOINT markers (else from a 'Checkpoint' line to the next heading)."""
    text = read(HANDOFF)
    m = re.search(r"<!-- CHECKPOINT -->\r?\n(.*?)<!-- /CHECKPOINT -->", text, re.S)
    if m:
        block = [l for l in m.group(1).splitlines() if l.strip()]
        return "\n".join(block), len(block)
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("Checkpoint")), None)
    if start is None:
        return "", 0
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("#")), len(lines))
    block = [l for l in lines[start:end] if l.strip()]
    return "\n".join(block), len(block)


def sections(text):
    """Yield (line number, heading, text) for every heading section, code blocks ignored."""
    current, start, buf, fenced = "(before first heading)", 1, [], False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        m = None if fenced else HEADING.match(line)
        if m:
            if buf:
                yield start, current, "\n".join(buf)
            current, start, buf = m.group(2).strip(), n, [line]
        else:
            buf.append(line)
    if buf:
        yield start, current, "\n".join(buf)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="exit 1 when anything is over budget")
    ap.add_argument("--all", action="store_true", help="list every always-loaded file, not only the ones over budget")
    args = ap.parse_args()

    files = tracked_files()
    over = 0

    # 1. Always loaded
    always = [p for p in ALWAYS_LOADED if (ROOT / p).exists()]
    always += sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(RULES_GLOB))
    rows = [(p, tokens(read(p))) for p in always]
    cp_text, cp_lines = checkpoint_text()
    rows.append((f"{HANDOFF} (checkpoint, {cp_lines} lines)", tokens(cp_text)))
    total = sum(t for _, t in rows)

    print("## 1. Always loaded at session start")
    for name, t in rows:
        flag = "OVER" if t > FILE_BUDGET else ""
        if flag or args.all:
            print(f"  {t:>6}  {name} {flag}")
        over += bool(flag)
    if cp_lines > CHECKPOINT_MAX_LINES:
        print(f"  OVER  checkpoint has {cp_lines} lines (rule: under {CHECKPOINT_MAX_LINES})")
        over += 1
    flag = "OVER" if total > ALWAYS_TOTAL_BUDGET else "ok"
    print(f"  total {total} / {ALWAYS_TOTAL_BUDGET} tokens: {flag}")
    over += total > ALWAYS_TOTAL_BUDGET

    # 2. Sections over budget
    print(f"\n## 2. Sections over {SECTION_BUDGET} tokens")
    big = []
    for p in files:
        if not p.endswith(".md") or p.startswith(SKIP_PREFIXES):
            continue
        for line, head, body in sections(read(p)):
            t = tokens(body)
            if t > SECTION_BUDGET:
                big.append((t, f"{p}:{line}", head))
    for t, where, head in sorted(big, reverse=True):
        print(f"  {t:>6}  {where}  {head[:70]}")
    if not big:
        print("  none")
    over += len(big)

    # 3. Folder README candidates
    print(f"\n## 3. Folders over {FOLDER_THRESHOLD} tokens without a README.md")
    size = defaultdict(int)
    has_readme = set()
    readme_text = "\n".join(read(p) for p in files if Path(p).name.lower() == "readme.md")
    for p in files:
        if p.startswith(SKIP_PREFIXES):
            continue
        path = Path(p)
        if path.name.lower() == "readme.md":
            has_readme.add(str(path.parent))
        if path.suffix.lower() not in TEXT_EXT:
            continue
        t = tokens(read(p))
        for parent in path.parents:
            if str(parent) == ".":
                break
            size[str(parent)] += t
    # A folder counts as covered when it has its own README.md or a README map row
    # names it (`folder/`); the rest are candidates for a folder README.
    candidates = sorted(
        (
            (t, d)
            for d, t in size.items()
            if t > FOLDER_THRESHOLD and d not in has_readme and f"{d}/" not in readme_text
        ),
        reverse=True,
    )
    for t, d in candidates:
        anc = next((str(a) for a in Path(d).parents if str(a) in has_readme), "repository README.md")
        print(f"  {t:>7}  {d}/   (nearest README: {anc})")
    if not candidates:
        print("  none")

    # 4. CLAUDE.md structure
    print("\n## 4. CLAUDE.md files (7 sections, lines, tokens)")
    claude_files = sorted(p for p in files if Path(p).name == "CLAUDE.md" and not p.startswith(SKIP_PREFIXES))
    for p in claude_files:
        text = read(p)
        lines = text.count("\n") + 1
        t = tokens(text)
        root = p == "CLAUDE.md"
        max_lines = ROOT_CLAUDE_MAX_LINES if root else FOLDER_CLAUDE_MAX_LINES
        max_tokens = FILE_BUDGET if root else FOLDER_CLAUDE_BUDGET
        heads = [m.group(2).strip() for m in map(HEADING.match, text.splitlines()) if m and len(m.group(1)) == 2]
        missing = [h for h in CLAUDE_SECTIONS if h not in heads]
        order_ok = [h for h in heads if h in CLAUDE_SECTIONS] == [h for h in CLAUDE_SECTIONS if h in heads]
        problems = []
        if missing:
            problems.append("missing: " + ", ".join(missing))
        if not order_ok:
            problems.append("sections out of order")
        if lines > max_lines:
            problems.append(f"{lines} lines > {max_lines}")
        if t > max_tokens:
            problems.append(f"{t} tokens > {max_tokens}")
        print(f"  {'OVER' if problems else 'ok  '}  {p}  ({lines} lines, {t} tokens){'  ' + '; '.join(problems) if problems else ''}")
        over += bool(problems)

    print(f"\n{over} item(s) over budget; {len(candidates)} folder README candidate(s).")
    return 1 if args.strict and over else 0


if __name__ == "__main__":
    sys.exit(main())
