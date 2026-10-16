---
id: "PGK-20261010-529f204b"
title: "Testing that unrelated wakeups do not restart recovery-conflict deadlock timers"
kind: decision
topics: [testing, recovery, replication, injection-points]
symbols: [ResolveRecoveryConflictWithBufferPin, ResolveRecoveryConflictWithLock, ProcWaitForSignal, PinCountWaiterCheckReadyForCleanup, enable_timeouts, STANDBY_DEADLOCK_TIMEOUT, INJECTION_POINT, InjectionPointRun, InjectionPointCacheRefresh, injection_points_attach, injection_points_detach, injection_notice, pg_log_backend_memory_contexts, wait_for_event, wait_for_log, wait_for_catchup, log_min_messages, standby-conflict-timeouts-armed]
evidence_state: mixed
delivery: local-only
applicability:
  repository: postgres
  inspected_commit: 9330457473cae55cc804ac73065517ff089ab37f
  tested_commit: unknown
  branch: codex/recovery-buffer-pin-wakeups-v9
  patch_identity: "Local commit 9330457473c 'Handle unrelated wakeups during recovery buffer pin and lock waits' (author alterego655); not posted or merged as of capture"
  configuration: "Test section requires a build with injection points (enable_injection_points=yes) and the injection_points extension; standby uses max_standby_streaming_delay=-1, deadlock_timeout=1d, log_startup_progress_interval=0, log_min_messages='warning, startup:notice'"
  platform: "macOS (Darwin 25.6) for earlier scratch-build runs; the committed notice variant has not been run"
last_checked: 2026-10-10
sources:
  - type: conversation
    id: "Claude Code session ab6576a4-96b7-463b-b5dc-d6e2563f844e, 2026-09-30 to 2026-10-10"
    scope: "Review and redesign of the 031 wakeup test, harness helper semantics, injection-point attach/detach mechanics, precedent research; summarized, not archived verbatim"
  - type: source
    id: "PostgreSQL excerpts at 9330457473cae55cc804ac73065517ff089ab37f"
    path: "../evidence/PGK-20261010-529f204b/source-excerpts.md"
  - type: conversation
    id: "Codex capture, 2026-10-10; conversation URL unavailable"
    scope: "User requested capture of research into established non-end-to-end regression tests; updates the existing record"
  - type: source
    id: "Historical REINDEX and VACUUM test evidence rechecked 2026-10-10"
    path: "../evidence/PGK-20261010-529f204b/committed-test-precedents.md"
  - type: commit
    id: "5bbdfa8a18d, 661643dedad, 38172d1856b, 1e4e5783e7d, ca2b5443e2d, fd6ecbfa75f (local postgres history)"
    scope: "Commit messages read for precedent of mechanism-level and wakeup-invariant tests"
supersedes: []
superseded_by: []
---

# Testing that unrelated wakeups do not restart recovery-conflict deadlock timers

## Current conclusion and applicability

The bug being fixed (Vitaly Davydov's standby deadlock-detector report): an unrelated wakeup of the startup process during a buffer-pin or relation-lock recovery-conflict wait made the resolver cancel its timers and return. The caller then re-entered with a fresh *relative* deadlock deadline. A stale kernel alarm left by `timeout.c` can repeat this indefinitely, so `STANDBY_DEADLOCK_TIMEOUT` never fires and, under `max_standby_streaming_delay = -1`, recovery can stay stuck.

**Decision:** check timer rearming directly, with deadlock outcomes covered in separate sections. Subject to the logging and long-timeout assumptions below, the 031 section checks that after an unrelated wakeup the resolver does **not set its timers again**, using a single injection point marker reached right after `enable_timeouts()` and the `notice` action. The outcome ("deadlock is detected on time") is left to the timing-based sections (5: buffer-pin deadlock; 6: relation-lock deadlock, added by the same commit).

Reasons:

- Directly checking rearming avoids waiting for the full repeated-alarm sequence to cause an indefinite recovery stall. This does not establish that all outcome tests require a controllable clock or that slow machines necessarily miss the bug.
- `deadlock_timeout = 1d` puts normal expiration far beyond the expected test duration. It does not disable the timer or make expiration impossible; the inference assumes observation completes before that deadline.

Evidence strength differs by claim:

- **Precedent research:** verified by source and commit inspection on 2026-10-10.
- **Ordering argument:** verified by source reading.
- **Earlier capture reports an experiment with the `wait` action** (scratch injection build, 2026-09-30; original run artifacts were not inspected in this update):
  - passed 2/2;
  - restoring either premature return failed the matching assertion.
- **The committed `notice` variant has not been run.** The main checkout is built without injection points.

## Test design (as committed in 9330457473c)

Per kind (`bufferpin`, `lock`):

1. Create the conflict. `VACUUM FREEZE` against a standby cursor pin, or `LOCK TABLE` against a standby `ACCESS SHARE` lock.
2. `wait_for_event('startup', BufferCleanup|relation)`.
   - The marker sits between `enable_timeouts()` and `ProcWaitForSignal`.
   - So when the wait appears, the first, legitimate pass over the marker has already happened, with nothing attached.
3. `injection_points_attach('standby-conflict-timeouts-armed', 'notice', '$kind')`.
   - The condition string is matched against the marker's `arg`, so only the resolver under test can fire.
4. Save the log offset. Call `pg_log_backend_memory_contexts(startup_pid)` to set startup's latch.
5. `wait_for_log("logging memory contexts of PID …")`. This proves startup handled the interrupt, so it left the original wait.
6. `wait_for_event` again. Startup is back in a wait. Any NOTICE from setting the timers again was written before it re-entered the wait.
7. `unlike(slurp_file(log, offset), /notice triggered for injection point standby-conflict-timeouts-armed/)`.
8. Detach the point, then `COMMIT` the holder, then `wait_for_catchup(..., 'replay', lsn('insert'))`.
   - The detach is required: re-attaching an attached name errors (`injection point "%s" already defined`), and a non-local attach outlives its session.
   - It comes before `COMMIT` so later replay cannot write a stray notice.
   - The catchup is the only check, in the last round, that the new loop exits once the pin or lock is released.
   - It uses the insert LSN because `VACUUM FREEZE` writes no commit record and may leave WAL unflushed.

Markers in `standby.c` (one name; the path is the arg):

- `INJECTION_POINT("standby-conflict-timeouts-armed", "lock")` at line 702
- `INJECTION_POINT("standby-conflict-timeouts-armed", "bufferpin")` at line 864

## Root cause of the design choices

### Why the ordering makes the absence check sound

`wait_for_event` matching after `wait_for_log` means startup reached a new wait after handling the wakeup. In the buggy code, setting the timers again (which hits the marker and writes the NOTICE) happens before that new wait. With the standard TAP setup capturing startup stderr directly, the NOTICE is written before startup enters that new wait, so it is available for the subsequent file read. This argument must be revisited if logging is redirected through an asynchronous logging collector; observing the wait alone would not prove that another process has flushed the message.

There is one caveat in the lock round. The fixed loop's "wait again" path and the buggy re-entry both show wait event `relation`, so step 6 cannot tell them apart. That is acceptable: step 6 only marks when the log is complete, and step 7 makes the distinction.

### How attach and detach work (source-verified)

- `INJECTION_POINT` compiles to nothing without `USE_INJECTION_POINTS`; otherwise it calls `InjectionPointRun`.
- Attach writes `{name, library, function, private_data}` into a 128-slot shared-memory array.
  - Each slot's `generation` is odd while in use and even while free.
  - The fields are written, then a write barrier, then the generation is incremented.
- Detach increments the generation (back to even) and does nothing else. No process is notified.
- Each process caches the resolved entry together with its slot and generation. `InjectionPointCacheRefresh` reuses the cached entry while the generation still matches and otherwise searches the array again, all without locking.
- The callback runs in the process that reaches the hook.
- The condition is enforced by the module callback (`injection_point_allowed`), not by core. A non-matching resolver still calls `injection_notice`, which then returns immediately.

### Harness helper semantics relied on

- `wait_for_event` wraps `poll_query_until` on `pg_stat_activity`.
  - It croaks on failure.
  - It allows up to `10 × timeout_default` attempts at 100 ms each, plus a psql connection per attempt, so the limit is on attempts, not wall-clock time.
  - It compares `wait_event` only, not `wait_event_type`.
- `wait_for_log` wraps `wait_for_file`.
  - It re-reads the log from the given offset every 100 ms and croaks after `10 × timeout_default` attempts.
  - It returns the new end-of-file offset.
  - The offset must be recorded before triggering the event.

## Precedent research: is a non-end-to-end test established?

Yes: committed regression tests check internal decisions using injection-point notices without reproducing every downstream consequence. This is precedent, not a universal rule or a guarantee that reviewers will accept this particular patch.

### Directly verified examples (2026-10-10 update)

| Commit | What the test checks | Consequence it does not reproduce |
| --- | --- | --- |
| [5bbdfa8a18dc56d3e64aa723a68e02e897cb5ec3](https://git.postgresql.org/pg/commitdiff/5bbdfa8a18dc56d3e64aa723a68e02e897cb5ec3), 2024-09-09, REINDEX CONCURRENTLY | `reindex_conc.sql` rebuilds simple, expression, partial, and expression-plus-partial indexes; expected notices distinguish safe from unsafe classification. The marker follows the `idx->safe` decision used for `PROC_IN_SAFE_IC`. | It does not arrange a competing operation that incorrectly skips waiting for the rebuild. |
| [661643dedad97f8b924991fdc739b1f47b0fb60b](https://git.postgresql.org/pg/commitdiff/661643dedad97f8b924991fdc739b1f47b0fb60b), 2025-06-25, VACUUM options | `vacuum.sql` uses empty tables with differing main/TOAST options and compares notices for resolved `index_cleanup` and `truncate` values, including multi-relation VACUUM. | It does not demonstrate actual dead index entry removal or physical file truncation. |

Michael Paquier committed both changes. The REINDEX message credits Michail Nikolaev for the fix and explains the choice of a simpler test with more coverage. The VACUUM message credits Nathan Bossart for the backend fix and Paquier for tests that inspect option values; it explicitly motivates them by speed, reliability, and coverage. The messages distinguish backport scope: REINDEX fix through 14 and VACUUM fix through 13, with these injection-point tests only through 17. These are statements from the commits, not an independently audited release matrix.

The [archived historical source evidence](../evidence/PGK-20261010-529f204b/committed-test-precedents.md) preserves both commit messages, SQL, expected output, and focused backend diffs. These were reread from local Git objects for this update; the original discussion threads were not reread.

**Application to 031:** the added section checks that a deliberately unrelated wakeup does not rearm the resolver timers. Existing buffer pin and added relation lock sections check deadlock errors and statistics separately. This is a reasonable division of coverage. It does not prove the timer stays active after that particular wakeup, nor reproduce the complete indefinite-stall sequence. A hypothetical cancellation-without-rearming implementation exposes a coverage gap, not nondeterminism in the narrow assertion, and is not a demonstrated defect in the current fix.

### Other precedents retained from the earlier capture

These entries retain the earlier capture's attribution and inspection scope; only the two examples above were independently rechecked for this update.

- **Closest precedent: `test_misc/t/011_lock_stats.pl`** (ca2b5443e2d, April 2026, co-authored by Fujii Masao). It covers fd6ecbfa75f by:
  - waking a lock waiter with `pg_log_backend_memory_contexts()`;
  - confirming the wakeup through "logging memory contexts";
  - asserting from the log that "still waiting for" appeared exactly once.

  The wakeup tool, proof-of-wakeup step and log-based invariant are the same as here. Fujii also reviews Vitaly's thread.
- **Injection-point NOTICE as evidence of an internal decision, in committed bug fixes:**
  - 5bbdfa8a18d, REINDEX CONCURRENTLY safe flag: "Michail has proposed a different test, but I have added something simpler with more coverage."
  - 661643dedad, VACUUM options: the injection tests are "faster, more reliable than the tests originally proposed by Shihao, and they also provide more coverage."
  - 38172d1856b, hash aggregation spill paths.
  - 1e4e5783e7d, nbtree incomplete-split repair.

  Their expected-output files also enforce absence of unexpected notices. Hash aggregation and B-tree tests can also assert output or completion, so they should not all be described as purely internal checks; REINDEX and VACUUM above establish the narrower point directly.
- **`test_misc/t/005_timeouts.pl`:** "Relying on sleep proved to be unstable on buildfarm." That test still asserts the outcome; the injection point is used only for synchronization.

What is new here:

- **Channel.** The two directly verified NOTICE-as-evidence examples are regression tests in the same backend (`injection_points_set_local()`) checked through expected output. This test reads a server-log NOTICE written by an auxiliary process. The pieces exist separately:
  - positive TAP matches on injection messages in the log: `test_shmem/t/001_late_shmem_alloc.pl`, `libpq/t/005_negotiate_encryption.pl`;
  - negative log checks: 011's `!log_contains`, `058_shutdown_crash_restart.pl`.
- **`log_min_messages = 'warning, startup:notice'`.** Per-process syntax from 38e0190ced7 (Feb 2026, PG19+). No TAP precedent; only `guc.sql` uses it.
- **A cross-process absence check that relies on code ordering** rather than an expected-output file.

## Limitations and trade-offs

1. **Tied to the implementation.** A correct alternative fix that set the timers again with the same absolute deadline would fail this test.
2. **Requires test-only `INJECTION_POINT` markers** in production code.
3. **Borrows a wakeup source.** `pg_log_backend_memory_contexts` is used for its side effect of setting the latch; 011 does the same.
4. **Gap: the timer still firing after a wakeup.** The test shows the timer is not set again, not that it still fires. A change that silently cancelled the timer on wakeup would pass this section.
   - Suggested supplementary coverage, not implemented: send the same wakeup in the real-timer lock section after observing the lock wait. Scheduling could still deliver it after timeout expiration, so this does not deterministically close the gap. No additional instrumentation is required merely to exclude this hypothetical faulty implementation.
5. **Runs only where injection points are enabled**, not on every buildfarm animal.
6. **Not backpatchable as is.** By branch:

   | Branch | Status |
   |---|---|
   | 19 / master | everything present |
   | 18 | `INJECTION_POINT(name, arg)` exists; wait event is `BufferPin`; no per-process `log_min_messages` |
   | 17 | `INJECTION_POINT(name)` with no arg; no `check_extension` |
   | 14–16 | no injection points (031 exists) |

   Memory-context requests to auxiliary processes work on 15+.

## Rejected or superseded approaches

- **`wait` action plus a custom polling loop with a `$valid_until` window (half of `deadlock_timeout`) and `usleep`.**
  - This was the earlier design. It ran correctly, and `injection_wait` does not consume the latch, so cleanup does not hang.
  - The time-budget loop risked false failures and was more machinery than needed.
  - The 1-day timer supplies a practical margin for omitting the validity window; it is not an unconditional timing guarantee.
- **`poll_query_until` as a drop-in replacement for the loop.** Not equivalent: cleanup needed the observed value, and the `BackgroundPsql` session timer is session-wide.
- **`adjust_conf` for settings absent from `postgresql.conf`.** It only rewrites existing lines; use `append_conf`.
- **Claim that `EnableStandbyMode` disables the startup-progress timer for good.** Refuted: `ResetUnloggedRelations` → `begin_startup_progress_phase` (`reinit.c`) turns it back on. The test sets `log_startup_progress_interval = 0`.
- **Separate marker names per path.** Replaced by one name with the path as `arg` plus a condition-string attach. Precedent for one name at two sites: `ri-before-pk-lock` in `ri_triggers.c`.
- **Attaching with the `error` action** (works at default log levels, avoiding per-process `log_min_messages`). Considered but not adopted: an ERROR in startup is fatal for recovery.

## Capture update and verification limits

The 2026-10-10 Codex capture reconciles the discussion following the question about established non-end-to-end test patterns into this existing record. It adds direct historical evidence rather than creating a duplicate. It also narrows earlier absolute claims about one-day timer expiration and outcome-test determinism, and records the logging assumption. Earlier reported experiment counts remain attributed to the previous capture; they are not new results. No database tests, builds, probes, or reproducers were run for this update. Submission and upstream merge status were not checked.

## Open questions

- Run the committed notice variant on an injection-points build. Check that it passes, and that reverting each resolver's loop fails the matching assertion.
- Whether reviewers accept the per-process `log_min_messages` line, or prefer another way to surface the marker.
- How to adapt the test for 17–18 if the fix is backpatched (Vitaly's fix was discussed as backpatch 15+).

## Sources and related knowledge

- [Source excerpts with line numbers and hashes](../evidence/PGK-20261010-529f204b/source-excerpts.md): `standby.c` markers and loops, the 031 section, and the 011 wakeup check.
- [PGK-20261008-5c464fad: Choosing TAP SQL helpers and proving WAL-wait outcomes](PGK-20261008-5c464fad-tap-sql-sessions-and-wal-wait-assertions.md): helper lifetimes (`query_safe`, `background_psql`, `poll_query_until`) used by this test.
- Related local reproducers, not archived here; they are in `/Users/qqj/dev/postgres-untracked-work/repro/`:
  - `911_standby_lock_deadlock_after_lock_wait.pl`: non-deterministic lock-path reproducer. Earlier runs: master fails 4/4; with the lock loop it passes 5/5.
  - `912_standby_late_buffer_pin.pl`: the separate late-pin fast-path bug (CF 6445).
- Mail thread: "Deadlock detector fails to activate on a hot standby replica", root Message-ID `44c24dcf-5710-410f-b1b6-d10b315f3d51@postgrespro.ru`. Not re-retrieved for this capture.
