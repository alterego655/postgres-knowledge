import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("wiki_bridge", Path(__file__).parents[1] / "scripts/wiki_bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.knowledge = self.repo("knowledge")
        self.source = self.repo("source")
        bridge.git(self.source, "remote", "add", "origin", "https://github.com/postgres/postgres.git")
        (self.source / "src.c").write_text("source\n")
        bridge.git(self.source, "add", "src.c")
        bridge.git(self.source, "commit", "-m", "source")
        self.write_wiki(self.source, "original")

    def repo(self, name):
        root = self.root / name
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        bridge.git(root, "config", "user.name", "Bridge Test")
        bridge.git(root, "config", "user.email", "bridge-test@example.invalid")
        return root

    def write_wiki(self, source, text):
        wiki = source / "openwiki"
        (wiki / ".claims").mkdir(parents=True, exist_ok=True)
        raw = ("# Wiki\n" + text + "\n").encode()
        (wiki / "quickstart.md").write_bytes(raw)
        version = "sha256:" + bridge.digest(raw)
        (wiki / ".claims/quickstart.json").write_text(json.dumps({
            "pageVersion": version, "verification": {"by": "test-fixture"},
            "claims": [{"evidence": [{"resource": "repo://src.c"}]}]}))
        (wiki / ".page-manifest.json").write_text(json.dumps({
            "schemaVersion": 1, "pages": {"/openwiki/quickstart.md": {"pageVersion": version}}}))
        (wiki / ".last-update.json").write_text(json.dumps({
            "status": "complete", "gitHead": bridge.git(source, "rev-parse", "HEAD"), "updatedAt": "fixture"}))

    def publish(self, source=None, bootstrap=False):
        return bridge.operate("publish", self.knowledge, source or self.source, bootstrap)

    def clone(self):
        clone = self.root / "second"
        subprocess.run(["git", "clone", "-q", str(self.source), str(clone)], check=True)
        return clone

    def test_roundtrip_preserves_bytes_and_excludes_os_junk(self):
        (self.source / "openwiki/.DS_Store").write_bytes(b"junk")
        self.publish(bootstrap=True)
        clone = self.clone()
        bridge.operate("restore", self.knowledge, clone)
        self.assertEqual(bridge.wiki_files(clone / "openwiki"), bridge.wiki_files(self.source / "openwiki"))
        self.assertFalse((clone / "openwiki/.DS_Store").exists())
        self.assertTrue(bridge.operate("status", self.knowledge, clone)["working_matches"])

    def test_noop_publish_does_not_rewrite_metadata(self):
        self.publish(bootstrap=True)
        metadata = self.knowledge / "code-wiki/postgres/source.json"
        before = metadata.read_bytes()
        self.publish()
        self.assertEqual(before, metadata.read_bytes())

    def test_refuses_active_run(self):
        (self.source / "openwiki/.run.json").write_text("{}")
        with self.assertRaisesRegex(bridge.BridgeError, "Active"):
            self.publish(bootstrap=True)

    def test_refuses_manual_page_edit(self):
        (self.source / "openwiki/quickstart.md").write_text("unverified")
        with self.assertRaisesRegex(bridge.BridgeError, "outside lifecycle"):
            self.publish(bootstrap=True)

    def test_refuses_source_head_drift(self):
        (self.source / "src.c").write_text("new source")
        bridge.git(self.source, "commit", "-am", "change")
        with self.assertRaisesRegex(bridge.BridgeError, "HEAD differs"):
            self.publish(bootstrap=True)

    def test_refuses_dirty_source(self):
        (self.source / "src.c").write_text("dirty")
        with self.assertRaisesRegex(bridge.BridgeError, "Tracked source"):
            self.publish(bootstrap=True)

    def test_refuses_symlink(self):
        (self.source / "openwiki/leak.md").symlink_to(self.source / "src.c")
        with self.assertRaisesRegex(bridge.BridgeError, "symlink"):
            self.publish(bootstrap=True)

    def test_refuses_unknown_files(self):
        (self.source / "openwiki/token.txt").write_text("fixture")
        with self.assertRaisesRegex(bridge.BridgeError, "Unexpected"):
            self.publish(bootstrap=True)

    def test_refuses_unpublished_work_on_restore(self):
        self.publish(bootstrap=True)
        self.write_wiki(self.source, "unpublished")
        with self.assertRaisesRegex(bridge.BridgeError, "unpublished"):
            bridge.operate("restore", self.knowledge, self.source)
        self.assertIn(b"unpublished", (self.source / "openwiki/quickstart.md").read_bytes())

    def test_other_writer_conflict_and_clean_restore_backup(self):
        self.publish(bootstrap=True)
        clone = self.clone()
        bridge.operate("restore", self.knowledge, clone)
        self.write_wiki(clone, "second writer")
        self.publish(clone)
        with self.assertRaisesRegex(bridge.BridgeError, "Canonical snapshot changed"):
            self.publish()
        old = (self.source / "openwiki/quickstart.md").read_bytes()
        result = bridge.operate("restore", self.knowledge, self.source)
        self.assertEqual((Path(result["backup"]) / "quickstart.md").read_bytes(), old)
        self.assertIn(b"second writer", (self.source / "openwiki/quickstart.md").read_bytes())

    def test_refuses_canonical_tamper(self):
        self.publish(bootstrap=True)
        (self.knowledge / "code-wiki/postgres/openwiki/INSTRUCTIONS.md").write_text("manual change")
        with self.assertRaisesRegex(bridge.BridgeError, "Canonical snapshot modified"):
            bridge.operate("restore", self.knowledge, self.source)


if __name__ == "__main__":
    unittest.main()
