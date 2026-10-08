# Files

- [Asynchronous I/O and ReadStream](aio-and-readstream.md) - How PostgreSQL issues, completes, and prefetches asynchronous reads: the AIO handle model, sync/worker/io_uring methods, and the ReadStream abstraction.
- [WAL I/O, WAL buffers, and the buffer manager](wal-io-and-buffering.md) - The durable write paths: WAL buffer insertion and flushing to segments, checkpoints and the redo point, and dirty-buffer flushing through smgr/md including bulk writes.
