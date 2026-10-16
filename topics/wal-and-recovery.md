# WAL and Recovery Investigations

Cases involving checkpoints, WAL durability ordering, recovery, and timeline selection.

- [PGK-20261008-5c464fad: Choosing TAP SQL helpers and proving WAL-wait outcomes](../records/PGK-20261008-5c464fad-tap-sql-sessions-and-wal-wait-assertions.md) — Use when choosing persistent versus one-shot SQL calls, coordinating concurrent waiters, or reviewing the strength of replay/write completion assertions.

- [PGK-20261008-c223c126: WAL insertion targets beyond page headers can stall standby waits](../records/PGK-20261008-c223c126-wal-insertion-page-boundary-waits.md) — Use when choosing WAIT targets, diagnosing boundary stalls, or separating incidental catalog WAL savings from replication latency.

- [PGK-20261010-529f204b: Testing that unrelated wakeups do not restart recovery-conflict deadlock timers](../records/PGK-20261010-529f204b-recovery-wakeup-timer-test-design.md) — Use when designing deterministic tests for timer or wakeup invariants in startup/recovery waits, using injection-point notices as log evidence, or justifying a mechanism test over a timing-based outcome test.

[Back to topic navigation](README.md)
