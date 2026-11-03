# Technical incidents and owner decisions

Owner request: pass technical dashboard problems to existing Hermes ops, display actual work and stops, and reserve “Решить сейчас” for explicit owner requests. Preserve CPA, limits, password-only login and 30-day sessions.

The displayed evidence model is reused by a bounded local intake command; it never calls providers. Its stable condition key excludes poll timestamps and quota counters inside the same warning band. Intake maintains the existing ops private checkpoint. A changed condition or recurrence queues a new version; absent/stale evidence never resolves it. The existing native fleet monitor hashes incident versions with its prior conditions, preserving one owner and the 15-minute schedule.

Progress reports require a live native ops execution in the caller's ancestor chain and the kernel process incarnation. The read-only publisher joins that execution later; a completed/failed process cannot remain “working”. Reports contain allowlisted action/blocker codes and a short explicit owner decision, with no raw logs or prompts. An owner request must match the current condition and source state; stale or changed evidence suspends it. A successful run is distinct from recovery.

The file-only HTTP service reads the validated sidecar. A report refreshes local checkpoint/execution metadata only, preserving the Court data, source times and 15-minute external-read gate. The existing scheduled publisher remains authoritative for source refresh. Ordinary UI installation cannot change this protected integration contract.

Acceptance: duplicate intake, changed conditions, recurrence, missing source, stale report, fake/native PID binding, blocked/failed/completed execution, explicit owner requests, preserved read-only auth/cadence and desktop/mobile evidence navigation. Live commissioning must include a real ops claim/final report, saved release/rollback receipt and unchanged protected CPA/auth/process evidence. No production fault injection or new repair capability is included.
