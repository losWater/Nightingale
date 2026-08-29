from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "夜莺B" / "scripts" / "run_final_protection.py"
TEST_TMP = ROOT / "tests" / ".tmp"


def load_module():
    spec = importlib.util.spec_from_file_location("nightingale_safe_runner", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载：{SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FinalProtectionRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def setUp(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        self.base = TEST_TMP / f"safe-runner-{uuid.uuid4().hex}"
        self.source = self.base / "source"
        self.source.mkdir(parents=True)
        config = {"optimization": {"metaheuristic": {
            "parameters": {"steps": 1}, "update_interval": 1
        }}}
        (self.source / "input_config.yaml").write_text(
            yaml.safe_dump(config), encoding="utf-8"
        )
        self.assets = []
        for name in ("elements.yaml", "chai.exe", "distribution.txt", "equivalence.txt"):
            path = self.base / name
            path.write_text(name, encoding="utf-8")
            self.assets.append(path)

    def tearDown(self):
        shutil.rmtree(self.base)

    def prepare(self, destination=None):
        destination = destination or self.base / "run"
        return self.mod.prepare_run(
            self.source, destination, steps=400, threads=8,
            elements=self.assets[0], executable=self.assets[1],
            distribution=self.assets[2], equivalence=self.assets[3],
        )

    def test_source_config_is_not_modified_and_run_config_has_parameters(self):
        before = self.mod.sha256(self.source / "input_config.yaml")
        _, manifest = self.prepare()
        after = self.mod.sha256(self.source / "input_config.yaml")
        self.assertEqual(before, after)
        run_config = yaml.safe_load((self.base / "run" / "input_config.yaml").read_text(encoding="utf-8"))
        self.assertEqual(run_config["optimization"]["metaheuristic"]["parameters"]["steps"], 400)
        self.assertEqual(manifest["parameters"]["threads"], 8)

    def test_manifest_hashes_all_inputs_and_records_command(self):
        command, manifest = self.prepare()
        persisted = json.loads((self.base / "run" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(persisted, manifest)
        self.assertEqual(set(manifest["files"]), {
            "source_config", "run_config", "elements", "executable", "distribution", "equivalence"
        })
        self.assertEqual(command, manifest["command"])
        self.assertTrue(all(len(item["sha256"]) == 64 for item in manifest["files"].values()))

    def test_existing_output_directory_is_rejected(self):
        destination = self.base / "existing"
        destination.mkdir()
        marker = destination / "stdout.log"
        marker.write_text("old evidence", encoding="utf-8")
        with self.assertRaisesRegex(FileExistsError, "拒绝覆盖"):
            self.prepare(destination)
        self.assertEqual(marker.read_text(encoding="utf-8"), "old evidence")

    def test_invalid_parameters_fail_before_creating_output(self):
        destination = self.base / "bad"
        with self.assertRaisesRegex(ValueError, "正整数"):
            self.mod.prepare_run(
                self.source, destination, steps=0, threads=8,
                elements=self.assets[0], executable=self.assets[1],
                distribution=self.assets[2], equivalence=self.assets[3],
            )
        self.assertFalse(destination.exists())

    def test_missing_asset_fails_before_creating_output(self):
        destination = self.base / "missing"
        with self.assertRaisesRegex(FileNotFoundError, "元素资产不存在"):
            self.mod.prepare_run(
                self.source, destination, steps=1, threads=1,
                elements=self.base / "absent.yaml", executable=self.assets[1],
                distribution=self.assets[2], equivalence=self.assets[3],
            )
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
