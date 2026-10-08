# Files

- [Scalability and contention: locks, ProcArray, and WAL throughput](scalability-and-contention.md) - The shared structures that become scalability bottlenecks and their mitigations: LWLocks and tranches, ProcArray/snapshot handling, WAL insertion and group commit, plus the wait-event and pg_stat_io observability used to find them.
