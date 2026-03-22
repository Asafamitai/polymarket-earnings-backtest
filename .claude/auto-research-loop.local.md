---
active: true
mode: metric
iteration: 1
max_iterations: 20
completion_promise: null
metric_name: ROI
metric_direction: higher
verify_cmd: python3 verify_metric.py 2>/dev/null | tail -1
scope: config.py,backtest/*.py
read_only: verify_metric.py,data/*
verify_timeout: 300
started_at: "2026-03-22T18:02:34Z"
test_cmd: 
lint_cmd: 
typecheck_cmd: 
max_consecutive_failures: 5
consecutive_failures: 0
last_diff_hash: none
last_head_hash: none
best_metric: 15.47
baseline_metric: 15.47
---

Optimize the Polymarket earnings backtest ROI. Improve edge detection, beat rate calculation, position sizing, and strategy logic. Focus on: 1) Better rolling window sizes 2) Edge threshold tuning 3) Confidence-weighted betting 4) Filtering out low-confidence trades 5) Using sector-specific beat rates

--- SCRATCHPAD INSTRUCTIONS (Ralph Loop) ---

A persistent scratchpad exists at .claude/auto-research-loop-scratchpad.md that carries your working memory across loop iterations. Follow these rules EVERY iteration:

1. READ FIRST: At the very start of this iteration, read .claude/auto-research-loop-scratchpad.md. It contains notes from your previous iterations -- what you tried, what worked, what failed, and what to do next. Do not skip this step.

2. SNAPSHOT MTIME: After reading the scratchpad, run this command to record its modification time (used to detect if you updated it):
   if [[ "$(uname)" == "Darwin" ]]; then stat -f "%m" .claude/auto-research-loop-scratchpad.md > .claude/.auto-research-loop-scratchpad-mtime; else stat -c "%Y" .claude/auto-research-loop-scratchpad.md > .claude/.auto-research-loop-scratchpad-mtime; fi

3. UPDATE BEFORE EXIT: Before you finish your work, update .claude/auto-research-loop-scratchpad.md with:
   - What you now understand about the task (Current Understanding)
   - Any decisions you made and why (Decisions Made)
   - What you tried and whether it worked (Approaches Tried)
   - Any blockers or errors you hit (Blockers Found)
   - Which files you created, modified, or deleted (Files Modified)
   - Specific next steps for the next iteration (Next Steps)

4. KEEP IT CONCISE: Bullet points, not prose. The scratchpad is injected into the system message -- keep it scannable.

5. DO NOT DELETE the scratchpad or remove previous entries. Append and update. Mark resolved blockers with [RESOLVED].

--- IMPLEMENTATION PLAN PROTOCOL ---

You MUST follow these rules for IMPLEMENTATION_PLAN.md in every iteration:

1. READ THE PLAN FIRST. Before doing any work, read IMPLEMENTATION_PLAN.md.

2. FIRST ITERATION -- POPULATE THE PLAN. If the Tasks section has no real tasks (only the default placeholder), your FIRST action must be:
   - Analyze the task prompt thoroughly.
   - Break it into discrete, actionable subtasks. Each task should be completable in a single iteration.
   - Write them using: - [ ] Task description (priority: high/medium/low)
   - Order by priority. Do NOT start implementation until the plan is written.

3. PICK THE NEXT TASK. Select the highest-priority unchecked task (- [ ]). Work on ONLY that task this iteration.

4. MARK COMPLETION. When you finish a task, change - [ ] to - [x] and move it to the Completed section with a note.

5. DISCOVER AND ADD. If you find new work during implementation, add it as a new task with appropriate priority. Do NOT silently do extra work without tracking it.

6. UPDATE NOTES. Record implementation decisions, API quirks, edge cases, or gotchas in the Notes section.

7. SAVE BEFORE EXIT. Always write updates to IMPLEMENTATION_PLAN.md before your iteration ends.

--- LOOP PROTOCOL ---

You are in METRIC MODE. Each iteration:
1. Read scratchpad + autoresearch-results.tsv + git log --oneline -20
2. Pick ONE focused change (fix crashes > exploit wins > explore > simplify > radical)
3. Make the change to in-scope files ONLY
4. git add + git commit -m "experiment: <description>" BEFORE verification
5. The stop hook automatically runs the verify command, compares to best metric, and keeps (commit stays) or discards (git reset --hard HEAD~1)
6. You will see the result (KEEP/DISCARD/CRASH) in the next iteration system message
7. Update scratchpad before exiting

NEVER STOP. NEVER ASK "should I continue?" One change per iteration. Mechanical verification only.

SIMPLICITY: A 0.5% improvement that adds 20 lines of ugly complexity? Probably not worth it. A 0.5% improvement from DELETING code? Definitely keep. Equal metric + simpler code = KEEP.

When stuck (>5 consecutive discards): re-read ALL in-scope files from scratch, review entire results log for patterns, combine 2-3 previously successful changes, try the OPPOSITE of what has not been working, try a radical architectural change.

--- READ-ONLY FILES (DO NOT MODIFY) ---

These files are LOCKED. They contain the evaluation logic or test infrastructure. Modifying them would game the metric rather than genuinely improving. Do NOT edit, rename, or delete:
  verify_metric.py,data/*

If you need to change how something is measured, ask the human. Improve the CODE, not the MEASUREMENT.

--- CIRCUIT BREAKER (auto-stop on stall) ---

A circuit breaker is active. If you fail to make meaningful progress for 5 consecutive iterations, the loop automatically stops.

What counts as progress:
- Making at least one git commit during the iteration
- Producing a different set of working-tree changes than the previous iteration

What triggers a failure:
- No commits AND the git diff is identical to the previous iteration

Rules to avoid tripping the breaker:
1. Commit early and often. After each meaningful change, commit it.
2. If something is not working after 2 attempts, change your approach fundamentally. Do not keep retrying the same fix.
3. If blocked by an external issue, document what you have tried and what is blocking you in the scratchpad rather than silently retrying.

