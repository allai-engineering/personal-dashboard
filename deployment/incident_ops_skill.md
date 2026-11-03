---
name: dashboard-incident-work
description: Claim dashboard technical incidents in the existing ops checkpoint, record actual diagnostic stages and blockers, and request an owner decision only when needed.
platforms: [linux]
---

# Dashboard incident work

Use the existing ops owner run and Plane/private checkpoint. The dashboard checkpoint is delivery/progress evidence, not a second issue tracker. Preserve any existing task reference; reconcile it before creating or delegating work.

1. Run `sudo -n -u hermes -g cpa-dashboard /usr/local/bin/dashboard-incident status`. Select queued or materially changed incidents. Each record carries a source `subject` for identification, plus a `record_id` and version `fingerprint`; both must match when reporting. Read the matching saved dashboard/fleet evidence to understand the impact. Unknown coverage is an investigation task, not proof of an outage.
2. Before diagnosis, report `accepted` with the action you actually start. Record another stage before preparing/testing a fix or checking recovery. The report command binds to this live native ops execution and rejects another process or stale incident version. A command failing to record is a real telemetry blocker: report it once; do not claim dashboard progress exists.
3. Diagnose independently using existing fixed probes, runbooks and access. Reuse installed approved recovery/integration capabilities within their preconditions. Prepare and test a bounded procedure when one is missing. A lack of procedure is work for Hermes to prepare, not a generic question for the owner. CPA, current limits, login, unrelated services and source schedules remain outside this task. Sending/deleting mail, spending, destructive cleanup and new remote access retain their existing exact-action boundaries.
4. Before ending, report each accepted incident:
   - `waiting`: a concrete external/technical blocker or expected quota reset; select its blocker code.
   - `needs_user`: an actual needed login, payment or specific owner approval, with one concrete decision and expected action. Try existing authorized access first. Record the decision; the normal existing owner notification reports it once, without another notification channel.
   - `resolved`: only after fresh source evidence marks this incident `source_state=clear` and independent verification confirms the outcome. Completed process, cleared error flag, or missing source is insufficient. Run `scan` after verified recovery to reconcile the fixed cached source; it does not start external collectors.

Report payload, JSON on stdin to `sudo -n -u hermes -g cpa-dashboard /usr/local/bin/dashboard-incident report`:

```json
{"record_id":"machine-example","fingerprint":"COPY_CURRENT_64_HEX","state":"waiting","action":"inspect_service","blocker":"no_safe_procedure","decision":null,"task_ref":null}
```

Use Python `subprocess.run(["sudo","-n","-u","hermes","-g","cpa-dashboard","/usr/local/bin/dashboard-incident","report"], input=json.dumps(payload), text=True, check=True)` or a private input file. Do not construct a shell command from source text. Never include credentials, raw logs, mail text or prompts. `task_ref` is the existing Plane/checkpoint identifier when available.

Actions: `diagnose`, `check_access`, `inspect_disk`, `inspect_service`, `inspect_backup`, `prepare_fix`, `test_fix`, `verify_recovery`, `wait_supervisor`, `wait_reset`, `check_balance`, `check_job`, `check_source`.

Blockers: `none`, `no_access`, `no_safe_procedure`, `active_work`, `awaiting_source`, `upstream`, `execution_failed`; owner-only: `login_required`, `payment_required`, `owner_approval`.

`accepted` means work was claimed; actual activity is separately checked against native PID/incarnation. A run ending without a final per-incident report is displayed as stopped without an outcome. Final reports preserve the last action and time. Notification frequency and the single existing ops schedule stay unchanged.

The sudo capability changes only this fixed helper process to the dashboard read group; it keeps uid hermes. Only exact `scan`, `status` and `report` invocations are allowed. It supplies neither a root shell nor a general group command.
