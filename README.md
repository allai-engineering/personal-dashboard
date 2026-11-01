# Personal dashboard

A compact, read-only dashboard for subscriptions, quota reset times, provider balances and machine problems. Low remaining quotas come first; unknown, stale and expired observations never become free capacity. Interface language: Russian.

This repository contains source and synthetic test data. Real snapshots, account identities, credentials and deployment secrets belong only in protected server storage. Publishing this code does not publish a live dashboard or grant access to it.

## Checks

```sh
PYTHONPATH=release python3 -m unittest discover -s . -p 'test_*.py'
for f in test_*.mjs; do node "$f"; done
npm ci
npx playwright install --with-deps chromium
npm run test:browser
```

The browser checks cover desktop and mobile widths, password-only login,30day sessions, navigation, low quotas, missing values, disabled accounts, authorization separation, read-only methods, JavaScript errors and horizontal overflow. Screenshots use synthetic example.test accounts. CI uses standard GitHub-hosted Linux runners; it has no production connection or provider secrets.

## Deployment

Hermes prepares UI changes on a branch, pushes and waits for green CI, reviews synthetic desktop/mobile screenshots, then merges and installs the tested main commit through a fixed server-side UI release helper. Only presentation files can be deployed by that helper. Login, backend, quota interpretation, collectors, schedules, CPA, plugins and provider limits stay outside its write scope.

Each release carries its commit identity. Concurrent/stale baselines are rejected. Post-install password/session/API/asset checks must pass; failed activation restores the prior release. An ordinary design improvement needs no new owner approval. Ask only when a necessary login or payment blocks the task. Broadening the helper's protected scope requires a separate owner request.

Public source is not a public license grant. No third-party license has been added on the owner's behalf.
