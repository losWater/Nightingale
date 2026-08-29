from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "repos" / "libchai" / "target" / "release" / "chai.exe"
AUDITOR = ROOT / "夜莺B" / "scripts" / "audit_cross_collision.py"
CONFIG = ROOT / "夜莺B" / "work" / "analysis_config_compat.yaml"
ELEMENTS = ROOT / "夜莺B" / "work" / "analysis_elements.yaml"
DISTRIBUTION = ROOT / "tools" / "chai-win" / "assets" / "distribution.txt"
EQUIVALENCE = ROOT / "tools" / "chai-win" / "assets" / "equivalence.txt"
TEST_TMP = ROOT / "tests" / ".tmp"


def load_auditor():
    spec = importlib.util.spec_from_file_location("nightingale_cross_auditor", AUDITOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载独立复算器: {AUDITOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(ENGINE.exists(), "需要预先编译当前 libchai release 引擎")
class CrossCollisionEngineParityTests(unittest.TestCase):
    def test_phonetic_shape_transition_equivalence_is_accepted_and_reported(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        base = TEST_TMP / f"phonetic-shape-transition-{uuid.uuid4().hex}"
        base.mkdir()
        try:
            config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
            tier = config["optimization"]["objective"]["characters_short"]["tiers"][0]
            tier["phonetic_shape_transition_equivalence"] = 1.0
            fixture = base / "config.yaml"
            fixture.write_text(
                yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000),
                encoding="utf-8",
            )
            result = subprocess.run(
                [str(ENGINE), "encode", str(fixture), "-e", str(ELEMENTS),
                 "-k", str(DISTRIBUTION), "-p", str(EQUIVALENCE)],
                cwd=base,
                text=True,
                encoding="utf-8",
                capture_output=True,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            match = re.search(r"音型过渡当量：([\d.]+)", result.stdout)
            self.assertIsNotNone(match, result.stdout)
            self.assertGreater(float(match.group(1)), 0.0)
        finally:
            shutil.rmtree(base)

    def test_weighted_tier_fingering_is_accepted_and_reported(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        base = TEST_TMP / f"weighted-fingering-{uuid.uuid4().hex}"
        base.mkdir()
        try:
            config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
            tier = config["optimization"]["objective"]["characters_short"]["tiers"][0]
            tier["weighted_fingering"] = [1.0, None, None, None, None, None, None, None]
            fixture = base / "config.yaml"
            fixture.write_text(
                yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000),
                encoding="utf-8",
            )
            result = subprocess.run(
                [str(ENGINE), "encode", str(fixture), "-e", str(ELEMENTS),
                 "-k", str(DISTRIBUTION), "-p", str(EQUIVALENCE)],
                cwd=base,
                text=True,
                encoding="utf-8",
                capture_output=True,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            match = re.search(r"加权同手：([\d.]+)", result.stdout)
            self.assertIsNotNone(match, result.stdout)
            self.assertGreaterEqual(float(match.group(1)), 0.0)
        finally:
            shutil.rmtree(base)

    def test_current_engine_matches_independent_auditor(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        base = TEST_TMP / f"engine-parity-{uuid.uuid4().hex}"
        base.mkdir()
        try:
            result = subprocess.run(
                [
                    str(ENGINE),
                    "encode",
                    str(CONFIG),
                    "-e",
                    str(ELEMENTS),
                    "-k",
                    str(DISTRIBUTION),
                    "-p",
                    str(EQUIVALENCE),
                ],
                cwd=base,
                text=True,
                encoding="utf-8",
                capture_output=True,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            match = re.search(r"字词交叉［硬碰撞：(\d+)；软碰撞当量：([\d.]+)；］", result.stdout)
            self.assertIsNotNone(match, result.stdout)
            engine_hard = int(match.group(1))
            engine_soft = float(match.group(2))

            outputs = list(base.glob("output-*/code.txt"))
            self.assertEqual(len(outputs), 1, outputs)
            auditor = load_auditor()
            config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
            elements = yaml.safe_load(ELEMENTS.read_text(encoding="utf-8"))
            audited = auditor.audit(config, elements, auditor.load_code(outputs[0]))

            self.assertEqual(audited["hard"], engine_hard)
            self.assertAlmostEqual(audited["soft"], engine_soft, places=9)
        finally:
            shutil.rmtree(base)


if __name__ == "__main__":
    unittest.main()
