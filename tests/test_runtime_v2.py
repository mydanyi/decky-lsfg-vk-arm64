import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'py_modules'))
# Decky itself is external; all config parsing, file writes and generated shell run for real.
sys.modules.setdefault('decky', types.SimpleNamespace(logger=logging.getLogger('test')))
from lsfg_vk import runtime_v2
from lsfg_vk.configuration import ConfigurationService
from lsfg_vk.config_schema import ConfigurationManager
from lsfg_vk.constants import JSON_FILENAME


class RuntimeV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = ConfigurationService(logging.getLogger('test'))
        for attr, value in {
            'user_home': self.root,
            'local_share_dir': self.root / 'layers',
            'config_dir': self.root / 'config',
            'config_file_path': self.root / 'config/conf.toml',
            'lsfg_script_path': self.root / 'lsfg-arm64',
        }.items():
            setattr(self.service, attr, value)
        self.service.config_dir.mkdir()
        self.service.local_share_dir.mkdir()
        self.manifest = self.service.local_share_dir / JSON_FILENAME
        self.manifest.write_text(json.dumps({'layer': {'name': runtime_v2.LAYER_NAME}}))
        config = ConfigurationManager.get_defaults()
        config.update(multiplier=2, flow_scale=0.7, performance_mode=True, enable_wsi=False)
        self.data = {'current_profile': 'decky-lsfg-vk', 'profiles': {'decky-lsfg-vk': config},
                     'global_config': {'dll': str(self.root / "Owner's games/Lossless.dll"), 'no_fp16': True}}

    def generate(self):
        self.service._save_profile_data(self.data)
        result = self.service.update_lsfg_script_from_profile_data(self.data)
        self.assertTrue(result['success'], result)
        env = dict(os.environ, LSFGVK_ENV='1', LSFGVK_MULTIPLIER='9', LSFGVK_PROFILE='stale')
        return json.loads(subprocess.check_output(['bash', str(self.service.lsfg_script_path),
            sys.executable, '-c', 'import os,json;print(json.dumps(dict(os.environ)))'], env=env))

    def test_v2_launch_reads_current_profile_and_globals(self):
        env = self.generate()
        self.assertIn('LSFGVK_CONFIG', env)
        runtime = tomllib.loads(Path(env['LSFGVK_CONFIG']).read_text())
        self.assertEqual(runtime['global']['dll'], str(self.root / "Owner's games/lsfg-vk.dll"))
        self.assertEqual(runtime['global']['allow_fp16'], False)
        p = runtime['profile'][0]
        self.assertEqual((p['multiplier'], p['flow_scale'], p['performance_mode']), (2, 0.7, True))
        self.assertEqual(p['pacing_mode'], 'vsync')
        self.assertTrue(p['override_present_mode'])
        self.assertEqual(env['ENABLE_LSFGVK_ARM64'], '1')
        self.assertNotIn('ENABLE_LSFGVK', env)
        self.assertNotIn('LSFG_PROCESS', env)
        self.assertIn('VK_LAYER_LS_frame_generation', env['VK_LOADER_LAYERS_DISABLE'])
        self.assertIn('VK_LAYER_LSFGVK_frame_generation', env['VK_LOADER_LAYERS_DISABLE'])
        self.assertEqual(env['DISABLE_LSFG'], '1')
        self.assertNotIn('DISABLE_LSFGVK', env)
        self.assertNotIn('LSFGVK_ENV', env)
        self.assertNotIn('LSFGVK_MULTIPLIER', env)

    def test_recovery_survives_profile_save_and_runtime_generation(self):
        self.data['profiles']['decky-lsfg-vk'].update(adaptive_recovery=True, dxvk_frame_rate=30)
        env = self.generate()
        runtime = tomllib.loads(Path(env['LSFGVK_CONFIG']).read_text())['profile'][0]
        self.assertIs(runtime['adaptive_recovery'], True)
        self.assertEqual(runtime['recovery_base_fps'], 30)
        self.assertEqual(runtime['multiplier'], 2)
        self.assertEqual(env['DXVK_FRAME_RATE'], '30')
        self.assertEqual(env['VKD3D_FRAME_RATE'], '30')

    def test_off_disables_layer_and_sets_runtime_bypass(self):
        self.data['profiles']['decky-lsfg-vk']['multiplier'] = 1
        env = self.generate()
        self.assertEqual(env.get('DISABLE_LSFGVK'), '1')
        self.assertNotIn('ENABLE_LSFGVK_ARM64', env)
        self.assertNotIn('LSFG_PROCESS', env)
        self.assertEqual(tomllib.loads(Path(env['LSFGVK_CONFIG']).read_text())['profile'][0]['multiplier'], 1)

    def test_profile_change_uses_stable_runtime_name(self):
        first = self.generate()
        self.assertIn('LSFGVK_CONFIG', first)
        first_name = tomllib.loads(Path(first['LSFGVK_CONFIG']).read_text())['profile'][0]['name']
        self.data['profiles']['other'] = dict(self.data['profiles']['decky-lsfg-vk'], multiplier=3)
        self.data['current_profile'] = 'other'
        second = self.generate()
        profile = tomllib.loads(Path(second['LSFGVK_CONFIG']).read_text())['profile'][0]
        self.assertEqual(profile['name'], first_name)
        self.assertEqual(profile['multiplier'], 3)

    def test_capabilities_returned_separately_from_persisted_settings(self):
        self.generate()
        result = self.service.get_config()
        self.assertTrue(result.get('runtime_v2'))
        self.assertNotIn('runtime_v2', result['config'])

    def _fail_runtime_writes(self):
        original_write = self.service._write_file

        def failing_write(path, content, mode=0o644):
            if Path(path).name == runtime_v2.RUNTIME_FILENAME:
                raise OSError('runtime file is not writable')
            return original_write(path, content, mode)

        self.service._write_file = failing_write

    def test_runtime_write_failure_is_reported(self):
        self.service._save_profile_data(self.data)
        self._fail_runtime_writes()
        result = self.service.update_lsfg_script_from_profile_data(self.data)
        self.assertFalse(result['success'])
        self.assertIn('runtime file is not writable', result['error'])

    def test_profile_switch_surfaces_runtime_write_failure(self):
        self.data['profiles']['other'] = dict(self.data['profiles']['decky-lsfg-vk'])
        self.service._save_profile_data(self.data)
        self._fail_runtime_writes()
        result = self.service.set_current_profile('other')
        self.assertFalse(result['success'])
        self.assertIn('runtime file is not writable', result['error'])

    def test_legacy_manifest_never_enables_original_engine(self):
        """A legacy owned manifest must fail, never launch the original engine."""
        self.manifest.write_text(json.dumps({'layer': {'name': 'VK_LAYER_LS_frame_generation'}}))
        self.service._save_profile_data(self.data)
        result = self.service.update_lsfg_script_from_profile_data(self.data)
        self.assertFalse(result['success'])
        self.assertIn('ARM64 v2 layer manifest', result.get('error', ''))
        self.assertFalse(self.service.lsfg_script_path.exists())



if __name__ == '__main__':
    unittest.main()
