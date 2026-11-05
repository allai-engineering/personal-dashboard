# Durable infrastructure task status

Owner request, 3 November 2026: show what the infrastructure specialist actually does and where it stopped. Preserve authentication, read-only data, CPA, current limits and external source cadence.

An unavailable source suspends the existing occurrence, stage and blocker instead of requeuing the same fault. A real changed condition, recovery or recurrence remains a distinct event. The native specialist writes its checked result to ops' canonical checkpoint; later owner evidence takes precedence.

An explicit preparation task can continue after the source becomes healthy. Show a matching ops or infra-dev accepted/waiting activity in the Hermes list and machine card, while preserving the healthy measurement. Keep the actual actor: returning to ops must not hide unfinished preparation or claim the specialist is still running. This must not create another fault, owner decision or recovery claim. Changed open conditions still require an exact incident match, and stale execution metadata cannot claim active work.

Refresh only local task/execution metadata at30second intervals through the existing publisher timer. Keep the15minute gate for external source reads. The publisher unit uses a fixed root-owned launcher that resolves the current-release symlink to a versioned script before loading any release code. Later assets-only UI installations cannot strand it on an inactive directory or mix code during startup. Court/event observations retain their own timestamps. A publisher from an inactive release cannot write. Snapshot commit and every UI release switch/rollback share a small root-owned coordination lock, provisioned by tmpfiles at boot; the lock contains no data.

Show stage and technical blocker even when its last-known observation is stale, explicitly marking current state unconfirmed. Never infer running or recovery, or request owner action, from stale metadata. Execution state is a sampled journal observation; process completion is not incident resolution.

Acceptance: deterministic tests for a freshness gap followed by the same fault, native child blocker persistence, a local tick observing completion without an external read, and stale presentation retaining its blocker without claiming active work. Run existing Python/JS and Chromium desktop/mobile tests. Public fixtures contain synthetic data only.


Independent preparation results are a separate, historical receipt, not recovery or a child heartbeat. The task owner records only independently rerun Linux acceptance results in the private fixed `profiles/ops/checkpoints/infra-results.json`: schema1, up to200 items with record_id, incident fingerprint, status passed_conditional/failed, tested_at and actual positive check count. No artifact paths, goals, commands, logs or request text reach the public API. Additional private receipt fields are omitted. The reader exports only the status/time/count and whether this is the current occurrence; a prior occurrence is labelled as such. Invalid, duplicate, missing or future-dated results are ignored without hiding live progress. This receipt never changes source health, owner decisions, liveness, task identity or cleanup authority. It does not imply production eligibility or freed space. Existing seven-field native progress RPC remains unchanged.

Historical preparation is joined to the physical record independently of the current incident condition. When source freshness/condition changes, its dated test result remains visible, while the old phase, actor, liveness and owner decision remain unconfirmed. A receipt does not rebind an older incident to the current one.

## Reading Hermes progress

The overview and Hermes task counters use the same phases as their cards: queued, active, waiting, interrupted, unconfirmed and verified recovery. A live owner process does not hide a recorded technical blocker. Work counts and execution counts remain separate: one execution can serve several tasks. A completed process is a process result requiring review, never proof of recovery.

Cards retain the last reported operation, its age and the stop reason. Evidence separates source observation, checkpoint update, execution-log read and publication time. A mismatched source condition retains only explicitly historical operation/blocker metadata; it cannot revive activity or an owner request. Historical Linux plan checks remain distinct from recovery. Mail's saved running flag has no native liveness identity, so it cannot establish active execution even immediately after publication. A limited mail diagnostic and an owner's resolved mark keep their existing scoped labels.

Within the current tab, missing ops observations retain unfinished preparation as unconfirmed history, including its last blocker, in Hermes and the machine card. A source measurement expiring or disappearing cannot confirm its completion. This is in-memory view history; it adds no persistent history store or proof that the specialist still runs.

These are presentation changes over the existing allowlisted contracts. They add no observer, service, source read or operational action. The protected evidence-view module still requires the separately reviewed integration release path; ordinary assets-only deployment must continue to reject its changed hash. Actual owner-phone acceptance of the candidate remains required before installation.
