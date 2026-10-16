# Source excerpts for PGK-20261010-529f204b

Captured 2026-10-10 from /Users/qqj/dev/postgres at commit 9330457473cae55cc804ac73065517ff089ab37f (branch codex/recovery-buffer-pin-wakeups-v9; tracked tree clean). Line numbers are from that commit.

## src/backend/storage/ipc/standby.c lines 690-735

SHA-256 of whole file: `419ff7bb1f57ed52cdcbad13d28079a0612409515d633836cbdc3c41df2264e4`

```
  690  			timeouts[cnt].fin_time = ltime;
  691  			cnt++;
  692  		}
  693  
  694  		got_standby_deadlock_timeout = false;
  695  		timeouts[cnt].id = STANDBY_DEADLOCK_TIMEOUT;
  696  		timeouts[cnt].type = TMPARAM_AFTER;
  697  		timeouts[cnt].delay_ms = DeadlockTimeout;
  698  		cnt++;
  699  
  700  		enable_timeouts(timeouts, cnt);
  701  		timeouts_armed = true;
  702  		INJECTION_POINT("standby-conflict-timeouts-armed", "lock");
  703  	}
  704  
  705  	/*
  706  	 * ProcWaitForSignal() can wake up even when the lock wait has not ended
  707  	 * and neither timeout has expired.  Keep waiting with the same timeouts
  708  	 * in that case.  Returning to the caller would restart the deadlock
  709  	 * timeout with a later deadline, which could keep it from ever expiring.
  710  	 *
  711  	 * If the standby delay limit was already reached above, no timeouts were
  712  	 * set.  Return after any wakeup so the caller can try resolving the
  713  	 * conflict again.
  714  	 */
  715  	for (;;)
  716  	{
  717  		ProcWaitForSignal(PG_WAIT_LOCK | locktag.locktag_type);
  718  
  719  		if (!timeouts_armed)
  720  			break;
  721  
  722  		if (*((volatile ProcWaitStatus *) &MyProc->waitStatus) != PROC_WAIT_STATUS_WAITING)
  723  			break;
  724  
  725  		/*
  726  		 * Exit if ltime is reached. Then all the backends holding conflicting
  727  		 * locks will be canceled in the next
  728  		 * ResolveRecoveryConflictWithLock() call.
  729  		 */
  730  		if (got_standby_lock_timeout)
  731  			break;
  732  
  733  		if (got_standby_deadlock_timeout)
  734  		{
  735  			VirtualTransactionId *backends;
```

## src/backend/storage/ipc/standby.c lines 852-900

SHA-256 of whole file: `419ff7bb1f57ed52cdcbad13d28079a0612409515d633836cbdc3c41df2264e4`

```
  852  			timeouts[cnt].fin_time = ltime;
  853  			cnt++;
  854  		}
  855  
  856  		got_standby_deadlock_timeout = false;
  857  		timeouts[cnt].id = STANDBY_DEADLOCK_TIMEOUT;
  858  		timeouts[cnt].type = TMPARAM_AFTER;
  859  		timeouts[cnt].delay_ms = DeadlockTimeout;
  860  		cnt++;
  861  
  862  		enable_timeouts(timeouts, cnt);
  863  		timeouts_armed = true;
  864  		INJECTION_POINT("standby-conflict-timeouts-armed", "bufferpin");
  865  	}
  866  
  867  	/*
  868  	 * ProcWaitForSignal() can wake up for unrelated reasons.  If timeouts
  869  	 * were set, keep waiting with the same deadlines until a timeout expires
  870  	 * or only our own pin remains.  The helper also makes sure we are
  871  	 * registered for another unpin notification before waiting again.  If the
  872  	 * delay limit had already passed, return after any wakeup so the caller
  873  	 * can retry.
  874  	 */
  875  	for (;;)
  876  	{
  877  		ProcWaitForSignal(WAIT_EVENT_BUFFER_CLEANUP);
  878  
  879  		if (!timeouts_armed)
  880  			break;
  881  
  882  		if (PinCountWaiterCheckReadyForCleanup(buffer))
  883  			break;
  884  
  885  		/* Request cancellation if the delay timeout has expired. */
  886  		if (got_standby_delay_timeout)
  887  		{
  888  			SendRecoveryConflictWithBufferPin(RECOVERY_CONFLICT_BUFFERPIN);
  889  			break;
  890  		}
  891  		else if (got_standby_deadlock_timeout)
  892  		{
  893  			/*
  894  			 * Send out a request for hot-standby backends to check themselves
  895  			 * for deadlocks.
  896  			 *
  897  			 * XXX The subsequent ResolveRecoveryConflictWithBufferPin() will
  898  			 * wait to be signaled by UnpinBuffer() again and send a request
  899  			 * for deadlocks check if deadlock_timeout happens. This causes
  900  			 * the request to continue to be sent every deadlock_timeout until
```

## src/test/recovery/t/031_recovery_conflict.pl lines 355-444

SHA-256 of whole file: `356253f3fe627f14d6a14afd40907814bd8d7d2020de871832f583ce2f93c070`

```
  355  $psql_standby->quit;
  356  
  357  # An unrelated wakeup must not restart the deadlock timer in either recovery
  358  # wait. Run these tests last because they use a long timeout.
  359  if (   $ENV{enable_injection_points} eq 'yes'
  360  	&& $node_primary->check_extension('injection_points'))
  361  {
  362  	$node_primary->safe_psql('postgres', 'CREATE EXTENSION injection_points');
  363  	$node_primary->wait_for_replay_catchup($node_standby);
  364  	$node_standby->adjust_conf('postgresql.conf',
  365  		'max_standby_streaming_delay', '-1');
  366  	$node_standby->append_conf('postgresql.conf',
  367  		'log_startup_progress_interval = 0');
  368  	# Set the deadlock timeout far beyond the expected test duration.
  369  	$node_standby->adjust_conf('postgresql.conf', 'deadlock_timeout', '1d');
  370  	# Log startup's notices so we can see if it sets the timer again.
  371  	$node_standby->append_conf('postgresql.conf',
  372  		q[log_min_messages = 'warning, startup:notice']);
  373  	$node_standby->restart();
  374  
  375  	my $startup_pid = $node_standby->safe_psql('postgres',
  376  		q[SELECT pid FROM pg_stat_activity WHERE backend_type = 'startup']);
  377  	my $point = 'standby-conflict-timeouts-armed';
  378  
  379  	for my $kind ('bufferpin', 'lock')
  380  	{
  381  		my $table = "test_recovery_wakeup_$kind";
  382  		my $wait_event = $kind eq 'bufferpin' ? 'BufferCleanup' : 'relation';
  383  
  384  		# Leave aborted rows for VACUUM to remove. Commit another insert to
  385  		# flush the WAL, then replay it before taking the cursor's snapshot.
  386  		$node_primary->safe_psql(
  387  			'postgres', qq[
  388  CREATE TABLE $table(a int) WITH (autovacuum_enabled = false);
  389  INSERT INTO $table VALUES (1);
  390  BEGIN;
  391  INSERT INTO $table SELECT generate_series(1, 100);
  392  ROLLBACK;
  393  INSERT INTO $table VALUES (2);
  394  ]);
  395  		$node_primary->wait_for_replay_catchup($node_standby);
  396  
  397  		my $session = $node_standby->background_psql('postgres');
  398  		$session->query_safe(
  399  			$kind eq 'bufferpin'
  400  			? "BEGIN; DECLARE c CURSOR FOR SELECT a FROM $table; FETCH FROM c;"
  401  			: "BEGIN; LOCK TABLE $table IN ACCESS SHARE MODE;");
  402  
  403  		$node_primary->safe_psql('postgres',
  404  			$kind eq 'bufferpin'
  405  			? "VACUUM FREEZE $table"
  406  			: "BEGIN; LOCK TABLE $table; COMMIT;");
  407  		$node_standby->wait_for_event('startup', $wait_event);
  408  
  409  		# The timer is already set. Log any attempt by this resolver to set it
  410  		# again.
  411  		$node_standby->safe_psql('postgres',
  412  			"SELECT injection_points_attach('$point', 'notice', '$kind');");
  413  
  414  		# Wake startup while the session still holds the pin or lock. Wait for
  415  		# its log message so we know it has left the original wait.
  416  		my $log_offset = -s $node_standby->logfile;
  417  		is( $node_standby->safe_psql(
  418  				'postgres',
  419  				"SELECT pg_log_backend_memory_contexts($startup_pid)"),
  420  			't',
  421  			"$kind: memory-context request sent to startup");
  422  		$node_standby->wait_for_log(
  423  			qr/logging memory contexts of PID $startup_pid\b/, $log_offset);
  424  
  425  		# Wait for startup to resume its wait for the pin or lock. Startup
  426  		# writes notices directly to the test log, so any notice from setting
  427  		# the timer again must be in the file by then.
  428  		$node_standby->wait_for_event('startup', $wait_event);
  429  		unlike(
  430  			slurp_file($node_standby->logfile, $log_offset),
  431  			qr/notice triggered for injection point \Q$point\E/,
  432  			"$kind: unrelated wakeup did not restart the deadlock timer");
  433  
  434  		# Stop recording timer setup before releasing the pin or lock.
  435  		$node_standby->safe_psql('postgres',
  436  			"SELECT injection_points_detach('$point');");
  437  		$session->query_safe('COMMIT;');
  438  		# Wait for replay too: VACUUM can return before flushing its WAL.
  439  		$node_primary->wait_for_catchup($node_standby, 'replay',
  440  			$node_primary->lsn('insert'));
  441  		$session->quit;
  442  	}
  443  }
  444  
```

## src/test/modules/test_misc/t/011_lock_stats.pl lines 122-158

SHA-256 of whole file: `763f4b41072d7a5f601b89ebfaa7c9163cf38da1846a99d280231c4ebcdab1b8`

```
  122  
  123  # Check that log_lock_waits message is emitted during a lock wait.
  124  $node->wait_for_log(qr/still waiting for AccessExclusiveLock on relation/,
  125  	$log_offset);
  126  
  127  # Wake the backend waiting on the lock and confirm it woke by calling
  128  # pg_log_backend_memory_contexts() and checking for the logged memory
  129  # contexts. This is necessary to test later that the "still waiting for"
  130  # message is logged exactly once per wait, even if the backend wakes
  131  # during the wait.
  132  $node->safe_psql(
  133  	'postgres', q[SELECT pg_log_backend_memory_contexts(pid)
  134  	FROM pg_locks WHERE locktype = 'relation' AND
  135  	relation = 'test_stat_tab'::regclass AND NOT granted;]);
  136  $node->wait_for_log(qr/logging memory contexts/, $log_offset);
  137  
  138  # deadlock_timeout fired, now commit in s1 and s2
  139  $s1->query_safe(q(COMMIT));
  140  $s2->query_safe(q(COMMIT));
  141  
  142  # check that pg_stat_lock has been updated
  143  wait_for_pg_stat_lock($node, 'relation');
  144  ok(1, "Lock stats ok for relation");
  145  
  146  # Check that log_lock_waits message is emitted when the lock is acquired
  147  # after waiting.
  148  $node->wait_for_log(qr/acquired AccessExclusiveLock on relation/,
  149  	$log_offset);
  150  
  151  # Check that the "still waiting for" message is logged exactly once per wait,
  152  # even if the backend wakes during the wait.
  153  my $log_contents = slurp_file($node->logfile, $log_offset);
  154  my @still_waiting = ($log_contents =~ /still waiting for/g);
  155  is( scalar @still_waiting,
  156  	1,
  157  	"still waiting logged exactly once despite wakeups from pg_log_backend_memory_contexts()"
  158  );
```

