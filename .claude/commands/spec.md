---
description: Create a numbered spec document for a new Spendly feature
argument-hint: <step-id> <feature-name>
allowed-tools: Read, Write, Glob, Bash(ls:*), Bash(git status:*), Bash(git pull:*), Bash(git checkout:*), Bash(git switch:*), Bash(git branch:*)
---

Create a spec document at `.claude/specs/<NN>-<slug>.md` for a new Spendly feature. Match the tone and structure of the existing spec at `.claude/specs/01-database-setup.md`.

**Arguments:** `$ARGUMENTS`

## 1. Prepare git working tree

Before doing anything else, make sure git is in a clean, safe state to start a new feature branch.

- Run `git status --porcelain`.
  - If the output is **non-empty**, the working tree is dirty. Stop immediately, show the changed files to the user, and ask them to commit or stash before re-running `/spec`. Do not proceed to any of the steps below.
- If the tree is clean, confirm both arguments are present in `$ARGUMENTS`:
  - First token = step id (positive integer).
  - Remaining tokens joined = feature name.
  - If either is missing or the step id is not a positive integer, stop and ask the user to supply both. Do not touch git until you have them.
- Compute the branch name:
  - `slug` → lowercase, spaces/underscores replaced with `-`, strip anything not `[a-z0-9-]`, collapse repeated `-`.
  - Branch name = `feature/<slug>`.
- Run these git commands **in order**, stopping and surfacing the error to the user if any of them fails (e.g. `main` doesn't exist, pull conflict, branch already exists):
  1. `git checkout main` — switch to `main` so the pull lands on the right branch.
  2. `git pull` — fetch the latest from the remote `main`.
  3. `git checkout -b feature/<slug>` — create the new feature branch and switch to it.
- Only after all three succeed, continue to step 2.

## 2. Parse arguments

- Using the same tokens confirmed in step 1: first token = step id, rest joined = feature name.
- Normalize:
  - `step_id` → two-digit zero-padded string (`2` → `02`, `07` → `07`, `15` → `15`).
  - `slug` → same normalization used for the branch name in step 1.
- Target path: `.claude/specs/<NN>-<slug>.md`.

## 3. Validate — no duplicate specs

Use `Glob` on `.claude/specs/*.md` to list existing specs. Stop and ask the user how to proceed if any of the following are true:

- **Exact collision:** the target path already exists.
- **Same step id, different slug:** e.g. asking for `02-authentication` when `02-auth.md` already exists.
- **Same slug, different step id:** e.g. asking for `03-auth` when `02-auth.md` already exists.

Present the conflict clearly (which existing file, why it matched) and offer options: overwrite, pick a different step id, or rename. Do not write anything until the user chooses.

## 4. Gather context

- `Read` `CLAUDE.md` for stack conventions (port 5001, parameterized SQL, no ORM, `data-*` JS pattern, v1 vs. v2 design tokens, etc.).
- `Read` `.claude/specs/01-database-setup.md` — this is the canonical template. Match its numbered `## N. Title` headings, `---` separators, and level of detail.
- Note the list of prior specs (sorted by step id) so section 2 ("Depends on") references real files.

## 5. Write the spec

Write to the target path. Use these sections, in this order, with `---` between each:

1. **Overview** — one paragraph on what this step adds and why it exists in the roadmap.
2. **Depends on** — bulleted list of prior spec filenames this step assumes are complete. `Nothing — this is the first step.` if step 01.
3. **Routes** — Flask routes added or changed in `app.py`. For each: method, path, template rendered, purpose. `No new routes` if not applicable.
4. **Database Changes** — new tables, altered columns, new seed data, migrations. Use a column table (name / type / constraints) matching the `01-database-setup.md` style. `None` if not applicable.
5. **Templates** — new/changed Jinja templates under `templates/`. For each: which base it extends, which blocks it fills, key markup notes.
6. **Files to Create** — new files (any type) with a one-line purpose each.
7. **Files to Change** — existing files with what changes and why.
8. **New Dependencies** — pip packages to add to `requirements.txt`. `None` if stdlib / already installed.
9. **Rules for Implementation** — constraints from `CLAUDE.md` that apply here (e.g. port 5001, parameterized SQL, `PRAGMA foreign_keys = ON`, `data-*` attribute pattern for JS, correct v1 vs. v2 design tokens) plus any feature-specific rules.
10. **Expected Behavior** — user-visible behavior once the step is done.
11. **Error Handling Expectations** — what should fail loudly, and how (constraint violations, form validation, etc.).
12. **Definition of Done** — checkbox list (`- [ ]`) covering deliverables. Implementers tick items as they land — this is the "confirmation of what was done" tracking.

First line of the file: `# Spec Document`.

## 6. Confirm

After writing, report to the user:

- The created path.
- The new git branch you created and switched to (`feature/<slug>`).
- The "Depends on" list you inferred.
- A one-line reminder: sections 3–8 (routes, DB, templates, files, dependencies) were filled from the feature name alone — review before starting implementation.
