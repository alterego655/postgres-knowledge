---
id: "PGK-20261016-2cd01b69"
title: "Understanding confirmed_flush_lsn and restart_lsn"
kind: investigation
topics: [replication, logical-decoding, replication-slots, failover]
symbols: [confirmed_flush, confirmed_flush_lsn, restart_lsn, catalog_xmin, two_phase_at, start_decoding_at, candidate_restart_lsn, candidate_restart_valid, candidate_catalog_xmin, candidate_xmin_lsn, last_saved_confirmed_flush, last_saved_restart_lsn, CreateDecodingContext, DecodingContextFindStartpoint, LogicalConfirmReceivedLocation, LogicalIncreaseRestartDecodingForSlot, LogicalIncreaseXminForSlot, LogicalSlotAdvanceAndCheckSnapState, SnapBuildXactNeedsSkip, SnapBuildProcessRunningXacts, SnapBuildSerialize, SnapBuildSerializationPoint, DecodeTXNNeedSkip, logicalmsg_decode, ReorderBufferFinishPrepared, PhysicalConfirmReceivedLocation, ProcessStandbyReplyMessage, WalSndPrepareWrite, XLogSendLogical, WalSndKeepalive, LogicalRepApplyLoop, send_feedback, StandbySlotsHaveCaughtup, synchronized_standby_slots, pg_logical_slot_get_changes, pg_replication_slot_advance, pg_copy_logical_replication_slot, update_local_synced_slot, get_flush_position, store_flush_position, CheckPointReplicationSlots, ReplicationSlotsComputeRequiredLSN, binary_upgrade_check_logical_slot_pending_wal, ReplicationSlotReserveWal, SnapBuildFindSnapshot, RestoreSlotFromDisk, decode_concurrent_changes]
evidence_state: supported
delivery: not-applicable
applicability:
  repository: postgres
  inspected_commit: f58ab18a90460cd297249bc80b13d84b2671bf0c
  tested_commit: unknown
  branch: "master (inspected from checkout on codex/wal-read-lsn-wait-v12; the uncommitted patch there touches walsender.c comments only among the cited files, and excerpts were taken from the commit itself)"
  patch_identity: not-applicable
  configuration: "Source review only; no runtime configuration exercised. The subscriber example describes the default subscription synchronous_commit = off."
  platform: not-applicable
last_checked: 2026-10-16
sources:
  - type: conversation
    id: "Claude Code session 8dea902e-23a6-45f6-a966-cf4f22cf3db6, 2026-10-15 to 2026-10-16"
    scope: "First-principles explanation of confirmed_flush_lsn, a source-checked review of that explanation pasted by the user (origin not stated), and an evaluation of the review; summarized, not archived verbatim"
  - type: source
    id: "PostgreSQL excerpts at f58ab18a90460cd297249bc80b13d84b2671bf0c"
    path: "../evidence/PGK-20261016-2cd01b69/source-excerpts.md"
  - type: conversation
    id: "Codex follow-up review, 2026-10-16"
    scope: "Review and plain-language revision of the existing record; source rechecked at the pinned commit, including REPACK and slot restoration. Summarized, not archived verbatim."
  - type: mailing-list
    id: "CAE9k0P=hiqRXUonnmtS-5Pu8SbO=yF6vcrVBcfEf2+93ng_f5Q@mail.gmail.com"
    path: "../evidence/PGK-20261016-2cd01b69/keepalive-history.md"
    scope: "2022 keepalive acknowledgement discussion, retrieved through the PostgreSQL archive on 2026-10-16; 12-message thread through 2022-11-04. Includes the verified documentation commit and distinguishes current recommendations from historical outcomes."
  - type: conversation
    id: "Codex keepalive follow-up, 2026-10-16"
    scope: "Why confirmed progress can advance without new row delivery; publisher progress, subscriber flush gating, and unfinished transaction retention. Source review only."
supersedes: []
superseded_by: []
---

# Understanding confirmed_flush_lsn and restart_lsn

`confirmed_flush_lsn` records how far a logical slot may treat its output as consumed. It tells PostgreSQL what progress has been accepted, so ordinary future reads can leave that output behind.

`confirmed_flush_lsn` can advance through a keepalive acknowledgement without new row changes being delivered. Even in streaming replication, it does not mean that every change recorded before that LSN has reached the consumer.

`restart_lsn` records how far back PostgreSQL may need to read WAL to produce the output still needed. These positions differ because a transaction can commit now even though some of its changes were written much earlier.

This record is supported by source reading at PostgreSQL commit `f58ab18a90460cd297249bc80b13d84b2671bf0c`. No runtime experiment was performed for it. All source line numbers refer to that commit, not to the modified working tree. The [evidence file](../evidence/PGK-20261016-2cd01b69/source-excerpts.md) contains numbered excerpts and whole-file hashes.

## One example explains why both positions exist

Suppose two transactions produce this WAL. The numbers are simplified positions, not actual measured LSNs.

```text
100–150  Alice changes some rows. Her transaction remains open.
200–250  Bob changes some rows.
300–310  Bob's commit record.
400–410  Alice's commit record, written later.
```

In ordinary decoding of committed transactions, Bob's transaction is delivered first. The consumer acknowledges 310, the end of Bob's commit record.

```text
confirmed_flush_lsn = 310
restart_lsn        <= 100
```

When the consumer reconnects, PostgreSQL may reread WAL from before Alice's first change. It reconstructs the transactions and suppresses Bob's already acknowledged transaction. Alice's transaction still needs delivery because its commit is beyond 310, including her changes at 100–150.

Discarding every change whose individual LSN is below 310 would lose Alice's changes. Starting WAL reading immediately after 310 would have the same problem.

| Position | What it means |
| --- | --- |
| `confirmed_flush_lsn` | Progress the slot may treat as consumed. |
| `restart_lsn` | The oldest WAL position this slot may still need for reconstruction. |
| `catalog_xmin` | The transaction-ID horizon protecting old catalog rows needed to interpret retained WAL. It is not an LSN. |

The startup log describes the two LSNs as streaming transactions committing after one position while reading WAL from another. Physical replication does not have this transaction-reconstruction gap: the receiver's reported flush position can directly advance its physical slot's `restart_lsn`.

Evidence: [decoding startup](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#logical) and [physical slot feedback](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#walsender).

## What “consumed” means

Processing WAL, returning changes, and acknowledging progress are separate actions.

- The decoder reads WAL and builds transaction state. Some records produce no output.
- An output plugin turns relevant changes into messages for the caller.
- Acknowledgement advances the progress that the slot may treat as consumed.

For streaming replication, the consumer supplies that acknowledgement in its feedback message's `flush` field. The position is expressed in the publisher's WAL coordinates. It is the consumer's claim about durable progress, not the publisher's own local WAL flush position. The consumer might have stored the changes safely without applying them yet. Acknowledged progress may also cover an interval that produced no new completed transaction output; it is not a claim to have received every earlier WAL record or row change.

The SQL interface combines returning changes and acknowledging progress:

```sql
-- Return changes without acknowledging them.
SELECT * FROM pg_logical_slot_peek_changes('demo_slot', NULL, NULL);

-- Return changes and automatically acknowledge the decoding progress.
SELECT * FROM pg_logical_slot_get_changes('demo_slot', NULL, NULL);
```

`get_changes()` acknowledges the reader's `EndRecPtr`. PostgreSQL does not wait for a separate confirmation that the SQL client saved the results. The acknowledged position can exceed the last displayed output row's LSN if the decoder subsequently processed WAL that produced no output.

Thus the field records accepted progress. By itself, it does not prove that an application received, saved, or applied the data.

Evidence: [SQL decoding and confirmation](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#sql-decoding) and [streaming feedback](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#walsender).

## Why a keepalive can advance progress without delivering new changes

Consider ordinary decoding that buffers a transaction until commit. These positions are illustrative, not measured LSNs.

```text
100  Alice inserts a row. Her transaction remains open.
150  The publisher has processed WAL through this position.
     It sends a keepalive reporting 150; Alice's change is still buffered.
     With no completed local transactions awaiting flush, the subscriber
     can acknowledge 150 in its flush feedback.
200  Alice commits later; her transaction becomes eligible for delivery.
```

The keepalive carries progress information, not Alice's row. In this case the subscriber is acknowledging that it has received the progress report and has no outstanding durability work for completed transactions that would prevent confirming that position. There need not be a new row change to flush. Any previously delivered completed transactions must already satisfy the subscriber's durability requirements.

The publisher and subscriber contribute different parts of this assurance:

1. `XLogSendLogical()` processes a WAL record and then advances `sentPtr` to its `EndRecPtr`, even if processing only buffered an unfinished transaction. `WalSndKeepalive()` uses that progress position when no explicit position is supplied. Progress is reported on the same ordered connection as the logical output; the keepalive is not permission to acknowledge an arbitrary publisher WAL tip.
2. `LogicalRepApplyLoop()` incorporates the keepalive's position into `last_received` and calls `send_feedback()`.
3. `send_feedback()` consults `get_flush_position()`. Completed local transactions have mappings from publisher end positions to subscriber commit positions. If a mapped local commit remains unflushed, flush feedback cannot simply jump to the keepalive position. When no such mappings remain pending, `flushpos = writepos = recvpos` is allowed.
4. The publisher receives that flush field and passes it to `LogicalConfirmReceivedLocation()`.

Here, “no pending transactions” means no completed local transactions still awaiting flush in this mapping. It does not mean there are no open transactions on the publisher, nor that every change seen by the decoder has reached the subscriber. The example is about ordinary commit-time delivery; two-phase output and streamed unfinished transactions have the separate event boundaries described below.

It is safe to confirm 150 without receiving Alice's row for two reasons. Her commit at 200 is beyond the confirmed boundary, so confirming 150 does not suppress her transaction's eventual output. Separately, `restart_lsn` must still preserve the older WAL needed to reconstruct her transaction. If decoding restarts, it can reread her change at 100 and deliver the transaction when it encounters the later commit. Raising `confirmed_flush_lsn` does not set `restart_lsn` to the same position or authorize discarding all earlier WAL.

This mechanism also lets progress advance through WAL that generates no relevant output, such as filtered transactions. Otherwise a subscriber with no new row changes could appear stuck. The feedback source explicitly identifies synchronous replication as a reason to report received progress when no flush work remains.

Evidence: [publisher decoding and keepalive](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#walsender), [subscriber keepalive and flush checks](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#worker), and the [2022 discussion and documentation fix](../evidence/PGK-20261016-2cd01b69/keepalive-history.md).

## Which paths change the field

The following paths were checked at the inspected commit. The implementation field is `slot->data.confirmed_flush`; the SQL view calls it `confirmed_flush_lsn`.

| Path | Value or progress recorded | Where the authorization comes from |
| --- | --- | --- |
| Streaming feedback | The client's reported flush LSN. | The consumer claims that progress is durable. |
| SQL `get_changes()` and its binary variant | The WAL reader's ending position. | Calling the consuming SQL function authorizes confirmation. The `peek` variants do not confirm. |
| `pg_replication_slot_advance()` | The effective target passed to the advancement machinery, after the public wrapper's limits. | The caller deliberately advances without receiving the skipped output. |
| Slot creation | The reader's `EndRecPtr` when a consistent decoding starting point is found. | Initialization; no consumer receipt has occurred. |
| Slot synchronization | The primary slot's position, copied directly or reached through advancement. | Synchronization copies the primary's state; it is not a new consumer acknowledgement. |
| Logical slot copy | The source slot's position. | The caller requests a copy of existing state. |
| Internal REPACK worker | The processed record's end position, when crossing WAL segments. | REPACK explicitly allows processed WAL to be released because the operation starts over after a crash. |

Startup also restores the field as part of loading a persistent slot from disk. That restores old state rather than accepting new progress. Initialization clears slot state before these meaningful positions are established.

`LogicalConfirmReceivedLocation()` ignores a position below the slot's current value. Some internal callers invoke it with that existing value to apply eligible retention proposals; these calls do not supply a new acknowledgement. Direct initialization, copying, and recovery are separate paths.

The REPACK behavior is an internal exception in this development commit. It is not permission for an ordinary persistent consumer to acknowledge data before it can recover that data.

Evidence: [setter and caller audit](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#writer-audit), [REPACK](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#repack), and [persistent slot restoration](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#slot).

## How PostgreSQL decides which output to skip

WAL reading and output selection use different positions:

```text
Read WAL from:       restart_lsn
Select output from: the requested start, raised to confirmed_flush_lsn
                    if the request is earlier
```

When no starting position is supplied, the decoding context uses `confirmed_flush_lsn`. Selecting a later session start does not itself update the slot's acknowledgement.

The snapshot builder's skip test is strict: it skips an item if the relevant record begins before `start_decoding_at`. The record depends on the kind of output:

| Output event | Record checked |
| --- | --- |
| Ordinary committed transaction | COMMIT record. |
| Prepared transaction delivered through two-phase decoding | PREPARE record. |
| Resolution of a prepared transaction | The later COMMIT PREPARED or ROLLBACK PREPARED record. |
| Nontransactional logical message | The message's own record; no commit is required. |

Acknowledging PREPARE does not acknowledge the later resolution. If PREPARE was before `two_phase_at`, PostgreSQL may need to send the transaction's contents when COMMIT PREPARED arrives.

Database, origin, publication, and plugin rules can further exclude output. A position beyond the acknowledgement is therefore eligible for processing, not a promise that every transaction there produces messages.

Commit callbacks use the end of the commit record as their output write location. Change callbacks use the change's own LSN. The walsender uses this location in its WAL-data header when emitting the final write for that callback; plugin payloads have their own fields. A change's position is before its transaction's commit, so acknowledging it cannot complete that transaction. It can acknowledge other transactions that committed earlier.

This also applies while large transactions are streamed before commit. Feedback can advance `confirmed_flush_lsn` during streaming, while an unfinished transaction still needs reconstruction after reconnecting. “A cut in commit order” is a useful explanation for ordinary committed transactions, not a complete definition for every output mode.

Evidence: [session start and callback locations](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#logical), [record-specific skip checks](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#decode), and [two-phase fallback](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#reorderbuffer).

## Why decoding progress alone cannot release old WAL

Continue the Alice and Bob example. The decoder has now processed Alice's commit at 400 and reached a running-transactions record at 500. A third transaction began at 450. Suppose 440 is an available serialized snapshot position sufficient to restart decoding for the transactions still tracked at 500.

The decoder can propose 440 as a new `restart_lsn`, but the consumer has still acknowledged only 310.

```text
Consumer acknowledgement:          310
Proposed new restart position:     440
Position making the proposal safe: 500
```

Adopting 440 now would allow WAL containing Alice's changes at 100–150 to be removed. Alice has been decoded, but she has not been acknowledged. After a crash, the consumer could still need her transaction to be reproduced.

PostgreSQL therefore keeps the proposal pending until acknowledgement reaches 500. Reaching that position covers Alice's commit and makes the newer restart state sufficient for the remaining work. It permits releasing the older history; it does not immediately delete WAL files.

The implementation calls these fields `candidate_restart_lsn` and `candidate_restart_valid`. Catalog retention has a similar pair, `candidate_catalog_xmin` and `candidate_xmin_lsn`. There is one pending candidate for each kind, and a proposal can be applied immediately if its required acknowledgement has already arrived. The slot need not adopt a new proposal on every record.

The oldest transaction still tracked by the active decoder can therefore differ from the oldest transaction the consumer has not acknowledged. The active decoder has already finished some work that a restarted decoder may have to do again.

Evidence: [proposal generation](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#snapbuild) and [candidate acceptance and persistence](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#logical).

## Restart points, snapshots, and slot creation

Decoding needs both transaction records and a way to interpret the catalog as it existed when those records were written. A serialized decoding snapshot stores state that helps it resume that work; `catalog_xmin` protects the old catalog rows it still needs.

Ordinary restart advancement uses positions associated with serialized snapshots. It considers candidates at running-transactions records. The source explains that this also avoids saving slot state after every commit. The snapshot positions constrain which candidates are available; batching controls when advancement is considered.

An existing serialized snapshot at the exact `restart_lsn` is not a universal requirement. Initial slot creation reserves WAL from an insertion or replay position and can build a consistent snapshot incrementally from later WAL. REPACK also has its own non-resumable advancement policy, described above.

At creation, `DecodingContextFindStartpoint()` reads until the snapshot builder reports consistency, then assigns the reader's `EndRecPtr` to `confirmed_flush_lsn`. It does not copy the builder's internal `start_decoding_at`, and no consumer has received data yet. Creation may need to wait for more WAL before that consistent point can be established.

When the creator exports and correctly uses the associated data snapshot, the initial copy and subsequent change stream fit together. Not every creation exports such a snapshot: the SQL creation path asks only for the catalog information needed for decoding.

Evidence: [initial WAL reservation](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#slot), [snapshot construction and serialization](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#snapbuild), [initial acknowledgement position](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#logical), and [SQL creation](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#slotfuncs).

## What is saved, and what happens after a crash

Updating `confirmed_flush_lsn` in memory does not necessarily write the slot file immediately.

- A slot save writes the persistent fields, including `confirmed_flush`, when the slot is dirty. The save function can return without writing when nothing is dirty.
- SQL consumption and explicit advancement mark the slot dirty even if only confirmed progress changed. An ordinary checkpoint can then save it.
- Streaming feedback does not necessarily dirty the slot for a confirmed-progress-only change. Applying a retention proposal can trigger a save.
- Shutdown checkpoints additionally arrange to save changed confirmed progress for valid logical slots.

For a persistent slot, WAL retention also accounts for `last_saved_restart_lsn` when it is older than the current in-memory restart position. Catalog retention similarly waits for the required state to be persisted before advancing its effective limit. PostgreSQL must preserve the history required by the state it could restore after a crash.

Consequently, a valid persistent slot can recover an older acknowledgement and deliver some output again. The lagging saved position is intended to cause repetition rather than a gap. This is not an unconditional promise against lost output: deliberate advancement, an incorrect acknowledgement, or loss of a valid slot's required resources changes the assumptions.

A consumer that persists its own progress can request that position when reconnecting. The built-in subscriber uses replication-origin progress. To prevent duplicate effects after its own crash, a consumer must recover its progress consistently with the effects it has applied. That can provide exactly-once application of effects even when messages are delivered more than once.

The saved slot position may lag previously acknowledged streaming progress. It is not a universal lower bound on what an arbitrary application has applied, because SQL consumption, initialization, and deliberate advancement need not correspond to applied data.

Evidence: [confirmation and saving](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#logical), [SQL dirty marking](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#sql-decoding), [slot save and recovery](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#slot), and [subscriber restart](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#worker).

## How the built-in subscriber acknowledges safely

Subscriptions default to `synchronous_commit = off`. A local commit may therefore finish before its WAL is flushed. The apply worker tracks a mapping from each publisher transaction's end LSN to the subscriber's local commit end LSN.

Once the local commit is flushed, the worker can report the corresponding publisher position as flushed. When there are no completed local transactions still awaiting flush, it can report its latest received position. That report does not complete an upstream transaction whose commit is still beyond the position.

The [keepalive example](#why-a-keepalive-can-advance-progress-without-delivering-new-changes) shows how the received position can advance without new row delivery. The local flush check protects completed work; the publisher retains the WAL needed for unfinished work.

Evidence: [subscriber commit mapping, feedback, and restart](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#worker) and [subscription default](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#subscription).

## Failover and upgrade

Slot synchronization checks that the standby has flushed WAL through the primary slot's confirmed position. It also checks whether the necessary WAL and catalog history remain available. If a suitable serialized snapshot exists at the remote restart position, it can copy `restart_lsn`, `confirmed_flush`, and `catalog_xmin` directly. Otherwise it uses advancement to establish the required decoding state; that read can wait for replay.

For a failover slot, `synchronized_standby_slots` makes the logical walsender wait for designated physical standbys to flush the relevant WAL. Under normal feedback, logical consumption cannot outrun that protected WAL position. The standby's synchronized logical slot can still lag: having WAL flushed and having slot metadata synchronized are separate conditions.

The `pg_upgrade` check reads WAL from `restart_lsn` in fast-forward mode, using the confirmed position to select remaining decodable work. It checks for output that would still depend on the old cluster's WAL. The WAL reader does not start at `confirmed_flush_lsn`.

Evidence: [slot synchronization](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#slotsync), [walsender waiting](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#walsender), [pending-WAL scan](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#logical), and [upgrade wrapper](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#upgrade).

## Corrections retained for future reviews

| Earlier claim | Corrected understanding |
| --- | --- |
| The field always proves durable receipt of every earlier change. | Streaming feedback confirms logical progress, which can advance through keepalives without delivery of unfinished transactions. Other paths initialize, copy, or deliberately advance progress without a new consumer acknowledgement. |
| No pending local transactions means no transaction is still open on the publisher. | The feedback check concerns completed local transactions awaiting flush; upstream transactions may still be open. |
| Acknowledged transactions can never be delivered again. | A crash can restore an older saved acknowledgement and cause repeated delivery. |
| Resuming means reading the next WAL record after the confirmed position. | Reading starts from `restart_lsn`; output selection uses the session's starting boundary. |
| Every restart position must already have a serialized snapshot. | Ordinary advancement uses serialized snapshot positions. Initial decoding can build state incrementally; internal REPACK has a separate policy. |
| PREPARE is the only boundary relevant to a two-phase transaction. | PREPARE and its later commit or rollback resolution are distinct output events. |
| Streaming an unfinished transaction cannot move confirmed progress. | Feedback can advance the position and cover other commits without completing that transaction. |
| Slot state is saved only with retention changes or at shutdown. | Dirty slots can also be saved at ordinary checkpoints and through explicit save paths. |
| Slot creation copies `start_decoding_at` into the field. | It assigns the reader's `EndRecPtr` after consistency is reached. |
| Slot synchronization always decodes up to the remote position. | It can copy state directly when a suitable serialized snapshot exists. |
| Consumer-side atomic progress tracking guarantees exactly-once delivery. | It can prevent duplicate effects even when delivery repeats. |

The original record was updated on 2026-10-16 after a further source review. The rewrite also adds the previously omitted REPACK caller and distinguishes saved slot state from the consumer's own durable progress. The record ID is unchanged.

## What the documentation history establishes

The 2022 thread began with exactly the apparent contradiction in the keepalive example: `confirmed_flush_lsn` could pass a change that the subscriber had not received. Ashutosh Sharma initially proposed reporting an earlier position. Ashutosh Bapat explained why interleaved WAL and later transaction commits made the existing behavior valid. The discussion then produced a documentation correction.

Commit `3e77b2eb3466aff9fe19e209ebc0d899ea869494`, committed by Amit Kapila on 2022-11-04, replaced the broad statement that older data was unavailable with wording about transactions committed before the confirmed position. It changed documentation only. The [history evidence](../evidence/PGK-20261016-2cd01b69/keepalive-history.md) records the messages, the exact patch, and the earlier 2015 distinction between retained WAL and confirmed progress.

This follow-up corrects an omission in the earlier explanation: keepalive acknowledgements make the distinction necessary even in normal streaming replication, independently of SQL consumption or explicit advancement. The record's stable ID and source-only evidence status are unchanged.

A further documentation clarification would be reasonable: explain keepalive progress and state that previously consumed output being unavailable through a slot does not mean all corresponding WAL has been removed. This is a recommendation, not a submitted or accepted patch. The history does not establish a need to rename the field or change its behavior; its name matches the streaming feedback field but does not explain every use of slot progress.

## Verification limits and follow-up

The evidence supports the source behavior described above at the inspected commit. It does not establish behavior in every released version. The numerical examples are explanations, not experiment results. Crash recovery, keepalive feedback, streamed-transaction retransmission, and the retention example were not exercised at runtime for this record.

A possible comment-only patch remains unreported: `binary_upgrade_check_logical_slot_pending_wal` has a header saying it returns true or false, while the implementation returns a pending WAL LSN or NULL. See the [header and return statements](../evidence/PGK-20261016-2cd01b69/source-excerpts.md#upgrade). This record does not change PostgreSQL code.

This record is retrieved through the knowledge repository's `records/` and `topics/` files. Saving it does not add it to OpenWiki search. No related investigation is linked without established relevance.
