# Captain Cockpit — throwaway UI prototype

Question: which overview structure makes it easiest to find an owner decision, understand a problem and inspect verified Hermes progress?

Run from the repository root:

```sh
npm run prototype:cockpit
```

Open `http://127.0.0.1:8880/?variant=A#overview`. The floating arrows switch between A (briefing), B (chronological ledger) and C (three-lane command deck). Left/right keyboard arrows also switch; form controls retain their normal arrow keys. All three are exploratory, not accepted product decisions.

The screen uses synthetic fixtures and an in-memory state. There is no backend connection, login, provider request, model request, persistent store or cross-device synchronization. It refuses to run on a non-loopback hostname. This is an isolated copy of the dashboard's overview shell, not a new production route; production sign-in and data fetching remain untouched.

Try these journeys:

1. Open an access or backup issue; inspect why it matters, ownership and evidence. Back returns to the originating item. Automatic seen-on-open and an explicit Seen control are alternative, unapproved experiments.
2. Open the laboratory. Make a previous failure stale; it remains unresolved. Mark it seen/acknowledged; it still does not resolve. Confirm a new successful observation to simulate recovery, or worsen access to re-escalate it.
3. Inspect Hermes. Compare planned, verified running, stale progress and a manual recovery after a scheduled failure. Completion and result coverage remain separate.
4. Select a validated presentation plan; the evidence/history composition changes. Select an invalid/unavailable plan; ordinary details and their facts remain. No live inference is used.

The laboratory exposes the relevant demo state after each action. Reload or Reset discards it. A compact seen issue remains available; urgent unresolved issues never compact. Dates are explicitly synthetic, and a hearing date does not become a procedural deadline.

This code is for a `prototype/captain-cockpit` branch only. It is not production-hardened or a deployment candidate. The bounded plan validator and state invariants include a small self-check; browser interaction checks are run as a disposable local probe, not a new maintained test suite. The earlier main-branch tests and release gates remain intact.

12ui draft generation was attempted but returned `The sponsored budget is exhausted`; no draft was produced. The local existing-style alternative uses no paid generation. Static synthetic views are imported into Superdesign through its no-generation/no-credit HTML import; the clickable prototype runs locally.

[Compare static mobile designs on the canvas](https://superdesign.dev/teams/002e88be-3ad0-4e7b-b7ce-df6579371c74/projects/f09b83c6-3f19-4080-a3a8-cba57322f1fa). These are visual drafts, while interactions and the scenario laboratory run in the local prototype. All three imported draft IDs/versions were refetched and checked; no variant was selected on the owner's behalf.

Verdict: awaiting owner review. No variant or review-state policy has been selected yet.
