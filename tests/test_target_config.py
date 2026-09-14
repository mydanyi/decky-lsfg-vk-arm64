"""Target mode must survive profile storage and control the actual launch contract."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'py_modules'))
from lsfg_vk.config_schema import ConfigurationManager
from lsfg_vk import runtime_v2


class TargetConfigTests(unittest.TestCase):
    def test_old_profile_defaults_to_fixed_and_runtime_target_is_disabled(self):
        config = ConfigurationManager.parse_toml_content('version = 1\n[[game]]\nexe = "old"\nmultiplier = 3\n')
        self.assertEqual(config.get('generation_mode'), 'fixed')
        self.assertEqual(config.get('target_fps'), 60)
        self.assertEqual(config.get('target_max_multiplier'), 4)
        profile = tomllib.loads(runtime_v2.runtime_toml({'multiplier': 3, 'target_fps': 120}))['profile'][0]
        self.assertEqual(profile.get('target_fps'), 0)
        self.assertEqual(profile['multiplier'], 3)

    def test_target_settings_round_trip_without_replacing_fixed_multiplier_or_cap(self):
        config = dict(ConfigurationManager.get_defaults(), generation_mode='target',
                      target_fps=120, target_max_multiplier=3, multiplier=1, dxvk_frame_rate=40)
        saved = ConfigurationManager.generate_toml_content(config)
        loaded = ConfigurationManager.parse_toml_content(saved)
        for key, value in {'generation_mode': 'target', 'target_fps': 120,
                           'target_max_multiplier': 3, 'multiplier': 1, 'dxvk_frame_rate': 40}.items():
            self.assertEqual(loaded.get(key), value, key)
        profile = tomllib.loads(runtime_v2.runtime_toml(loaded))['profile'][0]
        self.assertEqual((profile.get('target_fps'), profile['multiplier'], profile['recovery_base_fps']),
                         (120, 3, 40))

    def test_invalid_target_settings_are_rejected_before_coercion(self):
        for key, values in {'generation_mode': ['auto', '', None],
                            'target_fps': [29, 241, 60.5, True, None],
                            'target_max_multiplier': [1, 5, 2.5, False, None]}.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    config = {'generation_mode': 'target', key: value}
                    with self.assertRaises(ValueError):
                        ConfigurationManager.validate_config(config)
                    with self.assertRaises(ValueError):
                        runtime_v2.runtime_toml(config)

    def test_target_boundaries_are_valid(self):
        for fps, maximum in [(30, 2), (240, 4)]:
            config = ConfigurationManager.validate_config({'generation_mode': 'target',
                'target_fps': fps, 'target_max_multiplier': maximum})
            profile = tomllib.loads(runtime_v2.runtime_toml(config))['profile'][0]
            self.assertEqual((profile.get('target_fps'), profile['multiplier']), (fps, maximum))

    def test_target_launch_enables_layer_and_uses_effective_gpu_multiplier(self):
        for fixed, maximum, want_gmem in [(1, 2, True), (2, 4, False)]:
            with self.subTest(fixed=fixed, maximum=maximum):
                config = dict(generation_mode='target', target_fps=120,
                              target_max_multiplier=maximum, multiplier=fixed, dxvk_frame_rate=40)
                self.assertTrue(runtime_v2.is_enabled(config))
                script = '\n'.join(runtime_v2.launch_lines(config, Path('/tmp/target.toml')))
                script += '\nexec "$@"\n'
                env = dict(os.environ)
                env.pop('TU_AUTOTUNE_ALGO', None)
                child = json.loads(subprocess.check_output(['bash', '-c', script, 'target',
                    sys.executable, '-c', 'import os,json;print(json.dumps(dict(os.environ)))'], env=env))
                self.assertEqual(child.get('ENABLE_LSFGVK_ARM64'), '1')
                self.assertNotIn('DISABLE_LSFGVK', child)
                self.assertEqual(child.get('TU_AUTOTUNE_ALGO'), 'prefer_gmem' if want_gmem else None)


if __name__ == '__main__':
    unittest.main()
