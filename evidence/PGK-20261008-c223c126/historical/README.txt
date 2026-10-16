WAIT FOR LSN investigation: email attachments
============================================

These are the matching before/after WAL-layout runs recorded on 2026-09-20
(CST, UTC+08:00), investigating commit:
23cbadeeb4738b8f5e615f0c5a2ef7af6111d512

Before test revision: 20efbdffeb6418afa13d6c8457054735d11c7e3a (parent)
After test revision:  23cbadeeb4738b8f5e615f0c5a2ef7af6111d512
Both used the SAME historical server binary and Perl harness built from the
after revision, with fresh clusters. These are historical 35-assertion tests,
not the later HEAD test or the recently proposed SQL API patches.

Run                      Before             After
Full runtime             20.072 s           11.297 s
Assertions passed        35                 35
Section 7d wait target   0/0301A018         0/030143F0
Section 7d COMMIT end    0/0301A000         0/030143F0

These are the 14:00 layout-capture runs. Earlier discussion also cited a
separate 09:49 timing run; do not mix its timestamps with this pair.
No test was rerun to produce this attachment package. The retained WAL was
re-decoded on 2026-09-23 and matched the saved dump text byte for byte.

Files
-----
before-instrumentation.patch / after-instrumentation.patch
  Instrumentation-only diffs against the corresponding historical test.
  Each patch was applied to its original source in a temporary directory;
  the result matched the supplied instrumented script byte for byte.

before-049-wait-for-lsn.pl / after-049-wait-for-lsn.pl
  Exact instrumented script contents used for these runs. The additions wrap
  safe_psql() with Time::HiRes timing and copy pg_wal just after section 7d
  captures its target, before launching the six waiters. The copies retain
  their original fixed /tmp capture paths. To reproduce, use fresh capture
  destinations rather than reusing the existing directories.

before-049-wait-for-lsn.tap.log / after-049-wait-for-lsn.tap.log
  Full timestamped TAP harness logs (original regress_log_layout-* files).
  The harness supplies [HH:MM:SS.mmm](elapsed) prefixes. The instrumentation
  adds "TIMING <seconds> <node> <SQL>" notes for individual safe_psql calls.
  The prefix's elapsed time and TIMING duration are DIFFERENT measurements.

before-049-wait-for-lsn.prove.log / after-049-wait-for-lsn.prove.log
  Original prove -v output, including all 35 assertions and the final result.

before-primary.log / before-standby.log (and corresponding after files)
  Original server logs, with statement timestamps and backend PIDs.

before-waldump-through-7d.txt / after-waldump-through-7d.txt
  pg_waldump -b output from the live snapshots, through the COMMIT that
  precedes section 7d's waiters. These contain 136 and 135 records respectively.

before-waldump-through-8.txt / after-waldump-through-8.txt
  Extended dumps through section 8's segment switch. The before dump includes
  the later RUNNING_XACTS record that permits section 7d to finish. These
  also include section 7e, so they contain more records than the 7d snapshots.

23cbadeeb473-test-change.patch
  The original commit's change to the test, without investigation additions.

results.json / SHA256SUMS
  Retained before/after measurements and attachment checksums.

Where to look
-------------
In the before TAP log:
  14:00:27.678  receiver-restoration safe_psql timing note
  14:00:36.221  final mixed-mode position-check timing note
  Difference: 8.543 seconds, including waiter completion and cleanup.

In the after TAP log:
  14:00:46.545  receiver-restoration safe_psql timing note
  14:00:47.512  final mixed-mode position-check timing note
  Difference: 0.967 seconds.

The final SQL itself takes only 0.008 / 0.012 seconds. The large gap is
between log entries, while the test waits for the background sessions.

In the before extended WAL dump:
  COMMIT xid 717 starts at 0/03019FD8 (34 bytes, 40 aligned).
  Its aligned end is 0/0301A000, an 8192-byte WAL page boundary.
  The wait target 0/0301A018 skips the next page's 24-byte header.
  RUNNING_XACTS starts at 0/0301A018 (54 bytes, 56 aligned), ending 0/0301A050.

In the after extended WAL dump:
  COMMIT xid 717 starts at 0/030143C8 and ends at 0/030143F0.
  That end already equals the wait target; there is no corresponding
  RUNNING_XACTS record between it and section 8's switch.

Decoding commands and provenance
-------------------------------
The matching pg_waldump binary is:
  /tmp/pg-wait-investigation/historical-install/bin/pg_waldump

Commands used (append output redirection as desired):
  pg_waldump -b -p /tmp/pg-wait-investigation/layout-before-wal \
    -s 0/03000028 -e 0/0301A000
  pg_waldump -b -p /tmp/pg-wait-investigation/layout-after-wal \
    -s 0/03000028 -e 0/030143F0
  pg_waldump -b -p /tmp/pg-wait-investigation/layout-before-complete-wal \
    -s 0/03000028 -e 0/04000000
  pg_waldump -b -p /tmp/pg-wait-investigation/layout-after-complete-wal \
    -s 0/03000028 -e 0/04000000

The extended WAL was recovered from recycled segment files of these same
completed runs, using the WAL page addresses to identify the original segment.
Its prefix through each earlier captured record end was checked byte for byte
against the live snapshot. The files were copied under the original segment
name in separate directories before decoding. No new workload was introduced.

The package contains text dumps, not binary WAL segments or database clusters.
Scripts and logs retain their original paths, timestamps, PIDs, and test data.
