---
type: io-subsystem
title: "WAL I/O, WAL buffers, and the buffer manager"
description: "The durable write paths: WAL buffer insertion and flushing to segments, checkpoints and the redo point, and dirty-buffer flushing through smgr/md including bulk writes."
tags: [io, wal, buffers, checkpointer, smgr, direct-io]
sources:
  - id: openwiki-source-254cb721ac59e7e28b65943f
    resource: repo://src/backend/access/transam/xact.c
  - id: openwiki-source-3e8a000a3c74409e35b6a5ef
    resource: repo://src/backend/access/transam/xlog.c
  - id: openwiki-source-5f9c4c81c6bb0d093a71feb1
    resource: repo://src/backend/storage/buffer/bufmgr.c
  - id: openwiki-source-2e30a1e3ae4e095d4f495859
    resource: repo://src/backend/storage/smgr/bulk_write.c
  - id: openwiki-source-8239e657c28f394a74d5ef04
    resource: repo://src/backend/storage/smgr/md.c
  - id: openwiki-source-4db46eea5c06805e9f611ec6
    resource: repo://src/include/access/xlog_internal.h
generated: { by: "codex", at: "2026-10-07T07:53:28.576Z" }
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T07:53:28.576Z
---

# WAL I/O, WAL buffers, and the buffer manager

Two independent but coupled write paths make changes durable: the WAL path
(record then flush) and the data path (dirty shared buffer then smgr). This page
covers both, plus the checkpoint machinery that bounds how much WAL must be
retained.

## WAL insertion and WAL buffers

A WAL record is emitted by `XLogInsertRecord()`. Insertion reserves space in the
shared WAL buffers with `ReserveXLogInsertLocation()`. Concurrent inserters
coordinate through WAL insertion locks:

- `WALInsertLockAcquire()` / `WALInsertLockAcquireExclusive()`
- `WALInsertLockRelease()`
- `WALInsertLockUpdateInsertingAt()`

When the current WAL buffer page is exhausted, `AdvanceXLInsertBuffer()` makes
the next page available, writing out the previous one if necessary.

## Flush path to durable WAL

`XLogWrite()` writes buffered WAL to segment files; `XLogFlush()` makes a given
WAL position durable. Commits requiring synchronous local durability call it;
`RecordTransactionCommit()` also has an asynchronous branch that registers an
LSN for later flushing, so commit acknowledgement alone does not imply a flush.
The WAL writer uses `XLogBackgroundFlush()` to flush proactively.

Segment open/create/install and cleanup are handled by `XLogFileOpen()`,
`XLogFileInit()`, `InstallXLogFileSegment()`, and `RemoveOldXlogFiles()`.

## Segment naming and lifecycle

WAL files live under `pg_wal` and are named by timeline and segment number.
`XLogFileName()` and `XLogFilePath()` (with `XLOG_FNAME_LEN` == 24) build those
names. `wal_segment_size` is restricted to the range 1 MB to 1 GB. Old segments
are recycled or removed once they fall behind the last redo pointer and are no
longer needed by any consumer (including replication slots).

Source: `src/include/access/xlog_internal.h` (`XLogFileName`,
`XLogFilePath`, `XLOG_FNAME_LEN`), `src/backend/access/transam/xlog.c`
(`XLogFileInit`, `InstallXLogFileSegment`, `RemoveOldXlogFiles`).

## Checkpoints and the redo point

`CreateCheckPoint()` coordinates a checkpoint and calls `CheckPointGuts()`,
which flushes data buffers via `CheckPointBuffers()` -> `BufferSync()`.
`GetRedoRecPtr()` / `GetFullPageWriteInfo()` expose the redo pointer that
decides whether full-page writes are needed; a checkpoint advances that pointer,
which establishes a new recovery starting point. Slots and archiving impose
additional retention constraints; checkpoint completion alone does not permit
all older WAL to be removed.

For an online checkpoint in this checkout, `XLOG_CHECKPOINT_REDO` establishes
the redo point before the main data-write phase. `CheckPointGuts()` writes
checkpoint data and performs queued fsyncs. Only afterward does the checkpointer
insert and flush the final checkpoint record and update the control file.
`FlushBuffer()` enforces WAL-before-data for permanent buffers by flushing
through the page LSN before the data write. The redo marker itself is not
unconditionally flushed at checkpoint start.

```mermaid
sequenceDiagram
    participant CP as Checkpointer
    participant BM as Buffer Manager (shared buffers)
    participant SMGR as smgr / md
    participant WAL as WAL segments
    CP->>CP: CreateCheckPoint()
    CP->>WAL: Insert online redo marker and establish redo point
    CP->>BM: CheckPointGuts and CheckPointBuffers
    BM->>WAL: FlushBuffer ensures WAL through permanent page LSN
    BM->>SMGR: Write checkpoint-required data pages
    CP->>SMGR: ProcessSyncRequests
    CP->>WAL: Insert and flush final checkpoint record
    CP->>CP: Update control file, then eligible WAL cleanup
```

## Buffer manager and smgr

`ReadBuffer_common()` serves reads from the shared buffer pool or the storage
manager. `FlushBuffer()` writes a dirty buffer via smgr, landing in `md.c`'s
`mdwritev()` (with `mdwriteback()` and `mdimmedsync()` for writeback and
immediate durability). `register_dirty_segment()` queues fsync requests.

Checkpoint flushing walks buffers with `BufferSync()` -> `SyncOneBuffer()`;
the background writer pre-flushes with `BgBufferSync()`. `CheckpointWriteDelay()`
paces the checkpointer so it does not stall the system.

`md.c` names relation segment files via `_mdfd_segpath()`, opens/creates them
with `mdopenfork()` / `mdcreate()`, extends them with `mdextend()`, and chooses
its open flags (including direct-I/O behavior) in `_mdfd_open_flags()`.

## bulk_write: bypassing the buffer manager

Creating or rewriting large relations uses `bulk_write.c`, which bypasses the
buffer manager. `smgr_bulk_flush()` sorts pending pages, uses `smgrextend()`
for extension (including filling gaps), and `smgrwrite()` for existing blocks:

- `smgr_bulk_start_rel()` / `smgr_bulk_start_smgr()` open a bulk write.
- `smgr_bulk_write()` appends a page; several pages are batched into one WAL
  record to reduce header overhead.
- `smgr_bulk_flush()` sorts pending writes and issues them.
- `smgr_bulk_finish()` completes the build.

Because it bypasses the buffer manager, bulk write must register the relation
for fsyncing at the next checkpoint itself.

## Related

- Read side and prefetching: [Asynchronous I/O and ReadStream](./aio-and-readstream.md)
- WAL shipping to standbys: [WAL sender](../replication/walsender.md)
- Contention on the WAL insertion path: [Scalability and contention](../performance/scalability-and-contention.md)
