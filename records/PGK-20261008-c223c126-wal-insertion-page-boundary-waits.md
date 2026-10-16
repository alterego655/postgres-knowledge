---
id: "PGK-20261008-c223c126"
title: "WAL insertion targets beyond page headers can stall standby waits"
kind: investigation
topics: [wal-and-recovery, replication]
symbols: [pg_current_wal_insert_lsn, GetXLogInsertRecPtr, GetXLogInsertEndRecPtr, XLogBytePosToRecPtr, XLogBytePosToEndRecPtr, XLogRecordAssemble, smgr_targblock, WAIT FOR LSN]
evidence_state: supported
delivery: local-only
applicability:
  repository: postgresql/postgresql
  tested_commit: "23cbadeeb4738b8f5e615f0c5a2ef7af6111d512"
  branch: "historical isolated build; later HEAD comparison separately scoped below"
  patch_identity: "10076ae9e497cf59407d0f47ce7fee77762b82aa and 32ad7baa3954a7626e782943c9816748a54ec49f (local proposals)"
  configuration: "8192-byte WAL pages; 8-byte alignment; 1-second replay delay; synchronous commit enabled; fresh clusters"
  platform: "macOS; historical Clang build with assertions"
last_checked: "2026-10-08"
sources:
  - type: experiment
    path: "../evidence/PGK-20261008-c223c126/historical/README.txt"
  - type: control-experiment
    path: "../evidence/PGK-20261008-c223c126/layout/results.json"
  - type: source
    path: "../evidence/PGK-20261008-c223c126/source-excerpts.md"
  - type: conversation-summary
    path: "../evidence/PGK-20261008-c223c126/conversation-scope.md"
supersedes: []
superseded_by: []
---

# WAL insertion targets beyond page headers can stall standby waits

## Current conclusion and applicability

`pg_current_wal_insert_lsn()` can return the next insertion address **after the next page header** when the last reserved record ends exactly at a WAL page boundary. A standby may have processed every available record while remaining short of this target. Waiting then needs another WAL record, not merely delivery of the existing WAL. This was reproduced in historical section 7d of `src/test/recovery/t/049_wait_for_lsn.pl`.

Commit `23cbadeeb473` made that particular run faster by changing earlier catalog page selection and therefore moving section 7d away from the boundary. It did not remove the general target-selection hazard. The savings in WAL volume were incidental to backend reuse and page occupancy; they are not a general performance guarantee for combining SQL calls.

This record preserves historical experiments and local API proposals, not a claim that those proposals are merged or released. Capture-time checkout HEAD was `e797f46d6a58e28bbcada551e3f3bac7126c6b8d`; the runtime experiments below used other explicitly identified revisions. No runtime tests were repeated during capture.

## Reproduction and diagnosis

The [historical attachment package](../evidence/PGK-20261008-c223c126/historical/README.txt) contains exact instrumented tests, timestamped TAP output, server logs, original commit diff, and decoded WAL. Both variants used the same historical server and Perl harness built from `23cbadeeb4738b8f5e615f0c5a2ef7af6111d512`; the before test came from parent `20efbdffeb6418afa13d6c8457054735d11c7e3a`. Clusters were fresh, WAL compression was off, full-page writes and hint protection were enabled, and the standby had a one-second replay delay. Harness fsync settings do not turn synchronous commit into asynchronous commit.

| Controlled layout run | DDL backend sessions | DDL catch-ups | 7d target | Runtime |
| --- | ---: | ---: | --- | ---: |
| Before | 2 | 2 | `0/0301A018` | 20.072 s |
| After | 1 | 1 | `0/030143F0` | 11.297 s |
| After, but split DDL sessions | 2 | 1 | `0/0301A018` | 19.012 s |

All three passed 35 assertions. The split-session control retained only one catch-up yet restored the before WAL layout through section 7d, excluding commit timestamps. See [control results](../evidence/PGK-20261008-c223c126/layout/results.json) and [decoded control WAL](../evidence/PGK-20261008-c223c126/layout/split.dump).

The removed catch-up accounted for about one second. The large additional delay was elsewhere: in the matched before TAP log, receiver restoration completed at 14:00:27.678, while the final mixed-waiter position check completed at 14:00:36.221, an 8.543-second interval. The corresponding after interval was 0.967 seconds. These intervals include waiting and cleanup; the final SQL itself took only 0.008/0.012 seconds. Do not mix this 14:00 pair with timestamps from the separate 09:49 trial.

The instrumentation wraps `safe_psql()` with `Time::HiRes::time`, prints elapsed call time, node name, and a shortened SQL string using TAP `note()`, and preserves the original return value. The TAP harness supplies wall-clock prefixes. `diag()` prints the sampled target; a live `pg_wal` copy preserves evidence before launching six waiters. A live directory copy is not an atomic backup: inspect only the completed, validated prefix.

## Exact boundary mechanism

| Section 7d | Before | After |
| --- | --- | --- |
| COMMIT start | `0/03019FD8` | `0/030143C8` |
| COMMIT aligned end | `0/0301A000` | `0/030143F0` |
| Sampled insertion target | `0/0301A018` | `0/030143F0` |

Both runs emitted ten 59-byte INSERT records and one 34-byte COMMIT in this section: `10 × 64 + 40 = 680` aligned record bytes. The COMMIT length rounds up to 40 under 8-byte alignment. Thus `0/03019FD8 + 40 = 0/0301A000`, exactly an 8192-byte boundary. The extra `0x18` in the sampled target is the following page's 24-byte header. The analogous segment-start header is 40 bytes.

`GetXLogInsertRecPtr()` reads the globally reserved usable-byte counter `CurrBytePos` under its spinlock, then calls `XLogBytePosToRecPtr()`. The start-address conversion advances over a header at a boundary. The end-address conversion retains the boundary. These describe different valid positions; the longstanding insertion getter is not necessarily defective in its own contract. The problem is treating that address as an end guaranteed to be reached by the existing WAL. See [pinned source excerpts](../evidence/PGK-20261008-c223c126/source-excerpts.md).

A separate diagnostic probe found primary write/flush and standby write/flush/replay at `0/0301A000` while six waiters targeted `0/0301A018`. In the [before extended dump](../evidence/PGK-20261008-c223c126/historical/before-waldump-through-8.txt), the next record is a 54-byte `RUNNING_XACTS` at `0/0301A018`, aligned to 56 bytes and ending at `0/0301A050`. It supplies the progress missing from the wait target. Section 7e starts there afterward.

The background writer conditionally logs standby snapshots after a 15,000-ms interval and relevant WAL activity. The running-transactions path requests eventual flushing via `XLogSetAsyncXactLSN()`. Subsequent write, transmission, flush, and replay release the relevant waiters. This is not an unconditional 15-second guarantee and does not mean the background writer directly wakes every waiter.

## Why one combined SQL call changed subsequent WAL

Combining the two DDLs uses one backend session but still executes two autocommit transactions, XIDs 698 and 699. Backend-local target-page state can therefore survive between statements. Catalog insertion uses cached heap target pages and free-space searches; changing the selected `pg_proc` page changes both full-page-image requirements and the space available to later inserts. Detailed in-memory free-space search history was not traced; source behavior and decoded block selections support this explanation.

The first divergence is the procedure insertion at `0/0300CFC0`. Before, it uses `pg_proc` block 20 and logs a page image; after, it reuses block 18 and logs tuple data. For ordinary full-page writes, `XLogRecordAssemble()` tests `PageGetLSN(page) <= RedoRecPtr`. A page already changed after the checkpoint generally avoids another image. A standard uncompressed image omits the unused hole between `pd_lower` and `pd_upper`; unchanged WAL structure sizes do not explain these savings.

| Change through section 7d | Before aligned bytes | After aligned bytes | Saved |
| --- | ---: | ---: | ---: |
| XID 699 procedure: `pg_proc` page image replaced with tuple data | 7,840 | 312 | 7,528 |
| XID 700 `log_count`: page image has a 72-byte larger unused hole | 8,000 | 7,928 | 72 |
| XID 701 `log_wait_done`: tuple fits on already-modified page 20 | 7,968 | 296 | 7,672 |
| XID 701: avoid `pg_proc` FSM page image | 8,248 | 0 | 8,248 |
| Total aligned record bytes saved | | | **23,520** |
| Two fewer 24-byte WAL page headers | | | **48** |
| Total physical WAL saved | | | **23,568** |

The 272-byte aligned `log_wait_done` tuple does not fit the before page's 244-byte available capacity, but fits the after page's 316 bytes. A 72-byte occupancy difference crosses a placement threshold and causes much larger later image savings. Raw record sizes and block references are preserved in [record fields](../evidence/PGK-20261008-c223c126/layout/record-fields.json) and the before/after dumps.

An 8,241-byte `pg_depend` FSM image (8,248 aligned) appears in both runs, earlier in the after run: during XID 699 rather than XID 700. It contributes **zero net reduction**. Its earlier emission makes XID 699 itself 720 physical bytes larger, moving its COMMIT end from `0/0300F5B8` to `0/0300F888`. The final reduction emerges across subsequent transactions; attributing the entire later shift to that initial 720-byte increase is incorrect. An FSM hint-image record is physical recovery protection, not proof that the FSM change is transactionally owned by the surrounding DDL.

From `0/03000028` through the 7d COMMIT end, physical WAL is 106,456 versus 82,888 bytes, a 23,568-byte (about 22.1%) reduction in this measured interval only. The later COMMIT consequently lands inside a page. Different catalog occupancy, checkpoint state, or prior WAL can produce different positions.

## Fix strategies and their limits

A record-end insertion getter removes the dependency on a **new future reservation merely to cross a header**. `GetXLogInsertEndRecPtr()` still samples global reservations; it neither waits for concurrent insertions to finish nor forces writing or flushing. A concurrent backend can contribute to the sampled target, adding latency beyond the caller's own transaction. That is different from the boundary hazard: the reservation already exists, although its insertion and downstream progress may still stall.

For these locally synchronous-commit test transactions, sampling primary write or flush after COMMIT also covers the commit. Replacing only section 7d's target with `pg_current_wal_lsn()` reduced historical before runtimes to 12.590 and 12.375 seconds; see [results](../evidence/PGK-20261008-c223c126/target-fix/fixed-results.json). This substitution is not generally safe after `synchronous_commit=off`, because write/flush can still precede the caller's commit. Deliberately unreachable, future, and fencepost test targets must retain their intended meaning.

For read-your-writes, wait for **replay** of a target covering the successful commit before reading on the standby, with a suitable fresh snapshot. Write or flush progress alone does not establish query visibility. A frozen sampled target does not move as further WAL arrives. Failed or paused replication remains a reason to time out under any getter.

Keep exact numeric `WAIT FOR` semantics unless a different interpretation is explicitly designed. Silently rounding every target immediately after a page header down to the boundary could report success before a record beginning there has been processed. The safe boundary adjustment relies on knowing the input's insertion-address semantics.

Two local patches are preserved: [expose insertion-end SQL getter](../evidence/PGK-20261008-c223c126/api-patches/0001.patch), commit `10076ae9e497cf59407d0f47ce7fee77762b82aa`, and [use it in WAIT documentation/tests](../evidence/PGK-20261008-c223c126/api-patches/0002.patch), commit `32ad7baa3954a7626e782943c9816748a54ec49f`. The latter changes the documented target acquisition and test getter calls, not WAIT's numeric comparison contract. At the user's request, the added dedicated test and catalog-version bump were omitted from the final local patch. Previous conversation reported successful build, catalog regression checks, 74 TAP assertions, and documentation validation; original API validation logs were not retained at capture. Submission, merge, release, and backpatch status are unverified.

## Counterevidence, application implications, and open design work

Reverting only the catch-up commit on the later tested HEAD `e73841ffbceea314cf9fa3f64a5eae9f87a46449` did **not** recreate the boundary in two runs per variant. Section 7d ended at `0/03017DA8` on that HEAD and `0/0301D9F0` after the revert, with about one second of waiting in both cases. All 74 assertions passed. See [positions](../evidence/PGK-20261008-c223c126/head-revert/positions-summary.json) and [runtimes](../evidence/PGK-20261008-c223c126/head-revert/clean-results.json). This is evidence that the historical layout is fragile, not that the boundary risk disappeared. First-run timing also varied, so total-runtime differences alone are insufficient diagnosis.

A user-supplied report from Jobin Augustine described a Rust/deadpool application with 16 pooled connections and roughly one timeout per 2,000 waits. This is third-party evidence, not a measured general failure rate. A primary connection can be released while its application task waits on a standby, but if every task waits before issuing its next write, idle primary connections do not generate WAL. Independent incoming writes may mask the problem; connection availability alone cannot resolve it. Async task suspension also does not imply that the connection executing WAIT has been returned to its pool. The application's code, exact pool arrangement, and durability settings were not provided.

A backend-local completed-record-end getter could avoid unrelated reservations, but remains a separate proposal. `ProcLastRecPtr` is a start address and `XactLastRecEnd` is reset at transaction boundaries, so neither is a drop-in persistent public target getter. A commit-only API would not cover every WAL-wait use case: nontransactional logical messages generate WAL and expose their own end LSN without requiring a COMMIT record. Define whether a new getter covers the last backend record, the completed transaction, or session work including parallel workers; specify no-WAL, initial, abort, prepare, and connection-pool behavior. Retrieve a backend-local value before releasing the relevant connection. No such API was implemented in this investigation.

## Evidence and retrieval

The [evidence manifest](../evidence/PGK-20261008-c223c126/SHA256SUMS) protects retained artifacts. The historical package contains text WAL dumps, not archived binary segments or clusters. Its README records the original decoding commands and how extended dumps were recovered and checked against the earlier prefix. The original absolute temporary paths are historical provenance, not guaranteed current locations.

For a future investigation: time individual SQL calls, locate gaps between TAP timestamps, sample all relevant progress positions, decode with a matching `pg_waldump -b`, distinguish record length/alignment/page headers, and use controls that vary connection reuse separately from catch-up count. Passing assertions establishes only what those assertions actually check.

Related: [Choosing TAP SQL helpers and proving WAL-wait outcomes](PGK-20261008-5c464fad-tap-sql-sessions-and-wal-wait-assertions.md), an independent investigation of helper lifetime and assertion strength. The [conversation scope](../evidence/PGK-20261008-c223c126/conversation-scope.md) distinguishes unverified third-party and API-validation reports from retained experiments. This record is available through repository file search; no OpenWiki ingestion is claimed.
