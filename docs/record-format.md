# Experience Record Conventions

## Record boundaries

Organize each record around a reusable problem, root cause, or decision. Multiple conversations, experiments, and patch revisions about the same investigation update one record. Similar symptoms with different causes belong in separate, cross-linked records. A simple fix fully explained by its patch usually needs no additional article unless the user explicitly requests one.

Store records under `records/`. Use filenames of the form `PGK-YYYYMMDD-<8-random-hex-digits>-<short-topic>.md` and an `id` of `PGK-YYYYMMDD-<8-random-hex-digits>`. Use the user's timezone for the date. Check for existing IDs and paths before writing; generate another suffix on collision instead of overwriting a record. The random suffix reduces concurrent creation conflicts. Keep the assigned ID even when the title changes.

Write maintained prose, titles, and navigation in English. Preserve original evidence, identifiers, quotations, and tool output without silently translating or changing them; explain their significance in English.

## Metadata

Start from the [template](../templates/record.md), replace its placeholders, and remove irrelevant writing prompts. The template is not an actual record.

| Field | Meaning |
| --- | --- |
| `id`, `title` | Stable identity and a title describing the actual problem |
| `kind` | `bug`, `investigation`, or `decision`; identify mail or conversation input in the sources |
| `topics`, `symbols` | Topics and exact searchable functions, structures, parameters, or error identifiers |
| `evidence_state` | Headline conclusion: `hypothesis`, `supported`, `refuted`, or `mixed` |
| `delivery` | `not-applicable`, `unknown`, `local-only`, `submitted`, `merged`, or `released` |
| `applicability` | Repository, tested commit, branch, patch identity, configuration, and platform; use `unknown` where unestablished |
| `last_checked` | Date of the latest substantive evidence check; do not refresh for formatting edits alone |
| `sources` | Source types, URLs or Message-IDs actually retrieved, and necessary local evidence paths |
| `supersedes`, `superseded_by` | Optional relationships to other records |

A locally verified fix is not necessarily merged. `merged` requires an identifiable commit and branch; describe backports and release availability separately. When individual conclusions have different evidence strengths, distinguish them in the body rather than hiding them behind one overall status.

## Questions the record should answer

1. What conclusion can be reused, and under which conditions?
2. What are the symptoms and triggers, and how can they be reproduced?
3. What is the root cause or decision rationale, and which evidence supports it?
4. Why does the fix or approach work, and what was actually verified?
5. Which approaches failed, why were earlier hypotheses rejected, and what remains unknown?
6. Where are the original discussions, patches, test results, and related records?

## Evidence by source type

- **Conversations:** identify the relevant scope and preserve necessary excerpts. Label summaries as summaries; do not reconstruct missing verbatim messages or tool output.
- **Bugs and experiments:** record the actual revision, relevant uncommitted patch, reproduction commands, and before/after results. For concurrency issues, retain known interleavings, injection points, repetition counts, and verification limits.
- **Mail:** record Message-ID, author, date, archive URL actually accessed, and collection cutoff. Distinguish personal opinions, discussion consensus, patch submission, and actual merge. Repeated quotations are not independent evidence.

Store local evidence in `evidence/<record-id>/`, creating directories only when there are artifacts to preserve. Commit small, necessary artifacts; for large files, record a durable location and checksum. Do not describe unsaved logs as archived.

## Updates and retrieval

Search existing records before saving. Preserve IDs on updates, emphasize the current conclusion, and explain the evidence behind changes. Refuted content must not continue to appear as current fact.

Add an annotated link to the relevant topic page describing when the case is useful. Test retrieval with a plausible future question or exact symbol and check that the result includes applicability and sources. Finding a file with `rg` does not prove that `openwiki_search` indexes it.
