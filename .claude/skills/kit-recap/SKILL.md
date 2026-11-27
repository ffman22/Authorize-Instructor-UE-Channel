---
name: kit-recap
description: Save the session recap of a project-kit repository before /clear, at a topic change or when the context grows past about 120k tokens - checkpoint, decisions, lessons, session log, CLAUDE.md files, budget check, commit. Use when the user says recap, cerramos, save the session, or before clearing.
---

# Session recap

Goal: a fresh session continues from the files alone. Do every step; skip the commit only when nothing changed since the last recap.

1. `git pull --rebase`.
2. `docs/pipeline/handoff.md`: overwrite the block between `<!-- CHECKPOINT -->` and `<!-- /CHECKPOINT -->` (date, under 20 lines: critical path, next step per session, blockers, owner questions). Move finished items to `handoff_archive.md`.
3. `docs/catalog/decisions.md`: one dated row per decision taken this session (✅), in the last table. Proposals stay ◇ in their topic page.
4. `docs/pipeline/lessons_learned.md`: new lessons under their section (Working with the owner, Design lessons, Tool gotchas, Project tools already built). A gotcha seen twice also goes to the nearest `CLAUDE.md` "Gotchas".
5. `CLAUDE.md` files: update the root one and every folder `CLAUDE.md` whose tools, layout or rules changed; `README.md` when a folder, tool or topic page was added.
6. `docs/pipeline/session_log.md`: a short entry at the top (date, what was done, why, what is half done, where to start next); then `python3 tools/kit/rotate_session_log.py`.
7. `python3 tools/kit/context_budget.py --strict` must exit 0; fix what it reports.
8. Commit (`Session recap: <topic>`) and push following the repository's push rules.
9. Answer in the chat language of `.claude/kit.json`, in a few lines: what was saved and the next step.
