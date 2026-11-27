---
name: kit-audit
description: Context audit of a project-kit repository - token budgets of always-loaded files, sections, folders and every CLAUDE.md, with the fixes. Use when the user asks for a context audit, why sessions cost so much, or after large documentation changes.
---

# Context audit

1. `python3 tools/kit/context_budget.py --all` and read the report.
2. Fix in this order, keeping all content:
   - Always-loaded file over budget: move detail to its topic page, leave one linking line.
   - Section over 4,000 tokens: split it under subheadings (only headings change).
   - Folder over 20,000 tokens without a README: add its README (Scope, Rules that never break, Common confusions, Patterns) or a named row in the parent README map.
   - `CLAUDE.md` missing a section or over its caps: restore the seven sections (Intent, Non-obvious tooling, Architecture map, Rules (verifiable), Hard constraints and anti-patterns, Deeper docs, Gotchas); move detail out.
3. `python3 tools/kit/context_budget.py --strict` exits 0.
4. Report the before / after numbers in a few lines; commit on the user's yes.
