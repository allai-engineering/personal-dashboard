# Mail subscriptions and paid services

Show a compact mail-billing section below balances using the existing resource-card and disclosure components. This is data integration, with no visual redesign or change to account quotas.

Acceptance:

- Show provider domain, supported amount and currency, amount role (last payment, upcoming charge or unpaid invoice), explicitly stated renewal date, cancellation/payment-failure notices and source references.
- Source disclosures contain mailbox identity, dated evidence, opaque reference and only a validated fixed Gmail link. Never publish bodies, subjects, excerpts, extracted quotes, model output or credentials.
- Unknown amounts/dates remain null; a passed renewal date never rolls forward. Different currencies are not summed. An email receipt does not prove a current subscription or balance.
- Show stale/inaccessible checks and partial historical coverage. No records is not absence of subscriptions.
- The server reads a closed, size-limited sidecar through the existing safe regular-file reader. A missing/invalid sidecar is unavailable, never retained as fresh. Only the authenticated snapshot exposes it; refresh remains read-only.
- Preserve password-only login, 30-day cookies, existing collection cadence, CPA and limits. Existing quota-account grouping and retired-account exclusions remain unchanged.
- Verify schema/privacy, hosted server, unknown/stale/past renewal, source links and desktop/mobile rendering through the existing CI.

The separate daily Hermes collector uses configured DeepSeek Uncensored for extraction, Jev for evidence decisions, and deterministic grounding/deduplication. Only minimal structured billing facts cross into this public-source application's data contract. All fixtures are synthetic; actual service/account records remain on the private host.
