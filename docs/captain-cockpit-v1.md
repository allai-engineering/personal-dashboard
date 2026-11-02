# Captain Cockpit v1 — approved isolated working copy

Current follow-up authorization: the owner subsequently requested public installation with the existing update cadence, password-only/30-day login, CPA and limits preserved. The staging decisions below describe the first iteration; [cockpit-production.md](cockpit-production.md) governs the separately reviewed core integration release.

## Problem Statement

The owner needs a one-minute briefing of decisions, upcoming events and actual Hermes work. The existing resource dashboard lacks court coverage and execution evidence. A red observation must be explainable without implying that unknown data is healthy or that an agent is already repairing it.

## Solution

The owner selected layout B (Лента), then approved a working version with existing quota/balance/machine data, a court summary and verified Hermes states on an isolated authenticated copy. Opening an issue marks it seen; urgent unresolved issues remain prominent. Cross-device synchronization is deferred. The owner has not authorized production installation under this increment.

Prototype source: [Captain Cockpit research branch](https://github.com/allai-engineering/personal-dashboard/tree/prototype/captain-cockpit). Rewrite the selected structure for the real contracts; keep throwaway variants out of this branch.

## User Stories

1. As the owner, I want urgent decisions first, so that I can act in time.
2. As the owner, I want seven-day events with their actual kind and source date, so that publications and hearings do not become invented deadlines.
3. As the owner, I want existing quota/balance/machine pages to keep working, so that the new overview does not remove details.
4. As the owner, I want court receipt scope and broader search coverage separately, so that a narrow successful receipt cannot imply all courts were checked.
5. As the owner, I want incomplete and carried-forward case state identified, so that older evidence is not presented as a new check.
6. As the owner, I want actual execution, origin, liveness and result coverage, so that planned, scheduled, manual and completed work remain distinct.
7. As the owner, I want evidence details and a return to the originating row, so that I retain context.
8. As the owner, I want automatic seen state in this browser tab, so that nonurgent items become compact without being resolved.
9. As the owner, I want worsening to attract attention again, so that viewing an old state does not hide a new problem.
10. As the owner, I want unknown/stale/failed/partial states explicitly, so that missing data is never free quota or confirmed recovery.
11. As the owner, I want protected access on the isolated copy with the existing password verifier, so that real source data is not exposed by the earlier passwordless prototype.
12. As the owner, I want collection to read existing files/SQLite only, so that HTTP refresh does not run agents, generators or production collectors.

## Implementation Decisions

- Preserve the native DOM/CSS stack, existing authenticated snapshot interface and password/session/security semantics. Add optional validated court/task sidecar data; invalid/missing sidecars fail closed.
- Use the selected ledger hierarchy and current palette. Add Courts, Hermes and evidence entry points without breaking existing resource routes.
- Reuse existing quota/balance/machine view models and thresholds. Keep observation time distinct from retrieval/publication time.
- Normalize new Court/Hermes fields through an allowlist. No prompts, outputs, raw errors, document text, filesystem evidence paths or credentials enter the browser contract.
- Source data is captured into an owner-private directory outside Git. Existing owner-visible account identities remain only in that private authenticated copy. Source-specific timestamps and stale markers are preserved.
- Read execution SQLite with mode=ro and query_only, retaining scheduled/manual results. A running ledger entry needs separate identity/liveness evidence before being called active. Lack of evidence means unverified, not idle.
- Current Court normalized data cannot confirm future hearings or procedural deadlines. Export coverage and scope-labeled counts now; confirmed event dates remain unavailable until an authoritative structured source exists. Existing fresh quota resets and stored job schedules may populate upcoming events with correct labels.
- Seen state stores opaque identifiers/revisions in this browser tab only; it survives page reload but is not synchronized or an acknowledgement/resolution. Missing data does not clear retained unresolved incidents. Explicit fresh recovery may clear an incident; retired accounts leave active lists without being labelled recovered.
- The isolated preview uses a separate session-signing key while retaining the password verifier. Production auth material and service files are not modified. No real data is sent to design/model services or public CI.
- No new inference, collection schedule, notification channel or automatic operational action is introduced.

## Testing Decisions

Use the agreed working-copy scenarios at the existing high-level seams: authenticated snapshot/file serving and browser journeys. Add meaningful contract cases for sidecar allowlisting, unknown values, scope separation, missing/corrupt data and execution provenance. Browser checks cover ledger/evidence navigation, focus, seen/urgent/worsening/recovery and partial coverage. Existing Python, JavaScript and desktop/mobile checks remain mandatory. Linux CI uses synthetic fixtures only; private live-data verification runs locally without public artifacts.

## Out of Scope

Production deployment or restart; CPA, plugins, limits, authentication changes in production; live generation/model calls; shared preferences; unverified legal-date extraction; automatic repair/payment; publishing real identities or court evidence. Ops remains the tracker owner; this document does not create a second task queue.

## Further Notes

Tests and screenshots do not establish the one-minute usability target. The owner will review the isolated copy before a separately authorized installation. New protected backend/data modules cannot be installed through an unchanged presentation-only release helper; no gate is relaxed in this work.
