# Pinned source excerpts

Extracted during capture; line numbers refer to the stated revision.

## 23cbadeeb4738b8f5e615f0c5a2ef7af6111d512:src/backend/access/transam/xlog.c:1899 — XLogBytePosToRecPtr
```c
XLogBytePosToRecPtr(uint64 bytepos)
{
	uint64		fullsegs;
	uint64		fullpages;
	uint64		bytesleft;
	uint32		seg_offset;
	XLogRecPtr	result;

	fullsegs = bytepos / UsableBytesInSegment;
	bytesleft = bytepos % UsableBytesInSegment;

	if (bytesleft < XLOG_BLCKSZ - SizeOfXLogLongPHD)
	{
		/* fits on first page of segment */
		seg_offset = bytesleft + SizeOfXLogLongPHD;
	}
	else
	{
		/* account for the first page on segment with long header */
		seg_offset = XLOG_BLCKSZ;
		bytesleft -= XLOG_BLCKSZ - SizeOfXLogLongPHD;

		fullpages = bytesleft / UsableBytesInPage;
		bytesleft = bytesleft % UsableBytesInPage;

		seg_offset += fullpages * XLOG_BLCKSZ + bytesleft + SizeOfXLogShortPHD;
	}

	XLogSegNoOffsetToRecPtr(fullsegs, seg_offset, wal_segment_size, result);

	return result;
}
```

## 23cbadeeb4738b8f5e615f0c5a2ef7af6111d512:src/backend/access/transam/xlog.c:1939 — XLogBytePosToEndRecPtr
```c
XLogBytePosToEndRecPtr(uint64 bytepos)
{
	uint64		fullsegs;
	uint64		fullpages;
	uint64		bytesleft;
	uint32		seg_offset;
	XLogRecPtr	result;

	fullsegs = bytepos / UsableBytesInSegment;
	bytesleft = bytepos % UsableBytesInSegment;

	if (bytesleft < XLOG_BLCKSZ - SizeOfXLogLongPHD)
	{
		/* fits on first page of segment */
		if (bytesleft == 0)
			seg_offset = 0;
		else
			seg_offset = bytesleft + SizeOfXLogLongPHD;
	}
	else
	{
		/* account for the first page on segment with long header */
		seg_offset = XLOG_BLCKSZ;
		bytesleft -= XLOG_BLCKSZ - SizeOfXLogLongPHD;

		fullpages = bytesleft / UsableBytesInPage;
		bytesleft = bytesleft % UsableBytesInPage;

		if (bytesleft == 0)
			seg_offset += fullpages * XLOG_BLCKSZ + bytesleft;
		else
			seg_offset += fullpages * XLOG_BLCKSZ + bytesleft + SizeOfXLogShortPHD;
	}

	XLogSegNoOffsetToRecPtr(fullsegs, seg_offset, wal_segment_size, result);

	return result;
}
```

## 23cbadeeb4738b8f5e615f0c5a2ef7af6111d512:src/backend/access/transam/xlog.c:10108 — GetXLogInsertRecPtr
```c
GetXLogInsertRecPtr(void)
{
	XLogCtlInsert *Insert = &XLogCtl->Insert;
	uint64		current_bytepos;

	SpinLockAcquire(&Insert->insertpos_lck);
	current_bytepos = Insert->CurrBytePos;
	SpinLockRelease(&Insert->insertpos_lck);

	return XLogBytePosToRecPtr(current_bytepos);
}
```

## 23cbadeeb4738b8f5e615f0c5a2ef7af6111d512:src/backend/access/transam/xloginsert.c:688
```c
688: 			 * We assume page LSN is first data on *every* page that can be
689: 			 * passed to XLogInsert, whether it has the standard page layout
690: 			 * or not.
691: 			 */
692: 			XLogRecPtr	page_lsn = PageGetLSN(regbuf->page);
693: 
694: 			needs_backup = (page_lsn <= RedoRecPtr);
695: 			if (!needs_backup)
696: 			{
697: 				if (!XLogRecPtrIsValid(*fpw_lsn) || page_lsn < *fpw_lsn)
698: 					*fpw_lsn = page_lsn;
699: 			}
700: 		}
701: 
702: 		/* Determine if the buffer data needs to included */
703: 		if (regbuf->rdata_len == 0)
704: 			needs_data = false;
705: 		else if ((regbuf->flags & REGBUF_KEEP_DATA) != 0)
706: 			needs_data = true;
707: 		else
708: 			needs_data = !needs_backup;
709: 
710: 		bkpb.id = block_id;
711: 		bkpb.fork_flags = regbuf->forkno;
712: 		bkpb.data_length = 0;
713: 
714: 		if ((regbuf->flags & REGBUF_WILL_INIT) == REGBUF_WILL_INIT)
715: 			bkpb.fork_flags |= BKPBLOCK_WILL_INIT;
716: 
717: 		/*
718: 		 * If needs_backup is true or WAL checking is enabled for current
```

## 23cbadeeb4738b8f5e615f0c5a2ef7af6111d512:src/backend/access/transam/xloginsert.c:728
```c
728: 			/*
729: 			 * The page needs to be backed up, so calculate its hole length
730: 			 * and offset.
731: 			 */
732: 			if (regbuf->flags & REGBUF_STANDARD)
733: 			{
734: 				/* Assume we can omit data between pd_lower and pd_upper */
735: 				uint16		lower = ((const PageHeaderData *) page)->pd_lower;
736: 				uint16		upper = ((const PageHeaderData *) page)->pd_upper;
737: 
738: 				if (lower >= SizeOfPageHeaderData &&
739: 					upper > lower &&
740: 					upper <= BLCKSZ)
741: 				{
742: 					bimg.hole_offset = lower;
743: 					cbimg.hole_length = upper - lower;
744: 				}
745: 				else
746: 				{
747: 					/* No "hole" to remove */
748: 					bimg.hole_offset = 0;
749: 					cbimg.hole_length = 0;
750: 				}
751: 			}
752: 			else
753: 			{
754: 				/* Not a standard page header, don't try to eliminate "hole" */
755: 				bimg.hole_offset = 0;
756: 				cbimg.hole_length = 0;
757: 			}
758: 
```
