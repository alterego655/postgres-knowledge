# OpenWiki Storage and Maintenance

## Canonical storage and working copies

`code-wiki/postgres/openwiki/` is the canonical code Wiki snapshot. It contains pages, Claims, and durable metadata from completed updates. The adjacent `source.json` records the PostgreSQL source URL and commit, OpenWiki verification tool identifiers, export time, and file checksums. Git preserves snapshot history.

The PostgreSQL checkout's `openwiki/` is a restored working copy. OpenWiki 0.7.1 code mode and MCP retrieval still use the source repository root. The bridge preserves this contract without symlinks or modifications to the OpenWiki package. Both copies follow one maintenance workflow; do not edit them independently.

The initial migration preserved the original Wiki bytes and generation timestamps. Copying files did not reverify PostgreSQL behavior. Older deployment notes in the pages reflect their generation context; this guide describes the current storage and maintenance arrangement. All maintained Wiki and knowledge-base prose is in English.

## Set up a team checkout

1. Clone this knowledge repository and the PostgreSQL source.
2. Read `source_commit` in [source.json](../code-wiki/postgres/source.json) and ensure the source repository contains that commit. Use it to reproduce the documented implementation; recheck important conclusions when working on another revision.
3. Copy `knowledge.example.json` to `knowledge.local.json` and enter your local source path.
4. Run from this repository root:

```sh
python3 scripts/wiki_bridge.py restore
python3 scripts/wiki_bridge.py status
```

Use `--source /absolute/path/to/postgres` to override local configuration. The script does not switch source branches, fetch source, invoke a model, or push Git changes.

Restore stops when the existing working copy has unpublished changes. Preserve and verify them before proceeding. When replacing an old working copy, restore prints the backup path. Backups remain under `.wiki-backup-*` in the same parent directory; remove them only after confirming they are no longer needed. Exclude that directory pattern from source Git tracking and OpenWiki scans.

## Update the Wiki

Synchronize the knowledge repository and confirm no other maintainer is writing, then restore the working copy. To document newer source, explicitly choose the source commit; the bridge does not automatically track upstream.

```sh
python3 scripts/wiki_bridge.py restore
```

In the source checkout, ask Codex or OpenCode to update through OpenWiki's begin, page-job, submit, and finish lifecycle. Alternatively, with a configured model provider, run `openwiki code --update --print`. Keep the Wiki output language set to English. Only one host should maintain the Wiki at a time. Resume interrupted runs instead of publishing unfinished output.

After completion, return to the knowledge repository:

```sh
python3 scripts/wiki_bridge.py publish
python3 scripts/wiki_bridge.py status
git diff --stat -- code-wiki/postgres
```

Review the changes, then commit and push `code-wiki/postgres` when authorized. `publish` only copies local files; it is not a Git commit or remote publication. The initial migration used `--bootstrap`, which only works when no canonical snapshot exists and cannot overwrite one.

## Publication checks and conflicts

The bridge requires no active run, a completed last update, page hashes matching Claims and the page manifest, source HEAD matching the completed update, no tracked uncommitted source changes, and source Git tracking for cited evidence files. Unexpected files and symlinks stop the operation. `.DS_Store` and Apple resource sidecars are excluded from export.

The ignored `.wiki-bridge/` directory records each checkout's restored baseline. If another working copy has published a newer snapshot, an older baseline cannot overwrite it. Preserve both sets of work, then coordinate or repeat the update against the new canonical version. There is no force-overwrite option. The bridge lock covers transfers only; maintainers must coordinate a single writer throughout model generation.

The bridge checks structural and version consistency. It does not prove prose correctness or rerun OpenWiki's evidence resolver. Maintenance must still finish the OpenWiki lifecycle and verify important behavior against source and tests.

## Read and retrieve

Read the [Wiki entry point](../code-wiki/postgres/openwiki/quickstart.md) directly. Use the source URL and commit in `source.json` to interpret `repo://src/...` evidence against the corresponding source revision, not against files in this knowledge repository.

For OpenWiki MCP, set `root` to the PostgreSQL checkout containing the restored Wiki, then use `openwiki_search` and `openwiki_read`. Do not change the root to the knowledge repository. `status` displays both source HEAD and the documented source commit to expose revision differences.

Search across records and Wiki pages directly:

```sh
rg -n -i 'ReplicationSlotRelease|ephemeral|replication slot' records topics code-wiki/postgres/openwiki
```

MCP retrieval covers its supported Wiki pages; it does not automatically index `records/`. This migration does not enable a unified index, CI, scheduled tasks, or historical material ingestion.

## Test the bridge

The bridge uses only Python's standard library and Git. Run isolated tests:

```sh
python3 -m unittest discover -s tests -v
```

The tests use temporary repositories and cover round-trip restoration, conflicts, unfinished runs, source drift, manual page changes, symlink rejection, and backup preservation.
