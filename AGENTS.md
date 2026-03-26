# AGENTS.md

This repository uses this file as the **repo-local standing instruction set**
for coding agents.

## 1. Project Context

This project is a **CRE consistency auditing-and-repair system** built on top of
an indoor UAV RL stack.

When working in this repository, agents should assume the main engineering goal
is:

- not just "make RL code run"
- but "keep the implementation aligned with the CRE architecture, evidence
  pipeline, and repair workflow described in `doc/`"

## 2. Default Documentation Lookup Order

Before making non-trivial design or code decisions, consult `doc/` first.

Use this default lookup order unless the user asks otherwise:

1. `doc/roadmap.md`
2. the current detailed phase file under `doc/roadmap/phase*.md`
3. `doc/system_architecture_and _control_flow.md`
4. relevant files under `doc/specs/`
5. `Traceability.md`

Interpretation rule:

- `doc/roadmap.md` defines the main execution order
- `doc/roadmap/phase*.md` defines implementation-level goals for that phase
- `doc/system_architecture_and _control_flow.md` defines the canonical system architecture
- `doc/specs/*` defines auditable spec details and environment rules
- `Traceability.md` records the current repo-level mapping between roadmap and code

Agents should not skip these sources and should not rely only on local code
shape when the docs already define the intended architecture.

## 3. Phase-Aware Execution Rule

For most tasks, first determine which roadmap phase the change belongs to.

Preferred method:

1. read `doc/roadmap.md`
2. identify the current target phase
3. read the matching `doc/roadmap/phaseN.md`
4. implement only the part requested by the user or clearly on the critical path

If a task is not clearly part of a numbered phase, treat it as:

- `px` = project workflow / repository operations / meta-infrastructure

## 4. Required Close-Out Workflow After Substantive Changes

After any substantive code or documentation update, agents should perform this
close-out sequence unless the user explicitly says not to:

1. update `Traceability.md`
2. update or create the corresponding dev log under `doc/dev_log/`
3. run focused validation
4. save changes to git with a clear commit message
5. push to the remote repository

Dev-log rule:

- if the work belongs to `Phase N`, update:
  - `doc/dev_log/pN_dev_status.md`
- if the work is meta / workflow / repo-infrastructure work, update:
  - `doc/dev_log/px_dev_status.md`

Validation rule:

- validation should be proportionate to the change
- prefer targeted checks such as:
  - `python -m py_compile`
  - focused `pytest` targets
  - focused smoke tests over real repo artifacts

Reporting rule:

- in the dev log, always record:
  - what changed
  - how to validate
  - validation results

## 5. Required Final Response Structure

When reporting completed work, include the following briefly:

1. what changed
2. how it was verified
3. validation result
4. what should be done next

If git push fails, say so explicitly and distinguish:

- local commit succeeded
- remote push failed

## 6. Scope Guardrails

Do not stage or commit unrelated local changes unless the user explicitly asks.

If unrelated changes are present:

- leave them untouched
- stage only files relevant to the current task

This is especially important for:

- deleted local doc files
- untracked PDFs or notes
- generated logs and artifacts

## 7. Architecture Alignment Rule

When a conflict appears between current code shape and documented intended
architecture:

- prefer aligning toward the documented architecture in `doc/`
- unless the user explicitly instructs otherwise

When in doubt, preserve:

- `doc/roadmap.md`
- `doc/system_architecture_and _control_flow.md`
- the current phase plan in `doc/roadmap/phase*.md`

## 8. Runtime Evidence Rule

This repository is evidence-driven.

Agents should prefer solutions that:

- preserve machine-readable static reports
- preserve machine-readable dynamic reports
- preserve namespaced analysis bundles
- preserve deterministic validation paths

Avoid introducing logic that depends only on ad hoc prints or manual
interpretation when the same result can be represented as structured evidence.
