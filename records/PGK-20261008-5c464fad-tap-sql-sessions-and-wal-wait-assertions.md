---
id: "PGK-20261008-5c464fad"
title: "Choosing TAP SQL helpers and proving WAL-wait outcomes"
kind: decision
topics: [testing, replication, wal, recovery]
symbols: [safe_psql, psql, background_psql, query_safe, query, query_until, poll_query_until, log_count, log_wait_done, pg_current_wal_insert_lsn, WAIT FOR LSN]
evidence_state: supported
delivery: not-applicable
applicability:
  repository: postgres
  inspected_commit: e797f46d6a58e28bbcada551e3f3bac7126c6b8d
  tested_commit: unknown
  branch: codex/recovery-buffer-pin-wakeups-v9
  patch_identity: "No tracked modifications at capture; unrelated untracked files present"
  configuration: "Local TAP helper implementations and 031/049 tests; WAIT FOR LSN behavior belongs to this checkout"
  platform: "Source inspection only; no runtime platform validated"
last_checked: 2026-10-08
sources:
  - type: conversation
    id: "Current Codex conversation, explanation of tests 031 and 049, captured 2026-10-08"
    scope: "Perl syntax, SQL helper lifetimes, output markers, and WAL-wait assertions; summarized rather than archived verbatim"
  - type: source
    id: "PostgreSQL working-tree excerpts at e797f46d6a58e28bbcada551e3f3bac7126c6b8d"
    path: "../evidence/PGK-20261008-5c464fad/source-excerpts.md"
supersedes: []
superseded_by: []
---

# Choosing TAP SQL helpers and proving WAL-wait outcomes

## Current conclusion and applicability

Choose the helper by connection lifetime, the point at which Perl should resume, and who judges errors. Command completion does not imply transaction completion or connection closure. For WAL waits, distinguish a client output marker, command completion, and the observable postcondition promised by the wait mode.

This is a source-verified explanation of the local checkout, not a runtime test report or a claim that `WAIT FOR LSN` is available in a released PostgreSQL version. No source change, test execution, commit, or publication was performed for this capture.

**Correction to the conversation:** the explanation that test 7a starts with 30 rows is incorrect for the inspected checkout. Before 7a, setup and earlier sections insert rows 1 through 60; no intervening removal of those rows was found. Yet `log_count(i)` still uses `count >= 31 + i`. That lower bound can already be satisfied before the five new inserts are replayed, so it does not prove visibility of each corresponding insertion. The design lesson remains valid, but the current assertion is weaker than the earlier explanation claimed. See the evidence excerpts for setup, thresholds, and test sequencing.

## SQL helper decision table

| Helper | Connection lifetime and return point | Result and intended use |
| --- | --- | --- |
| `$node->safe_psql($db, $sql)` | Starts a fresh psql connection; waits for process completion | Returns stdout; forces `on_error_stop` and `on_error_die`. Use for setup, cleanup, and operations required to succeed. |
| `$node->psql($db, $sql)` | Starts a fresh psql connection; waits for process completion | Scalar context returns exit status; list context returns `(status, stdout, stderr)`. Use to inspect expected SQL failures. Invocation failures, signals, and unhandled timeouts can still throw. |
| `$node->background_psql($db, ...)` | Starts a persistent client, normally waiting for connection establishment | Returns a session object. Use when transactions, locks, cursors, settings, or concurrent activity must survive between calls; call `quit` when finished. |
| `$session->query_safe($sql)` | Uses existing session; waits for batch completion markers on stdout and stderr | Returns output and dies on nonempty stderr. Session stays open. Even notices can matter. |
| `$session->query($sql)` | Uses existing session; waits for batch completion | Scalar context returns output; list context returns `(output, stderr_flag)`. The flag is not an exit status or SQLSTATE. Use with appropriate error-stop settings when inspecting errors. |
| `$session->query_until($regex, $sql)` | Sends the batch once; returns when stdout matches the regex | Allows later statements to remain active or blocked while Perl proceeds. Does not certify whole-batch success or completion. |
| `$node->poll_query_until($db, $sql, $expected)` | Repeats the query in fresh clients | Returns 1 on matching output with empty stderr, 0 on retry exhaustion; default expected output is `t`. Use observation queries and check the returned boolean. |

`safe_psql` can print notices on stderr without failing if the process succeeded; `query_safe` uses nonempty stderr as its failure criterion. “Safe” does not mean SQL escaping or automatic transaction wrapping.

With the normal `ON_ERROR_STOP` setting, a SQL script error produces exit status 3; successful process completion produces 0. `$out` holds stdout, not the exit status; `$err` holds stderr, including possible notices. A persistent session has no per-command process exit status while its client remains alive. `on_error_stop => 0` keeps psql processing after ordinary SQL errors; it cannot prevent server disconnection or repair an aborted transaction.

## Why a finished lock command can keep its lock

```perl
my $session = $standby->background_psql($db);
$session->query_safe('BEGIN; LOCK TABLE t IN ACCESS SHARE MODE;');
$primary->safe_psql($db, 'DROP TABLE t');
```

Assuming the lock is available, acquisition finishes and `query_safe` returns. The standby transaction remains open, retaining the lock until its transaction ends or its connection closes. The primary's separate lock manager does not directly conflict with that standby lock. The conflict arises when standby recovery tries to replay the primary's WAL.

Replacing the session call with `safe_psql('BEGIN; LOCK ...')` would let psql exit at the end of its input, close the connection, roll back the unfinished transaction, and release the lock before Perl proceeds. Use one-shot calls for completed operations; persistent clients for retained session state.

## Start markers versus completion and data checks

Test 049 section 7a pauses replay, then repeatedly commits an insert on the primary, obtains `pg_current_wal_insert_lsn()`, and starts a standby client with:

```perl
$session->query_until(qr/start/, qq[
    \\echo start
    WAIT FOR LSN '${lsn}';
    SELECT log_count(${i});
]);
```

- `qr/start/` is a Perl regex matching stdout.
- `\\echo start` in `qq[...]` becomes psql's `\echo start`; this client command prints the marker before the SQL wait.
- Seeing the marker permits the Perl loop to launch another session. It does not prove the server has entered its wait, nor that the wait is complete.
- Commands following `WAIT FOR LSN` execute later in the same client sequence. Their output can supply separate completion/postcondition evidence.

Using `query_safe` for the entire batch would wait for its end. With replay resumed only after the loop, the first iteration could stall until timeout. `query_until` enables the necessary concurrency. Its input needs appropriate SQL terminators and a trailing newline.

`log_count(i)` is a PL/pgSQL function returning void. `SELECT count(*) ... INTO count` assigns a local variable. Only when the threshold passes does `RAISE LOG 'count %', i` emit a server-log marker. A failed condition returns silently; the test later fails to find the expected marker. The output is not the client's stdout and is not a useful SQL return value. The current numeric threshold has the limitation noted above.

`log_wait_done(prefix, i)` also returns void but unconditionally writes a server-log marker such as `write_done 2`. It proves that control reached that statement, not independently that WAL reached the requested position. In the Perl source, `\$\$` preserves PostgreSQL's literal `$$` body delimiters instead of interpolating Perl's process-ID variable. PL/pgSQL `BEGIN ... END` delimits a code block, not a separate transaction.

## Why replay and write tests need different postconditions

A replay wait should allow a subsequent query to see the corresponding committed changes. A status-only assertion could miss an implementation that incorrectly reports completion early. A data check is useful provided its predicate actually distinguishes old state from the requested new state.

A standby-write wait promises WAL write progress, not replay or durable flush. Visible rows are therefore not a valid required postcondition for write completion. Section 7b stops walreceiver, starts five write waiters, resumes walreceiver, looks for `log_wait_done` markers, and finally asserts `pg_stat_wal_receiver.written_lsn >=` the largest target. That position check complements the log markers.

Two limitations must remain explicit:

1. The inspected 7b calls `poll_query_until` to observe five `WaitForWalWrite` waiters but does not check its boolean result. A polling timeout alone therefore is not an enforced assertion at that call site.
2. A final written-LSN check establishes the final state, not necessarily the state at each earlier wakeup. The log markers by themselves do not independently validate the wait's result or the precise wakeup boundary.

Possible improvements, not implemented here: derive the replay threshold from actual setup state or use a predicate for uniquely identified inserted rows; assert the polling result; validate the appropriate WAL position as close as possible to each completion. Returning and collecting query output instead of server logs is another possible implementation of the same testing intent.

## Perl reading notes

Traditional subroutines receive arguments in `@_`; bare `shift` inside a subroutine consumes its first argument. Methods receive the invocant first, commonly unpacked as `$self`. `my` declares lexical variables, `$` denotes scalar values, `@` denotes an array, and `$sessions[$i]` selects one array element. `->` calls methods. `=>` is the fat comma used for option pairs. `qq[...]` is an interpolated string, not an array; `${name}` marks a variable boundary. SQL quotes inside `qq` do not suppress Perl interpolation. `qr/.../m` builds a regex with line-sensitive anchors. `-s $node->logfile` saves file size for later log searches. `ok`, `is`, `like`, and `cmp_ok` are Test::More assertions; `done_testing()` finishes the TAP plan.

In test 031, enabling `log_recovery_conflict_waits` and lowering `deadlock_timeout` intends to exercise extra logging during short recovery waits. The comment explicitly says the test does not rely on those additional messages: incidental code-path coverage is weaker than asserting message content or occurrence.

## Verification and sources

The current conversation supplied the learning questions; source inspection independently checked the helper contracts and the test bodies. CodeGraph was attempted first; these Perl files were not indexed, so direct reads were used. The inspected tracked tree was clean at the recorded revision. No runtime behavior was newly reproduced. Source snapshots include original line numbers and SHA-256 hashes; later checkout changes require rechecking applicability.

See [preserved source excerpts](../evidence/PGK-20261008-5c464fad/source-excerpts.md), [WAL and recovery navigation](../topics/wal-and-recovery.md), and [replication navigation](../topics/replication.md). This curated record is discoverable by repository file search; OpenWiki indexing is separate and was not performed.
