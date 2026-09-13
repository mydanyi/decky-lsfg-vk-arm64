import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'py_modules'))
sys.path.insert(0, str(ROOT))
from lsfg_vk.runtime_v2 import runtime_toml, launch_lines
from shared_config import get_defaults


class RecoveryConfigTests(unittest.TestCase):
    def test_missing_setting_defaults_to_recovery(self):
        self.assertIs(get_defaults()['adaptive_recovery'], True)
        profile = tomllib.loads(runtime_toml({'multiplier': 2}))['profile'][0]
        self.assertIs(profile['adaptive_recovery'], True)
        saved = tomllib.loads(runtime_toml({'adaptive_recovery': False}))['profile'][0]
        self.assertIs(saved['adaptive_recovery'], False)

    def test_recovery_carries_manual_cap_without_changing_multiplier(self):
        config = {'adaptive_recovery': True, 'multiplier': 2, 'dxvk_frame_rate': 30}
        profile = tomllib.loads(runtime_toml(config))['profile'][0]
        self.assertEqual(profile['recovery_base_fps'], 30)
        self.assertIs(profile['adaptive_recovery'], True)
        self.assertEqual(profile['multiplier'], 2)
        self.assertNotIn('unset DXVK_FRAME_RATE', '\n'.join(launch_lines(config, Path('/tmp/config'))))

    def test_uncapped_mode_is_explicit(self):
        profile = tomllib.loads(runtime_toml({'adaptive_recovery': True}))['profile'][0]
        self.assertEqual(profile['recovery_base_fps'], 0)


if __name__ == '__main__':
    unittest.main()
