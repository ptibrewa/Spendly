---
description: Run security-reviewer and code-quality-reviewer on the current diff in parallel, then produce a combined review report
argument-hint: [optional: feature name or scope hint]
allowed-tools: Agent, Read, Write, Bash, Glob, Grep
---

You are orchestrating a two-agent review of the current changes. The `security-reviewer` and `code-quality-reviewer` subagents both run on the git diff, then you merge their reports into one document.

## Steps

1. **Establish scope.** Run:
   ```bash
   git status
   git diff --stat HEAD
   ```
   If there are no uncommitted changes, check the last commit (`git log -1 --stat`) and treat that as the scope. If there's nothing to review at all, tell the user and stop.

   If `$ARGUMENTS` names a feature or points at specific files, pass that as a scope hint to both subagents so they can focus.

2. **Invoke both subagents in parallel.** In a single message, make two Agent tool calls:
   - `subagent_type: "security-reviewer"` — prompt: "Review the current git diff for security issues. Scope hint: `$ARGUMENTS` (if empty, review the full diff). Return your standard report."
   - `subagent_type: "code-quality-reviewer"` — prompt: "Review the current git diff for code-quality issues. Scope hint: `$ARGUMENTS` (if empty, review the full diff). Return your standard report."

   **Capture both final reports verbatim.**

3. **Merge into a combined report.** Write it to `reviews/<feature-or-date>.md` (create the directory if needed) AND print it to the user. Structure:

   ```markdown
   # Combined Review — <scope>

   **Date:** <today>
   **Scope:** <files/commits reviewed>

   ## Verdict
   - Security: <clean / N issues (highest severity)>
   - Code quality: <clean / N issues (highest severity)>
   - Overall: <ship / fix-before-merge / blocker>

   ## Top priorities
   Ordered list, most urgent first. Merge findings from both agents by real-world urgency:
   CRITICAL/HIGH security → HIGH quality → MEDIUM security → MEDIUM quality → the rest.
   For each item: one line naming the file:line, category, and the fix.

   ## Overlaps
   If both agents flagged the same file/line from different angles (e.g. an unparameterized query flagged as both SQLi and a correctness/convention issue), note the overlap here so the user only fixes it once.

   ## Human-decision items
   Anything either agent said needs a call from the user (spec ambiguity, deploy-story questions, intentional scaffold placeholders).

   ## Appendix — raw agent reports
   ### security-reviewer
   <verbatim report>

   ### code-quality-reviewer
   <verbatim report>
   ```

4. **Reply to the user** with a 3–5 sentence summary: overall verdict, top 1–3 priorities, and the report path.

Do not fix anything. Both subagents are read-only by design and this command is orchestration only — recommendations are for the user to approve.

## Input
$ARGUMENTS
