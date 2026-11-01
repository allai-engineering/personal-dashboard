# Issue tracker: Plane through ops

Ops is the sole task owner. Tasks live in the existing Plane workflow and ops' private checkpoint. GitHub (`allai-engineering/personal-dashboard`) hosts source, pull requests and CI, not a competing issue queue.

## Conventions

- Work from the supplied ops brief and checkpoint context. Preserve the existing task identity, accepted scope and acceptance criteria.
- Return proposed specs, tickets, dependencies, triage changes and results to ops against that identity. Ops owns durable tracking and workflow updates.
- Return genuinely missing decisions or context to ops; do not invent them or start a new setup interview for settled decisions.
- Keep private task details out of public source, issues, PRs and CI. Public descriptions and fixtures must remain generic or synthetic.
- This configuration grants no additional authority to publish, merge, deploy, change authentication or alter protected data semantics. Existing scope and release gates still apply.

## Pull requests as a triage surface

**PRs as a request surface: no.**

Pull requests carry approved code changes and reviews; they are not a task-intake surface.

## When a skill says "publish to the issue tracker"

Return the document or proposal to ops for the existing Plane task. Do not create GitHub issues or a local-markdown task queue.

## When a skill says "fetch the relevant ticket"

Read the supplied ops brief and checkpoint context. Ask ops for any missing task context instead of querying private systems independently.

## Wayfinding operations

Return proposed maps, child tickets, blockers and decisions to ops. Ops maintains their identities and relationships in the existing workflow; a delegated worker does not independently claim, assign or close tasks.
