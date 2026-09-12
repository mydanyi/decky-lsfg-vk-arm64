import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'py_modules'))
sys.modules.setdefault('decky', types.SimpleNamespace(logger=logging.getLogger('test')))

from lsfg_vk import runtime_v2
from lsfg_vk.config_schema import ConfigurationManager
from lsfg_vk.constants import CONFIG_FILENAME, JSON_FILENAME, LIB_FILENAME, VULKAN_LAYER_DIR
from lsfg_vk.installation import InstallationService


class InstallationV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

        self.service = InstallationService(logging.getLogger('test'))
        self.service.user_home = self.home
        self.service.local_lib_dir = self.home / '.local/lib'
        self.service.local_share_dir = self.home / VULKAN_LAYER_DIR
        self.service.config_dir = self.home / '.config/lsfg-vk-arm64'
        self.service.config_file_path = self.service.config_dir / CONFIG_FILENAME
        self.service.lsfg_launch_script_path = self.home / 'lsfg-arm64'
        self.service.lsfg_script_path = self.home / 'lsfg-arm64'
        self.service.lib_file = self.service.local_lib_dir / LIB_FILENAME
        self.service.json_file = self.service.local_share_dir / JSON_FILENAME

        self.service.local_lib_dir.mkdir(parents=True)
        self.service.local_share_dir.mkdir(parents=True)
        self.service.config_dir.mkdir(parents=True)

    def create_existing_config(self):
        profile_data = {
            'current_profile': 'my-game',
            'profiles': {
                'my-game': dict(ConfigurationManager.get_defaults(), multiplier=3, flow_scale=0.6),
                'decky-lsfg-vk-arm64': ConfigurationManager.get_defaults(),
            },
            'global_config': {'dll': '/custom/Lossless.dll', 'no_fp16': True},
        }
        self.service.config_file_path.write_text(
            ConfigurationManager.generate_toml_content_multi_profile(profile_data)
        )
        return profile_data

    def test_reinstall_preserves_existing_profiles_and_values(self):
        self.create_existing_config()
        with mock.patch.dict(os.environ, {'HOME': str(self.home)}, clear=True):
            self.service._create_config_file()

        parsed = ConfigurationManager.parse_toml_content_multi_profile(
            self.service.config_file_path.read_text()
        )
        self.assertEqual(parsed['current_profile'], 'my-game')
        self.assertIn('my-game', parsed['profiles'])
        self.assertEqual(parsed['profiles']['my-game']['multiplier'], 3)
        self.assertEqual(parsed['profiles']['my-game']['flow_scale'], 0.6)
        self.assertEqual(parsed['global_config']['dll'], '/custom/Lossless.dll')
        self.assertTrue(parsed['global_config']['no_fp16'])

    def test_v2_install_writes_native_binary_and_layer_manifest(self):
        binary = self.home / 'bin/liblsfg-vk-v2-arm64.so'
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b'ELF-ARM64-V2')

        self.service._install_v2_files(binary)

        self.assertEqual(self.service.lib_file.read_bytes(), b'ELF-ARM64-V2')
        manifest = json.loads(self.service.json_file.read_text())
        self.assertEqual(manifest['layer']['name'], runtime_v2.LAYER_NAME)
        self.assertEqual(manifest['layer']['library_path'], str(self.service.lib_file))
        self.assertFalse(self.service.lib_file.with_suffix('.so.new').exists())


if __name__ == '__main__':
    unittest.main()
