# Keepalive acknowledgement history

Evidence for PGK-20261016-2cd01b69, collected on 2026-10-16. This is a focused synthesis, not a verbatim mail archive or a runtime reproduction. Messages were retrieved through the Agora PostgreSQL archive using their Message-IDs. The supplied official flat-thread URL initially failed to load through the web tool; the archive resolved the same root Message-ID. Links below are canonical official message references.

The archive returned 12 messages in the root thread, from 2022-09-08 through 2022-11-04, with `has_more = false`. The thread was reviewed through its commit announcement. This collection does not establish the absence of later discussions in separate threads. Dates below are UTC. Replies are members of the returned thread; the two Bapat messages also carry References back to its root.

## Original question and explanation

- **Ashutosh Sharma, 2022-09-08 10:44:** [Original report](https://www.postgresql.org/message-id/CAE9k0P%3DhiqRXUonnmtS-5Pu8SbO%3DyF6vcrVBcfEf2%2B93ng_f5Q%40mail.gmail.com). Message-ID: `CAE9k0P=hiqRXUonnmtS-5Pu8SbO=yF6vcrVBcfEf2+93ng_f5Q@mail.gmail.com`. Reports confirmed progress passing changes buffered in an unfinished transaction, through keepalive feedback. Initially proposes advertising the transaction begin position instead.
- **Ashutosh Bapat, 2022-09-08 12:53:** [Explanation](https://www.postgresql.org/message-id/CAExHW5vfjYtGoQo049%3Dy9W_MpeeJECc%2BB4np93pVm0Y47EGOGQ%40mail.gmail.com). Message-ID: `CAExHW5vfjYtGoQo049=y9W_MpeeJECc+B4np93pVm0Y47EGOGQ@mail.gmail.com`. Explains interleaving of WAL records and why an unfinished transaction with a later commit remains deliverable after restart. His suggestion that logical replication inherited the pattern from physical replication is expressed as a hypothesis, not established naming history. His subscriber-application wording must not be generalized to all logical consumers.
- **Ashutosh Bapat, 2022-09-19 11:54:** [Documentation correction proposed](https://www.postgresql.org/message-id/CAExHW5shWeMDjHtmwK4T6Ktx%2BkQvGpCgJ3w%3D_MpWT%3DnynC3XSg%40mail.gmail.com). Message-ID: `CAExHW5shWeMDjHtmwK4T6Ktx+kQvGpCgJ3w=_MpWT=nynC3XSg@mail.gmail.com`. Identifies the second sentence as misleading and proposes describing transactions committed before the confirmed boundary. Separately identifies `restart_lsn` as the WAL retention boundary.
- **Ashutosh Sharma, 2022-09-19 14:39:** [Patch submission](https://www.postgresql.org/message-id/CAE9k0P%3DA%2BefJSNpfgiP8DwZ0braPV_Fo2tXQTwamdWLOp9W5yQ%40mail.gmail.com). Message-ID: `CAE9k0P=A+efJSNpfgiP8DwZ0braPV_Fo2tXQTwamdWLOp9W5yQ@mail.gmail.com`. Submitted `fix-doc-for-confirmed_flush_lsn.patch`. The verified Git change below establishes the final implementation outcome; no attachment hash is claimed here.
- **Amit Kapila, 2022-11-04 09:59:** [Commit announcement](https://www.postgresql.org/message-id/CAA4eK1%2BE7PySjDp7UvcvvBOkQShj%3DOvgajmh1N-JX2NuGin0Jg%40mail.gmail.com). Message-ID: `CAA4eK1+E7PySjDp7UvcvvBOkQShj=Ovgajmh1N-JX2NuGin0Jg@mail.gmail.com`. Announces the push. The thread's final acknowledgement is from Sharma at 11:41 that day.

## Verified Git outcomes

The excerpts below were obtained locally with `git show --format=fuller <commit> -- <path>`. They are original Git output. The 2015 change exposed both positions and explicitly distinguished their purposes. The 2022 change corrected only documentation; it did not rename the field or change keepalive behavior. Backport coverage was not investigated.

### 3f811c2d6f51b13b71adff99e82894dd48cee055

[Commit](https://github.com/postgres/postgres/commit/3f811c2d6f51b13b71adff99e82894dd48cee055)

```diff
commit 3f811c2d6f51b13b71adff99e82894dd48cee055
Author:     Andres Freund <andres@anarazel.de>
AuthorDate: Mon Aug 10 13:28:18 2015 +0200
Commit:     Andres Freund <andres@anarazel.de>
CommitDate: Mon Aug 10 13:28:18 2015 +0200

    Add confirmed_flush column to pg_replication_slots.
    
    There's no reason not to expose both restart_lsn and confirmed_flush
    since they have rather distinct meanings. The former is the oldest WAL
    still required and valid for both physical and logical slots, whereas
    the latter is the location up to which a logical slot's consumer has
    confirmed receiving data. Most of the time a slot will require older
    WAL (i.e. restart_lsn) than the confirmed
    position (i.e. confirmed_flush_lsn).
    
    Author: Marko Tiikkaja, editorialized by me
    Discussion: 559D110B.1020109@joh.to

diff --git a/doc/src/sgml/catalogs.sgml b/doc/src/sgml/catalogs.sgml
index 12471d1c6e1..1e895e4999a 100644
--- a/doc/src/sgml/catalogs.sgml
+++ b/doc/src/sgml/catalogs.sgml
@@ -5577,6 +5577,17 @@
       automatically removed during checkpoints.
       </entry>
      </row>
+
+     <row>
+      <entry><structfield>confirmed_flush</structfield></entry>
+      <entry><type>pg_lsn</type></entry>
+      <entry></entry>
+      <entry>The address (<literal>LSN</literal>) up to which the logical
+      slot's consumer has confirmed receiving data. Data older than this is
+      not available anymore. <literal>NULL</> for physical slots.
+      </entry>
+     </row>
+
     </tbody>
    </tgroup>
   </table>
```

### 3e77b2eb3466aff9fe19e209ebc0d899ea869494

[Commit](https://github.com/postgres/postgres/commit/3e77b2eb3466aff9fe19e209ebc0d899ea869494)

```diff
commit 3e77b2eb3466aff9fe19e209ebc0d899ea869494
Author:     Amit Kapila <akapila@postgresql.org>
AuthorDate: Fri Nov 4 09:00:46 2022 +0530
Commit:     Amit Kapila <akapila@postgresql.org>
CommitDate: Fri Nov 4 09:00:46 2022 +0530

    Doc: Improve the description of confirmed_flush_lsn in pg_replication_slots.
    
    Make it clear that the data corresponding to the transactions committed
    before confirmed_flush_lsn is not available anymore.
    
    Author: Ashutosh Sharma
    Reviewd by: Ashutosh Bapat
    Discussion: https://postgr.es/m/CAE9k0P=hiqRXUonnmtS-5Pu8SbO=yF6vcrVBcfEf2+93ng_f5Q@mail.gmail.com

diff --git a/doc/src/sgml/system-views.sgml b/doc/src/sgml/system-views.sgml
index 947598e7e7e..7c716fe3276 100644
--- a/doc/src/sgml/system-views.sgml
+++ b/doc/src/sgml/system-views.sgml
@@ -2413,8 +2413,9 @@ SELECT * FROM pg_locks pl LEFT JOIN pg_prepared_xacts ppx
       </para>
       <para>
        The address (<literal>LSN</literal>) up to which the logical
-       slot's consumer has confirmed receiving data. Data older than this is
-       not available anymore. <literal>NULL</literal> for physical slots.
+       slot's consumer has confirmed receiving data. Data corresponding to the
+       transactions committed before this <literal>LSN</literal> is not
+       available anymore. <literal>NULL</literal> for physical slots.
       </para></entry>
      </row>
 
```

## Current verification and recommendation

The current mechanism was checked at `f58ab18a90460cd297249bc80b13d84b2671bf0c`; see the [numbered source evidence](source-excerpts.md). Publisher decoding advances `sentPtr`; a keepalive carries progress; subscriber feedback checks completed local transactions against local WAL flush; the publisher confirms the reported flush position. The source also retains older WAL and compares an ordinary transaction's commit position with the output boundary.

The [current system-view documentation](https://www.postgresql.org/docs/current/view-pg-replication-slots.html), retrieved on 2026-10-16, retained the 2022 wording. The [replication protocol documentation](https://www.postgresql.org/docs/current/protocol-replication.html) separately explains that the logical streaming start uses the greater of the requested LSN and the slot's confirmed position, including progress where there is no data to process. These are dated observations of mutable documentation URLs.

Recommendation from this investigation: explain keepalive progress explicitly and distinguish output availability through a slot from physical WAL retention. This is not a new community decision, submitted patch, or evidence for changing the field's behavior. No runtime test was performed for this capture.
