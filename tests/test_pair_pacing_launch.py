import json
import logging
import os
from pathlib import Path
import shlex
import subprocess
import sys
import types
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
decky = sys.modules.setdefault("decky", types.ModuleType("decky"))
if not hasattr(decky, "logger"):
    decky.logger = logging.getLogger(__name__)

from lsfg_vk import runtime_v2
from lsfg_vk.config_schema_generated import (
    get_script_generation_logic,
    get_script_parsing_logic,
)

CHILD_VARIABLES = (
    "LSFGVK_PACE_FPS", "DXVK_FRAME_RATE", "VKD3D_FRAME_RATE",
    "TU_AUTOTUNE_ALGO", "LSFGVK_TIMING_TRIGGER",
)


class TestPairPacingLaunch(unittest.TestCase):
    def launch_lines(self, multiplier, cap):
        config = {"multiplier": multiplier, "dxvk_frame_rate": cap}
        common = get_script_generation_logic()(config)
        return [*common, *runtime_v2.launch_lines(config, Path("/tmp/decky-v2.toml"))]

    def child_env(self, multiplier, cap):
        lines = self.launch_lines(multiplier, cap)
        dump_code = (
            "import json, os; "
            f"keys = {CHILD_VARIABLES!r}; "
            "print(json.dumps({k: os.environ[k] for k in keys if k in os.environ}))"
        )
        command = "exec " + shlex.join([sys.executable, "-c", dump_code])
        env = os.environ.copy()
        env.update(LSFGVK_PACE_FPS="99", LSFGVK_TIMING_TRIGGER="trigger",
                   DXVK_FRAME_RATE="99", VKD3D_FRAME_RATE="99",
                   TU_AUTOTUNE_ALGO="inherited")
        result = subprocess.run(
            ["bash", "-c", "\n".join([*lines, command])], env=env,
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

    def test_default_disables_pair_pacing_and_preserves_driver_caps(self):
        for cap in (30, 72):
            with self.subTest(multiplier=2, cap=cap):
                child = self.child_env(2, cap)
                self.assertNotIn("LSFGVK_PACE_FPS", child)
                self.assertEqual(child.get("DXVK_FRAME_RATE"), str(cap))
                self.assertEqual(child.get("VKD3D_FRAME_RATE"), str(cap))
                self.assertEqual(child.get("TU_AUTOTUNE_ALGO"), "prefer_gmem")

    def test_parser_preserves_original_pair_cap(self):
        for cap in (30, 72):
            with self.subTest(multiplier=2, cap=cap):
                parsed = get_script_parsing_logic()(self.launch_lines(2, cap))
                self.assertEqual(parsed["dxvk_frame_rate"], cap)

    def test_non_pair_cases_clear_inherited_pacing(self):
        for multiplier, cap in ((1, 30), (3, 30), (2, 0)):
            with self.subTest(multiplier=multiplier, cap=cap):
                self.assertNotIn("LSFGVK_PACE_FPS", self.child_env(multiplier, cap))

    def test_non_pair_cases_preserve_ordinary_caps(self):
        for multiplier, cap in ((1, 30), (3, 30), (2, 0)):
            with self.subTest(multiplier=multiplier, cap=cap):
                child = self.child_env(multiplier, cap)
                for key in ("DXVK_FRAME_RATE", "VKD3D_FRAME_RATE"):
                    if cap:
                        self.assertEqual(child.get(key), str(cap))
                    else:
                        self.assertNotIn(key, child)

    def test_all_cases_clear_inherited_timing_trigger(self):
        for multiplier, cap in ((2, 30), (2, 72), (1, 30), (3, 30), (2, 0)):
            with self.subTest(multiplier=multiplier, cap=cap):
                self.assertNotIn("LSFGVK_TIMING_TRIGGER", self.child_env(multiplier, cap))


if __name__ == "__main__":
    unittest.main()
