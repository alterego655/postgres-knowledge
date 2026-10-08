# Files

- [Logical decoding and logical replication](logical-decoding.md) - How logical decoding turns WAL records into a change stream: the decode dispatch, reorder buffer, snapshot builder, replication origins and progress, output plugins such as pgoutput, and the apply workers on the subscriber.
- [Replication slots: persistence, invalidation, and synchronization](replication-slots.md) - The replication slot lifecycle: durable state, restart_lsn/catalog_xmin retention, acquire/release locking, invalidation causes, and synchronized/failover slots.
- [Timelines, WAL recovery, and promotion](timeline-and-recovery.md) - WAL recovery as it relates to replication: redo and record replay, timeline IDs and history files, recovery targets and apply delay, standby restartpoints, and promotion.
- [WAL receiver and hot standby](walreceiver-and-hot-standby.md) - How a standby connects and streams WAL: the walreceiver main loop, received/flushed/applied position tracking, hot-standby feedback, and recovery-conflict resolution while serving read-only queries.
- [WAL sender: physical streaming and synchronous replication](walsender.md) - How a walsender process streams WAL to a standby or logical subscriber, processes standby feedback, drives synchronous replication acknowledgements, and handles timeline changes and termination.
