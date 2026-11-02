# Owner-authorized Captain Cockpit integration release

The owner explicitly requested public installation and server-side updates on the existing cadence, preserving password-only login, 30-day sessions, CPA and all limits. This supersedes the earlier staging-only installation boundary, without expanding ordinary dashboard-dev permissions.

## Data and cadence

Existing quota/balance/discovery gates and machine schedules remain byte-identical. A separate data-only oneshot publishes the Court/Hermes sidecar every 15 minutes, matching the existing operations interval. It reads existing evidence; it does not run Court checks, agents, generations or provider APIs. Court reads use Hermes' existing SSH alias, host keys and authorization. Configuration is root-private outside Git. The HTTP server still only reads published files.

Evidence coverage expires after 30 minutes without a successful publication; original Court observations retain their own age. Process liveness is valid for at most two minutes after observation. A 15-minute publisher does not establish that a process is still running throughout that interval. Failed source reads publish unknown, without retaining a successful receipt as current.

## Installation boundary

`deployment/cockpit_release.py` is an owner-operated integration installer, not a new Hermes sudo capability. It accepts only the reviewed exact main commit with green push CI, verifies the current release/policy, keeps authentication assets unchanged and backs up changed dashboard-only files. It installs the core, a fixed source configuration, a dashboard ExecStart drop-in and the data-only service/timer. It switches the release atomically and verifies the old signed session, read-only API, source schema, assets, security headers and protected service/config identities. A failed activation restores the previous release, policy and unit/config files.

The existing UI release broker and sudoers are unchanged. This explicitly reviewed core upgrade establishes a new exact protected-source baseline, including the publisher and tests. This is not an automatic exception or hash rebaseline by dashboard-dev: subsequent UI-only releases must still match that baseline and reject changes to core, login, source semantics, collectors and tests.

## Verification

Use the existing authenticated file/snapshot and browser seams, plus the scheduled publisher's output and owner installation/rollback transaction. Tests cover isolated Python mode, 15-minute due gating, source-time preservation, source failures, historical coverage versus live process proof, and failed-install restoration. CI and screenshots contain synthetic data only. Native acceptance checks the real service sandbox and an unattended timer publication without changing provider collection cadence. Public HTTPS is checked from outside the private network; phone UI is covered by mobile browser tests, with actual-device acceptance reported separately.
