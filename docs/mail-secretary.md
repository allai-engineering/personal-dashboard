# Mail secretary

Owner-authorized mail integration, 4 November 2026. The existing password gate and 30-day sessions are unchanged. `/api/snapshot` reads the separately validated metadata-only `mail-secretary.json`; it never starts an agent or mail operation. The source and native profile live in private hermes-infra under operations/mail_secretary.

The cockpit sidebar preserves the existing visual language and has four lanes. Actual current run metadata is separate from case states; a run older than ten minutes is unconfirmed. Missing data has unknown counts. Saved cases survive source/model failures, with dated evidence, explicit or unknown deadline, next step and blocker. Completion concerns reviewing a notice, never unverified payment or external resolution. Queued ops work is waiting, not active.

Only enums, timestamps, counts and opaque IDs cross the public schema. No free-form model output, subjects, names, addresses, source text or credential-bearing links. A source reference can be resolved privately by the secretary. No public endpoint performs mailbox changes.

Design: 12ui candidate D, retained layout/assets/style; integrate its mail sidebar and envelope icon only. Generated changes to quotas, Court rows, existing decisions and invented confidence percentages were excluded because they are outside scope and unsupported. The original LayerDoc was reused for the final comparison without a second generation. Desktop/mobile browser fixtures are synthetic.

Release requires full Python/JS/browser gates, exact branch and main CI, and the existing guarded integration installer for the two protected backend files. UI-only deployment cannot broaden this scope. On failure restore the previous verified release and policy; retain new private evidence and pause the mail job. No CPA or unrelated collection changes are permitted.
