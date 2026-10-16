# Source excerpts for PGK-20261016-2cd01b69

Captured and checked on 2026-10-16 using `git show f58ab18a90460cd297249bc80b13d84b2671bf0c:<path>` from the PostgreSQL repository. Line numbers and SHA-256 values refer to the committed files, independently of local edits.

The original excerpts and whole-file hashes were verified before this update. Existing excerpt ranges are retained or extended; additional excerpts support the corrections, the omitted REPACK caller, and the restoration path. The keepalive follow-up adds publisher progress, keepalive receipt, and feedback-field excerpts. These are source observations, not runtime test results.

<a id="logical"></a>

## src/backend/replication/logical/logical.c

SHA-256 of whole file at commit: `033d5c0a9ecc086396478489cd68c8dd5d924a1f6a1e026464dc72afbc0d6a0b`

### Lines 630-660: CreateDecodingContext: session start S vs slot confirmed_flush C

```c
  630  	if (!XLogRecPtrIsValid(start_lsn))
  631  	{
  632  		/* continue from last position */
  633  		start_lsn = slot->data.confirmed_flush;
  634  	}
  635  	else if (start_lsn < slot->data.confirmed_flush)
  636  	{
  637  		/*
  638  		 * It might seem like we should error out in this case, but it's
  639  		 * pretty common for a client to acknowledge a LSN it doesn't have to
  640  		 * do anything for, and thus didn't store persistently, because the
  641  		 * xlog records didn't result in anything relevant for logical
  642  		 * decoding. Clients have to be able to do that to support synchronous
  643  		 * replication.
  644  		 *
  645  		 * Starting at a different LSN than requested might not catch certain
  646  		 * kinds of client errors; so the client may wish to check that
  647  		 * confirmed_flush_lsn matches its expectations.
  648  		 */
  649  		elog(LOG, "%X/%08X has been already streamed, forwarding to %X/%08X",
  650  			 LSN_FORMAT_ARGS(start_lsn),
  651  			 LSN_FORMAT_ARGS(slot->data.confirmed_flush));
  652  
  653  		start_lsn = slot->data.confirmed_flush;
  654  	}
  655  
  656  	ctx = StartupDecodingContext(output_plugin_options,
  657  								 start_lsn, InvalidTransactionId, false,
  658  								 fast_forward, false, false,
  659  								 xl_routine, prepare_write,
  660  								 do_write, update_progress);
```

### Lines 690-695: startup message naming both positions

```c
  690  	ereport(LogicalDecodingLogLevel(),
  691  			(errmsg("starting logical decoding for slot \"%s\"",
  692  					NameStr(slot->data.name)),
  693  			 errdetail("Streaming transactions committing after %X/%08X, reading WAL from %X/%08X.",
  694  					   LSN_FORMAT_ARGS(slot->data.confirmed_flush),
  695  					   LSN_FORMAT_ARGS(slot->data.restart_lsn))));
```

### Lines 723-748: DecodingContextFindStartpoint: initial value is EndRecPtr at consistency

```c
  723  	/* Wait for a consistent starting point */
  724  	for (;;)
  725  	{
  726  		XLogRecord *record;
  727  		char	   *err = NULL;
  728  
  729  		/* the read_page callback waits for new WAL */
  730  		record = XLogReadRecord(ctx->reader, &err);
  731  		if (err)
  732  			elog(ERROR, "could not find logical decoding starting point: %s", err);
  733  		if (!record)
  734  			elog(ERROR, "could not find logical decoding starting point");
  735  
  736  		LogicalDecodingProcessRecord(ctx, ctx->reader);
  737  
  738  		/* only continue till we found a consistent spot */
  739  		if (DecodingContextReady(ctx))
  740  			break;
  741  
  742  		CHECK_FOR_INTERRUPTS();
  743  	}
  744  
  745  	SpinLockAcquire(&slot->mutex);
  746  	slot->data.confirmed_flush = ctx->reader->EndRecPtr;
  747  	if (slot->data.two_phase)
  748  		slot->data.two_phase_at = ctx->reader->EndRecPtr;
```

### Lines 964-969: commit callback write location = end of commit record

```c
  964  	error_context_stack = &errcallback;
  965  
  966  	/* set output state */
  967  	ctx->accept_writes = true;
  968  	ctx->write_xid = txn->xid;
  969  	ctx->write_location = txn->end_lsn; /* points to the end of the record */
```

### Lines 1190-1196: change callback write location

```c
 1190  	/*
 1191  	 * Report this change's lsn so replies from clients can give an up-to-date
 1192  	 * answer. This won't ever be enough (and shouldn't be!) to confirm
 1193  	 * receipt of this transaction, but it might allow another transaction's
 1194  	 * commit to be confirmed with one message.
 1195  	 */
 1196  	ctx->write_location = change->lsn;
```

### Lines 1599-1605: stream change callback write location

```c
 1599  	/*
 1600  	 * Report this change's lsn so replies from clients can give an up-to-date
 1601  	 * answer. This won't ever be enough (and shouldn't be!) to confirm
 1602  	 * receipt of this transaction, but it might allow another transaction's
 1603  	 * commit to be confirmed with one message.
 1604  	 */
 1605  	ctx->write_location = change->lsn;
```

### Lines 1817-1896: LogicalIncreaseRestartDecodingForSlot: candidate (valid-at, restart)

```c
 1817  
 1818  /*
 1819   * Mark the minimal LSN (restart_lsn) we need to read to replay all
 1820   * transactions that have not yet committed at current_lsn.
 1821   *
 1822   * Just like LogicalIncreaseXminForSlot this only takes effect when the
 1823   * client has confirmed to have received current_lsn.
 1824   */
 1825  void
 1826  LogicalIncreaseRestartDecodingForSlot(XLogRecPtr current_lsn, XLogRecPtr restart_lsn)
 1827  {
 1828  	bool		updated_lsn = false;
 1829  	ReplicationSlot *slot;
 1830  
 1831  	slot = MyReplicationSlot;
 1832  
 1833  	Assert(slot != NULL);
 1834  	Assert(XLogRecPtrIsValid(restart_lsn));
 1835  	Assert(XLogRecPtrIsValid(current_lsn));
 1836  
 1837  	SpinLockAcquire(&slot->mutex);
 1838  
 1839  	/* don't overwrite if have a newer restart lsn */
 1840  	if (restart_lsn <= slot->data.restart_lsn)
 1841  	{
 1842  		SpinLockRelease(&slot->mutex);
 1843  	}
 1844  
 1845  	/*
 1846  	 * We might have already flushed far enough to directly accept this lsn,
 1847  	 * in this case there is no need to check for existing candidate LSNs
 1848  	 */
 1849  	else if (current_lsn <= slot->data.confirmed_flush)
 1850  	{
 1851  		slot->candidate_restart_valid = current_lsn;
 1852  		slot->candidate_restart_lsn = restart_lsn;
 1853  		SpinLockRelease(&slot->mutex);
 1854  
 1855  		/* our candidate can directly be used */
 1856  		updated_lsn = true;
 1857  	}
 1858  
 1859  	/*
 1860  	 * Only increase if the previous values have been applied, otherwise we
 1861  	 * might never end up updating if the receiver acks too slowly. A missed
 1862  	 * value here will just cause some extra effort after reconnecting.
 1863  	 */
 1864  	else if (!XLogRecPtrIsValid(slot->candidate_restart_valid))
 1865  	{
 1866  		slot->candidate_restart_valid = current_lsn;
 1867  		slot->candidate_restart_lsn = restart_lsn;
 1868  		SpinLockRelease(&slot->mutex);
 1869  
 1870  		elog(DEBUG1, "got new restart lsn %X/%08X at %X/%08X",
 1871  			 LSN_FORMAT_ARGS(restart_lsn),
 1872  			 LSN_FORMAT_ARGS(current_lsn));
 1873  	}
 1874  	else
 1875  	{
 1876  		XLogRecPtr	candidate_restart_lsn;
 1877  		XLogRecPtr	candidate_restart_valid;
 1878  		XLogRecPtr	confirmed_flush;
 1879  
 1880  		candidate_restart_lsn = slot->candidate_restart_lsn;
 1881  		candidate_restart_valid = slot->candidate_restart_valid;
 1882  		confirmed_flush = slot->data.confirmed_flush;
 1883  		SpinLockRelease(&slot->mutex);
 1884  
 1885  		elog(DEBUG1, "failed to increase restart lsn: proposed %X/%08X, after %X/%08X, current candidate %X/%08X, current after %X/%08X, flushed up to %X/%08X",
 1886  			 LSN_FORMAT_ARGS(restart_lsn),
 1887  			 LSN_FORMAT_ARGS(current_lsn),
 1888  			 LSN_FORMAT_ARGS(candidate_restart_lsn),
 1889  			 LSN_FORMAT_ARGS(candidate_restart_valid),
 1890  			 LSN_FORMAT_ARGS(confirmed_flush));
 1891  	}
 1892  
 1893  	/* candidates are already valid with the current flush position, apply */
 1894  	if (updated_lsn)
 1895  		LogicalConfirmReceivedLocation(slot->data.confirmed_flush);
 1896  }
```

### Lines 1915-1967: LogicalConfirmReceivedLocation: monotonic update and candidate acceptance

```c
 1915  
 1916  		/* remember the old restart lsn */
 1917  		restart_lsn = MyReplicationSlot->data.restart_lsn;
 1918  
 1919  		/*
 1920  		 * Prevent moving the confirmed_flush backwards, as this could lead to
 1921  		 * data duplication issues caused by replicating already replicated
 1922  		 * changes.
 1923  		 *
 1924  		 * This can happen when a client acknowledges an LSN it doesn't have
 1925  		 * to do anything for, and thus didn't store persistently. After a
 1926  		 * restart, the client can send the prior LSN that it stored
 1927  		 * persistently as an acknowledgement, but we need to ignore such an
 1928  		 * LSN. See similar case handling in CreateDecodingContext.
 1929  		 */
 1930  		if (lsn > MyReplicationSlot->data.confirmed_flush)
 1931  			MyReplicationSlot->data.confirmed_flush = lsn;
 1932  
 1933  		/* if we're past the location required for bumping xmin, do so */
 1934  		if (XLogRecPtrIsValid(MyReplicationSlot->candidate_xmin_lsn) &&
 1935  			MyReplicationSlot->candidate_xmin_lsn <= lsn)
 1936  		{
 1937  			/*
 1938  			 * We have to write the changed xmin to disk *before* we change
 1939  			 * the in-memory value, otherwise after a crash we wouldn't know
 1940  			 * that some catalog tuples might have been removed already.
 1941  			 *
 1942  			 * Ensure that by first writing to ->xmin and only update
 1943  			 * ->effective_xmin once the new state is synced to disk. After a
 1944  			 * crash ->effective_xmin is set to ->xmin.
 1945  			 */
 1946  			if (TransactionIdIsValid(MyReplicationSlot->candidate_catalog_xmin) &&
 1947  				MyReplicationSlot->data.catalog_xmin != MyReplicationSlot->candidate_catalog_xmin)
 1948  			{
 1949  				MyReplicationSlot->data.catalog_xmin = MyReplicationSlot->candidate_catalog_xmin;
 1950  				MyReplicationSlot->candidate_catalog_xmin = InvalidTransactionId;
 1951  				MyReplicationSlot->candidate_xmin_lsn = InvalidXLogRecPtr;
 1952  				updated_xmin = true;
 1953  			}
 1954  		}
 1955  
 1956  		if (XLogRecPtrIsValid(MyReplicationSlot->candidate_restart_valid) &&
 1957  			MyReplicationSlot->candidate_restart_valid <= lsn)
 1958  		{
 1959  			Assert(XLogRecPtrIsValid(MyReplicationSlot->candidate_restart_lsn));
 1960  
 1961  			MyReplicationSlot->data.restart_lsn = MyReplicationSlot->candidate_restart_lsn;
 1962  			MyReplicationSlot->candidate_restart_lsn = InvalidXLogRecPtr;
 1963  			MyReplicationSlot->candidate_restart_valid = InvalidXLogRecPtr;
 1964  			updated_restart = true;
 1965  		}
 1966  
 1967  		SpinLockRelease(&MyReplicationSlot->mutex);
```

### Lines 1972-2024: save before releasing horizons

```c
 1972  #ifdef USE_INJECTION_POINTS
 1973  			XLogSegNo	seg1,
 1974  						seg2;
 1975  
 1976  			XLByteToSeg(restart_lsn, seg1, wal_segment_size);
 1977  			XLByteToSeg(MyReplicationSlot->data.restart_lsn, seg2, wal_segment_size);
 1978  
 1979  			/* trigger injection point, but only if segment changes */
 1980  			if (seg1 != seg2)
 1981  				INJECTION_POINT("logical-replication-slot-advance-segment", NULL);
 1982  #endif
 1983  
 1984  			ReplicationSlotMarkDirty();
 1985  			ReplicationSlotSave();
 1986  			elog(DEBUG1, "updated xmin: %u restart: %u", updated_xmin, updated_restart);
 1987  		}
 1988  
 1989  		/*
 1990  		 * Now the new xmin is safely on disk, we can let the global value
 1991  		 * advance. We do not take ProcArrayLock or similar since we only
 1992  		 * advance xmin here and there's not much harm done by a concurrent
 1993  		 * computation missing that.
 1994  		 */
 1995  		if (updated_xmin)
 1996  		{
 1997  			SpinLockAcquire(&MyReplicationSlot->mutex);
 1998  			MyReplicationSlot->effective_catalog_xmin = MyReplicationSlot->data.catalog_xmin;
 1999  			SpinLockRelease(&MyReplicationSlot->mutex);
 2000  
 2001  			ReplicationSlotsComputeRequiredXmin(false);
 2002  		}
 2003  
 2004  		/*
 2005  		 * Now that the new restart_lsn is safely on disk, recompute the
 2006  		 * global WAL retention requirement.
 2007  		 */
 2008  		if (updated_restart)
 2009  			ReplicationSlotsComputeRequiredLSN();
 2010  	}
 2011  	else
 2012  	{
 2013  		SpinLockAcquire(&MyReplicationSlot->mutex);
 2014  
 2015  		/*
 2016  		 * Prevent moving the confirmed_flush backwards. See comments above
 2017  		 * for the details.
 2018  		 */
 2019  		if (lsn > MyReplicationSlot->data.confirmed_flush)
 2020  			MyReplicationSlot->data.confirmed_flush = lsn;
 2021  
 2022  		SpinLockRelease(&MyReplicationSlot->mutex);
 2023  	}
 2024  }
```

### Lines 2094-2155: Pending-output check reads from restart_lsn

```c
 2094  XLogRecPtr
 2095  LogicalReplicationSlotCheckPendingWal(XLogRecPtr end_of_wal,
 2096  									  XLogRecPtr scan_cutoff_lsn)
 2097  {
 2098  	XLogRecPtr	last_pending_wal = InvalidXLogRecPtr;
 2099  
 2100  	Assert(MyReplicationSlot);
 2101  	Assert(end_of_wal >= scan_cutoff_lsn);
 2102  
 2103  	PG_TRY();
 2104  	{
 2105  		LogicalDecodingContext *ctx;
 2106  
 2107  		/*
 2108  		 * Create our decoding context in fast_forward mode, passing start_lsn
 2109  		 * as InvalidXLogRecPtr, so that we start processing from the slot's
 2110  		 * confirmed_flush.
 2111  		 */
 2112  		ctx = CreateDecodingContext(InvalidXLogRecPtr,
 2113  									NIL,
 2114  									true,	/* fast_forward */
 2115  									XL_ROUTINE(.page_read = read_local_xlog_page,
 2116  											   .segment_open = wal_segment_open,
 2117  											   .segment_close = wal_segment_close),
 2118  									NULL, NULL, NULL);
 2119  
 2120  		/*
 2121  		 * Start reading at the slot's restart_lsn, which we know points to a
 2122  		 * valid record.
 2123  		 */
 2124  		XLogBeginRead(ctx->reader, MyReplicationSlot->data.restart_lsn);
 2125  
 2126  		/* Invalidate non-timetravel entries */
 2127  		InvalidateSystemCaches();
 2128  
 2129  		while (ctx->reader->EndRecPtr < end_of_wal)
 2130  		{
 2131  			XLogRecord *record;
 2132  			char	   *errm = NULL;
 2133  
 2134  			record = XLogReadRecord(ctx->reader, &errm);
 2135  
 2136  			if (errm)
 2137  				elog(ERROR, "could not find record for logical decoding: %s", errm);
 2138  
 2139  			if (record != NULL)
 2140  				LogicalDecodingProcessRecord(ctx, ctx->reader);
 2141  
 2142  			if (ctx->processing_required)
 2143  			{
 2144  				last_pending_wal = ctx->reader->ReadRecPtr;
 2145  
 2146  				/*
 2147  				 * If we find a decodable WAL after the scan_cutoff_lsn point,
 2148  				 * we can terminate the scan early.
 2149  				 */
 2150  				if (last_pending_wal >= scan_cutoff_lsn)
 2151  					break;
 2152  
 2153  				/* Reset the flag and continue checking */
 2154  				ctx->processing_required = false;
 2155  			}
```

### Lines 2190-2227: Advance uses fast-forward mode and reads from restart_lsn

```c
 2190  XLogRecPtr
 2191  LogicalSlotAdvanceAndCheckSnapState(XLogRecPtr moveto,
 2192  									bool *found_consistent_snapshot)
 2193  {
 2194  	LogicalDecodingContext *ctx;
 2195  	XLogRecPtr	retlsn;
 2196  
 2197  	Assert(XLogRecPtrIsValid(moveto));
 2198  
 2199  	if (found_consistent_snapshot)
 2200  		*found_consistent_snapshot = false;
 2201  
 2202  	PG_TRY();
 2203  	{
 2204  		/*
 2205  		 * Create our decoding context in fast_forward mode, passing start_lsn
 2206  		 * as InvalidXLogRecPtr, so that we start processing from my slot's
 2207  		 * confirmed_flush.
 2208  		 */
 2209  		ctx = CreateDecodingContext(InvalidXLogRecPtr,
 2210  									NIL,
 2211  									true,	/* fast_forward */
 2212  									XL_ROUTINE(.page_read = read_local_xlog_page,
 2213  											   .segment_open = wal_segment_open,
 2214  											   .segment_close = wal_segment_close),
 2215  									NULL, NULL, NULL);
 2216  
 2217  		/*
 2218  		 * Wait for specified streaming replication standby servers (if any)
 2219  		 * to confirm receipt of WAL up to moveto lsn.
 2220  		 */
 2221  		WaitForStandbyConfirmation(moveto);
 2222  
 2223  		/*
 2224  		 * Start reading at the slot's restart_lsn, which we know to point to
 2225  		 * a valid record.
 2226  		 */
 2227  		XLogBeginRead(ctx->reader, MyReplicationSlot->data.restart_lsn);
```

### Lines 2261-2278: advance path confirms and marks dirty

```c
 2261  		if (XLogRecPtrIsValid(ctx->reader->EndRecPtr))
 2262  		{
 2263  			LogicalConfirmReceivedLocation(moveto);
 2264  
 2265  			/*
 2266  			 * If only the confirmed_flush LSN has changed the slot won't get
 2267  			 * marked as dirty by the above. Callers on the walsender
 2268  			 * interface are expected to keep track of their own progress and
 2269  			 * don't need it written out. But SQL-interface users cannot
 2270  			 * specify their own start positions and it's harder for them to
 2271  			 * keep track of their progress, so we should make more of an
 2272  			 * effort to save it for them.
 2273  			 *
 2274  			 * Dirty the slot so it is written out at the next checkpoint. The
 2275  			 * LSN position advanced to may still be lost on a crash but this
 2276  			 * makes the data consistent after a clean shutdown.
 2277  			 */
 2278  			ReplicationSlotMarkDirty();
```

<a id="snapbuild"></a>

## src/backend/replication/logical/snapbuild.c

SHA-256 of whole file at commit: `a82c737725e78cd97f86236efef204611fb79eff1763c0cba6a47122b88060f9`

### Lines 305-311: SnapBuildXactNeedsSkip

```c
  305   * Should the contents of transaction ending at 'ptr' be decoded?
  306   */
  307  bool
  308  SnapBuildXactNeedsSkip(SnapBuild *builder, XLogRecPtr ptr)
  309  {
  310  	return ptr < builder->start_decoding_at;
  311  }
```

### Lines 995-1016: creation: start_decoding_at pushed past pre-consistency commits

```c
  995  
  996  	/*
  997  	 * Transactions preceding BUILDING_SNAPSHOT will neither be decoded, nor
  998  	 * will they be part of a snapshot.  So we don't need to record anything.
  999  	 */
 1000  	if (builder->state == SNAPBUILD_START ||
 1001  		(builder->state == SNAPBUILD_BUILDING_SNAPSHOT &&
 1002  		 TransactionIdPrecedes(xid, builder->next_phase_at)))
 1003  	{
 1004  		/* ensure that only commits after this are getting replayed */
 1005  		if (builder->start_decoding_at <= lsn)
 1006  			builder->start_decoding_at = lsn + 1;
 1007  		return;
 1008  	}
 1009  
 1010  	if (builder->state < SNAPBUILD_CONSISTENT)
 1011  	{
 1012  		/* ensure that only commits after this are getting replayed */
 1013  		if (builder->start_decoding_at <= lsn)
 1014  			builder->start_decoding_at = lsn + 1;
 1015  
 1016  		/*
```

### Lines 1195-1199: snapshot serialized at running_xacts

```c
 1195  			return;
 1196  	}
 1197  	else
 1198  		SnapBuildSerialize(builder, lsn);
 1199  
```

### Lines 1225-1270: candidate proposal at running_xacts

```c
 1225  	 */
 1226  	xmin = ReorderBufferGetOldestXmin(builder->reorder);
 1227  	if (xmin == InvalidTransactionId)
 1228  		xmin = running->oldestRunningXid;
 1229  	elog(DEBUG3, "xmin: %u, xmax: %u, oldest running: %u, oldest xmin: %u",
 1230  		 builder->xmin, builder->xmax, running->oldestRunningXid, xmin);
 1231  	LogicalIncreaseXminForSlot(lsn, xmin);
 1232  
 1233  	/*
 1234  	 * Also tell the slot where we can restart decoding from. We don't want to
 1235  	 * do that after every commit because changing that implies an fsync of
 1236  	 * the logical slot's state file, so we only do it every time we see a
 1237  	 * running xacts record.
 1238  	 *
 1239  	 * Do so by looking for the oldest in progress transaction (determined by
 1240  	 * the first LSN of any of its relevant records). Every transaction
 1241  	 * remembers the last location we stored the snapshot to disk before its
 1242  	 * beginning. That point is where we can restart from.
 1243  	 */
 1244  
 1245  	/*
 1246  	 * Can't know about a serialized snapshot's location if we're not
 1247  	 * consistent.
 1248  	 */
 1249  	if (builder->state < SNAPBUILD_CONSISTENT)
 1250  		return;
 1251  
 1252  	txn = ReorderBufferGetOldestTXN(builder->reorder);
 1253  
 1254  	/*
 1255  	 * oldest ongoing txn might have started when we didn't yet serialize
 1256  	 * anything because we hadn't reached a consistent state yet.
 1257  	 */
 1258  	if (txn != NULL && XLogRecPtrIsValid(txn->restart_decoding_lsn))
 1259  		LogicalIncreaseRestartDecodingForSlot(lsn, txn->restart_decoding_lsn);
 1260  
 1261  	/*
 1262  	 * No in-progress transaction, can reuse the last serialized snapshot if
 1263  	 * we have one.
 1264  	 */
 1265  	else if (txn == NULL &&
 1266  			 XLogRecPtrIsValid(builder->reorder->current_restart_decoding_lsn) &&
 1267  			 XLogRecPtrIsValid(builder->last_serialized_snapshot))
 1268  		LogicalIncreaseRestartDecodingForSlot(lsn,
 1269  											  builder->last_serialized_snapshot);
 1270  }
```

### Lines 1285-1307: Snapshot construction supports both restoration and incremental building

```c
 1285  	/* ---
 1286  	 * Build catalog decoding snapshot incrementally using information about
 1287  	 * the currently running transactions. There are several ways to do that:
 1288  	 *
 1289  	 * a) There were no running transactions when the xl_running_xacts record
 1290  	 *	  was inserted, jump to CONSISTENT immediately. We might find such a
 1291  	 *	  state while waiting on c)'s sub-states.
 1292  	 *
 1293  	 * b) This (in a previous run) or another decoding slot serialized a
 1294  	 *	  snapshot to disk that we can use. Can't use this method while finding
 1295  	 *	  the start point for decoding changes as the restart LSN would be an
 1296  	 *	  arbitrary LSN but we need to find the start point to extract changes
 1297  	 *	  where we won't see the data for partial transactions. Also, we cannot
 1298  	 *	  use this method when a slot needs a full snapshot for export or direct
 1299  	 *	  use, as that snapshot will only contain catalog modifying transactions.
 1300  	 *
 1301  	 * c) First incrementally build a snapshot for catalog tuples
 1302  	 *	  (BUILDING_SNAPSHOT), that requires all, already in-progress,
 1303  	 *	  transactions to finish.  Every transaction starting after that
 1304  	 *	  (FULL_SNAPSHOT state), has enough information to be decoded.  But
 1305  	 *	  for older running transactions no viable snapshot exists yet, so
 1306  	 *	  CONSISTENT will only be reached once all of those have finished.
 1307  	 * ---
```

### Lines 1330-1375: No-running-transactions and saved-snapshot alternatives

```c
 1330  	/*
 1331  	 * a) No transaction were running, we can jump to consistent.
 1332  	 *
 1333  	 * This is not affected by races around xl_running_xacts, because we can
 1334  	 * miss transaction commits, but currently not transactions starting.
 1335  	 *
 1336  	 * NB: We might have already started to incrementally assemble a snapshot,
 1337  	 * so we need to be careful to deal with that.
 1338  	 */
 1339  	if (running->oldestRunningXid == running->nextXid)
 1340  	{
 1341  		if (!XLogRecPtrIsValid(builder->start_decoding_at) ||
 1342  			builder->start_decoding_at <= lsn)
 1343  			/* can decode everything after this */
 1344  			builder->start_decoding_at = lsn + 1;
 1345  
 1346  		/* As no transactions were running xmin/xmax can be trivially set. */
 1347  		builder->xmin = running->nextXid;	/* < are finished */
 1348  		builder->xmax = running->nextXid;	/* >= are running */
 1349  
 1350  		/* so we can safely use the faster comparisons */
 1351  		Assert(TransactionIdIsNormal(builder->xmin));
 1352  		Assert(TransactionIdIsNormal(builder->xmax));
 1353  
 1354  		builder->state = SNAPBUILD_CONSISTENT;
 1355  		builder->next_phase_at = InvalidTransactionId;
 1356  
 1357  		ereport(LogicalDecodingLogLevel(),
 1358  				errmsg("logical decoding found consistent point at %X/%08X",
 1359  					   LSN_FORMAT_ARGS(lsn)),
 1360  				errdetail("There are no running transactions."));
 1361  
 1362  		return false;
 1363  	}
 1364  
 1365  	/*
 1366  	 * b) valid on disk state and while neither building full snapshot nor
 1367  	 * creating a slot.
 1368  	 */
 1369  	else if (!builder->building_full_snapshot &&
 1370  			 !builder->in_slot_creation &&
 1371  			 SnapBuildRestore(builder, lsn))
 1372  	{
 1373  		/* there won't be any state to cleanup */
 1374  		return false;
 1375  	}
```

### Lines 1528-1535: Serialization point handling

```c
 1528  void
 1529  SnapBuildSerializationPoint(SnapBuild *builder, XLogRecPtr lsn)
 1530  {
 1531  	if (builder->state < SNAPBUILD_CONSISTENT)
 1532  		SnapBuildRestore(builder, lsn);
 1533  	else
 1534  		SnapBuildSerialize(builder, lsn);
 1535  }
```

### Lines 1761-1771: A serialized snapshot establishes a later restart point

```c
 1761  	/*
 1762  	 * Now there's no way we can lose the dumped state anymore, remember this
 1763  	 * as a serialization point.
 1764  	 */
 1765  	builder->last_serialized_snapshot = lsn;
 1766  
 1767  	MemoryContextSwitchTo(old_ctx);
 1768  
 1769  out:
 1770  	ReorderBufferSetRestartPoint(builder->reorder,
 1771  								 builder->last_serialized_snapshot);
```

<a id="decode"></a>

## src/backend/replication/logical/decode.c

SHA-256 of whole file at commit: `d7ed23f3e0f2905ac35163a6c73c6884c5cf276c216a02ac01d232dff8c4038f`

### Lines 139-145: other serialization points

```c
  139  	{
  140  			/* this is also used in END_OF_RECOVERY checkpoints */
  141  		case XLOG_CHECKPOINT_SHUTDOWN:
  142  		case XLOG_END_OF_RECOVERY:
  143  			SnapBuildSerializationPoint(builder, buf->origptr);
  144  
  145  			break;
```

### Lines 628-638: non-transactional message skip

```c
  628  	if (message->dbId != ctx->slot->data.database ||
  629  		FilterByOrigin(ctx, origin_id))
  630  		return;
  631  
  632  	if (message->transactional &&
  633  		!SnapBuildProcessChange(builder, xid, buf->origptr))
  634  		return;
  635  	else if (!message->transactional &&
  636  			 (SnapBuildCurrentState(builder) != SNAPBUILD_CONSISTENT ||
  637  			  SnapBuildXactNeedsSkip(builder, buf->origptr)))
  638  		return;
```

### Lines 703-756: Commit skip check and two-phase resolution

```c
  703  	SnapBuildCommitTxn(ctx->snapshot_builder, buf->origptr, xid,
  704  					   parsed->nsubxacts, parsed->subxacts,
  705  					   parsed->xinfo);
  706  
  707  	/* ----
  708  	 * Check whether we are interested in this specific transaction, and tell
  709  	 * the reorderbuffer to forget the content of the (sub-)transactions
  710  	 * if not.
  711  	 *
  712  	 * We can't just use ReorderBufferAbort() here, because we need to execute
  713  	 * the transaction's invalidations.  This currently won't be needed if
  714  	 * we're just skipping over the transaction because currently we only do
  715  	 * so during startup, to get to the first transaction the client needs. As
  716  	 * we have reset the catalog caches before starting to read WAL, and we
  717  	 * haven't yet touched any catalogs, there can't be anything to invalidate.
  718  	 * But if we're "forgetting" this commit because it happened in another
  719  	 * database, the invalidations might be important, because they could be
  720  	 * for shared catalogs and we might have loaded data into the relevant
  721  	 * syscaches.
  722  	 * ---
  723  	 */
  724  	if (DecodeTXNNeedSkip(ctx, buf, parsed->dbId, origin_id))
  725  	{
  726  		for (i = 0; i < parsed->nsubxacts; i++)
  727  		{
  728  			ReorderBufferForget(ctx->reorder, parsed->subxacts[i], buf->origptr);
  729  		}
  730  		ReorderBufferForget(ctx->reorder, xid, buf->origptr);
  731  
  732  		return;
  733  	}
  734  
  735  	/* tell the reorderbuffer about the surviving subtransactions */
  736  	for (i = 0; i < parsed->nsubxacts; i++)
  737  	{
  738  		ReorderBufferCommitChild(ctx->reorder, xid, parsed->subxacts[i],
  739  								 buf->origptr, buf->endptr);
  740  	}
  741  
  742  	/*
  743  	 * Send the final commit record if the transaction data is already
  744  	 * decoded, otherwise, process the entire transaction.
  745  	 */
  746  	if (two_phase)
  747  	{
  748  		ReorderBufferFinishPrepared(ctx->reorder, xid, buf->origptr, buf->endptr,
  749  									SnapBuildGetTwoPhaseAt(ctx->snapshot_builder),
  750  									commit_time, origin_id, origin_lsn,
  751  									parsed->twophase_gid, true);
  752  	}
  753  	else
  754  	{
  755  		ReorderBufferCommit(ctx->reorder, xid, buf->origptr, buf->endptr,
  756  							commit_time, origin_id, origin_lsn);
```

### Lines 797-840: PREPARE handling and skip check

```c
  797  	/*
  798  	 * Remember the prepare info for a txn so that it can be used later in
  799  	 * commit prepared if required. See ReorderBufferFinishPrepared.
  800  	 */
  801  	if (!ReorderBufferRememberPrepareInfo(ctx->reorder, xid, buf->origptr,
  802  										  buf->endptr, prepare_time, origin_id,
  803  										  origin_lsn))
  804  		return;
  805  
  806  	/* We can't start streaming unless a consistent state is reached. */
  807  	if (SnapBuildCurrentState(builder) < SNAPBUILD_CONSISTENT)
  808  	{
  809  		ReorderBufferSkipPrepare(ctx->reorder, xid);
  810  		return;
  811  	}
  812  
  813  	/*
  814  	 * Check whether we need to process this transaction. See
  815  	 * DecodeTXNNeedSkip for the reasons why we sometimes want to skip the
  816  	 * transaction.
  817  	 *
  818  	 * We can't call ReorderBufferForget as we did in DecodeCommit as the txn
  819  	 * hasn't yet been committed, removing this txn before a commit might
  820  	 * result in the computation of an incorrect restart_lsn. See
  821  	 * SnapBuildProcessRunningXacts. But we need to process cache
  822  	 * invalidations if there are any for the reasons mentioned in
  823  	 * DecodeCommit.
  824  	 */
  825  	if (DecodeTXNNeedSkip(ctx, buf, parsed->dbId, origin_id))
  826  	{
  827  		ReorderBufferSkipPrepare(ctx->reorder, xid);
  828  		ReorderBufferInvalidate(ctx->reorder, xid, buf->origptr);
  829  		return;
  830  	}
  831  
  832  	/* Tell the reorderbuffer about the surviving subtransactions. */
  833  	for (i = 0; i < parsed->nsubxacts; i++)
  834  	{
  835  		ReorderBufferCommitChild(ctx->reorder, xid, parsed->subxacts[i],
  836  								 buf->origptr, buf->endptr);
  837  	}
  838  
  839  	/* replay actions of all transaction + subtransactions in order */
  840  	ReorderBufferPrepare(ctx->reorder, xid, parsed->twophase_gid);
```

### Lines 875-891: ROLLBACK PREPARED skip check

```c
  875  	/*
  876  	 * Check whether we need to process this transaction. See
  877  	 * DecodeTXNNeedSkip for the reasons why we sometimes want to skip the
  878  	 * transaction.
  879  	 */
  880  	skip_xact = DecodeTXNNeedSkip(ctx, buf, parsed->dbId, origin_id);
  881  
  882  	/*
  883  	 * Send the final rollback record for a prepared transaction unless we
  884  	 * need to skip it. For non-two-phase xacts, simply forget the xact.
  885  	 */
  886  	if (two_phase && !skip_xact)
  887  	{
  888  		ReorderBufferFinishPrepared(ctx->reorder, xid, buf->origptr, buf->endptr,
  889  									InvalidXLogRecPtr,
  890  									abort_time, origin_id, origin_lsn,
  891  									parsed->twophase_gid, false);
```

### Lines 1335-1341: DecodeTXNNeedSkip

```c
 1335  DecodeTXNNeedSkip(LogicalDecodingContext *ctx, XLogRecordBuffer *buf,
 1336  				  Oid txn_dbid, ReplOriginId origin_id)
 1337  {
 1338  	if (SnapBuildXactNeedsSkip(ctx->snapshot_builder, buf->origptr) ||
 1339  		(txn_dbid != InvalidOid && txn_dbid != ctx->slot->data.database) ||
 1340  		FilterByOrigin(ctx, origin_id))
 1341  		return true;
```

<a id="sql-decoding"></a>

## src/backend/replication/logical/logicalfuncs.c

SHA-256 of whole file at commit: `e3cb2e1953b9d33690cb48b39a9ebc73853530fe2da1c0cec3a07b786a2a5c89`

### Lines 241-267: Read WAL from restart_lsn and process records

```c
  241  		/*
  242  		 * Decoding of WAL must start at restart_lsn so that the entirety of
  243  		 * xacts that committed after the slot's confirmed_flush can be
  244  		 * accumulated into reorder buffers.
  245  		 */
  246  		XLogBeginRead(ctx->reader, MyReplicationSlot->data.restart_lsn);
  247  
  248  		/* invalidate non-timetravel entries */
  249  		InvalidateSystemCaches();
  250  
  251  		/* Decode until we run out of records */
  252  		while (ctx->reader->EndRecPtr < end_of_wal)
  253  		{
  254  			XLogRecord *record;
  255  			char	   *errm = NULL;
  256  
  257  			record = XLogReadRecord(ctx->reader, &errm);
  258  			if (errm)
  259  				elog(ERROR, "could not find record for logical decoding: %s", errm);
  260  
  261  			/*
  262  			 * The {begin_txn,change,commit_txn}_wrapper callbacks above will
  263  			 * store the description into our tuplestore.
  264  			 */
  265  			if (record != NULL)
  266  			{
  267  				LogicalDecodingProcessRecord(ctx, ctx->reader);
```

### Lines 288-310: SQL get confirms and marks dirty

```c
  288  		/*
  289  		 * Next time, start where we left off. (Hunting things, the family
  290  		 * business..)
  291  		 */
  292  		if (XLogRecPtrIsValid(ctx->reader->EndRecPtr) && confirm)
  293  		{
  294  			LogicalConfirmReceivedLocation(ctx->reader->EndRecPtr);
  295  
  296  			/*
  297  			 * If only the confirmed_flush_lsn has changed the slot won't get
  298  			 * marked as dirty by the above. Callers on the walsender
  299  			 * interface are expected to keep track of their own progress and
  300  			 * don't need it written out. But SQL-interface users cannot
  301  			 * specify their own start positions and it's harder for them to
  302  			 * keep track of their progress, so we should make more of an
  303  			 * effort to save it for them.
  304  			 *
  305  			 * Dirty the slot so it's written out at the next checkpoint.
  306  			 * We'll still lose its position on crash, as documented, but it's
  307  			 * better than always losing the position even on clean restart.
  308  			 */
  309  			ReplicationSlotMarkDirty();
  310  		}
```

### Lines 333-345: Get confirms; peek does not

```c
  333  Datum
  334  pg_logical_slot_get_changes(PG_FUNCTION_ARGS)
  335  {
  336  	return pg_logical_slot_get_changes_guts(fcinfo, true, false);
  337  }
  338  
  339  /*
  340   * SQL function returning the changestream as text, only peeking ahead.
  341   */
  342  Datum
  343  pg_logical_slot_peek_changes(PG_FUNCTION_ARGS)
  344  {
  345  	return pg_logical_slot_get_changes_guts(fcinfo, false, false);
```

<a id="slot"></a>

## src/backend/replication/slot.c

SHA-256 of whole file at commit: `b668a8efcfa5c43077850bf65ad1b296a6be27b1a1d6762c98e2d878ce9ddeb0`

### Lines 1340-1365: WAL retention uses last_saved_restart_lsn

```c
 1340  		/* invalidated slots need not apply */
 1341  		if (invalidated)
 1342  			continue;
 1343  
 1344  		/*
 1345  		 * For persistent slot use last_saved_restart_lsn to compute the
 1346  		 * oldest LSN for removal of WAL segments.  The segments between
 1347  		 * last_saved_restart_lsn and restart_lsn might be needed by a
 1348  		 * persistent slot in the case of database crash.  Non-persistent
 1349  		 * slots can't survive the database crash, so we don't care about
 1350  		 * last_saved_restart_lsn for them.
 1351  		 */
 1352  		if (persistency == RS_PERSISTENT)
 1353  		{
 1354  			if (XLogRecPtrIsValid(last_saved_restart_lsn) &&
 1355  				restart_lsn > last_saved_restart_lsn)
 1356  			{
 1357  				restart_lsn = last_saved_restart_lsn;
 1358  			}
 1359  		}
 1360  
 1361  		if (XLogRecPtrIsValid(restart_lsn) &&
 1362  			(!XLogRecPtrIsValid(min_required) ||
 1363  			 restart_lsn < min_required))
 1364  			min_required = restart_lsn;
 1365  	}
```

### Lines 1744-1789: Initial restart_lsn does not require an existing serialized decoding snapshot

```c
 1744  	/*
 1745  	 * For logical slots log a standby snapshot and start logical decoding at
 1746  	 * exactly that position. That allows the slot to start up more quickly.
 1747  	 * But on a standby we cannot do WAL writes, so just use the replay
 1748  	 * pointer; effectively, an attempt to create a logical slot on standby
 1749  	 * will cause it to wait for an xl_running_xact record to be logged
 1750  	 * independently on the primary, so that a snapshot can be built using the
 1751  	 * record.
 1752  	 *
 1753  	 * None of this is needed (or indeed helpful) for physical slots as
 1754  	 * they'll start replay at the last logged checkpoint anyway. Instead,
 1755  	 * return the location of the last redo LSN, where a base backup has to
 1756  	 * start replay at.
 1757  	 */
 1758  	if (SlotIsPhysical(slot))
 1759  		restart_lsn = GetRedoRecPtr();
 1760  	else if (RecoveryInProgress())
 1761  		restart_lsn = GetXLogReplayRecPtr(NULL);
 1762  	else
 1763  		restart_lsn = GetXLogInsertRecPtr();
 1764  
 1765  	SpinLockAcquire(&slot->mutex);
 1766  	slot->data.restart_lsn = restart_lsn;
 1767  	SpinLockRelease(&slot->mutex);
 1768  
 1769  	/* prevent WAL removal as fast as possible */
 1770  	ReplicationSlotsComputeRequiredLSN();
 1771  
 1772  	/* Checkpoint shouldn't remove the required WAL. */
 1773  	XLByteToSeg(slot->data.restart_lsn, segno, wal_segment_size);
 1774  	if (XLogGetLastRemovedSegno() >= segno)
 1775  		elog(ERROR, "WAL required by replication slot %s has been removed concurrently",
 1776  			 NameStr(slot->data.name));
 1777  
 1778  	LWLockRelease(ReplicationSlotAllocationLock);
 1779  
 1780  	if (!RecoveryInProgress() && SlotIsLogical(slot))
 1781  	{
 1782  		XLogRecPtr	flushptr;
 1783  
 1784  		/* make sure we have enough information to start */
 1785  		flushptr = LogStandbySnapshot();
 1786  
 1787  		/* and make sure it's fsynced to disk */
 1788  		XLogFlush(flushptr);
 1789  	}
```

### Lines 2360-2392: shutdown checkpoint flush of changed confirmed_flush

```c
 2360  		/* save the slot to disk, locking is handled in SaveSlotToPath() */
 2361  		sprintf(path, "%s/%s", PG_REPLSLOT_DIR, NameStr(s->data.name));
 2362  
 2363  		/*
 2364  		 * Slot's data is not flushed each time the confirmed_flush LSN is
 2365  		 * updated as that could lead to frequent writes.  However, we decide
 2366  		 * to force a flush of all logical slot's data at the time of shutdown
 2367  		 * if the confirmed_flush LSN is changed since we last flushed it to
 2368  		 * disk.  This helps in avoiding an unnecessary retreat of the
 2369  		 * confirmed_flush LSN after restart.
 2370  		 */
 2371  		if (is_shutdown && SlotIsLogical(s))
 2372  		{
 2373  			SpinLockAcquire(&s->mutex);
 2374  
 2375  			if (s->data.invalidated == RS_INVAL_NONE &&
 2376  				s->data.confirmed_flush > s->last_saved_confirmed_flush)
 2377  			{
 2378  				s->just_dirtied = true;
 2379  				s->dirty = true;
 2380  			}
 2381  			SpinLockRelease(&s->mutex);
 2382  		}
 2383  
 2384  		/*
 2385  		 * Track if we're going to update slot's last_saved_restart_lsn. We
 2386  		 * need this to know if we need to recompute the required LSN.
 2387  		 */
 2388  		if (s->last_saved_restart_lsn != s->data.restart_lsn)
 2389  			last_saved_restart_lsn_updated = true;
 2390  
 2391  		SaveSlotToPath(s, path, LOG);
 2392  	}
```

### Lines 2538-2546: Save returns without writing when the slot is not dirty

```c
 2538  	/* first check whether there's something to write out */
 2539  	SpinLockAcquire(&slot->mutex);
 2540  	was_dirty = slot->dirty;
 2541  	slot->just_dirtied = false;
 2542  	SpinLockRelease(&slot->mutex);
 2543  
 2544  	/* and don't do anything if there's nothing to write */
 2545  	if (!was_dirty)
 2546  		return;
```

### Lines 2581-2585: A save copies all persistent fields

```c
 2581  	SpinLockAcquire(&slot->mutex);
 2582  
 2583  	memcpy(&cp.slotdata, &slot->data, sizeof(ReplicationSlotPersistentData));
 2584  
 2585  	SpinLockRelease(&slot->mutex);
```

### Lines 2675-2684: Save records the persisted confirmed and restart positions

```c
 2675  	/*
 2676  	 * Successfully wrote, unset dirty bit, unless somebody dirtied again
 2677  	 * already and remember the confirmed_flush LSN value.
 2678  	 */
 2679  	SpinLockAcquire(&slot->mutex);
 2680  	if (!slot->just_dirtied)
 2681  		slot->dirty = false;
 2682  	slot->last_saved_confirmed_flush = cp.slotdata.confirmed_flush;
 2683  	slot->last_saved_restart_lsn = cp.slotdata.restart_lsn;
 2684  	SpinLockRelease(&slot->mutex);
```

### Lines 2898-2911: Startup restores persistent fields and clears pending candidates

```c
 2898  		/* restore the entire set of persistent data */
 2899  		memcpy(&slot->data, &cp.slotdata,
 2900  			   sizeof(ReplicationSlotPersistentData));
 2901  
 2902  		/* initialize in memory state */
 2903  		slot->effective_xmin = cp.slotdata.xmin;
 2904  		slot->effective_catalog_xmin = cp.slotdata.catalog_xmin;
 2905  		slot->last_saved_confirmed_flush = cp.slotdata.confirmed_flush;
 2906  		slot->last_saved_restart_lsn = cp.slotdata.restart_lsn;
 2907  
 2908  		slot->candidate_catalog_xmin = InvalidTransactionId;
 2909  		slot->candidate_xmin_lsn = InvalidXLogRecPtr;
 2910  		slot->candidate_restart_lsn = InvalidXLogRecPtr;
 2911  		slot->candidate_restart_valid = InvalidXLogRecPtr;
```

<a id="worker"></a>

## src/backend/replication/logical/worker.c

SHA-256 of whole file at commit: `17c9870546cc232206da82b94a6be6160c22ec88b94d2e53e5fcc40e7c0be0c6`

### Lines 2565-2577: Apply commits origin progress with the local transaction

```c
 2565  		/*
 2566  		 * Update origin state so we can restart streaming from correct
 2567  		 * position in case of crash.
 2568  		 */
 2569  		replorigin_xact_state.origin_lsn = commit_data->end_lsn;
 2570  		replorigin_xact_state.origin_timestamp = commit_data->committime;
 2571  
 2572  		CommitTransactionCommand();
 2573  
 2574  		if (IsTransactionBlock())
 2575  		{
 2576  			EndTransactionBlock(false);
 2577  			CommitTransactionCommand();
```

### Lines 2578-2584: commit records remote/local mapping

```c
 2578  		}
 2579  
 2580  		pgstat_report_stat(false);
 2581  
 2582  		store_flush_position(commit_data->end_lsn, XactLastCommitEnd);
 2583  	}
 2584  	else
```

### Lines 3964-4001: get_flush_position

```c
 3964  get_flush_position(XLogRecPtr *write, XLogRecPtr *flush,
 3965  				   bool *have_pending_txes)
 3966  {
 3967  	dlist_mutable_iter iter;
 3968  	XLogRecPtr	local_flush = GetFlushRecPtr(NULL);
 3969  
 3970  	*write = InvalidXLogRecPtr;
 3971  	*flush = InvalidXLogRecPtr;
 3972  
 3973  	dlist_foreach_modify(iter, &lsn_mapping)
 3974  	{
 3975  		FlushPosition *pos =
 3976  			dlist_container(FlushPosition, node, iter.cur);
 3977  
 3978  		*write = pos->remote_end;
 3979  
 3980  		if (pos->local_end <= local_flush)
 3981  		{
 3982  			*flush = pos->remote_end;
 3983  			dlist_delete(iter.cur);
 3984  			pfree(pos);
 3985  		}
 3986  		else
 3987  		{
 3988  			/*
 3989  			 * Don't want to uselessly iterate over the rest of the list which
 3990  			 * could potentially be long. Instead get the last element and
 3991  			 * grab the write position from there.
 3992  			 */
 3993  			pos = dlist_tail_element(FlushPosition, node,
 3994  									 &lsn_mapping);
 3995  			*write = pos->remote_end;
 3996  			*have_pending_txes = true;
 3997  			return;
 3998  		}
 3999  	}
 4000  
 4001  	*have_pending_txes = !dlist_is_empty(&lsn_mapping);
```

### Lines 4166-4180: Keepalive updates last_received before feedback

```c
 4166  					else if (c == PqReplMsg_Keepalive)
 4167  					{
 4168  						XLogRecPtr	end_lsn;
 4169  						TimestampTz timestamp;
 4170  						bool		reply_requested;
 4171  
 4172  						end_lsn = pq_getmsgint64(&s);
 4173  						timestamp = pq_getmsgint64(&s);
 4174  						reply_requested = pq_getmsgbyte(&s);
 4175  
 4176  						if (last_received < end_lsn)
 4177  							last_received = end_lsn;
 4178  
 4179  						send_feedback(last_received, reply_requested, false);
 4180  
```

### Lines 4390-4397: report received position when nothing pending

```c
 4390  	get_flush_position(&writepos, &flushpos, &have_pending_txes);
 4391  
 4392  	/*
 4393  	 * No outstanding transactions to flush, we can report the latest received
 4394  	 * position. This is important for synchronous replication.
 4395  	 */
 4396  	if (!have_pending_txes)
 4397  		flushpos = writepos = recvpos;
```

### Lines 4426-4429: Feedback fields distinguish received, flushed, and applied progress

```c
 4426  	pq_sendbyte(reply_message, PqReplMsg_StandbyStatusUpdate);
 4427  	pq_sendint64(reply_message, recvpos);	/* write */
 4428  	pq_sendint64(reply_message, flushpos);	/* flush */
 4429  	pq_sendint64(reply_message, writepos);	/* apply */
```

### Lines 5775-5775: start from replication origin progress

```c
 5775  	origin_startpos = replorigin_session_get_progress(false);
```

<a id="slotsync"></a>

## src/backend/replication/logical/slotsync.c

SHA-256 of whole file at commit: `b538c5f0de85904768496be45db70d0d4240becf23d5a9324b5b872180fa15e4`

### Lines 228-240: remote confirmed_lsn must be <= standby flush

```c
  228  	XLogRecPtr	latestFlushPtr = GetStandbyFlushRecPtr(NULL);
  229  
  230  	Assert(slot->data.invalidated == RS_INVAL_NONE);
  231  
  232  	/*
  233  	 * Make sure that concerned WAL is received and flushed before syncing
  234  	 * slot to target lsn received from the primary server.
  235  	 */
  236  	if (remote_slot->confirmed_lsn > latestFlushPtr)
  237  	{
  238  		update_slotsync_skip_stats(SS_SKIP_WAL_NOT_FLUSHED);
  239  
  240  		/*
```

### Lines 255-305: Reject unavailable history and avoid mismatched two-phase state

```c
  255  	/*
  256  	 * Don't overwrite if we already have a newer catalog_xmin and
  257  	 * restart_lsn.
  258  	 */
  259  	if (remote_slot->restart_lsn < slot->data.restart_lsn ||
  260  		TransactionIdPrecedes(remote_slot->catalog_xmin,
  261  							  slot->data.catalog_xmin))
  262  	{
  263  		/* Update slot sync skip stats */
  264  		update_slotsync_skip_stats(SS_SKIP_WAL_OR_ROWS_REMOVED);
  265  
  266  		/*
  267  		 * This can happen in following situations:
  268  		 *
  269  		 * If the slot is temporary, it means either the initial WAL location
  270  		 * reserved for the local slot is ahead of the remote slot's
  271  		 * restart_lsn or the initial xmin_horizon computed for the local slot
  272  		 * is ahead of the remote slot.
  273  		 *
  274  		 * If the slot is persistent, both restart_lsn and catalog_xmin of the
  275  		 * synced slot could still be ahead of the remote slot. Since we use
  276  		 * slot advance functionality to keep snapbuild/slot updated, it is
  277  		 * possible that the restart_lsn and catalog_xmin are advanced to a
  278  		 * later position than it has on the primary. This can happen when
  279  		 * slot advancing machinery finds running xacts record after reaching
  280  		 * the consistent state at a later point than the primary where it
  281  		 * serializes the snapshot and updates the restart_lsn.
  282  		 *
  283  		 * We LOG the message if the slot is temporary as it can help the user
  284  		 * to understand why the slot is not sync-ready. In the case of a
  285  		 * persistent slot, it would be a more common case and won't directly
  286  		 * impact the users, so we used DEBUG1 level to log the message.
  287  		 */
  288  		ereport(slot->data.persistency == RS_TEMPORARY ? LOG : DEBUG1,
  289  				errmsg("could not synchronize replication slot \"%s\"",
  290  					   remote_slot->name),
  291  				errdetail("Synchronization could lead to data loss, because the remote slot needs WAL at LSN %X/%08X and catalog xmin %u, but the standby has LSN %X/%08X and catalog xmin %u.",
  292  						  LSN_FORMAT_ARGS(remote_slot->restart_lsn),
  293  						  remote_slot->catalog_xmin,
  294  						  LSN_FORMAT_ARGS(slot->data.restart_lsn),
  295  						  slot->data.catalog_xmin));
  296  
  297  		/*
  298  		 * Skip updating the configuration. This is required to avoid syncing
  299  		 * two_phase_at without syncing confirmed_lsn. Otherwise, the prepared
  300  		 * transaction between old confirmed_lsn and two_phase_at will
  301  		 * unexpectedly get decoded and sent to the downstream after
  302  		 * promotion. See comments in ReorderBufferFinishPrepared.
  303  		 */
  304  		return false;
  305  	}
```

### Lines 310-337: direct copy when serialized snapshot exists

```c
  310  	 */
  311  	if (remote_slot->confirmed_lsn > slot->data.confirmed_flush ||
  312  		remote_slot->restart_lsn > slot->data.restart_lsn ||
  313  		TransactionIdFollows(remote_slot->catalog_xmin,
  314  							 slot->data.catalog_xmin))
  315  	{
  316  		/*
  317  		 * We can't directly copy the remote slot's LSN or xmin unless there
  318  		 * exists a consistent snapshot at that point. Otherwise, after
  319  		 * promotion, the slots may not reach a consistent point before the
  320  		 * confirmed_flush_lsn which can lead to a data loss. To avoid data
  321  		 * loss, we let slot machinery advance the slot which ensures that
  322  		 * snapbuilder/slot statuses are updated properly.
  323  		 */
  324  		if (SnapBuildSnapshotExists(remote_slot->restart_lsn))
  325  		{
  326  			/*
  327  			 * Update the slot info directly if there is a serialized snapshot
  328  			 * at the restart_lsn, as the slot can quickly reach consistency
  329  			 * at restart_lsn by restoring the snapshot.
  330  			 */
  331  			SpinLockAcquire(&slot->mutex);
  332  			slot->data.restart_lsn = remote_slot->restart_lsn;
  333  			slot->data.confirmed_flush = remote_slot->confirmed_lsn;
  334  			slot->data.catalog_xmin = remote_slot->catalog_xmin;
  335  			SpinLockRelease(&slot->mutex);
  336  
  337  			updated_xmin_or_lsn = true;
```

### Lines 339-383: Advance only when direct snapshot-based copying is unavailable

```c
  339  		else
  340  		{
  341  			bool		found_consistent_snapshot;
  342  			XLogRecPtr	old_confirmed_lsn = slot->data.confirmed_flush;
  343  			XLogRecPtr	old_restart_lsn = slot->data.restart_lsn;
  344  			TransactionId old_catalog_xmin = slot->data.catalog_xmin;
  345  
  346  			LogicalSlotAdvanceAndCheckSnapState(remote_slot->confirmed_lsn,
  347  												&found_consistent_snapshot);
  348  
  349  			/* Sanity check */
  350  			if (slot->data.confirmed_flush != remote_slot->confirmed_lsn)
  351  				ereport(ERROR,
  352  						errmsg_internal("synchronized confirmed_flush for slot \"%s\" differs from remote slot",
  353  										remote_slot->name),
  354  						errdetail_internal("Remote slot has LSN %X/%08X but local slot has LSN %X/%08X.",
  355  										   LSN_FORMAT_ARGS(remote_slot->confirmed_lsn),
  356  										   LSN_FORMAT_ARGS(slot->data.confirmed_flush)));
  357  
  358  			/*
  359  			 * If we can't reach a consistent snapshot, the slot won't be
  360  			 * persisted. See update_and_persist_local_synced_slot().
  361  			 */
  362  			if (!found_consistent_snapshot)
  363  			{
  364  				Assert(MyReplicationSlot->data.persistency == RS_TEMPORARY);
  365  
  366  				ereport(LOG,
  367  						errmsg("could not synchronize replication slot \"%s\"",
  368  							   remote_slot->name),
  369  						errdetail("Synchronization could lead to data loss, because the standby could not build a consistent snapshot to decode WALs at LSN %X/%08X.",
  370  								  LSN_FORMAT_ARGS(slot->data.restart_lsn)));
  371  
  372  				skip_reason = SS_SKIP_NO_CONSISTENT_SNAPSHOT;
  373  			}
  374  
  375  			/*
  376  			 * It is possible that the slot's xmin or LSNs are not updated,
  377  			 * when the synced slot has reached consistent snapshot state or
  378  			 * cannot build one at all.
  379  			 */
  380  			updated_xmin_or_lsn = (old_confirmed_lsn != slot->data.confirmed_flush ||
  381  								   old_restart_lsn != slot->data.restart_lsn ||
  382  								   old_catalog_xmin != slot->data.catalog_xmin);
  383  		}
```

### Lines 417-425: Save updated synchronized state

```c
  417  	/*
  418  	 * We have to write the changed xmin to disk *before* we change the
  419  	 * in-memory value, otherwise after a crash we wouldn't know that some
  420  	 * catalog tuples might have been removed already.
  421  	 */
  422  	if (updated_config || updated_xmin_or_lsn)
  423  	{
  424  		ReplicationSlotMarkDirty();
  425  		ReplicationSlotSave();
```

<a id="slotfuncs"></a>

## src/backend/replication/slotfuncs.c

SHA-256 of whole file at commit: `6f21b8c39910bddb41044a90b22363f331bb96f7437ed8c6964536ebb9de27f7`

### Lines 174-181: SQL creation: catalog-only snapshot

```c
  174  	ctx = CreateInitDecodingContext(plugin, NIL,
  175  									false,	/* just catalogs is OK */
  176  									false,	/* not repack */
  177  									restart_lsn,
  178  									XL_ROUTINE(.page_read = read_local_xlog_page,
  179  											   .segment_open = wal_segment_open,
  180  											   .segment_close = wal_segment_close),
  181  									NULL, NULL, NULL);
```

### Lines 569-580: Public advancement clamps the target to available WAL

```c
  569  	/*
  570  	 * We can't move slot past what's been flushed/replayed so clamp the
  571  	 * target position accordingly.
  572  	 */
  573  	if (!RecoveryInProgress())
  574  		moveto = Min(moveto, GetFlushRecPtr(NULL));
  575  	else
  576  		moveto = Min(moveto, GetXLogReplayRecPtr(NULL));
  577  
  578  	/* Acquire the slot so we "own" it */
  579  	ReplicationSlotAcquire(NameStr(*slotname), true, true);
  580  
```

### Lines 845-857: copy slot installs source confirmed_flush

```c
  845  		MyReplicationSlot->effective_xmin = copy_effective_xmin;
  846  		MyReplicationSlot->effective_catalog_xmin = copy_effective_catalog_xmin;
  847  
  848  		MyReplicationSlot->data.xmin = copy_xmin;
  849  		MyReplicationSlot->data.catalog_xmin = copy_catalog_xmin;
  850  		MyReplicationSlot->data.restart_lsn = copy_restart_lsn;
  851  		MyReplicationSlot->data.confirmed_flush = copy_confirmed_flush;
  852  		SpinLockRelease(&MyReplicationSlot->mutex);
  853  
  854  		ReplicationSlotMarkDirty();
  855  		ReplicationSlotsComputeRequiredXmin(false);
  856  		ReplicationSlotsComputeRequiredLSN();
  857  		ReplicationSlotSave();
```

<a id="walsender"></a>

## src/backend/replication/walsender.c

SHA-256 of whole file at commit: `8f780339ae9110ff8a8b23953e15b3c44023061602d64742b1ba78ca54fca236`

### Lines 1625-1639: WAL-data header carries write location

```c
 1625  WalSndPrepareWrite(LogicalDecodingContext *ctx, XLogRecPtr lsn, TransactionId xid, bool last_write)
 1626  {
 1627  	/* can't have sync rep confused by sending the same LSN several times */
 1628  	if (!last_write)
 1629  		lsn = InvalidXLogRecPtr;
 1630  
 1631  	resetStringInfo(ctx->out);
 1632  
 1633  	pq_sendbyte(ctx->out, PqReplMsg_WALData);
 1634  	pq_sendint64(ctx->out, lsn);	/* dataStart */
 1635  	pq_sendint64(ctx->out, lsn);	/* walEnd */
 1636  
 1637  	/*
 1638  	 * Fill out the sendtime later, just as it's done in XLogSendPhysical, but
 1639  	 * reserve space here.
```

### Lines 1865-1877: Wait applies to an active failover slot

```c
 1865  static bool
 1866  NeedToWaitForStandbys(XLogRecPtr flushed_lsn, uint32 *wait_event)
 1867  {
 1868  	int			elevel = got_STOPPING ? ERROR : WARNING;
 1869  	bool		failover_slot;
 1870  
 1871  	failover_slot = (replication_active && MyReplicationSlot->data.failover);
 1872  
 1873  	/*
 1874  	 * Note that after receiving the shutdown signal, an ERROR is reported if
 1875  	 * any slots are dropped, invalidated, or inactive. This measure is taken
 1876  	 * to prevent the walsender from waiting indefinitely.
 1877  	 */
```

### Lines 1878-1878: failover slot waits for synchronized_standby_slots

```c
 1878  	if (failover_slot && !StandbySlotsHaveCaughtup(flushed_lsn, elevel))
```

### Lines 1879-1909: Wait for designated standbys through the relevant flushed WAL position

```c
 1879  	{
 1880  		*wait_event = WAIT_EVENT_WAIT_FOR_STANDBY_CONFIRMATION;
 1881  		return true;
 1882  	}
 1883  
 1884  	*wait_event = 0;
 1885  	return false;
 1886  }
 1887  
 1888  /*
 1889   * Returns true if we need to wait for WALs to be flushed to disk, or if not
 1890   * all standbys have caught up to the flushed position (flushed_lsn) when the
 1891   * current acquired slot is a logical failover slot and we are
 1892   * streaming; otherwise, returns false.
 1893   *
 1894   * If returning true, the function sets the appropriate wait event in
 1895   * wait_event; otherwise, wait_event is set to 0.
 1896   */
 1897  static bool
 1898  NeedToWaitForWal(XLogRecPtr target_lsn, XLogRecPtr flushed_lsn,
 1899  				 uint32 *wait_event)
 1900  {
 1901  	/* Check if we need to wait for WALs to be flushed to disk */
 1902  	if (target_lsn > flushed_lsn)
 1903  	{
 1904  		*wait_event = WAIT_EVENT_WAL_SENDER_WAIT_FOR_WAL;
 1905  		return true;
 1906  	}
 1907  
 1908  	/* Check if the standby slots have caught up to the flushed position */
 1909  	return NeedToWaitForStandbys(flushed_lsn, wait_event);
```

### Lines 2512-2523: physical slot: restart_lsn = flush

```c
 2512  PhysicalConfirmReceivedLocation(XLogRecPtr lsn)
 2513  {
 2514  	bool		changed = false;
 2515  	ReplicationSlot *slot = MyReplicationSlot;
 2516  
 2517  	Assert(XLogRecPtrIsValid(lsn));
 2518  	SpinLockAcquire(&slot->mutex);
 2519  	if (slot->data.restart_lsn != lsn)
 2520  	{
 2521  		changed = true;
 2522  		slot->data.restart_lsn = lsn;
 2523  	}
```

### Lines 2640-2647: standby reply confirms flush

```c
 2640  	 * Advance our local xmin horizon when the client confirmed a flush.
 2641  	 */
 2642  	if (MyReplicationSlot && XLogRecPtrIsValid(flushPtr))
 2643  	{
 2644  		if (SlotIsLogical(MyReplicationSlot))
 2645  			LogicalConfirmReceivedLocation(flushPtr);
 2646  		else
 2647  			PhysicalConfirmReceivedLocation(flushPtr);
```

### Lines 3726-3736: Decoding advances sentPtr even when no transaction output is emitted

```c
 3726  	if (record != NULL)
 3727  	{
 3728  		/*
 3729  		 * Note the lack of any call to LagTrackerWrite() which is handled by
 3730  		 * WalSndUpdateProgress which is called by output plugin through
 3731  		 * logical decoding write api.
 3732  		 */
 3733  		LogicalDecodingProcessRecord(logical_decoding_ctx, logical_decoding_ctx->reader);
 3734  
 3735  		sentPtr = logical_decoding_ctx->reader->EndRecPtr;
 3736  	}
```

### Lines 4445-4463: Keepalive carries explicit progress or sentPtr

```c
 4445  static void
 4446  WalSndKeepalive(bool requestReply, XLogRecPtr writePtr)
 4447  {
 4448  	elog(DEBUG2, "sending replication keepalive");
 4449  
 4450  	/* construct the message... */
 4451  	resetStringInfo(&output_message);
 4452  	pq_sendbyte(&output_message, PqReplMsg_Keepalive);
 4453  	pq_sendint64(&output_message, XLogRecPtrIsValid(writePtr) ? writePtr : sentPtr);
 4454  	pq_sendint64(&output_message, GetCurrentTimestamp());
 4455  	pq_sendbyte(&output_message, requestReply ? 1 : 0);
 4456  
 4457  	/* ... and send it wrapped in CopyData */
 4458  	pq_putmessage_noblock(PqMsg_CopyData, output_message.data, output_message.len);
 4459  
 4460  	/* Set local flag */
 4461  	if (requestReply)
 4462  		waiting_for_ping_response = true;
 4463  }
```

<a id="reorderbuffer"></a>

## src/backend/replication/logical/reorderbuffer.c

SHA-256 of whole file at commit: `ab7372f8e30bf246d546aa8dd314a727bc49faf622a9e3cac6eaf9870120d739`

### Lines 3040-3071: two_phase_at fallback

```c
 3040  	/* add the gid in the txn */
 3041  	txn->gid = pstrdup(gid);
 3042  
 3043  	/*
 3044  	 * It is possible that this transaction is not decoded at prepare time
 3045  	 * either because by that time we didn't have a consistent snapshot, or
 3046  	 * two_phase was not enabled, or it was decoded earlier but we have
 3047  	 * restarted. We only need to send the prepare if it was not decoded
 3048  	 * earlier. We don't need to decode the xact for aborts if it is not done
 3049  	 * already.
 3050  	 */
 3051  	if ((txn->final_lsn < two_phase_at) && is_commit)
 3052  	{
 3053  		/*
 3054  		 * txn must have been marked as a prepared transaction and skipped but
 3055  		 * not sent a prepare. Also, the prepare info must have been updated
 3056  		 * in txn even if we skip prepare.
 3057  		 */
 3058  		Assert((txn->txn_flags & RBTXN_PREPARE_STATUS_MASK) ==
 3059  			   (RBTXN_IS_PREPARED | RBTXN_SKIPPED_PREPARE));
 3060  		Assert(XLogRecPtrIsValid(txn->final_lsn));
 3061  
 3062  		/*
 3063  		 * By this time the txn has the prepare record information and it is
 3064  		 * important to use that so that downstream gets the accurate
 3065  		 * information. If instead, we have passed commit information here
 3066  		 * then downstream can behave as it has already replayed commit
 3067  		 * prepared after the restart.
 3068  		 */
 3069  		ReorderBufferReplay(txn, rb, xid, txn->final_lsn, txn->end_lsn,
 3070  							txn->prepare_time, txn->origin_id, txn->origin_lsn);
 3071  	}
```

### Lines 3092-3106: Prepared-transaction commit or rollback remains a separate event

```c
 3092  	txn->final_lsn = commit_lsn;
 3093  	txn->end_lsn = end_lsn;
 3094  	txn->commit_time = commit_time;
 3095  	txn->origin_id = origin_id;
 3096  	txn->origin_lsn = origin_lsn;
 3097  
 3098  	if (is_commit)
 3099  		rb->commit_prepared(rb, txn, commit_lsn);
 3100  	else
 3101  		rb->rollback_prepared(rb, txn, prepare_end_lsn, prepare_time);
 3102  
 3103  	/* cleanup: make sure there's no cache pollution */
 3104  	ReorderBufferExecuteInvalidations(txn->ninvalidations,
 3105  									  txn->invalidations);
 3106  	ReorderBufferCleanupTXN(rb, txn);
```

<a id="subscription"></a>

## src/backend/commands/subscriptioncmds.c

SHA-256 of whole file at commit: `f54b5c1574c81532e18b32086db5304f71dd440f8352976d4600507325ad33a6`

### Lines 782-784: subscription synchronous_commit default off

```c
  782  	/* The default for synchronous_commit of subscriptions is off. */
  783  	if (opts.synchronous_commit == NULL)
  784  		opts.synchronous_commit = "off";
```

<a id="upgrade"></a>

## src/backend/utils/adt/pg_upgrade_support.c

SHA-256 of whole file at commit: `06b735cacf7ebb3f80370a40cfe92f86a075d7d3248e8f50fb44bf36bc9ad9af`

### Lines 286-296: upgrade pending-WAL check (header comment)

```c
  286  /*
  287   * Verify the given slot has already consumed all the WAL changes.
  288   *
  289   * Returns true if there are no decodable WAL records after the
  290   * confirmed_flush_lsn. Otherwise false.
  291   *
  292   * This is a special purpose function to ensure that the given slot can be
  293   * upgraded without data loss.
  294   */
  295  Datum
  296  binary_upgrade_check_logical_slot_pending_wal(PG_FUNCTION_ARGS)
```

### Lines 325-332: actual return values

```c
  325  
  326  	/* Clean up */
  327  	ReplicationSlotRelease();
  328  
  329  	if (XLogRecPtrIsValid(last_pending_wal))
  330  		PG_RETURN_LSN(last_pending_wal);
  331  	else
  332  		PG_RETURN_NULL();
```

<a id="repack"></a>

## src/backend/commands/repack_worker.c

SHA-256 of whole file at commit: `ffd531f06fc3075af4ea9bd0a235efe6bade06ef767633cf472bb366762baf85`

### Lines 406-434: REPACK advances processed WAL because it restarts from scratch after a crash

```c
  406  			/*
  407  			 * We want to allow WAL to be recycled while REPACK is running.
  408  			 *
  409  			 * In normal usage of a replication slot, we need to be very
  410  			 * careful not to advance the LSN until it's been confirmed as
  411  			 * received by the remote.  In REPACK's case, this is not needed:
  412  			 * REPACK will never try to replay the same WAL after a crash, and
  413  			 * if there _is_ a crash, the whole REPACK has to be started from
  414  			 * scratch anyway.
  415  			 *
  416  			 * So here we disregard the careful LSN tracking and just move the
  417  			 * LSN locations forward to what we've processed.  Note that it
  418  			 * would be bogus to move the xmin forward, though, so we don't
  419  			 * touch that.
  420  			 *
  421  			 * This can be done on whatever schedule is convenient, but in
  422  			 * order not to cause unnecessary load, we only do it as we cross
  423  			 * each WAL segment boundary.
  424  			 */
  425  			end_lsn = ctx->reader->EndRecPtr;
  426  			XLByteToSeg(end_lsn, segno_new, wal_segment_size);
  427  			if (segno_new != repack_current_segment)
  428  			{
  429  				LogicalIncreaseRestartDecodingForSlot(end_lsn, end_lsn);
  430  				LogicalConfirmReceivedLocation(end_lsn);
  431  				elog(DEBUG1, "REPACK: confirmed receive location %X/%08X",
  432  					 LSN_FORMAT_ARGS(end_lsn));
  433  				repack_current_segment = segno_new;
  434  			}
```

<a id="writer-audit"></a>

## Assignment and confirmation caller audit

The searches below cover explicit assignments and calls to the confirmation helper in backend source at the inspected commit. Local-variable reads in the first search are not field writes. Whole-structure initialization and restoration are separate: the restoration excerpt above shows `memcpy` of persistent state. The main record classifies meaningful state changes rather than counting textual matches.

Search expression: `(confirmed_flush|confirmed_lsn)[[:space:]]*=`

```text
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/logical.c:746:	slot->data.confirmed_flush = ctx->reader->EndRecPtr;
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/logical.c:1882:		confirmed_flush = slot->data.confirmed_flush;
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/logical.c:1931:			MyReplicationSlot->data.confirmed_flush = lsn;
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/logical.c:2020:			MyReplicationSlot->data.confirmed_flush = lsn;
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/slotsync.c:333:			slot->data.confirmed_flush = remote_slot->confirmed_lsn;
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/slotsync.c:342:			XLogRecPtr	old_confirmed_lsn = slot->data.confirmed_flush;
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/slotsync.c:1041:		remote_slot->confirmed_lsn = isnull ? InvalidXLogRecPtr :
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/slot.c:495:	slot->last_saved_confirmed_flush = InvalidXLogRecPtr;
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/slot.c:2682:	slot->last_saved_confirmed_flush = cp.slotdata.confirmed_flush;
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/slot.c:2905:		slot->last_saved_confirmed_flush = cp.slotdata.confirmed_flush;
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/slotfuncs.c:797:		copy_confirmed_flush = second_slot_contents.data.confirmed_flush;
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/slotfuncs.c:851:		MyReplicationSlot->data.confirmed_flush = copy_confirmed_flush;
```

Search expression: `LogicalConfirmReceivedLocation\(`

```text
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/commands/repack_worker.c:430:				LogicalConfirmReceivedLocation(end_lsn);
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/logical.c:1755: * receiving current_lsn with LogicalConfirmReceivedLocation().
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/logical.c:1815:		LogicalConfirmReceivedLocation(slot->data.confirmed_flush);
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/logical.c:1895:		LogicalConfirmReceivedLocation(slot->data.confirmed_flush);
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/logical.c:1902:LogicalConfirmReceivedLocation(XLogRecPtr lsn)
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/logical.c:2263:			LogicalConfirmReceivedLocation(moveto);
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/logical/logicalfuncs.c:294:			LogicalConfirmReceivedLocation(ctx->reader->EndRecPtr);
f58ab18a90460cd297249bc80b13d84b2671bf0c:src/backend/replication/walsender.c:2645:			LogicalConfirmReceivedLocation(flushPtr);
```
