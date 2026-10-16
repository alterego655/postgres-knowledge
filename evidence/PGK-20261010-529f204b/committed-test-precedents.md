# Committed examples of internal-decision regression tests

Captured 2026-10-10 from local PostgreSQL Git objects. These are source artifacts, not test-run results. The discussion links in commit messages are pointers; their threads were not reread for this capture.

## 5bbdfa8a18dc56d3e64aa723a68e02e897cb5ec3

### Commit metadata and message

```text
commit 5bbdfa8a18dc56d3e64aa723a68e02e897cb5ec3
Author:     Michael Paquier <michael@paquier.xyz>
AuthorDate: Mon Sep 9 13:49:36 2024 +0900
Commit:     Michael Paquier <michael@paquier.xyz>
CommitDate: Mon Sep 9 13:49:36 2024 +0900

    Fix waits of REINDEX CONCURRENTLY for indexes with predicates or expressions
    
    As introduced by f9900df5f94, a REINDEX CONCURRENTLY job done for an
    index with predicates or expressions would set PROC_IN_SAFE_IC in its
    MyProc->statusFlags, causing it to be ignored by other concurrent
    operations.
    
    Such concurrent index rebuilds should never be ignored, as a predicate
    or an expression could call a user-defined function that accesses a
    different table than the table where the index is rebuilt.
    
    A test that uses injection points is added, backpatched down to 17.
    Michail has proposed a different test, but I have added something
    simpler with more coverage.
    
    Oversight in f9900df5f949.
    
    Author: Michail Nikolaev
    Discussion: https://postgr.es/m/CANtu0oj9A3kZVduFTG0vrmGnKB+DCHgEpzOp0qAyOgmks84j0w@mail.gmail.com
    Backpatch-through: 14
```

### src/test/modules/injection_points/sql/reindex_conc.sql

SHA-256: `1121de77a23ba830b8391efe6d846e245573d2d0beb3126fa0e7f8c64fccf226`

```text
-- Tests for REINDEX CONCURRENTLY
CREATE EXTENSION injection_points;

-- Check safety of indexes with predicates and expressions.
SELECT injection_points_set_local();
SELECT injection_points_attach('reindex-conc-index-safe', 'notice');
SELECT injection_points_attach('reindex-conc-index-not-safe', 'notice');

CREATE SCHEMA reindex_inj;
CREATE TABLE reindex_inj.tbl(i int primary key, updated_at timestamp);

CREATE UNIQUE INDEX ind_simple ON reindex_inj.tbl(i);
CREATE UNIQUE INDEX ind_expr ON reindex_inj.tbl(ABS(i));
CREATE UNIQUE INDEX ind_pred ON reindex_inj.tbl(i) WHERE mod(i, 2) = 0;
CREATE UNIQUE INDEX ind_expr_pred ON reindex_inj.tbl(abs(i)) WHERE mod(i, 2) = 0;

REINDEX INDEX CONCURRENTLY reindex_inj.ind_simple;
REINDEX INDEX CONCURRENTLY reindex_inj.ind_expr;
REINDEX INDEX CONCURRENTLY reindex_inj.ind_pred;
REINDEX INDEX CONCURRENTLY reindex_inj.ind_expr_pred;

-- Cleanup
SELECT injection_points_detach('reindex-conc-index-safe');
SELECT injection_points_detach('reindex-conc-index-not-safe');
DROP TABLE reindex_inj.tbl;
DROP SCHEMA reindex_inj;

DROP EXTENSION injection_points;
```

### src/test/modules/injection_points/expected/reindex_conc.out

SHA-256: `a59ec389861cc6b8055db641ec815e2b8f9801b7925293fc4fa4f3adae42d3ec`

```text
-- Tests for REINDEX CONCURRENTLY
CREATE EXTENSION injection_points;
-- Check safety of indexes with predicates and expressions.
SELECT injection_points_set_local();
 injection_points_set_local 
----------------------------
 
(1 row)

SELECT injection_points_attach('reindex-conc-index-safe', 'notice');
 injection_points_attach 
-------------------------
 
(1 row)

SELECT injection_points_attach('reindex-conc-index-not-safe', 'notice');
 injection_points_attach 
-------------------------
 
(1 row)

CREATE SCHEMA reindex_inj;
CREATE TABLE reindex_inj.tbl(i int primary key, updated_at timestamp);
CREATE UNIQUE INDEX ind_simple ON reindex_inj.tbl(i);
CREATE UNIQUE INDEX ind_expr ON reindex_inj.tbl(ABS(i));
CREATE UNIQUE INDEX ind_pred ON reindex_inj.tbl(i) WHERE mod(i, 2) = 0;
CREATE UNIQUE INDEX ind_expr_pred ON reindex_inj.tbl(abs(i)) WHERE mod(i, 2) = 0;
REINDEX INDEX CONCURRENTLY reindex_inj.ind_simple;
NOTICE:  notice triggered for injection point reindex-conc-index-safe
REINDEX INDEX CONCURRENTLY reindex_inj.ind_expr;
NOTICE:  notice triggered for injection point reindex-conc-index-not-safe
REINDEX INDEX CONCURRENTLY reindex_inj.ind_pred;
NOTICE:  notice triggered for injection point reindex-conc-index-not-safe
REINDEX INDEX CONCURRENTLY reindex_inj.ind_expr_pred;
NOTICE:  notice triggered for injection point reindex-conc-index-not-safe
-- Cleanup
SELECT injection_points_detach('reindex-conc-index-safe');
 injection_points_detach 
-------------------------
 
(1 row)

SELECT injection_points_detach('reindex-conc-index-not-safe');
 injection_points_detach 
-------------------------
 
(1 row)

DROP TABLE reindex_inj.tbl;
DROP SCHEMA reindex_inj;
DROP EXTENSION injection_points;
```

### Backend change

```diff
diff --git a/src/backend/commands/indexcmds.c b/src/backend/commands/indexcmds.c
index c5a56c75f69..b987e023849 100644
--- a/src/backend/commands/indexcmds.c
+++ b/src/backend/commands/indexcmds.c
@@ -61,6 +61,7 @@
 #include "utils/builtins.h"
 #include "utils/fmgroids.h"
 #include "utils/guc.h"
+#include "utils/injection_point.h"
 #include "utils/inval.h"
 #include "utils/lsyscache.h"
 #include "utils/memutils.h"
@@ -3782,8 +3783,16 @@ ReindexRelationConcurrently(const ReindexStmt *stmt, Oid relationOid, const Rein
 		RestrictSearchPath();
 
 		/* determine safety of this index for set_indexsafe_procflags */
-		idx->safe = (indexRel->rd_indexprs == NIL &&
-					 indexRel->rd_indpred == NIL);
+		idx->safe = (RelationGetIndexExpressions(indexRel) == NIL &&
+					 RelationGetIndexPredicate(indexRel) == NIL);
+
+#ifdef USE_INJECTION_POINTS
+		if (idx->safe)
+			INJECTION_POINT("reindex-conc-index-safe");
+		else
+			INJECTION_POINT("reindex-conc-index-not-safe");
+#endif
+
 		idx->tableId = RelationGetRelid(heapRel);
 		idx->amId = indexRel->rd_rel->relam;
 
```

## 661643dedad97f8b924991fdc739b1f47b0fb60b

### Commit metadata and message

```text
commit 661643dedad97f8b924991fdc739b1f47b0fb60b
Author:     Michael Paquier <michael@paquier.xyz>
AuthorDate: Wed Jun 25 10:03:46 2025 +0900
Commit:     Michael Paquier <michael@paquier.xyz>
CommitDate: Wed Jun 25 10:03:46 2025 +0900

    Avoid scribbling of VACUUM options
    
    This fixes two issues with the handling of VacuumParams in vacuum_rel().
    This code path has the idea to change the passed-in pointer of
    VacuumParams for the "truncate" and "index_cleanup" options for the
    relation worked on, impacting the two following scenarios where
    incorrect options may be used because a VacuumParams pointer is shared
    across multiple relations:
    - Multiple relations in a single VACUUM command.
    - TOAST relations vacuumed with their main relation.
    
    The problem is avoided by providing to the two callers of vacuum_rel()
    copies of VacuumParams, before the pointer is updated for the "truncate"
    and "index_cleanup" options.
    
    The refactoring of the VACUUM option and parameters done in 0d831389749a
    did not introduce an issue, but it has encouraged the problem we are
    dealing with in this commit, with b84dbc8eb80b for "truncate" and
    a96c41feec6b for "index_cleanup" that have been added a couple of years
    after the initial refactoring.  HEAD will be improved with a different
    patch that hardens the uses of VacuumParams across the tree.  This
    cannot be backpatched as it introduces an ABI breakage.
    
    The backend portion of the patch has been authored by Nathan, while I
    have implemented the tests.  The tests rely on injection points to check
    the option values, making them faster, more reliable than the tests
    originally proposed by Shihao, and they also provide more coverage.
    This part can only be backpatched down to v17.
    
    Reported-by: Shihao Zhong <zhong950419@gmail.com>
    Author: Nathan Bossart <nathandbossart@gmail.com>
    Co-authored-by: Michael Paquier <michael@paquier.xyz>
    Discussion: https://postgr.es/m/CAGRkXqTo+aK=GTy5pSc-9cy8H2F2TJvcrZ-zXEiNJj93np1UUw@mail.gmail.com
    Backpatch-through: 13
```

### src/test/modules/injection_points/sql/vacuum.sql

SHA-256: `f121cfc3c88087d33cf38d320467c46b070c3c759cf69bcaacd72da0c15a6968`

```text
-- Tests for VACUUM

CREATE EXTENSION injection_points;

SELECT injection_points_set_local();
SELECT injection_points_attach('vacuum-index-cleanup-auto', 'notice');
SELECT injection_points_attach('vacuum-index-cleanup-disabled', 'notice');
SELECT injection_points_attach('vacuum-index-cleanup-enabled', 'notice');
SELECT injection_points_attach('vacuum-truncate-auto', 'notice');
SELECT injection_points_attach('vacuum-truncate-disabled', 'notice');
SELECT injection_points_attach('vacuum-truncate-enabled', 'notice');

-- Check state of index_cleanup and truncate in VACUUM.
CREATE TABLE vac_tab_on_toast_off(i int, j text) WITH
  (autovacuum_enabled=false,
   vacuum_index_cleanup=true, toast.vacuum_index_cleanup=false,
   vacuum_truncate=true, toast.vacuum_truncate=false);
CREATE TABLE vac_tab_off_toast_on(i int, j text) WITH
  (autovacuum_enabled=false,
   vacuum_index_cleanup=false, toast.vacuum_index_cleanup=true,
   vacuum_truncate=false, toast.vacuum_truncate=true);
-- Multiple relations should use their options in isolation.
VACUUM vac_tab_on_toast_off, vac_tab_off_toast_on;

-- Check "auto" case of index_cleanup and "truncate" controlled by
-- its GUC.
CREATE TABLE vac_tab_auto(i int, j text) WITH
  (autovacuum_enabled=false,
   vacuum_index_cleanup=auto, toast.vacuum_index_cleanup=auto);
SET vacuum_truncate = false;
VACUUM vac_tab_auto;
SET vacuum_truncate = true;
VACUUM vac_tab_auto;
RESET vacuum_truncate;

DROP TABLE vac_tab_auto;
DROP TABLE vac_tab_on_toast_off;
DROP TABLE vac_tab_off_toast_on;

-- Cleanup
SELECT injection_points_detach('vacuum-index-cleanup-auto');
SELECT injection_points_detach('vacuum-index-cleanup-disabled');
SELECT injection_points_detach('vacuum-index-cleanup-enabled');
SELECT injection_points_detach('vacuum-truncate-auto');
SELECT injection_points_detach('vacuum-truncate-disabled');
SELECT injection_points_detach('vacuum-truncate-enabled');
DROP EXTENSION injection_points;
```

### src/test/modules/injection_points/expected/vacuum.out

SHA-256: `b7a44457a17030c9debba98677af8593c8eaec52692879c1097df9dfedb5ed36`

```text
-- Tests for VACUUM
CREATE EXTENSION injection_points;
SELECT injection_points_set_local();
 injection_points_set_local 
----------------------------
 
(1 row)

SELECT injection_points_attach('vacuum-index-cleanup-auto', 'notice');
 injection_points_attach 
-------------------------
 
(1 row)

SELECT injection_points_attach('vacuum-index-cleanup-disabled', 'notice');
 injection_points_attach 
-------------------------
 
(1 row)

SELECT injection_points_attach('vacuum-index-cleanup-enabled', 'notice');
 injection_points_attach 
-------------------------
 
(1 row)

SELECT injection_points_attach('vacuum-truncate-auto', 'notice');
 injection_points_attach 
-------------------------
 
(1 row)

SELECT injection_points_attach('vacuum-truncate-disabled', 'notice');
 injection_points_attach 
-------------------------
 
(1 row)

SELECT injection_points_attach('vacuum-truncate-enabled', 'notice');
 injection_points_attach 
-------------------------
 
(1 row)

-- Check state of index_cleanup and truncate in VACUUM.
CREATE TABLE vac_tab_on_toast_off(i int, j text) WITH
  (autovacuum_enabled=false,
   vacuum_index_cleanup=true, toast.vacuum_index_cleanup=false,
   vacuum_truncate=true, toast.vacuum_truncate=false);
CREATE TABLE vac_tab_off_toast_on(i int, j text) WITH
  (autovacuum_enabled=false,
   vacuum_index_cleanup=false, toast.vacuum_index_cleanup=true,
   vacuum_truncate=false, toast.vacuum_truncate=true);
-- Multiple relations should use their options in isolation.
VACUUM vac_tab_on_toast_off, vac_tab_off_toast_on;
NOTICE:  notice triggered for injection point vacuum-index-cleanup-enabled
NOTICE:  notice triggered for injection point vacuum-truncate-enabled
NOTICE:  notice triggered for injection point vacuum-index-cleanup-disabled
NOTICE:  notice triggered for injection point vacuum-truncate-disabled
NOTICE:  notice triggered for injection point vacuum-index-cleanup-disabled
NOTICE:  notice triggered for injection point vacuum-truncate-disabled
NOTICE:  notice triggered for injection point vacuum-index-cleanup-enabled
NOTICE:  notice triggered for injection point vacuum-truncate-enabled
-- Check "auto" case of index_cleanup and "truncate" controlled by
-- its GUC.
CREATE TABLE vac_tab_auto(i int, j text) WITH
  (autovacuum_enabled=false,
   vacuum_index_cleanup=auto, toast.vacuum_index_cleanup=auto);
SET vacuum_truncate = false;
VACUUM vac_tab_auto;
NOTICE:  notice triggered for injection point vacuum-index-cleanup-auto
NOTICE:  notice triggered for injection point vacuum-truncate-disabled
NOTICE:  notice triggered for injection point vacuum-index-cleanup-auto
NOTICE:  notice triggered for injection point vacuum-truncate-disabled
SET vacuum_truncate = true;
VACUUM vac_tab_auto;
NOTICE:  notice triggered for injection point vacuum-index-cleanup-auto
NOTICE:  notice triggered for injection point vacuum-truncate-enabled
NOTICE:  notice triggered for injection point vacuum-index-cleanup-auto
NOTICE:  notice triggered for injection point vacuum-truncate-enabled
RESET vacuum_truncate;
DROP TABLE vac_tab_auto;
DROP TABLE vac_tab_on_toast_off;
DROP TABLE vac_tab_off_toast_on;
-- Cleanup
SELECT injection_points_detach('vacuum-index-cleanup-auto');
 injection_points_detach 
-------------------------
 
(1 row)

SELECT injection_points_detach('vacuum-index-cleanup-disabled');
 injection_points_detach 
-------------------------
 
(1 row)

SELECT injection_points_detach('vacuum-index-cleanup-enabled');
 injection_points_detach 
-------------------------
 
(1 row)

SELECT injection_points_detach('vacuum-truncate-auto');
 injection_points_detach 
-------------------------
 
(1 row)

SELECT injection_points_detach('vacuum-truncate-disabled');
 injection_points_detach 
-------------------------
 
(1 row)

SELECT injection_points_detach('vacuum-truncate-enabled');
 injection_points_detach 
-------------------------
 
(1 row)

DROP EXTENSION injection_points;
```

### Backend change

```diff
diff --git a/src/backend/commands/vacuum.c b/src/backend/commands/vacuum.c
index 33a33bf6b1c..02993d320da 100644
--- a/src/backend/commands/vacuum.c
+++ b/src/backend/commands/vacuum.c
@@ -56,6 +56,7 @@
 #include "utils/fmgroids.h"
 #include "utils/guc.h"
 #include "utils/guc_hooks.h"
+#include "utils/injection_point.h"
 #include "utils/memutils.h"
 #include "utils/snapmgr.h"
 #include "utils/syscache.h"
@@ -634,7 +635,15 @@ vacuum(List *relations, VacuumParams *params, BufferAccessStrategy bstrategy,
 
 			if (params->options & VACOPT_VACUUM)
 			{
-				if (!vacuum_rel(vrel->oid, vrel->relation, params, bstrategy))
+				VacuumParams params_copy;
+
+				/*
+				 * vacuum_rel() scribbles on the parameters, so give it a copy
+				 * to avoid affecting other relations.
+				 */
+				memcpy(&params_copy, params, sizeof(VacuumParams));
+
+				if (!vacuum_rel(vrel->oid, vrel->relation, &params_copy, bstrategy))
 					continue;
 			}
 
@@ -2008,9 +2017,16 @@ vacuum_rel(Oid relid, RangeVar *relation, VacuumParams *params,
 	Oid			save_userid;
 	int			save_sec_context;
 	int			save_nestlevel;
+	VacuumParams toast_vacuum_params;
 
 	Assert(params != NULL);
 
+	/*
+	 * This function scribbles on the parameters, so make a copy early to
+	 * avoid affecting the TOAST table (if we do end up recursing to it).
+	 */
+	memcpy(&toast_vacuum_params, params, sizeof(VacuumParams));
+
 	/* Begin a transaction for vacuuming this relation */
 	StartTransactionCommand();
 
@@ -2191,6 +2207,15 @@ vacuum_rel(Oid relid, RangeVar *relation, VacuumParams *params,
 		}
 	}
 
+#ifdef USE_INJECTION_POINTS
+	if (params->index_cleanup == VACOPTVALUE_AUTO)
+		INJECTION_POINT("vacuum-index-cleanup-auto", NULL);
+	else if (params->index_cleanup == VACOPTVALUE_DISABLED)
+		INJECTION_POINT("vacuum-index-cleanup-disabled", NULL);
+	else if (params->index_cleanup == VACOPTVALUE_ENABLED)
+		INJECTION_POINT("vacuum-index-cleanup-enabled", NULL);
+#endif
+
 	/*
 	 * Check if the vacuum_max_eager_freeze_failure_rate table storage
 	 * parameter was specified. This overrides the GUC value.
@@ -2221,6 +2246,15 @@ vacuum_rel(Oid relid, RangeVar *relation, VacuumParams *params,
 			params->truncate = VACOPTVALUE_DISABLED;
 	}
 
+#ifdef USE_INJECTION_POINTS
+	if (params->truncate == VACOPTVALUE_AUTO)
+		INJECTION_POINT("vacuum-truncate-auto", NULL);
+	else if (params->truncate == VACOPTVALUE_DISABLED)
+		INJECTION_POINT("vacuum-truncate-disabled", NULL);
+	else if (params->truncate == VACOPTVALUE_ENABLED)
+		INJECTION_POINT("vacuum-truncate-enabled", NULL);
+#endif
+
 	/*
 	 * Remember the relation's TOAST relation for later, if the caller asked
 	 * us to process it.  In VACUUM FULL, though, the toast table is
@@ -2299,15 +2333,12 @@ vacuum_rel(Oid relid, RangeVar *relation, VacuumParams *params,
 	 */
 	if (toast_relid != InvalidOid)
 	{
-		VacuumParams toast_vacuum_params;
-
 		/*
 		 * Force VACOPT_PROCESS_MAIN so vacuum_rel() processes it.  Likewise,
 		 * set toast_parent so that the privilege checks are done on the main
 		 * relation.  NB: This is only safe to do because we hold a session
 		 * lock on the main relation that prevents concurrent deletion.
 		 */
-		memcpy(&toast_vacuum_params, params, sizeof(VacuumParams));
 		toast_vacuum_params.options |= VACOPT_PROCESS_MAIN;
 		toast_vacuum_params.toast_parent = relid;
 
```
