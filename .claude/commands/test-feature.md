---
description: Run test-writer then test-runner on a newly implemented feature, and produce a combined summary report
argument-hint: <feature name> [— path/to/spec]
allowed-tools: Agent, Read, Write, Glob, Grep
---

You are orchestrating a two-step test flow for a feature the user just implemented, followed by a combined summary report. The feature (and optionally a spec path) is provided in `$ARGUMENTS`.

## Steps

1. **Parse `$ARGUMENTS`.** The user may have given:
   - Just a feature name (e.g. `add-expense`)
   - A feature name plus a spec path (e.g. `add-expense — specs/003-add-expense.md`)
   - Nothing — in which case ask the user which feature to test and where its spec lives, then stop.

2. **Locate the spec.** If no spec path was given, look in `specs/`, `docs/`, or the repo root for a doc that matches the feature name. If you can't find one, ask the user before proceeding — do NOT let the subagents fall back to reading the implementation for intent.

3. **Invoke the `test-writer` subagent** via the Agent tool with `subagent_type: "test-writer"`. In the prompt, include:
   - The feature name
   - The spec path (or the spec content, pasted inline, if the doc is short)
   - Any known implementation entry points (route path, module) so it can wire up fixtures — but remind it that behavioral expectations come from the spec, not the code
   - Explicit instruction to return its standard final report

   **Capture its full final report verbatim** — you'll need it for the combined summary.

4. **Invoke the `test-runner` subagent** via the Agent tool with `subagent_type: "test-runner"`. In its prompt, pass:
   - The full test-writer report from step 3
   - The test file path(s) test-writer created
   - The spec path (so test-runner can classify failures against it)

   **Capture its full final report verbatim** too.

5. **Produce a combined summary report.** Write it to `tests/reports/<feature>-<YYYY-MM-DD>.md` (create the directory if needed) AND print it to the user. Structure:

   ```markdown
   # Test Report — <feature>

   **Date:** <today>
   **Spec:** <path or "none provided">
   **Test file(s):** <paths>

   ## Verdict
   <one line: all green / N failures / blocked>

   ## From test-writer
   - Acceptance criteria covered: <list>
   - Tests written: <count>
   - Spec gaps deliberately not tested: <list or "none">

   ## From test-runner
   - Passed / failed / errored / skipped counts
   - Failing tests with classification (impl bug / test bug / spec ambiguity / env issue)
   - Regressions in the wider suite: <list or "none">

   ## Spec vs. implementation mismatches
   <bugs surfaced by either agent — these are the highest-priority items>

   ## Recommended next steps
   <ordered list from test-runner, with any human-decision items called out>

   ## Appendix — raw agent reports
   ### test-writer
   <verbatim report>

   ### test-runner
   <verbatim report>
   ```

6. **Reply to the user** with a tight 3–5 sentence summary: verdict, top 1–3 next steps, and the report path so they can open it. Do not implement fixes — test-runner is read-only and its recommendations are for the user to approve.

## Input
$ARGUMENTS
