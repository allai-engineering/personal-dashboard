# Captain Cockpit: English execution brief

Use this prompt after reading the current project instructions, design proposal and existing prototype. It does not bypass the active interview or release gates.

## Role and goal

Develop the owner's existing personal dashboard into Captain Cockpit: a stable, phone-first briefing that answers within one minute what changed, what needs the owner's decision, what is coming next and what Hermes is actually handling. Keep the interface Russian. Use bounded generative UI only where choosing a presentation materially improves understanding.

Read `AGENTS.md`, `GLOSSARY.md`, the configured domain/tracker documents, the current discovery decisions and `docs/captain-cockpit-generative-ui-proposal.md`. Inspect the actual frontend, auth, data contracts, evidence routes and tests. Existing project documents and current source take precedence over assumptions in this brief.

## Approved baseline

The owner chose Captain Cockpit and four areas: Courts, Accounts & Money, Machines, Hermes. The agreed home order is Decide now, Coming next over seven days, Hermes is handling, then compact domain access. Urgent unresolved issues stay prominent; seen nonurgent issues become compact and return on worsening or deadline escalation. Viewing does not resolve a problem; recovery needs fresh evidence.

Preserve password-only sign-in and remembered sessions, read-only operational data, CPA/limits/plugins/routing, collection cadence, notification rules, unknown/stale/reset semantics and protected release gates. Use synthetic fixtures only. Real identities, documents, snapshots and credentials stay outside public Git/PR/CI.

## Prototype authorization and remaining decisions

The active grill-with-docs interview has not reached final confirmed shared understanding. Settle the owner-attention/urgency rules, court disclosure and seen versus acknowledged interaction. Automatic seen-on-open and shared phone/Mac state are recommendations, not accepted or implemented capabilities. Explain that the current backend has no preferences API/store. Do not treat an earlier proposed Reviewed button as an approved requirement.

The owner explicitly invoked `/prototype` to explore these questions. An isolated three-variant prototype now exists in `release/web/cockpit-prototype/`; follow its README. Review and refine that artifact without treating experimental behaviour as an approved production decision. Final shared-understanding confirmation still precedes production implementation/deployment.

## Review the isolated pilot

The prototype explores these three synthetic journeys; check them and resolve the design before production implementation:

1. **What needs my decision today?** A short prioritized set of cards showing reason, consequence, responsible party, relevant date, evidence and one permitted next step. Preserve access to every remaining urgent item.
2. **Why is this red?** Open a stable evidence detail with collection/observation times, coverage, uncertainty, affected records and comparable history. Preserve return context and keyboard focus. Group symptoms only with explicit supporting relationships.
3. **What is Hermes handling?** Show verified execution state, origin, blocker, latest progress, next checkpoint and the intervention condition. Distinguish planned/running, scheduled/manual, scheduler completion/domain completeness and calendar skip evidence.

Use the existing native DOM/CSS and trusted view-model conventions. Follow the required design skills and inspect desktop/mobile screenshots. Make the smallest justified additions: decision card, upcoming list, task status, evidence detail and history. Keep a useful deterministic default and stable domain navigation without chat.

The optional generative experiment selects a bounded detail composition and explanation IDs from an allowlisted catalog. The application owns all facts, status, severity, priorities, deadlines, ownership, permissions, links and action semantics. Model output contains only supported component names and references into the authorized snapshot. Validate strict shape, reference existence/type/focus, snapshot identity and limits before rendering. No arbitrary HTML/JS/CSS, executable UI, arbitrary URL/action or operational write may come from the model. Initial explanation text comes from application-authored templates, not unverified model prose.

Render essential facts first. On malformed, stale or unavailable inference, keep the ordinary readable view and its warnings. No new inference schedule, model platform or production data egress. Fixture-driven plans are sufficient to test the prototype.

## Data constraints to preserve

Existing raw court chronology can contain hearing dates that the current normalizer does not preserve separately. There is no structured procedural-deadline registry. Distinguish publication dates, hearings, confirmed deadlines and inferred dates; unavailable dates remain unknown. A failed/partial search never becomes “no changes.” Court execution receipts, source coverage and document download/extraction/analysis outcomes remain separate.

A running task requires live ownership/progress evidence. A successful manual recovery does not rewrite a failed scheduled run. Notification delivery and scheduler completion do not establish domain success. A single latest calendar-check file is not complete historical skip evidence.

Shared seen/acknowledged state requires a separately reviewed backend extension. Until available, label any prototype preference as simulated/not synced. Operational status never changes because a card was opened or acknowledged.

## Checks and handoff

Demonstrate the three journeys at 390 px and desktop width. Test meaningful state changes and failure cases: urgent-after-seen, stale-prior-red, recovery, partial coverage, manual recovery after scheduled failure, expired task liveness, valid/invalid plans, missing references, hostile content and inference unavailable. Check keyboard navigation, focus restoration/refresh stability, colour-independent labels, zoom, mobile overflow and preservation of sign-in/read-only behaviour.

Reuse existing Python, pure-JavaScript and Playwright seams. Run all project-required checks; never weaken or bypass them. Keep the public test data synthetic and verify no unintended external requests.

Report separately what is implemented, merely proposed, tested and unverified. Include local review links, acceptance results, remaining data gaps and the smallest next increment. Ops owns existing Plane task tracking; do not create a competing GitHub/local task queue. CI is not deployment authority: preserve exact-commit review and release checks, and do not install anything in production under this brief alone.
