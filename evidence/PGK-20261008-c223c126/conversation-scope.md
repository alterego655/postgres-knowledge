# Conversation evidence and limits

This is a capture summary, not a verbatim transcript. The conversation investigated historical commit 23cbadeeb4738b8f5e615f0c5a2ef7af6111d512, quantified catalog WAL changes, compared target getters, created two local SQL API commits, and discussed application connection pools. Capture date: 2026-10-08.

A user-supplied email attributed to Jobin Augustine reported an independently written Rust application using deadpool with 16 pooled connections, approximately one timeout per 2,000 waits, and all application tasks stalled waiting. No application source, absolute mail date, or Message-ID was supplied for this report. It is third-party evidence, not an independently repeated experiment. The meaning of asynchronous commit and the arrangement of primary/standby pools were not established.

The earlier conversation reported successful build, test_setup/enum/opr_sanity, all 74 recovery TAP assertions, and XML documentation validation for the two local API patches. Their original /tmp/pg-insert-end-api validation logs were unavailable at capture; these results are conversation-reported, not independently revalidated here. The Git patch objects were available and are preserved. No submission, merge, backpatch, or release outcome was verified.

A session/backend-local WAL-end getter was discussed but not implemented. Its semantics for transaction boundaries, no-WAL operations, abort, prepared transactions, and parallel workers remain design work. The central distinction is between completion of already reserved WAL and dependence on a new, future WAL reservation.
