# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Spendly — a Flask + Jinja2 + SQLite personal expense tracker. This is a **teaching scaffold**: `app.py` intentionally contains placeholder routes returning strings like `"Add expense — coming in Step 7"`, and `database/db.py` is an empty stub whose docstring lists the functions students are expected to write (`get_db()`, `init_db()`, `seed_db()`). When adding features, replace the corresponding placeholder — don't invent a parallel structure.

## Commands

All Python commands assume the venv is active (`source venv/bin/activate`) or use `venv/bin/python3` directly.

- **Install deps:** `pip install -r requirements.txt`
- **Run the app:** `python3 app.py` — Flask serves on **port 5001** (not 5000), with `debug=True` (auto-reload on template/CSS/JS changes).
- **Run tests:** `pytest` — the project ships `pytest` + `pytest-flask` but has no tests yet.
- **Single test:** `pytest path/to/test_file.py::test_name`

There is no lint/type-check command configured.

## Architecture

### Request flow
`app.py` is the single entrypoint. It creates the Flask app at module scope (no factory), registers routes inline, and calls `app.run(debug=True, port=5001)` under `__main__`. All routes currently either render a Jinja template from `templates/` or return a placeholder string.

### Templates (Jinja2)
Every page extends `templates/base.html`, which defines the shared shell: `<head>` (Google Fonts: DM Serif Display, DM Sans, Poppins), sticky `.navbar`, `<main>` with `{% block content %}`, `.footer` with Privacy / Terms links, and a `<script>` tag for `main.js`. New pages should `{% extends "base.html" %}` and fill `{% block title %}` and `{% block content %}`.

The video modal on `landing.html` is placed **at page-content level**, not inside `base.html`, because it's landing-specific. Its markup uses `data-open-video` (on any trigger button) and `data-close-video` (on backdrop and close button) — the JS in `main.js` wires up those attributes plus the Escape key. If you add more modals, follow the same `data-*` attribute pattern rather than adding per-modal JS.

### Styling
`static/css/style.css` is one file organized by banner comments (`/* Variables */`, `/* Navbar */`, `/* Hero */`, `/* Hero v2 */`, `/* Legal pages */`, `/* Video modal */`, `/* Responsive */`). Two design systems currently coexist:
- **Original** (auth pages, features, CTA, footer): DM Serif Display for display type, DM Sans for body, `--ink`/`--paper`/`--accent` color vars, `.btn-primary`/`.btn-ghost` buttons.
- **Hero v2** (landing hero + product preview): Poppins throughout, `--sage`/`--ink-black`/`--gray-*` vars, `.btn-solid`/`.btn-outline` buttons, rounded 14–22px corners.

When editing the landing hero or preview card, use the v2 tokens. For everything else, use the original tokens. Breakpoints: `900px` (features/hero collapse), `700px` (preview stats stack), `600px` (nav simplification, hero-v2 buttons full-width).

### Database (not yet implemented)
`database/db.py` is a stub. When implementing it: use SQLite, enable `PRAGMA foreign_keys = ON`, set `row_factory = sqlite3.Row`, and gate all DDL with `CREATE TABLE IF NOT EXISTS`. The `.gitignore` reserves `expense_tracker.db` as the on-disk filename.

### JavaScript
`static/js/main.js` uses vanilla JS with self-invoking IIFEs — one per feature. Guard each block with an existence check on its root element (see the `if (!modal) return;` pattern in `initVideoModal`) so the same script can be included on pages that don't use the feature.

## Conventions worth preserving

- **Port 5001**, not Flask's default 5000 — likely to avoid macOS AirPlay conflicts. Don't change it without a reason.
- Placeholder text `"Coming in Step N"` in routes signals where the teaching scaffold expects future work; treat it as a TODO, not as behavior to preserve.
- Legal pages (`privacy.html`, `terms.html`) start with a Jinja comment flagging the content as placeholder that must be reviewed by counsel before launch. Keep that comment when editing.
- The demo video ID `dQw4w9WgXcQ` in the landing modal is a Rickroll placeholder — a Jinja comment above the modal flags it. Swap for a real ID before launch.
