# Isolated Captain Cockpit review

This candidate is not installed in production. It uses the existing authenticated file-only HTTP server and a separate, owner-private staging directory outside every Git checkout. There is no provider generation, production collector trigger or new schedule.

## Private capture

Prepare a mode-0600 JSON config outside Git, in a mode-0700 directory owned by the local user:

```json
{
  "dashboard": {
    "alias": "existing-ssh-alias",
    "ssh_config": "/absolute/path/to/existing/ssh-config",
    "data_root": "/absolute/path/to/published-dashboard-data",
    "auth_path": "/absolute/path/to/existing-dashboard-auth"
  },
  "hermes_home": "/absolute/path/to/existing/hermes-home",
  "court": {
    "alias": "existing-court-ssh-alias",
    "data_root": "/absolute/path/to/existing/court-case-root"
  }
}
```

Only already-authorized SSH aliases are accepted. The dashboard/Hermes reader uses noninteractive sudo; Court reads as the existing SSH account. Fixed files and SQLite queries are allowlisted. Execution SQLite uses `mode=ro` and `query_only`, with WAL visibility. No Hermes runtime initialization is imported. Source prompts, outputs, raw errors, case names and document text are not exported by the new reader.

From the repository:

```sh
python3 tools/capture_cockpit.py --config /private/path/sources.json --private-dir /private/path
python3 tools/stage_cockpit.py --private-dir /private/path --port 8891
```

Open `http://127.0.0.1:8891/` on this computer. The existing password verifier is copied once through the encrypted SSH channel; the production session-signing key is never copied. A separate staging signing key preserves password-only login and the 30-day cookie without sharing production cookies. The loopback server is not a public phone-access release. Never commit or attach this private directory, auth verifier, cookies, source snapshots or live screenshots.

Capture is manual. The refresh button only rereads local files; it does not run SSH or collectors. Observations retain their original times. In particular, the two-minute execution snapshot can expire while this review copy remains open. Recapture explicitly when a new observation is needed; do not change the existing collection cadence to make a screenshot look healthy.

## Evidence limits

- A narrow KAD receipt is separate from broader court coverage. Counts are scoped to their actual source. Saved KAD cases do not prove every court was checked.
- No reliable structured upcoming hearing/deadline feed was found. Those dates remain unavailable; no prose-derived deadlines are created. Quota resets and stored job launches have distinct labels.
- Latest scheduled and manual execution outcomes are retained separately. A matching live process incarnation is required before a ledger row becomes active. Process completion is not domain-result coverage.
- Seen state persists only opaque tags in this browser tab. Changes attract attention again. Unknown data retains a previously observed issue while the page is running; incident history is not persisted across reloads. Cross-device synchronization is deferred.
- Existing account identities are useful to the owner and stay inside this private authenticated copy. Public tests, screenshots and CI use synthetic data only.

## Release boundary

The candidate changes protected backend/data files as well as UI. The unchanged automatic UI broker must reject such a release. Do not rebaseline trusted hashes or bypass a gate. Production installation requires a separately reviewed integration release, with an agreed publisher location, host transport, source permissions, collection policy, exact CI commit and rollback package. The staging commands above do not prepare or execute that production change.
