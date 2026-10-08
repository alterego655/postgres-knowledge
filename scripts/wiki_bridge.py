#!/usr/bin/env python3
"""Store OpenWiki snapshots separately while preserving its source-root contract."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid


class BridgeError(Exception):
    pass


def require(ok, message):
    if not ok:
        raise BridgeError(message)


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    require(result.returncode == 0, result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(files):
    return digest(json.dumps({k: digest(v) for k, v in sorted(files.items())}, sort_keys=True).encode())


def safe_path(root, target):
    for part in target.relative_to(root).parts:
        root = root / part
        require(not root.is_symlink(), f"Refusing symlink: {root}")


def wiki_files(root):
    require(not root.is_symlink(), f"Refusing symlink: {root}")
    if not root.exists():
        return {}
    require(not (root / ".run.json").exists(), f"Active OpenWiki run: {root}; finish or resume it first")
    files = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"Refusing symlink: {path}")
        if path.is_dir():
            continue
        name = path.relative_to(root).as_posix()
        if path.name == ".DS_Store" or path.name.startswith("._"):
            continue
        require(path.is_file(), f"Not a regular file: {path}")
        allowed = (name in (".last-update.json", ".page-manifest.json")
                   or (name.startswith(".claims/") and name.endswith(".json"))
                   or (name.endswith(".md") and not any(p.startswith(".") for p in Path(name).parts)))
        require(allowed, f"Unexpected wiki file (review before exporting): {name}")
        files[name] = path.read_bytes()
    return files


def completed(files):
    require(files, "No wiki files found")
    last = json.loads(files[".last-update.json"])
    require(last.get("status") == "complete", "Wiki update is not complete")
    require(last.get("gitHead"), "Missing source commit")
    manifest = json.loads(files[".page-manifest.json"])
    require(manifest.get("schemaVersion") == 1, "Unsupported OpenWiki manifest schema")
    versions = set()
    claims = 0
    pages = manifest["pages"]
    require(pages, "Empty page manifest")
    expected = set()
    for page, info in pages.items():
        require(page.startswith("/openwiki/") and ".." not in Path(page).parts, "Invalid page path")
        relative = page[len("/openwiki/"):]
        sidecar = ".claims/" + str(Path(relative).with_suffix(".json"))
        expected.add(sidecar)
        data = json.loads(files[sidecar])
        version = "sha256:" + digest(files[relative])
        require(version == data["pageVersion"] == info["pageVersion"], f"Page changed outside lifecycle: {page}")
        require(data.get("claims"), f"Missing Claims: {page}")
        claims += len(data["claims"])
        versions.add(data.get("verification", {}).get("by", "unknown"))
    actual = {p for p in files if p.startswith(".claims/")}
    require(actual == expected, "Claims and page manifest disagree")
    return last, {"pages": len(pages), "claims": claims, "verification_tools": sorted(versions)}


def replace_directory(target, files):
    """Swap a prepared copy; retain the previous tree as a recovery backup."""
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".wiki-stage-", dir=target.parent))
    backup = None
    try:
        for name, content in files.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        if target.exists():
            backup = target.with_name(".wiki-backup-" + uuid.uuid4().hex)
            target.rename(backup)
        try:
            stage.rename(target)
        except BaseException:
            if backup:
                backup.rename(target)
            raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return str(backup) if backup else None


@contextmanager
def locked(root):
    local = root / ".wiki-bridge"
    safe_path(root, local)
    local.mkdir(exist_ok=True)
    lock = local / "lock"
    try:
        lock.mkdir()
    except FileExistsError:
        raise BridgeError(f"Bridge locked: {lock}; verify no other writer before removing a stale lock")
    try:
        yield local
    finally:
        lock.rmdir()


def snapshot(bundle):
    safe_path(bundle, bundle / "source.json")
    files = wiki_files(bundle / "openwiki")
    meta = json.loads((bundle / "source.json").read_text())
    require(meta.get("schema_version") == 1, "Unsupported snapshot schema")
    last, _ = completed(files)
    require(meta["wiki_digest"] == identity(files), "Canonical snapshot modified without bridge publication")
    require(meta["files"] == {k: digest(v) for k, v in sorted(files.items())}, "Snapshot file checksums disagree")
    require(meta["source_commit"] == last["gitHead"], "Snapshot source commit mismatch")
    return files, meta


def operate(command, knowledge, source, bootstrap=False):
    knowledge, source = Path(knowledge).resolve(), Path(source).resolve()
    require(Path(git(knowledge, "rev-parse", "--show-toplevel")) == knowledge, "Knowledge path must be a Git root")
    require(Path(git(source, "rev-parse", "--show-toplevel")) == source, "Source path must be a Git root")
    require(knowledge != source, "Source and knowledge repositories must differ")
    bundle = knowledge / "code-wiki" / "postgres"
    working = source / "openwiki"
    safe_path(knowledge, bundle)
    safe_path(source, working)
    with locked(knowledge) as local:
        state_file = local / "state.json"
        state = json.loads(state_file.read_text()) if state_file.exists() else {}
        base = state.get(str(source))
        canonical, meta = snapshot(bundle) if bundle.exists() else ({}, {})
        current = wiki_files(working)
        current_id, canonical_id = identity(current), identity(canonical)
        if command == "status":
            return {"canonical_exists": bool(canonical), "working_matches": bool(canonical) and current_id == canonical_id,
                    "source_head": git(source, "rev-parse", "HEAD"), "documented_commit": meta.get("source_commit"),
                    "working_has_baseline": base is not None, "wiki_digest": meta.get("wiki_digest")}
        backup = None
        if command == "restore":
            require(canonical, "No canonical snapshot; publish --bootstrap first")
            require(not current or current_id == canonical_id or (base and current_id == base["wiki_digest"]),
                    "Working wiki has unpublished changes; refusing to overwrite")
            git(source, "cat-file", "-e", meta["source_commit"] + "^{commit}")
            if current_id != canonical_id:
                backup = replace_directory(working, canonical)
            new_id = canonical_id
        elif command == "publish":
            require(not bootstrap or not canonical, "Bootstrap cannot replace an existing canonical snapshot")
            require(bool(canonical) or bootstrap, "First publication requires --bootstrap")
            require(not canonical or (base and base["wiki_digest"] == canonical_id),
                    "Canonical snapshot changed or no restore baseline; restore/reconcile before publishing")
            last, counts = completed(current)
            head = git(source, "rev-parse", "HEAD")
            require(last["gitHead"] == head, "Source HEAD differs from completed Wiki; finish an OpenWiki update first")
            require(not git(source, "status", "--porcelain", "--untracked-files=no"), "Tracked source changes must be committed or cleared first")
            # Every cited file must belong to the reproducible source revision.
            for name, raw in current.items():
                if not name.startswith(".claims/"):
                    continue
                for claim in json.loads(raw)["claims"]:
                    for evidence in claim["evidence"]:
                        resource = evidence["resource"]
                        require(resource.startswith("repo://"), "Unsupported evidence resource")
                        path = resource[len("repo://"):].split("#", 1)[0]
                        require(path and ".." not in Path(path).parts and not path.startswith("/"), "Unsafe evidence path")
                        require(bool(git(source, "ls-files", "--", path)), f"Evidence is not tracked by source Git: {path}")
            source_url = meta.get("source_repository") or git(source, "remote", "get-url", "origin")
            require(source_url == "https://github.com/postgres/postgres.git", "Expected PostgreSQL upstream origin on bootstrap")
            if current_id != canonical_id:
                metadata = {"schema_version": 1, "source_repository": source_url, "source_commit": head,
                            "openwiki_updated_at": last.get("updatedAt"), "exported_at": datetime.now(timezone.utc).isoformat(),
                            "wiki_digest": current_id, "files": {k: digest(v) for k, v in sorted(current.items())}, **counts}
                export = {"openwiki/" + k: v for k, v in current.items()}
                export["source.json"] = (json.dumps(metadata, indent=2, ensure_ascii=False) + "\n").encode()
                backup = replace_directory(bundle, export)
            new_id = current_id
        else:
            raise BridgeError("Unknown operation")
        # Confirm no cooperating-independent writer changed the source during copying.
        require(identity(wiki_files(working)) == (canonical_id if command == "restore" else current_id),
                "Working Wiki changed during transfer; do not publish or commit until reconciled")
        require(identity(snapshot(bundle)[0]) == new_id, "Canonical Wiki changed during transfer")
        state[str(source)] = {"wiki_digest": new_id}
        temporary = local / ("state-" + uuid.uuid4().hex + ".json")
        temporary.write_text(json.dumps(state, indent=2) + "\n")
        temporary.replace(state_file)
        return {"operation": command, "wiki_digest": new_id, "backup": backup,
                "note": "No Git commit, push, model call, or schedule was performed."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status", "restore", "publish"])
    parser.add_argument("--knowledge-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source", type=Path)
    parser.add_argument("--bootstrap", action="store_true", help="Allow the first publication only")
    args = parser.parse_args()
    try:
        source = args.source
        if source is None:
            source = Path(json.loads((args.knowledge_root / "knowledge.local.json").read_text())["source_repository"])
        require(not args.bootstrap or args.command == "publish", "--bootstrap is only valid for publish")
        print(json.dumps(operate(args.command, args.knowledge_root, source, args.bootstrap), indent=2))
    except (BridgeError, OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"wiki-bridge: {exc}\n")


if __name__ == "__main__":
    main()
