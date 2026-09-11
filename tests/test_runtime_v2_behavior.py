import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import tomllib
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'py_modules'))
sys.modules.setdefault('decky', types.SimpleNamespace(logger=logging.getLogger('test')))

from lsfg_vk import runtime_v2
from lsfg_vk.constants import JSON_FILENAME
from lsfg_vk.dll_detection import DllDetectionService


def make_config(**overrides):
    config = {
        'multiplier': 2,
        'flow_scale': 0.8,
        'performance_mode': False,
        'no_fp16': False,
        'dll': '/games/Lossless Scaling/Lossless.dll',
    }
    config.update(overrides)
    return config


class RuntimeTomlTests(unittest.TestCase):
    def test_matches_official_v2_config_fields(self):
        document = tomllib.loads(runtime_v2.runtime_toml(make_config()))
        self.assertEqual(document['version'], 2)
        self.assertTrue(document['global']['allow_fp16'])
        self.assertEqual(document['global']['log_level'], 'info')
        self.assertEqual(document['global']['dll'], '/games/Lossless Scaling/lsfg-vk.dll')

        profile = document['profile'][0]
        self.assertEqual(profile['name'], runtime_v2.RUNTIME_PROFILE)
        self.assertEqual(profile['pacing_mode'], 'vsync')
        self.assertTrue(profile['override_present_mode'])
        self.assertEqual(profile['multiplier'], 2)
        self.assertEqual(profile['flow_scale'], 0.8)
        self.assertFalse(profile['performance_mode'])

    def test_legacy_1x_fields_are_not_emitted(self):
        profile = tomllib.loads(runtime_v2.runtime_toml(make_config()))['profile'][0]
        self.assertNotIn('experimental_present_mode', profile)
        self.assertNotIn('hdr_mode', profile)

    def test_allow_fp16_is_the_inverse_of_no_fp16(self):
        document = tomllib.loads(runtime_v2.runtime_toml(make_config(no_fp16=True)))
        self.assertFalse(document['global']['allow_fp16'])
        document = tomllib.loads(runtime_v2.runtime_toml(make_config(no_fp16=False)))
        self.assertTrue(document['global']['allow_fp16'])

    def test_invalid_multiplier_or_flow_scale_is_rejected(self):
        for bad_config in (
            make_config(multiplier=0),
            make_config(multiplier=-2),
            make_config(flow_scale=0.0),
            make_config(flow_scale=1.5),
        ):
            with self.subTest(config=bad_config):
                with self.assertRaises(ValueError):
                    runtime_v2.runtime_toml(bad_config)

    def test_empty_dll_is_omitted(self):
        document = tomllib.loads(runtime_v2.runtime_toml(make_config(dll='')))
        self.assertNotIn('dll', document['global'])

    def test_dll_path_rewrites_lossless_names(self):
        self.assertEqual(runtime_v2.dll_path('/games/Lossless Scaling/Lossless.dll'),
                         '/games/Lossless Scaling/lsfg-vk.dll')
        self.assertEqual(runtime_v2.dll_path('/x/LosslessScaling.DLL'), '/x/lsfg-vk.dll')
        self.assertEqual(runtime_v2.dll_path('/x/other.dll'), '/x/other.dll')
        self.assertEqual(runtime_v2.dll_path(''), '')

    def test_manifest_declares_a_global_v2_layer(self):
        library = Path('/home/x/.local/lib/liblsfg-vk.so')
        manifest = runtime_v2.manifest(library)
        self.assertEqual(manifest['layer']['name'], runtime_v2.LAYER_NAME)
        self.assertEqual(manifest['layer']['type'], 'GLOBAL')
        self.assertEqual(manifest['layer']['library_path'], str(library))
        self.assertEqual(manifest['layer']['enable_environment'], {'ENABLE_LSFGVK': '1'})
        self.assertEqual(manifest['layer']['disable_environment'], {'DISABLE_LSFGVK': '1'})

    def test_is_v2_manifest_only_matches_the_v2_layer_name(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'layer.json'
            path.write_text(json.dumps({'layer': {'name': runtime_v2.LAYER_NAME}}))
            self.assertTrue(runtime_v2.is_v2_manifest(path))

            path.write_text(json.dumps({'layer': {'name': 'VK_LAYER_LS_frame_generation'}}))
            self.assertFalse(runtime_v2.is_v2_manifest(path))

            path.write_text('{not json')
            self.assertFalse(runtime_v2.is_v2_manifest(path))

            self.assertFalse(runtime_v2.is_v2_manifest(Path(temp) / 'missing.json'))


class EngineAwareDllDetectionTests(unittest.TestCase):
    """The DLL name follows the installed engine, they are not interchangeable."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.common = self.home / '.local/share/Steam/steamapps/common/Lossless Scaling'
        self.common.mkdir(parents=True)
        self.service = DllDetectionService(logging.getLogger('test'))
        self.service.local_share_dir = self.home / 'layers'
        self.service.local_share_dir.mkdir(parents=True)

    def install_engine(self, layer_name):
        (self.service.local_share_dir / JSON_FILENAME).write_text(
            json.dumps({'layer': {'name': layer_name}})
        )

    def detect(self, **env):
        environment = {'HOME': str(self.home)}
        environment.update(env)
        with mock.patch.dict(os.environ, environment, clear=True):
            return self.service.check_lossless_scaling_dll()

    def test_v1_install_detects_lossless_dll(self):
        (self.common / 'Lossless.dll').write_bytes(b'MZ')
        result = self.detect()
        self.assertTrue(result['detected'], result)
        self.assertEqual(Path(result['path']).name, 'Lossless.dll')

    def test_v1_install_ignores_lsfg_vk_dll(self):
        (self.common / 'lsfg-vk.dll').write_bytes(b'MZ')
        result = self.detect()
        self.assertFalse(result['detected'], result)

    def test_v2_install_detects_lsfg_vk_dll(self):
        self.install_engine(runtime_v2.LAYER_NAME)
        (self.common / 'lsfg-vk.dll').write_bytes(b'MZ')
        result = self.detect()
        self.assertTrue(result['detected'], result)
        self.assertEqual(Path(result['path']).name, 'lsfg-vk.dll')

    def test_v2_install_ignores_only_lossless_dll(self):
        self.install_engine(runtime_v2.LAYER_NAME)
        (self.common / 'Lossless.dll').write_bytes(b'MZ')
        result = self.detect()
        self.assertFalse(result['detected'], result)

    def test_v2_install_prefers_lsfg_vk_dll_when_both_exist(self):
        self.install_engine(runtime_v2.LAYER_NAME)
        (self.common / 'Lossless.dll').write_bytes(b'MZ')
        (self.common / 'lsfg-vk.dll').write_bytes(b'MZ')
        result = self.detect()
        self.assertTrue(result['detected'], result)
        self.assertEqual(Path(result['path']).name, 'lsfg-vk.dll')

    def test_missing_dll_reports_not_detected(self):
        result = self.detect()
        self.assertFalse(result['detected'], result)
        self.assertIsNone(result['path'])

    def test_env_override_must_match_the_engine(self):
        override = self.home / 'custom' / 'lsfg-vk.dll'
        override.parent.mkdir()
        override.write_bytes(b'MZ')

        # 1.x engine must not accept a v2-named override.
        result = self.detect(LSFG_DLL_PATH=str(override))
        self.assertFalse(result['detected'], result)

        # 2.0 engine accepts it.
        self.install_engine(runtime_v2.LAYER_NAME)
        result = self.detect(LSFG_DLL_PATH=str(override))
        self.assertTrue(result['detected'], result)
        self.assertEqual(result['path'], str(override))

    def test_detects_dll_in_an_extra_steam_library(self):
        extra = self.home / 'extra-library'
        extra_common = extra / 'steamapps/common/Lossless Scaling'
        extra_common.mkdir(parents=True)
        (extra_common / 'Lossless.dll').write_bytes(b'MZ')

        steam_root = self.home / '.local/share/Steam'
        (steam_root / 'steamapps').mkdir(parents=True, exist_ok=True)
        (steam_root / 'steamapps/libraryfolders.vdf').write_text(
            '"libraryfolders"\n{\n    "1"\n    {\n        "path"        "'
            + str(extra).replace('\\', '/') + '"\n    }\n}\n'
        )

        result = self.detect()
        self.assertTrue(result['detected'], result)
        self.assertEqual(Path(result['path']).parent, extra_common)


class LaunchLineInjectionTests(unittest.TestCase):
    def test_enabled_config_enables_layer_without_disable_flag(self):
        lines = runtime_v2.launch_lines(make_config(multiplier=2), Path('/tmp/decky-v2.toml'))
        self.assertIn('export ENABLE_LSFGVK=1', lines)
        self.assertIn('unset DISABLE_LSFGVK', lines)
        self.assertNotIn('export DISABLE_LSFGVK=1', lines)

    def test_off_config_injects_nothing(self):
        lines = runtime_v2.launch_lines(make_config(multiplier=1), Path('/tmp/decky-v2.toml'))
        self.assertIn('export DISABLE_LSFGVK=1', lines)
        self.assertIn('unset ENABLE_LSFGVK', lines)
        self.assertNotIn('export ENABLE_LSFGVK=1', lines)

    def test_is_enabled_only_above_1x(self):
        self.assertFalse(runtime_v2.is_enabled(make_config(multiplier=1)))
        self.assertTrue(runtime_v2.is_enabled(make_config(multiplier=2)))


class DxvkFrameRateTests(unittest.TestCase):
    """Base FPS Cap is forwarded as-is; the generator must not clamp 72 to 60."""

    def setUp(self):
        from lsfg_vk.config_schema_generated import get_script_generation_logic
        self.generate = get_script_generation_logic()

    def frame_rate_lines(self, value):
        return [
            line for line in self.generate(make_config(dxvk_frame_rate=value))
            if 'DXVK_FRAME_RATE' in line
        ]

    def test_cap_of_72_is_emitted_without_clamping(self):
        self.assertEqual(self.frame_rate_lines(72), ['export DXVK_FRAME_RATE=72'])

    def test_cap_of_0_clears_inherited_limits(self):
        import os
        import subprocess

        lines = self.generate(make_config(dxvk_frame_rate=0))
        env = os.environ.copy()
        env["DXVK_FRAME_RATE"] = "99"
        env["VKD3D_FRAME_RATE"] = "88"

        result = subprocess.run(
            ["/bin/sh", "-c", "\n".join(lines) + '\nprintf "${DXVK_FRAME_RATE-unset} ${VKD3D_FRAME_RATE-unset}"'],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(result.stdout, "unset unset")


if __name__ == '__main__':
    unittest.main()
