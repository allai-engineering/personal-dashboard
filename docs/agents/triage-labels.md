# Triage labels

Keep the five canonical roles as the shared vocabulary. Ops maps these roles to the existing Plane workflow; the strings below are vocabulary, not instructions to create tracker labels or statuses.

| Role in mattpocock/skills | Shared vocabulary | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Maintainer needs to evaluate the task |
| `needs-info` | `needs-info` | Waiting for more information |
| `ready-for-agent` | `ready-for-agent` | Fully specified and ready for agent implementation |
| `ready-for-human` | `ready-for-human` | Requires human implementation |
| `wontfix` | `wontfix` | Will not be actioned |

When a skill asks to apply or remove a label, return the proposed role and rationale to ops for the existing task. Do not create or change live labels or statuses in GitHub or Plane.

See `issue-tracker.md` for task ownership and handoff rules.
