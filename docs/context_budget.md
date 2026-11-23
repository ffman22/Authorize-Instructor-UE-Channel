# Context budget

Token estimate = characters / 4. Checked by `python3 tools/context_budget.py --strict`.

| Group | Budget (tokens) |
|---|---|
| `CLAUDE.md` | 1,800 |
| Each file in `.claude/rules/` | 500 |
| Each `SKILL.md` | 700 |
| Total always-loaded (CLAUDE.md + rules) | 3,000 |

Rules: keep CLAUDE.md to rules and pointers; details go to `docs/`; read sections, not files; batch tool calls; `/clear` with recap near 120k tokens.
