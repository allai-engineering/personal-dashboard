# Dashboard changes

The owner authorizes Hermes to improve dashboard structure/UI, run checks and install verified UI releases autonomously. Make small, useful changes driven by a real usability/data-display problem. Keep the existing daily collection policy and problem-only notifications. Existing ops is the sole owner; a cosmetic idea is not a reason for another scheduled model loop.

Before a nontrivial visual redesign, inspect desktop/mobile and use the installed 12ui design workflow when available. If it needs a paid generation or login, report that concrete blocker. Local visual checks and synthetic screenshots remain available without that service.

Preserve password-only login/30day cookies, unknown/stale/reset semantics, critical<10%/low<25%, account grouping, disabled exclusions, and read-only APIs. Login files, backend, data-model modules, security headers, tests and CI gates are protected from automatic UI deployment. Never weaken a test to make a change pass. Work on presentation only; use the separate approved integration broker for a new data adapter. Never store or publish secrets, real account names/email addresses, snapshots, logs, generated request text or private infrastructure inventory.

Run Python tests, all test_*.mjs scripts and Chromium desktop/mobile tests. Inspect the screenshots. Push a branch, wait for its exact CI commit, merge only when green, then wait for green CI on the exact main SHA. Install with the server helper and verify its receipt. Restore the previous verified release on a regression. Report the resulting user benefit or a concrete blocker, not every check. Never modify CPA, limits, plugins, routing or another service to complete a UI change.
