# Mail secretary

Owner-authorized mail integration, 4 November 2026. The existing password gate and 30-day sessions are unchanged. `/api/snapshot` reads the separately validated metadata-only `mail-secretary.json`; it never starts an agent or mail operation. The source and native profile live in private hermes-infra under operations/mail_secretary.

The cockpit sidebar preserves the existing visual language and has four lanes. Actual current run metadata is separate from case states; a run older than ten minutes is unconfirmed. Missing data has unknown counts. Saved cases survive source/model failures, with dated evidence, explicit or unknown deadline, next step and blocker. Completion concerns reviewing a notice, never unverified payment or external resolution. Queued ops work is waiting, not active.

Only enums, timestamps, counts and opaque IDs cross the public schema. No free-form model output, subjects, names, addresses, source text or credential-bearing links. A source reference can be resolved privately by the secretary. No public endpoint performs mailbox changes.

Design: 12ui candidate D, retained layout/assets/style; integrate its mail sidebar and envelope icon only. Generated changes to quotas, Court rows, existing decisions and invented confidence percentages were excluded because they are outside scope and unsupported. The original LayerDoc was reused for the final comparison without a second generation. Desktop/mobile browser fixtures are synthetic.

Release requires full Python/JS/browser gates, exact branch and main CI, and the existing guarded integration installer for the two protected backend files. UI-only deployment cannot broaden this scope. On failure restore the previous verified release and policy; retain new private evidence and pause the mail job. No CPA or unrelated collection changes are permitted.

## v2 approved owner workflow

Daily brief and case controls follow 12ui candidate C: blue-tinted brief, source panel, blue investigation action, wrapping controls. Dynamic facts replace illustration counts/dates. Reuse the existing envelope and CSS status marks; omit duplicate decorative icons, retaining accessible native details/date controls. No raster asset is declared by the generated design. A separate authenticated POST returns only an on-demand bounded redacted source excerpt; it never enters snapshots, logs or public fixtures. Persisted proof stores offsets/hash, not text. Metadata-only evidence is explicitly labelled.

Owner actions go through the fixed local socket broker, preserving the web service's existing sandbox and authentication. Investigate queues for the next daily run; Remind uses a future Istanbul calendar date; Already resolved records an owner decision (not proof of external payment). Conflicts and save failures are visible; buttons never claim saved on an unacknowledged request. Decisions survive reload and are applied by the secretary on following runs. No mail sending/payment/cancellation is introduced. Code-review baseline: 9f2443c15c9cc4607b6aadce4f374dcbbd70a1fb. Scope explicitly includes the protected HTTP action boundary and its guarded installation.
