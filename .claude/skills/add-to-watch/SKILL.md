---
name: add-to-watch
description: Turn a coach swim plan (pasted text or a screenshot) into a Garmin workout and push it to Luis's watch. Use when Luis says "add to my watch", "add this to my watch" or "push to my watch".
---

# Add a swim workout to the watch

1. Find the name. It is tomorrow's date in `Mon-DD` form (run on Oct 16, the name is `Oct-17`).
   When Luis gives a name or a date, use his.
2. Write `examples/<name>.json`. Set `"name"` to the same name. Translate the plan with the
   acronym glossary in `AGENTS.md`. Put each translation choice on one line in `"_comment"`.
3. Check the spec. This must exit 0:
   `.venv/bin/python -m swim_plan create examples/<name>.json --dry-run > /dev/null`
4. Upload and push:
   `.venv/bin/python -m swim_plan create examples/<name>.json --push`
5. Commit only the spec: `git add examples/<name>.json && git commit -m "Add <name> swim workout"`.
   Push to `origin main` only when Luis asks.
6. Reply in 1 or 2 lines: the name, the total distance, and "on the watch".

Do not ask Luis to confirm a translation step that the glossary covers. Ask only when a plan
line has two readings that change the distance.
