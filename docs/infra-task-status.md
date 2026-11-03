# Durable infrastructure task status

Owner request, 3 November 2026: show what the infrastructure specialist actually does and where it stopped. Preserve authentication, read-only data, CPA, current limits and external source cadence.

An unavailable source suspends the existing occurrence, stage and blocker instead of requeuing the same fault. A real changed condition, recovery or recurrence remains a distinct event. The native specialist writes its checked result to ops' canonical checkpoint; later owner evidence takes precedence.

An explicit preparation task can continue after the source becomes healthy. Show a matching infra-dev accepted/waiting activity in the Hermes list and machine card, while preserving the healthy measurement. This must not create another fault, owner decision or recovery claim. Changed open conditions still require an exact incident match, and stale execution metadata cannot claim active work.

Refresh only local task/execution metadata at30second intervals through the existing publisher timer. Keep the15minute gate for external source reads. Court/event observations retain their own timestamps. A publisher from an inactive release cannot write. Snapshot commit and every UI release switch/rollback share a small root-owned coordination lock, provisioned by tmpfiles at boot; the lock contains no data.

Show stage and technical blocker even when its last-known observation is stale, explicitly marking current state unconfirmed. Never infer running or recovery, or request owner action, from stale metadata. Execution state is a sampled journal observation; process completion is not incident resolution.

Acceptance: deterministic tests for a freshness gap followed by the same fault, native child blocker persistence, a local tick observing completion without an external read, and stale presentation retaining its blocker without claiming active work. Run existing Python/JS and Chromium desktop/mobile tests. Public fixtures contain synthetic data only.
