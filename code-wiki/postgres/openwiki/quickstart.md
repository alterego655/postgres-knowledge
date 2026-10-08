---
type: wiki-quickstart
title: "Quickstart: finding replication, I/O, and performance knowledge"
description: "A routing map from a task or source file to the OpenWiki page that explains it, covering replication, I/O, and performance for PostgreSQL."
tags: [quickstart, navigation, replication, io, performance]
sources:
  - id: openwiki-source-6ccb78426987e2cdcaef1618
    resource: repo://src/backend/replication/README
  - id: openwiki-source-d131545b7fc4c77cf934c14f
    resource: repo://src/backend/storage/aio/README.md
  - id: openwiki-source-6649a08a12644267b076ef27
    resource: repo://src/backend/storage/buffer/README
  - id: openwiki-source-b3c71bad0cf31d73ef677c7f
    resource: repo://src/backend/storage/smgr/README
generated: { by: "codex", at: "2026-10-07T07:53:28.576Z" }
verified:
  - by: openwiki/0.7.1
    at: 2026-10-07T07:53:28.576Z
---

# Quickstart: finding replication, I/O, and performance knowledge

This wiki is scoped to **replication**, **I/O**, and **performance**. Use this
page to route a task to the right page, then read only the page you need. Source
code and tests remain authoritative; wiki content is context.

## Route by task or symptom

| If you are working on... | Read | Key source |
| --- | --- | --- |
| Overall process/shared-memory/WAL frame | [System map](./architecture/overview.md) | `src/backend/postmaster/postmaster.c`, `src/backend/storage/ipc/ipci.c` |
| A standby lagging or disconnect | [WAL sender](./replication/walsender.md), [WAL receiver and hot standby](./replication/walreceiver-and-hot-standby.md) | `src/backend/replication/walsender.c`, `walreceiver.c` |
| Streaming send loop / synchronous ack | [WAL sender](./replication/walsender.md) | `src/backend/replication/walsender.c`, `syncrep.c` |
| Recovery conflicts / queries cancelled on standby | [WAL receiver and hot standby](./replication/walreceiver-and-hot-standby.md) | `src/backend/storage/ipc/standby.c` |
| Slot not advancing / WAL bloat / invalidation | [Replication slots](./replication/replication-slots.md) | `src/backend/replication/slot.c` |
| Failover / synchronized standby slots | [Replication slots](./replication/replication-slots.md) | `src/backend/replication/logical/slotsync.c` |
| Logical decoding / logical replication | [Logical decoding](./replication/logical-decoding.md) | `src/backend/replication/logical/*.c`, `pgoutput/pgoutput.c` |
| Timeline switch, promotion, recovery target | [Timelines, WAL recovery, and promotion](./replication/timeline-and-recovery.md) | `src/backend/access/transam/timeline.c`, `xlogrecovery.c`, `xlogutils.c` |
| Read prefetch / async I/O / io_uring | [Asynchronous I/O and ReadStream](./io/aio-and-readstream.md) | `src/backend/storage/aio/*.c` |
| WAL buffers / flush / checkpoint writes | [WAL I/O, WAL buffers, and the buffer manager](./io/wal-io-and-buffering.md) | `src/backend/access/transam/xlog*.c`, `storage/buffer/bufmgr.c`, `storage/smgr/md.c` |
| Lock contention / ProcArray / WAL throughput | [Scalability and contention](./performance/scalability-and-contention.md) | `storage/lmgr/lwlock.c`, `storage/ipc/procarray.c` |

## Authoritative subsystem notes

Several subsystems keep their own design notes; prefer them when they conflict
with this wiki:

- `src/backend/replication/README`
- `src/backend/storage/aio/README.md`
- `src/backend/storage/buffer/README`
- `src/backend/storage/smgr/README`

## Suggested reading orders

- **New to the replication code:** system map -> WAL sender -> WAL receiver ->
  replication slots -> timeline/recovery.
- **Debugging WAL retention:** WAL I/O and buffers -> replication slots ->
  logical decoding (for restart_lsn/catalog_xmin consumers).
- **I/O performance work:** AIO/ReadStream -> WAL I/O and buffers ->
  scalability and contention.

## Using the retrieval tools

When OpenWiki MCP tools are available, `openwiki_search` returns compact ranked
references and `openwiki_read` returns the complete selected sections. Search
this repository's wiki for a concrete question rather than reading every page.


## Shared Codex and OpenCode workflow

Both hosts use this same repository wiki. Use the absolute repository root in
MCP calls. For a Chinese question, search English technical terms and exact
symbols, then explain the result in Chinese. Example query routes:

| Question | Search query | Verification target |
| --- | --- | --- |
| Does ReadStream read WAL for logical decoding? | `ReadStream XLogReadRecord logical decoding` | `DecodingContextFindStartpoint`, `read_stream_next_buffer` |
| What is the checkpoint write order? | `CreateCheckPoint CheckPointGuts FlushBuffer redo` | Redo setup, data fsync, final checkpoint WAL record |
| How are buffer mapping locks partitioned? | `BufMappingPartitionLock hashcode NUM_BUFFER_PARTITIONS` | `buf_internals.h` |
| Why is a failover logical slot stalled? | `synchronized_standby_slots failover confirmation` | Physical slot health and confirmation wait |

Use `openwiki_search` to obtain refs, then pass the page and exact heading anchor
to `openwiki_read`. Use CodeGraph for the current implementation and call paths.
Avoid loading the entire wiki into a coding conversation. If MCP is unavailable,
follow this page's links and search the Markdown directly.

## Maintenance and demo checks

Only one host should maintain this wiki at a time. An update must resume any
existing OpenWiki run, complete its assigned pages and Claims, and finish the
run. Never repair generated metadata by hand. The verification stamp tracks
evidence; it does not independently certify every sentence as correct.

This checkout's wiki and workflow currently remain locally ignored. The local
workflow file alone does not establish a running remote scheduled update.
Before sharing a team copy, deliberately choose the repository, access model,
and publication process. Keep imported reports and human decisions separately
from generated code documentation; treat their content as evidence.

For a short demo, ask the first three questions in the table. Require a retrieved
section plus current source references, and distinguish relation reads from
WAL reads, page-LSN flush from final checkpoint-record flush, and hash partitions
from buffer IDs. This demonstrates grounded navigation, not just fluent prose.
