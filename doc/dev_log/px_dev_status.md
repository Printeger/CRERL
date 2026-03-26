# Project Workflow Development Status

Updated: 2026-03-26

## 1. This Iteration Goal

This iteration adds a repository-local standing instruction file so future
coding sessions do not need to repeat the same workflow rules manually.

The practical goal is:

- make the agent automatically look in `doc/` first
- make the agent automatically update `Traceability.md`
- make the agent automatically update the relevant `doc/dev_log/`
- make the agent automatically save to git and push after substantive changes

## 2. Implemented Results

### 2.1 Repo-Local Agent Rule File Added

A new file was added at the repository root:

- `AGENTS.md`

This file now acts as the repo-local standing instruction set for coding
agents.

### 2.2 Default Documentation Lookup Order Is Now Explicit

`AGENTS.md` now tells the agent to consult `doc/` first, using this order:

1. `doc/roadmap.md`
2. `doc/roadmap/phase*.md`
3. `doc/system_architecture_and _control_flow.md`
4. `doc/specs/*`
5. `Traceability.md`

This means future sessions do not need the user to repeatedly say:

- "先看 `doc/`"
- "先对照 roadmap"
- "先看架构文档"

### 2.3 Close-Out Workflow Is Now Standardized

`AGENTS.md` now also defines a default close-out sequence after substantive
changes:

1. update `Traceability.md`
2. update or create the matching `doc/dev_log/pN_dev_status.md`
3. run focused validation
4. commit to git
5. push to remote

It also defines the fallback dev-log name for non-phase work:

- `doc/dev_log/px_dev_status.md`

### 2.4 Scope Guardrails Were Added

The repo-local rules now explicitly say not to stage or commit unrelated local
changes unless the user asks.

This is important for this repo because there are often:

- local deleted docs
- untracked PDFs
- generated logs and artifacts

### 2.5 Final Reporting Expectations Are Now Stable

The standing rules now tell the agent to close out each substantive task with:

- what changed
- how it was verified
- validation result
- what should be done next

This should make future status updates more consistent.

## 3. Main Files Added or Changed

Files:

- `AGENTS.md`
- `doc/dev_log/px_dev_status.md`
- `Traceability.md`

## 4. How To Validate

### 4.1 File Presence

Verify that the following files exist:

- `AGENTS.md`
- `doc/dev_log/px_dev_status.md`

### 4.2 Rule Content Check

Open `AGENTS.md` and confirm it contains:

- a default `doc/` lookup order
- a standard close-out workflow
- a `Traceability.md` update rule
- a `doc/dev_log/` update rule
- a git save/push rule

### 4.3 Traceability Update

Verify that `Traceability.md` was updated as part of this change.

## 5. Validation Results

Validation run on 2026-03-26:

- `AGENTS.md` created successfully
- `doc/dev_log/px_dev_status.md` created successfully
- `Traceability.md` refreshed successfully

## 6. Current Conclusion

The repository now has a standing workflow instruction layer.

This should reduce repeated prompting such as:

- where to read docs from
- whether to update `Traceability.md`
- whether to write a dev log
- whether to commit and push

## 7. Next Step

The next best step is simply to keep using these standing rules and refine them
when the workflow changes.

If needed later, this can be extended with:

- phase-specific agent notes
- analyzer-specific workflow conventions
- report/repair close-out templates
