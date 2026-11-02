# Captain Cockpit: bounded generative UI pilot

Status: reviewable design proposal with an isolated exploratory prototype, 2 November 2026. No production cockpit, new live-data integration, inference call or deployment has been performed. The working interface language remains Russian; this proposal is in English for handoff.

## 1. Goal and decision status

Within one minute, the owner should understand what changed, what needs their decision, what is coming next and what Hermes is actually handling. Keep a familiar application shell and a useful default briefing without requiring chat or model availability.

### Approved by the owner

- Captain Cockpit is the product direction.
- First-version areas: Courts, Accounts & Money, Machines, Hermes.
- Home order: Decide now; Coming next, covering seven days; Hermes is handling; compact access to the four areas.
- Urgent unresolved issues remain prominent. Seen nonurgent issues become compact and regain prominence after worsening or deadline escalation.
- Viewing an issue does not resolve it. Recovery requires fresh evidence.
- Preserve sign-in, CPA limits, schedules, notification rules and read-only operational access.

### Recommendations awaiting agreement

- Whether opening details automatically marks an item seen, or an explicit Reviewed control is required. The latest UX recommendation is automatic seen-on-open; the earlier explicit-control recommendation was not accepted or implemented.
- Shared seen state across phone and Mac. This is a design requirement candidate, not an existing capability.
- The proposed owner-attention criteria, court-card disclosure level and exact urgency thresholds.
- Evidence detail navigation, history retention, grouping rules and this bounded generative presentation contract.

There is no final confirmation that the active interview has reached shared understanding. The owner subsequently invoked `/prototype`, explicitly authorizing an exploratory artifact to help resolve the remaining decisions. That prototype is now on a separate branch; no variant or review-state policy is silently accepted. The interview's final confirmation still precedes production implementation, not this authorized discovery experiment. The proposal itself is not new production deployment authority.

## 2. Current state and reusable parts

Inspected source baseline: `0e57bb0` in the existing personal-dashboard repository. This is a source assessment, not a fresh production-health attestation.

| Existing part | Reuse | Missing for the pilot |
| --- | --- | --- |
| Hash navigation and overview/subscriptions/balances/machines pages | Keep current deep links and stable domain access | Courts and Hermes views; stable issue/detail identifiers |
| Attention rows, account/resource cards, badges and native details | Retain surfaces, typography, spacing, relative/absolute time helpers | Ownership, next checkpoint, evidence reference and reason fields |
| Quota/balance/machine view models | Preserve unknown/stale/reset semantics and existing display thresholds | Cross-domain decision records; no AI reclassification |
| Validated snapshot GET and read-only operations/integrations contracts | Existing retrieval/authentication boundary | Court/task/evidence contracts and sanitized history |
| Password-only login, remembered sessions and origin/CSP controls | Preserve unchanged | No preference API or shared seen-state store exists |
| Python tests, view-model assertions and desktop/mobile Playwright | Extend existing behaviour seams | Cockpit transitions, focus restoration, hostile plans and provenance checks |

The frontend uses native DOM modules and CSS; there is no React application to migrate. Existing DOM creation uses text nodes rather than model-produced HTML.

The automatic UI installer protects the backend, data-model modules, login, tests and CI. A new adapter must use the approved integration path. New protected contracts or source files need their own reviewed scope; do not relax gates or automatically rebaseline trusted hashes to fit this proposal. Draft documentation is not deployment-ready metadata.

### Court and task evidence gaps

- Daily Court receipts distinguish `ok`, `partial` and `error`, with run identity, scope, counts, errors and report/snapshot references. Older case state can be carried forward after a failed collection; its presence does not establish a fresh check.
- Raw KAD chronology can contain `HearingDate` and `HearingPlace`. The inspected normalizer retains the place but does not preserve a separate normalized hearing timestamp. The pilot must not invent that date from the normalized record.
- There is no structured procedural-deadline registry. Evidence-linked analyses may discuss dates, but automatic extraction/confirmation is a separate data task. An event publication date is not a deadline.
- SOJ motion is currently text-oriented. Search coverage and completeness require their own receipts; a partial search cannot become “no new cases.”
- Act download, extraction and analysis are separate outcomes. Awaiting publication is distinct from a downloaded and analyzed document.
- Hermes execution history distinguishes scheduled and direct/manual origins. `completed` and successful notification delivery do not establish complete court collection. Combine execution evidence with the domain receipt.
- A running label needs live execution ownership/progress evidence. A scheduled task is not running; a manual recovery must retain its origin and cannot replace a failed scheduled result.
- Calendar skip needs evidence for that execution/date. A last-check file alone is not historical proof of every past skip.

No new court collection or live provider request is needed for the synthetic pilot.

## 3. The three end-to-end journeys

### A. What needs my decision today?

Open the normal cockpit home. The application selects eligible records and sorts by its reviewed urgency rules and relevant dates. An initial short list has a visible total and an accessible route to every remaining urgent issue; truncation cannot imply there are no more.

A decision card contains a meaningful headline, what changed, why it matters, the responsible party, a relevant date or “not known,” observation age and one permitted next step. That step opens details, approved evidence or an existing authorized destination. It never invokes repair, payment, token refresh or a new collection through generated UI.

The recommendation is that personal decisions/access/payment needs belong in Decide now. Work belongs in Hermes is handling only when evidence establishes that it is underway. An unassigned failure remains explicit; the interface must not imply that Hermes has taken ownership.

Court example, entirely synthetic: a hearing is confirmed for a future date, while the action needed from the owner is not established. Show “Review the hearing details,” not “File an appeal by this date.” The latter requires separately confirmed evidence and authority.

### B. Why is this red?

Open the card into a stable detail route. Retain the originating section, item and scroll position so Back restores context. The evidence view shows the underlying observation, source identity, observation time, receipt time, last successful check, coverage and known uncertainty. Show a comparison/history only when actual comparable observations exist.

Example: a collector is unreachable and account quotas are stale. The application may group them only with an explicit dependency/correlation reference. The parent explains the supported relationship and lists every affected observation. Without such evidence, keep separate symptoms and say the cause is unconfirmed.

Red is always accompanied by a text label and reason. A failed collection can make current state unknown while retaining a historical problem. It does not prove service failure, and it cannot clear the last incident.

### C. What is Hermes handling?

Open Hermes is handling, then a task. Show the actual execution identity, scheduled/manual origin, verified phase, blocker, most recent progress, next checkpoint and the condition requiring owner intervention. Unknown fields are explicitly unknown.

The detail keeps planned work, a live run, a failed scheduled run and a successful manual retry distinct. A task can be marked completed by the scheduler while its domain result is partial; display both facts. Resolution of an incident requires domain evidence, not a green task badge alone.

If active ownership/progress expires, change the presentation to “progress not confirmed,” preserving the prior state as history. A proposed future checkpoint is labelled planned rather than promised or measured.

## 4. Phone-first concrete design

The text below is the original wireframe specification. A runnable, fixture-only prototype now compares a briefing, ledger and command deck; see [prototype instructions](../release/web/cockpit-prototype/README.md). It reuses the existing light background, green ink, card surfaces, warning colours and system font. Production navigation and authentication are untouched.

At 390 px, use one readable column, 44 px minimum primary targets, wrapping labels and a visible freshness summary. At desktop width, keep the same content order and stable navigation; evidence may occupy a neighbouring column. No automatic rearrangement while the owner is reading or using the keyboard.

Illustrative text and values below are synthetic. The clock and fixture date are fixed for testing; these are not current observations.

```text
HOME · 390 px
Captain Cockpit             [Refresh]
Some sources incomplete · [Coverage]
[Cockpit] [Courts] [Accounts] [More]

DECIDE NOW                           2
┌ Account access needs renewal        ┐
│ Quota could not be checked          │
│ Owner: You · Checked 10 min ago     │
│ Next: review the access requirement │
│ [Open details]                     │
└────────────────────────────────────┘

COMING NEXT · 7 DAYS
Court hearing · in 2 days
Confirmed date · [Open event]

HERMES IS HANDLING
Collection retry · verified running
Latest progress 2 min ago
Next checkpoint: planned 14:30
[View progress]

Courts · partial  | Accounts · 1 issue
Machines · fresh | Hermes · 1 active
```

```text
EVIDENCE · 390 px
[Back to cockpit]  Access observation
Access check failed · quota unknown
Observed 14:10 · received 14:11
Last successful observation: yesterday

What changed / Why it matters
Affected records: 2 · relationship verified
[Each underlying observation]

History: successful → failed → stale
Uncertainty: current quota is unavailable
[Open permitted source]
```

```text
TASK · 390 px
[Back to cockpit] Collection retry
Verified running · manual recovery
Latest progress 14:20
Next checkpoint 14:30 · planned
Blocker: none recorded

Earlier scheduled run: failed
Domain coverage: partial
Owner intervention: only if access is required
[Execution evidence] [Domain evidence]
```

The More control is a proposed compact mobile disclosure, not an accepted navigation redesign. Keep domain entry points available without requiring chat. Do not add decorative charts, a chat-only homepage or a separate agent platform.

## 5. Small component contract

The application creates trusted view models. Presentations resolve opaque record IDs against that model. Model output cannot supply values, statuses, severity, dates, links, ownership, executable callbacks or HTML.

| Allowed component | Bound inputs | Behaviour |
| --- | --- | --- |
| `decision_card` | incident/decision ID | Known reason, consequence, ownership, time and approved next step |
| `upcoming_list` | confirmed event IDs | Seven-day chronology; distinguish event/hearing/deadline kinds |
| `task_status` | execution ID | Origin, progress evidence, blocker and checkpoint |
| `evidence_detail` | observation ID | Provenance, freshness, uncertainty and allowlisted evidence references |
| `history` | validated history ID | Comparable observations with gaps; no interpolation or invented values |

Reuse an ordinary history list for the first pilot. A richer comparison is justified only when multiple records have aligned units, timestamps and coverage. A selected comparison never manufactures missing measurements.

### Proposed presentation plan

```json
{
  "schema": "cockpit-view-plan-v1",
  "snapshot_id": "synthetic-snapshot-1",
  "focus_id": "synthetic-incident-1",
  "blocks": [
    {"component": "evidence_detail", "record_ids": ["synthetic-observation-1"]},
    {"component": "history", "record_ids": ["synthetic-history-1"]}
  ],
  "explanation_ids": ["access-check-failed-current-quota-unknown"]
}
```

This is a proposed production contract. The exploratory prototype implements a narrower fixture-only validator: strict keys, three allowed detail component types, at most four blocks/four references per block, exact snapshot/focus identity and supported unique typed references. Decision/upcoming components remain ordinary deterministic UI. No live model output or explanation generation is used. A production implementation still needs reviewed limits and a full parser boundary. Every ID must exist in the same authorized snapshot, be compatible with its component and be permitted for that focus.

The initial explanation set is application-authored text with verified values filled by the application. The model can select relevant explanation IDs. Arbitrary factual prose is excluded from the pilot: schema validation cannot establish that free text is true. A later free-text explanation needs its own grounding/evaluation and privacy decision.

### Separate facts and presentation

- Observation: opaque ID, source/evidence references, observed/received time, last successful check, typed outcome, coverage and freshness. A collection error and an observed service failure are distinct.
- Incident: observation IDs, application-calculated severity, reason, ownership basis, permitted step, first/last observation, change identity and supported correlation references.
- Event: date with offset/timezone semantics, kind (`published_event`, `hearing`, `confirmed_deadline`, `inferred_date`), evidence and confirmation status. A date-only source remains date-only; no invented midnight timestamp. Inferred dates are clearly separated and do not silently become confirmed reminders.
- Task: execution ID, actual state, scheduled/manual origin, latest verified progress, ownership/liveness evidence, domain result coverage and an optional explicitly planned checkpoint.
- Presentation preference: seen and acknowledged state are independent of resolution. Opening evidence cannot change source outcome. Persistence rules remain unapproved.

Do not give the model a generic field-path binding language, arbitrary URLs, arbitrary action names, data retrieval tools or write tools. Use text nodes, fixed event handlers and application-resolved destinations. Apply the same authentication and evidence authorization after every plan lookup; an opaque ID is not authorization.

## 6. Where generative UI helps, and where it does not

The home shell, priorities, seven-day list and required warnings are deterministic. They work immediately with inference disabled. Refresh reads the existing snapshots and never adds a collector run or model schedule.

The optional experiment is inside an explicitly opened detail view: select a supported explanation/history composition for “why red?” or an execution/domain-evidence composition for “what is Hermes handling?” Evaluate this against the direct-component baseline. Adopt inference only if the owner understands the answer faster or more accurately without losing provenance.

The application renders required status/evidence first. An optional plan may enrich the view once; it cannot remove urgent items, coverage warnings or underlying observations, change urgency, reorder navigation or move keyboard focus. Keep the current view stable while reading. No model request on every poll or page load. Any future inference routing, privacy allowance, latency limit and spend budget must be explicit; prototype fixtures require no live inference.

### Existing components versus one constrained renderer

| Option | Fit here | Proposed choice |
| --- | --- | --- |
| Existing DOM components plus a small strict plan dispatcher | Reuses the current stack and trusted view models; five fixed types need no general layout engine | First pilot |
| `json-render` core/catalog with a custom renderer | Provides schema/catalog primitives, but this native-DOM app would still need its renderer/bindings and dependency review | Reconsider only if the validated component catalog becomes materially larger or genuinely nested |

The official json-render documentation describes typed catalogs and custom schema/renderer support. Its supplied examples do not make adoption cost-free for this application. The recommendation to keep the existing DOM for this pilot is a project-specific inference. [Introduction](https://json-render.dev/docs), [Custom schema and renderer](https://json-render.dev/docs/custom-schema), [Schemas](https://json-render.dev/docs/schemas).

A2UI is useful background for trusted declarative catalogs across client/agent boundaries. Google's October article also describes choosing among known layouts rather than generating an entire screen. The pilot adopts that bounded-selection principle without adding another renderer or inferring any promised performance gain here. [A2UI](https://a2ui.org/), [Google's inference-format discussion](https://developers.googleblog.com/fast-reliable-a2ui/).

### Failure behaviour

Malformed JSON, an unknown component, stale snapshot identity, missing/mismatched references, forbidden fields, inference timeout or unavailable inference produces the ordinary deterministic detail with a short “standard view” notice. No blank page, raw model exception or silent loss of facts. Do not fetch a URL or run an action supplied by the plan. Persist no raw prompts, documents or responses as debugging logs.

## 7. Freshness, evidence and review rules

Use per-source/per-field freshness from trusted data contracts; receipt time cannot refresh an old observation. Preserve current quota thresholds, reset semantics and source-specific TTLs. A seven-day display horizon is not a seven-day freshness window. Court expectations follow the existing working-day schedule; a holiday is neither an unexplained missed check nor proof that a skip occurred.

Keep unknown, stale, partial, failed and confirmed outcomes distinguishable in text. An aggregate green state requires known coverage; a missing field never supplies zero. Previously red evidence becoming stale leaves the unresolved issue visible with “current state unconfirmed,” rather than turning green or silently disappearing.

Seen means exposed to the owner; acknowledged means an explicit owner statement of awareness; resolved means confirmed recovery/completion. No inferred acknowledgement from a tap. The seen-on-open recommendation needs an exact interaction definition, accessibility checks and agreement before implementation. Re-escalation should key off a meaningful source change or a reviewed deadline threshold, not every new snapshot timestamp.

Shared state is not implemented: the current API supports snapshot reads and login, not preference writes. A production preference store would be a separately reviewed backend extension limited to display metadata; operational data and CPA remain read-only. A prototype could simulate preferences and label them “demo / not synced,” never claim phone/Mac synchronization.

Evidence links resolve through authenticated, allowlisted application references. Filesystem paths, arbitrary private-server URLs and raw documents are not public static assets. Any eventual document viewing/download requires its own authorization path; initial detail can show sanitized evidence metadata. All examples, plans and CI fixtures remain synthetic.

## 8. Acceptance checklist for the implementation

Unchecked items below are required demonstrations, not current claims.

- [ ] At 390 px and desktop widths, all three journeys work without chat and keep stable navigation; no horizontal page overflow.
- [ ] The owner can locate a decision, understand a failure and inspect real-versus-planned task status without losing list position or context. Test the one-minute goal with the owner; automated tests alone cannot prove it.
- [ ] Every material status exposes source, observation age and coverage; publication, hearing, confirmed deadline and inferred date stay distinct.
- [ ] Urgent unresolved items survive seen/acknowledged transitions. Seen nonurgent items compact; a meaningful worsening re-escalates them.
- [ ] Failed collection, partial coverage, stale prior red, missing values, expired quotas and confirmed recovery have separate fixtures and asserted outcomes.
- [ ] Scheduled failure plus manual recovery retains both outcomes. Planned is not running; expired liveness is unknown; completed-but-partial is explicit.
- [ ] Correlated incidents retain every child observation. Unsupported correlation remains unconfirmed.
- [ ] Valid plan renders expected components. Unknown type, hostile HTML text, forbidden URL/action, wrong snapshot, missing reference, type mismatch, excessive size and unavailable inference fall back safely with the same essential facts.
- [ ] Keyboard users can navigate, open details and return; focus returns to its trigger, survives refresh, remains visible and is never moved by inference. Use native links/buttons; announce only meaningful status changes. Verify at 200% text zoom and with reduced motion.
- [ ] Mobile targets are at least 44 px; status does not rely on colour. Headings, accessible names, reading order and evidence disclosure are verified.
- [ ] Authentication, 30-day session behaviour, origin/security headers, rejected operational writes, cadence and protected production boundaries remain covered by existing checks.
- [ ] Synthetic screenshots are inspected at desktop/mobile widths using the project's required design workflow. No real data, credentials, court texts, provider requests or inference calls enter fixtures/CI.

Test seams: prefer pure view-model/plan validation tests, the existing snapshot/server boundary and the current Playwright journeys. Test externally visible outcomes; avoid tests that merely repeat component markup.

## 9. Smallest incremental implementation plan

These are proposed increments for ops to track, not newly created tasks or GitHub issues.

1. Review the owner-authorized exploratory prototype, resolve urgency, court disclosure and seen/acknowledged semantics, then obtain confirmation of shared understanding. Record qualifying decisions without speculative ADRs.
2. Use the isolated, phone-first synthetic prototype to compare all three journeys and fixture-driven presentation choices. It adds no framework, backend writes, model service or production deployment. Preserve its code on the prototype branch; treat the final production implementation as a separate increment.
3. Prepare a reviewed read-only Court/task/evidence adapter contract through the existing integration path. Preserve hearing-date semantics, receipt coverage and execution origin. Structured legal deadlines remain unavailable until separately evidence-confirmed. Verify isolated fixtures before any live-data integration.
4. Connect the deterministic cockpit end to end, preserving existing routes/authentication/semantics. Add optional validated detail selection only if prototype review justifies it. Shared review-state persistence remains a separately scoped backend increment if chosen.
5. Follow the existing ops/Plane ownership, independent review, exact-commit GitHub CI, protected-scope release and rollback checks. This proposal and the research follow-up confer no new production deployment authority.

## 10. Verification record

Implemented: documentation and an isolated native-HTML/CSS/JS prototype with three variants, synthetic journeys, in-memory seen/acknowledgement states and bounded presentation-plan selection/fallback. Existing discovery decisions are preserved. Proposed: the production contracts, adapters, shared state and release increments above.

Existing baseline checks run locally: 52 Python tests passed; all five `test_*.mjs` scripts passed; both desktop/mobile Playwright cases passed. Existing synthetic overview screenshots were inspected at 1440 px and 390 px. These cover the existing dashboard, not the new cockpit acceptance criteria. The current rows are compact and readable but lack ownership, checkpoints and per-incident evidence journeys.

Documentation checks: whitespace, balanced code fences, parseable JSON examples and local Markdown link targets passed. No new validator, accessibility or user-performance result is implied by these document checks.

Prototype verification: a disposable Chromium probe checked 33 responsive/interaction conditions, including all variants at 390/1440 px, focus return, seen/urgent/re-escalation, stale/recovery, task origin/status, plan rejection/fallback and zero external requests. A small pure-state self-check covers invariants. Later Back/skip-link refinements were checked in the app browser. These checks do not establish owner usability or production readiness.

Not implemented: shared review state, new live court/task adapters, actual generative inference or production deployment. Cross-device synchronization, legal-deadline extraction, comprehensive assistive-technology testing and the one-minute user goal remain unverified. 12ui generation returned an exhausted sponsored budget; local existing-style variants were authored instead, with no-credit static imports into Superdesign for visual review.
