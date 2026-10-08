# PostgreSQL Development Knowledge Base

This repository preserves reusable PostgreSQL development knowledge: bug triggers and root causes, experiment results, design decisions, and the arguments and conclusions from mailing-list discussions. Each record identifies its applicable versions, evidence, and remaining uncertainties to help future investigations.

The repository stores the canonical code Wiki snapshot, investigation records, and topic navigation. OpenWiki maintains a working copy in a PostgreSQL checkout. After a completed update, the bridge publishes the snapshot back here while preserving source references and Claims semantics.

## Start here

- [PostgreSQL code Wiki](code-wiki/postgres/openwiki/quickstart.md): replication, WAL, I/O, and performance mechanisms.
- [Code Wiki source revision](code-wiki/postgres/source.json): source commit, verification tools, and file checksums.
- [Topic navigation](topics/README.md): investigations grouped by replication, WAL and recovery, I/O, and performance.
- [Experience records](records/): one record per reusable problem, root cause, or decision.
- [Record conventions](docs/record-format.md): when to create or update a record and how to describe its verification status.
- [Record template](templates/record.md): a starting point, not a verified case.
- [OpenWiki integration](docs/openwiki-integration.md): canonical storage, working copies, and retrieval boundaries.
- [Evidence](evidence/): necessary reproduction scripts, patches, source excerpts, and experiment output.

Historical conversations, mail, and bug cases have not been imported. No scheduled tasks are enabled.

## Capture knowledge

Request capture explicitly in a development conversation, for example:

> Use pg-knowledge-capture to preserve this investigation, including reproduction conditions, failed approaches, verification results, and applicable versions.

The assistant should search existing records before deciding whether to create, extend, or supersede one. After saving, update the relevant topic entry and try retrieving the record with a realistic question. Ordinary code questions do not automatically create records.

All maintained documentation and records are written in English, regardless of the conversation language. Preserve original evidence verbatim when needed and provide an English explanation rather than altering quotations or logs.

Search from the repository root, for example:

```sh
rg -n -i 'ReplicationSlotRelease|ephemeral|replication slot' records topics
```

No matches may mean the knowledge has not been recorded or the query missed it; it does not prove that PostgreSQL has no related issue.

## Manage changes

Markdown holds the current knowledge; Git preserves its evolution. Review each group of changes, stage only the relevant files, and commit when requested or authorized by an established workflow. An ordinary save request does not automatically authorize a commit or push.

When new evidence overturns a conclusion, update the current conclusion and retain a concise explanation of the change. Commit history does not replace applicability and invalidation notes in the record itself.

For collaboration, use branches and pull requests to review conclusions and evidence. Preserve other contributors' uncommitted changes. The private GitHub repository provides a remote copy; inviting collaborators or changing visibility is a separate decision.

## Local configuration

Copy [knowledge.example.json](knowledge.example.json) to `knowledge.local.json` and enter the absolute path to your PostgreSQL checkout. Git ignores this file so machine-specific paths are not shared with other contributors.

The bridge reads this configuration to locate the checkout. Run `python3 scripts/wiki_bridge.py status` to compare the canonical and working copies. See [OpenWiki integration](docs/openwiki-integration.md) for restore, maintenance, and publication instructions. Background synchronization, scheduled tasks, and a unified index are not enabled.
