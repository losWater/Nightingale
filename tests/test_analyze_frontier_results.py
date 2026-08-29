from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "夜莺B" / "scripts" / "analyze_frontier_results.py"
TEST_TMP = ROOT / "tests" / ".tmp"
GOOD_METRIC = """分数：1；
一字全码［选重率：0.1%；组合当量：1.2；1500 选重：0；1500 选重平方：0；3500 选重：2；3500 选重平方：2；6000 选重：3；］
一字简码［选重率：0.0%；组合当量：1.1；1500 选重：0；1500 选重平方：0；1500 三键：900；3500 选重：2；3500 选重平方：2；3500 三键：2000；］
字词交叉［硬碰撞：0；软碰撞当量：1.5；］
"""


def load_module():
    spec = importlib.util.spec_from_file_location("nightingale_frontier", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载：{SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FrontierResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def setUp(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        self.base = TEST_TMP / f"frontier-{uuid.uuid4().hex}"
        self.base.mkdir()

    def tearDown(self):
        shutil.rmtree(self.base)

    def make_suite(self, profiles=("alpha",), threads=1, metric=GOOD_METRIC):
        (self.base / "manifest.json").write_text(json.dumps({
            "profiles": list(profiles), "threads": threads
        }), encoding="utf-8")
        for profile in profiles:
            output = self.base / profile / "output-test"
            for thread in range(threads):
                directory = output / str(thread)
                directory.mkdir(parents=True)
                (directory / "metric.txt").write_text(metric, encoding="utf-8")

    def test_valid_suite_uses_manifest_profiles_and_threads(self):
        self.make_suite(profiles=("custom",), threads=2)
        rows = self.mod.collect(self.base)
        self.assertEqual([(x["profile"], x["thread"]) for x in rows],
                         [("custom", 0), ("custom", 1)])

    def test_metric_format_change_fails_with_path_and_section(self):
        self.make_suite(metric=GOOD_METRIC.replace("一字简码", "简码新版"))
        metric = next(self.base.glob("alpha/output-*/*/metric.txt"))
        with self.assertRaisesRegex(ValueError, rf"一字简码.*{metric.name}"):
            self.mod.collect(self.base)

    def test_missing_thread_is_rejected(self):
        self.make_suite(threads=2)
        shutil.rmtree(self.base / "alpha" / "output-test" / "1")
        with self.assertRaisesRegex(ValueError, r"缺失=\[1\]"):
            self.mod.collect(self.base)

    def test_missing_profile_directory_is_rejected(self):
        self.make_suite()
        shutil.rmtree(self.base / "alpha")
        with self.assertRaisesRegex(FileNotFoundError, "缺少profile目录"):
            self.mod.collect(self.base)

    def test_multiple_output_directories_are_rejected(self):
        self.make_suite()
        (self.base / "alpha" / "output-extra").mkdir()
        with self.assertRaisesRegex(ValueError, "恰有一个output目录"):
            self.mod.collect(self.base)

    def test_missing_manifest_is_rejected(self):
        with self.assertRaisesRegex(FileNotFoundError, "缺少实验manifest"):
            self.mod.collect(self.base)

    def test_no_valid_candidate_is_rejected_before_pareto(self):
        rows = [{"valid": 0}]
        with self.assertRaisesRegex(ValueError, "没有满足硬门槛"):
            self.mod.mark_frontier(rows, self.base)


if __name__ == "__main__":
    unittest.main()
