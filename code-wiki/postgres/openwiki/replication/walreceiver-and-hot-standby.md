---
type: replication-subsystem
title: "WAL receiver and hot standby"
description: "How a standby connects and streams WAL: the walreceiver main loop, received/flushed/applied position tracking, hot-standby feedback, and recovery-conflict resolution while serving read-only queries."
tags: [replication, wal-receiver, hot-standby, recovery-conflicts, feedback]
sources:
  - id: openwiki-source-09f8616e4f6ee2f36d3e306a
    resource: repo://src/backend/access/transam/xlogrecovery.c
  - id: openwiki-source-cb6e854ca8972f59de73d8e5
    resource: repo://src/backend/replication/walreceiver.c
  - id: openwiki-source-07c25d096b3a0189f781d383
    resource: repo://src/backend/replication/walreceiverfuncs.c
  - id: openwiki-source-2ae9142c4f1200cf975a56ae
    resource: repo://src/backend/storage/ipc/standby.c
  - id: openwiki-source-f2e0c07935966ec3caf3aecb
    resource: repo://src/include/storage/standby.h
generated: { by: "codex", at: "2026-10-07T07:53:28.576Z" }
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T07:53:28.576Z
---

# WAL receiver and hot standby

A standby has two cooperating pieces: a **WAL receiver** process that streams
WAL from the primary and writes it to `pg_wal`, and the **startup process** that
replays it while the system serves read-only queries. This page covers the
receiver, the position feedback, and the conflict resolution that keeps replay
from being blocked forever.

## Connecting and streaming

The startup process requests a stream with `RequestXLogStreaming()`, providing
the timeline and start LSN, and the receiver begins at
`WalReceiverMain()`. It waits for a start position with
`WalRcvWaitForStartPosition()` and fetches any missing timeline history files
with `WalRcvFetchTimeLineHistoryFiles()`.

Incoming messages are decoded by `XLogWalRcvProcessMsg()`; WAL data is written
by `XLogWalRcvWrite()` and flushed by `XLogWalRcvFlush()`. `XLogWalRcvClose()`
handles the end of a segment. On shutdown, `ShutdownWalRcv()` stops the worker
and `WalRcvDie()` runs the exit path.

Sources: `src/backend/replication/walreceiverfuncs.c`
(`RequestXLogStreaming`, `ShutdownWalRcv`, `WalRcvRunning`, `WalRcvStreaming`,
`WalRcvGetState`), `src/backend/replication/walreceiver.c`
(`WalReceiverMain`, `WalRcvWaitForStartPosition`,
`WalRcvFetchTimeLineHistoryFiles`, `XLogWalRcvProcessMsg`, `XLogWalRcvWrite`,
`XLogWalRcvFlush`, `XLogWalRcvClose`, `WalRcvDie`).

## Position tracking

Three positions matter and are distinct:

| Position | Getter | Meaning |
| --- | --- | --- |
| Received/written | `GetWalRcvWriteRecPtr()` | WAL written to the standby's `pg_wal` |
| Flushed | `GetWalRcvFlushRecPtr()` | WAL fsync'd on the standby |
| Applied/replayed | `GetXLogReplayRecPtr()` | WAL replayed by the startup process |

`GetXLogReceiptTime()` reports when the current WAL was received, which frames
`GetReplicationApplyDelay()` and `GetReplicationTransferLatency()`. These feed
`synchronous_commit` semantics and `pg_stat_wal_receiver`
(`pg_stat_get_wal_receiver`).

Source: `src/backend/replication/walreceiverfuncs.c`
(`GetWalRcvFlushRecPtr`, `GetWalRcvWriteRecPtr`, `GetReplicationApplyDelay`,
`GetReplicationTransferLatency`), `src/backend/replication/walreceiver.c`
(`pg_stat_get_wal_receiver`),
`src/backend/access/transam/xlogrecovery.c` (`GetXLogReplayRecPtr`,
`GetXLogReceiptTime`).

## Feedback to the primary

The receiver sends the primary its progress so the primary can advance the
standby's slot and release WAL:

- `XLogWalRcvSendReply()` reports write/flush/apply positions.
- `ProcessWalSndrMessage()` handles the primary's reply (its WAL end and time).
- `XLogWalRcvSendHSFeedback()` sends **hot-standby feedback**, including the
  standby's xmin and catalog xmin horizons, to protect row versions needed by
  standby queries and logical decoding. This reduces cleanup conflicts; it
  does not eliminate all recovery-conflict classes.
- `WalRcvComputeNextWakeup()` schedules the next reply;
  `WalRcvRequestApplyReply()` forces one when the apply position advances.

Source: `src/backend/replication/walreceiver.c` (`XLogWalRcvSendReply`,
`ProcessWalSndrMessage`, `XLogWalRcvSendHSFeedback`,
`WalRcvComputeNextWakeup`, `WalRcvRequestApplyReply`).

## Recovery conflicts

Replay must sometimes wait for a read-only query that is using data it wants to
change or truncate. The `RecoveryConflictReason` reasons are:

- `RECOVERY_CONFLICT_LOCK` — a backend holds a lock blocking replay.
- `RECOVERY_CONFLICT_SNAPSHOT` — a backend holds a snapshot blocking cleanup.
- `RECOVERY_CONFLICT_LOGICALSLOT` — a logical slot must be invalidated.
- `RECOVERY_CONFLICT_BUFFERPIN` — a buffer pin blocks replay.
- `RECOVERY_CONFLICT_STARTUP_DEADLOCK` and
  `RECOVERY_CONFLICT_BUFFERPIN_DEADLOCK` — deadlock resolution involving the
  startup process.

Resolution functions wait, cancel queries, or terminate conflicting sessions
according to the conflict class and applicable delay rules:

- `ResolveRecoveryConflictWithSnapshot()` / `...SnapshotFullXid()`.
- `ResolveRecoveryConflictWithVirtualXIDs()`, `...Tablespace()`,
  `...Database()`, `...Lock()`, and `ResolveRecoveryConflictWithBufferPin()`.
- `CheckRecoveryConflictDeadlock()` with `StandbyDeadLockHandler()`,
  `StandbyTimeoutHandler()`, and `StandbyLockTimeoutHandler()`.
- `WaitExceedsMaxStandbyDelay()` enforces `max_standby_streaming_delay` /
  `max_standby_archive_delay`; `LogRecoveryConflict()` records the conflict.

For a buffer-pin conflict, trace the holder, startup-process wait, and
wakeup/cancellation path. Claims about a particular premature-wakeup bug need
a separate reproducer and patch review.

Sources: `src/include/storage/standby.h` (`RecoveryConflictReason`),
`src/backend/storage/ipc/standby.c` (`ResolveRecoveryConflictWithSnapshot`,
`ResolveRecoveryConflictWithVirtualXIDs`,
`ResolveRecoveryConflictWithTablespace`, `ResolveRecoveryConflictWithDatabase`,
`ResolveRecoveryConflictWithLock`, `ResolveRecoveryConflictWithBufferPin`,
`SendRecoveryConflictWithBufferPin`, `CheckRecoveryConflictDeadlock`,
`StandbyDeadLockHandler`, `StandbyTimeoutHandler`, `WaitExceedsMaxStandbyDelay`,
`GetStandbyLimitTime`, `LogRecoveryConflict`).

## Promotion interaction

When finishing recovery, `FinishWalRecovery()` calls `XLogShutdownWalRcv()`
before writing new local WAL, so a live receiver cannot overwrite those records.
Do not describe promotion as a request to restart the receiver. Promotion also
switches the node to a new timeline.
See [Timelines, WAL recovery, and promotion](./timeline-and-recovery.md).

```mermaid
sequenceDiagram
    participant SP as Startup process
    participant WR as WAL receiver
    participant PRI as Primary
    SP->>WR: RequestXLogStreaming(tli, lsn)
    WR->>PRI: START_REPLICATION
    PRI-->>WR: WAL data
    WR->>WR: XLogWalRcvWrite / Flush
    SP->>SP: ApplyWalRecord (replay)
    WR->>PRI: XLogWalRcvSendReply + HS feedback
    PRI->>PRI: advance slot, release WAL
```

## Related

- Physical slot that retains the WAL: [Replication slots](./replication-slots.md)
- Replay and timeline logic: [Timelines, WAL recovery, and promotion](./timeline-and-recovery.md)
- Sender side: [WAL sender](./walsender.md)
