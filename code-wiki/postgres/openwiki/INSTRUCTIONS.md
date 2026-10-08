# Repository wiki brief

This wiki is primarily for an active PostgreSQL contributor working on
**Replication**, **I/O**, and **Performance**. Optimize for durable internals
knowledge that a coding agent can retrieve to reason about that work, not for
general user documentation.

## Scope — prioritize

- **Replication**: physical and logical replication; WAL sender/receiver;
  streaming replication and hot standby; replication slots (physical/logical,
  failover/synchronized slots, slot synchronization and invalidation);
  logical decoding (decoder, ReorderBuffer, catalog/snapshot handling,
  replication origins and progress); timeline management and recovery
  conflicts; synchronous replication.
- **I/O**: asynchronous I/O (AIO, io_uring, worker pools); ReadStream and
  buffer reads/prefetching; the buffer manager; checkpointer and background
  writer; WAL I/O (XLogWrite, WAL buffers, segment lifecycle); storage manager
  (smgr/md) and direct I/O; I/O statistics.
- **Performance**: scalability and contention (LWLocks, ProcArray, shared
  memory structures); WAL throughput and group commit; checkpoint/vacuum
  performance; wait events; representative benchmarks.

## Writing guidance

- Ground every material claim in specific source: prefer bounded references to
  named functions and files (e.g. `XLogSendPhysical` in
  `src/backend/replication/walsender.c`). Explain ownership, control and data
  flow, ordering/lifecycle, invariants, and failure semantics.
- Prefer a small number of meaningfully-scoped pages over a flat inventory.
- Use Mermaid diagrams where a sequence/state/flow diagram carries more signal
  than prose (e.g. the walsender send loop, slot synchronization, ReadStream
  state machine, checkpoint WAL flush ordering).
- Cross-link related pages so a reader can move from subsystem overview to WAL
  sender to slots to logical decoding without dead ends.

## Evidence and maintenance quality

- Cite the bounded implementation or explanatory comment that establishes each
  behavior, not just a one-line function declaration. Preserve stable Claim IDs
  when correcting the same proposition.
- Treat this checkout as the version boundary. Distinguish implemented behavior
  from design goals in README files; do not infer released-version support.
- Keep relation-page I/O, WAL-file I/O, local durability, and remote write/flush/
  replay acknowledgements distinct. Explain important ordering and ownership.
- Preserve the English wiki for reliable symbol search; include English query
  examples for Chinese-speaking contributors and respond in the user's language.
- Keep source-grounded internals separate from local patch speculation. Add
  representative focused tests where supported by repository evidence.
- OpenCode and Codex use the same wiki and a single maintenance queue. Do not
  edit generated Claims, indexes, provenance, or run state directly.

## Excluded material

- Client tools (psql, pg_dump), platform/porting details, build system
  minutiae, extension/contrib modules unrelated to the focus areas, and
  documentation-only or localization changes.
- Do not document local scratch artifacts, benchmark result HTML, or patch
  drafts (see `.openwikiignore`).

## Focus files (weight these in research)

`src/backend/access/transam/xlog.c`, `xlogutils.c`, `xlogrecovery.c`,
`src/backend/replication/walsender.c`, `walreceiver.c`, `slot.c`,
`slotsync.c`, `logical/`, `src/include/replication/`,
`src/backend/storage/buffer/`, `src/backend/storage/aio/`,
`src/backend/storage/smgr/`, `src/backend/utils/activity/pgstat*.c`.
