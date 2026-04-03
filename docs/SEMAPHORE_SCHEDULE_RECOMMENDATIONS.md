# Semaphore Schedule Recommendations

## Goal

Allow routine operational visibility without making offline endpoints fail the whole job.

This matters because in production:

- not every workstation will be online at the same time
- notebooks may be off-network
- some endpoints will only come online during business hours

Because of that, the operational playbooks now use `ignore_unreachable: true`.

---

## Recommended Scheduling

### Run on a schedule

These are good candidates for recurring jobs in Semaphore:

- `win_ping`
- `healthcheck_agent`

Suggested cadence:

- `win_ping`: every `30m` or every `1h`
- `healthcheck_agent`: every `2h` or every `4h`

This gives enough operational visibility without generating too much noise.

### Run on demand

These should normally remain manual or tied to rollout windows:

- `install_sharex`
- `configure_sharex_spool`
- `uninstall_lightshot`
- `install_agent`

Reason:

- they change workstation state
- they are not pure diagnostics
- they are better used for rollout, remediation or version update

If you later want periodic drift correction, schedule them carefully with:

- small batches
- maintenance windows
- serial rollout

---

## Daily Cron?

A single daily cron for every playbook is not the best default.

Better model:

- diagnostics and healthchecks: recurring
- installation/update/remediation: controlled rollout

---

## Expected Behavior With Offline Hosts

When a host is unreachable:

- the playbook should continue
- the task log should still show which host was unreachable
- the overall job should not fail only because some endpoints were offline

This matches the operational reality of a large Windows fleet.
