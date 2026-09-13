import asyncio
import json
import logging
import os
import shlex
import subprocess
import sys
import tempfile
import tomllib
import types
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'py_modules'))

sys.modules.setdefault('decky', types.SimpleNamespace(
    logger=logging.getLogger('test'),
    DECKY_USER_HOME='',
    DECKY_HOME='',
    migrate_logs=lambda *a, **k: None,
    migrate_settings=lambda *a, **k: None,
    migrate_runtime=lambda *a, **k: None,
))

import lsfg_vk.installation as installation_module
from lsfg_vk import runtime_v2
from lsfg_vk.config_schema import ConfigurationManager

FIXTURE_BINARY = b'\x7fELF' + b'arm64-coexistence-payload'
SENTINEL = b'UPSTREAM-SENTINEL'
UPSTREAM_LAYER = 'VK_LAYER_LSFGVK_frame_generation'
OWN_LAYER = 'VK_LAYER_LSFGVK_ARM64_frame_generation'
ENV_KEYS = ['ENABLE_LSFGVK_ARM64', 'ENABLE_LSFGVK', 'DISABLE_LSFGVK',
            'DISABLE_LSFG', 'LSFGVK_CONFIG', 'LSFGVK_PROFILE', 'LSFG_PROCESS',
            'VK_LOADER_LAYERS_DISABLE']


class CoexistenceTestBase(unittest.TestCase):
    """Temp user home with seeded upstream install + bundled v2 ARM64 payload."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

        self.plugin_root = self.home / 'plugin'
        bundled = self.plugin_root / 'bin'
        bundled.mkdir(parents=True)
        (bundled / runtime_v2.ARM_BINARY).write_bytes(FIXTURE_BINARY)

        self.decky = sys.modules['decky']
        previous = getattr(self.decky, 'DECKY_USER_HOME', '')
        self.decky.DECKY_USER_HOME = str(self.home)
        self.addCleanup(lambda: setattr(self.decky, 'DECKY_USER_HOME', previous))
        env_patch = mock.patch.dict(os.environ, {'HOME': str(self.home)})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        home_patch = mock.patch('pathlib.Path.home', return_value=self.home)
        home_patch.start()
        self.addCleanup(home_patch.stop)

        file_patch = mock.patch.object(
            installation_module, '__file__',
            str(self.plugin_root / 'py_modules' / 'lsfg_vk' / 'installation.py'))
        file_patch.start()
        self.addCleanup(file_patch.stop)

    def seed_upstream(self):
        for path in self.upstream_paths():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(SENTINEL)

    def upstream_paths(self):
        return [self.upstream_lib(), self.upstream_json(), self.upstream_conf(),
                self.upstream_runtime(), self.upstream_launcher(),
                self.upstream_json().with_name('VkLayer_LS_frame_generation.json')]

    def upstream_lib(self):
        return self.home / '.local/lib/liblsfg-vk.so'

    def upstream_json(self):
        return (self.home / '.local/share/vulkan/implicit_layer.d/'
                'VkLayer_LSFGVK_frame_generation.json')

    def upstream_conf(self):
        return self.home / '.config/lsfg-vk/conf.toml'

    def upstream_runtime(self):
        return self.home / '.config/lsfg-vk/decky-v2.toml'

    def upstream_launcher(self):
        return self.home / 'lsfg'

    def lib_path(self):
        return self.home / '.local/lib/liblsfg-vk-arm64.so'

    def json_path(self):
        return (self.home / '.local/share/vulkan/implicit_layer.d/'
                'VkLayer_LSFGVK_ARM64_frame_generation.json')

    def conf_path(self):
        return self.home / '.config/lsfg-vk-arm64/conf.toml'

    def runtime_path(self):
        return self.home / '.config/lsfg-vk-arm64/decky-v2.toml'

    def launcher_path(self):
        return self.home / 'lsfg-arm64'

    def owned_paths(self):
        return [self.lib_path(), self.json_path(), self.conf_path(),
                self.runtime_path(), self.launcher_path()]

    def make_plugin(self):
        from lsfg_vk.plugin import Plugin
        return Plugin()

    def run_main(self, plugin):
        with mock.patch('platform.machine', return_value='aarch64'):
            asyncio.run(plugin._main())

    def child_env(self):
        script = ('import os,json;print(json.dumps('
                  '{k:os.getenv(k) for k in %r}))' % (ENV_KEYS,))
        proc = subprocess.run(
            ['bash', str(self.launcher_path()), sys.executable, '-c', script],
            env=dict(os.environ, ENABLE_LSFGVK='1', LSFG_PROCESS='upstream',
                     VK_LOADER_LAYERS_DISABLE='VK_LAYER_keep_disabled'),
            capture_output=True, text=True, check=True)
        return json.loads(proc.stdout)

    def enable_frame_generation(self):
        # A new install defaults to 1x (off). Enable through the actual config API.
        result = asyncio.run(self.make_plugin().update_lsfg_config({'multiplier': 2}))
        self.assertTrue(result['success'], result)


class FreshInstallCoexistenceTests(CoexistenceTestBase):
    def test_fresh_install_leaves_upstream_intact_and_enables_own_layer(self):
        self.seed_upstream()

        self.run_main(self.make_plugin())

        for path in self.upstream_paths():
            self.assertEqual(path.read_bytes(), SENTINEL, path)
        for path in self.owned_paths():
            self.assertTrue(path.exists(), f'{path} was not installed')
        self.assertEqual(self.lib_path().read_bytes(), FIXTURE_BINARY)

        manifest = json.loads(self.json_path().read_text())
        self.assertEqual(manifest['layer']['name'], OWN_LAYER)
        self.assertEqual(manifest['layer']['library_path'], str(self.lib_path()))
        self.assertEqual(manifest['layer']['enable_environment'],
                         {'ENABLE_LSFGVK_ARM64': '1'})
        self.assertNotEqual(manifest['layer']['name'], UPSTREAM_LAYER)

        self.assertIsNone(self.child_env()['ENABLE_LSFGVK_ARM64'])
        self.enable_frame_generation()
        env = self.child_env()
        self.assertEqual(env['ENABLE_LSFGVK_ARM64'], '1')
        self.assertIsNone(env['ENABLE_LSFGVK'], 'launcher must not enable upstream')
        self.assertIsNone(env['DISABLE_LSFGVK'])
        self.assertEqual(env['LSFGVK_CONFIG'], str(self.runtime_path()))
        self.assertIsNone(env['LSFG_PROCESS'])
        self.assertEqual(set(env['VK_LOADER_LAYERS_DISABLE'].split(',')), {
            'VK_LAYER_keep_disabled', 'VK_LAYER_LS_frame_generation', UPSTREAM_LAYER})


class ConfigurationUpdateCoexistenceTests(CoexistenceTestBase):
    def test_configuration_update_rewrites_only_owned_state(self):
        self.seed_upstream()
        self.run_main(self.make_plugin())

        profile_data = {
            'current_profile': 'my-game',
            'profiles': {'my-game': dict(ConfigurationManager.get_defaults(),
                                         multiplier=3, flow_scale=0.6)},
            'global_config': {'dll': '', 'no_fp16': False},
        }
        self.conf_path().write_text(
            ConfigurationManager.generate_toml_content_multi_profile(profile_data))

        service = self.make_plugin().configuration_service
        result = service.update_lsfg_script_from_profile_data(profile_data)
        self.assertTrue(result['success'], result)

        for path in self.upstream_paths():
            self.assertEqual(path.read_bytes(), SENTINEL, path)
        runtime = tomllib.loads(self.runtime_path().read_text())
        self.assertEqual(runtime['version'], 2)
        self.assertEqual(runtime['profile'][0]['multiplier'], 3)
        self.assertEqual(runtime['profile'][0]['flow_scale'], 0.6)
        self.assertEqual(self.lib_path().read_bytes(), FIXTURE_BINARY)
        check = asyncio.run(self.make_plugin().check_lsfg_vk_installed())
        self.assertTrue(check['installed'], check)


class UninstallReinstallCoexistenceTests(CoexistenceTestBase):
    def test_upstream_installed_after_fork_does_not_replace_fork(self):
        plugin = self.make_plugin()
        self.run_main(plugin)
        for path in self.owned_paths():
            self.assertTrue(path.exists(), path)
        before = {path: path.read_bytes() for path in self.owned_paths()}
        self.seed_upstream()
        self.run_main(plugin)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content, path)
        # Upstream's current uninstall removes these three files individually.
        for path in (self.upstream_lib(), self.upstream_launcher(),
                     self.upstream_json().with_name('VkLayer_LS_frame_generation.json')):
            path.unlink()
        self.assertTrue(plugin.installation_service.check_installation()['installed'])
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content, path)

    def test_runtime_uninstall_preserves_upstream_and_own_profiles(self):
        self.seed_upstream()
        plugin = self.make_plugin()
        self.run_main(plugin)
        self.assertTrue(self.conf_path().exists())
        result = asyncio.run(plugin.uninstall_lsfg_vk())
        self.assertTrue(result['success'], result)
        self.assertFalse(self.lib_path().exists())
        self.assertFalse(self.json_path().exists())
        self.assertFalse(self.launcher_path().exists())
        self.assertTrue(self.conf_path().exists())
        for path in self.upstream_paths():
            self.assertEqual(path.read_bytes(), SENTINEL, path)

    def test_uninstall_and_reinstall_touch_only_owned_paths(self):
        self.seed_upstream()
        self.run_main(self.make_plugin())
        for path in self.owned_paths():
            self.assertTrue(path.exists(), path)

        plugin = self.make_plugin()
        plugin.installation_service.cleanup_on_uninstall()

        self.assertFalse(self.lib_path().exists())
        self.assertFalse(self.json_path().exists())
        self.assertFalse(self.launcher_path().exists())
        self.assertTrue(self.runtime_path().exists())
        self.assertTrue(self.conf_path().exists(), 'profiles must survive uninstall')
        for path in self.upstream_paths():
            self.assertEqual(path.read_bytes(), SENTINEL, path)

        self.run_main(self.make_plugin())

        self.assertEqual(self.lib_path().read_bytes(), FIXTURE_BINARY)
        for path in self.owned_paths():
            self.assertTrue(path.exists(), path)
        for path in self.upstream_paths():
            self.assertEqual(path.read_bytes(), SENTINEL, path)


class NoMigrationNoFlatpakTests(CoexistenceTestBase):
    def test_obsolete_flatpak_mutations_never_call_shared_service(self):
        plugin = self.make_plugin()
        plugin.flatpak_service = mock.Mock()
        for method, argument in (
            (plugin.install_flatpak_extension, '24.08'),
            (plugin.uninstall_flatpak_extension, '24.08'),
            (plugin.set_flatpak_app_override, 'org.example.Game'),
            (plugin.remove_flatpak_app_override, 'org.example.Game'),
        ):
            with self.subTest(method=method.__name__):
                result = asyncio.run(method(argument))
                self.assertFalse(result['success'], result)
                self.assertIn('not supported', result['error'])
        self.assertEqual(plugin.flatpak_service.mock_calls, [])

    def test_startup_moves_no_upstream_files_and_never_invokes_flatpak(self):
        self.seed_upstream()
        self.upstream_json().write_text(json.dumps(
            {'layer': {'name': UPSTREAM_LAYER,
                       'library_path': str(self.upstream_lib())}}))
        before = {path: path.read_bytes() for path in self.upstream_paths()}

        plugin = self.make_plugin()
        self.run_main(plugin)
        with mock.patch.object(self.decky, 'migrate_logs', create=True) as logs, \
             mock.patch.object(self.decky, 'migrate_settings', create=True) as settings, \
             mock.patch.object(self.decky, 'migrate_runtime', create=True) as runtime, \
             mock.patch.object(self.decky, 'DECKY_HOME', str(self.home), create=True), \
             mock.patch.object(plugin.flatpak_service, 'get_extension_status') as flatpak:
            asyncio.run(plugin._migration())
            asyncio.run(plugin._uninstall())
            logs.assert_not_called()
            settings.assert_not_called()
            runtime.assert_not_called()
            flatpak.assert_not_called()

        for path in self.upstream_paths():
            self.assertEqual(path.read_bytes(), before[path], path)
        self.assertEqual(json.loads(self.upstream_json().read_text())
                         ['layer']['name'], UPSTREAM_LAYER)
        self.assertFalse(self.lib_path().exists())


class LegacyZipRemovedTests(CoexistenceTestBase):
    def test_missing_payload_with_legacy_zip_present_fails(self):
        self.seed_upstream()
        (self.plugin_root / 'bin' / runtime_v2.ARM_BINARY).unlink()
        legacy = self.plugin_root / 'bin' / 'lsfg-vk_noui.zip'
        with zipfile.ZipFile(legacy, 'w') as archive:
            archive.writestr('liblsfg-vk.so', b'ARBITRARY-UPSTREAM-BYTES')

        self.run_main(self.make_plugin())

        for path in self.owned_paths():
            self.assertFalse(path.exists(), f'{path} came from the legacy zip path')
        for path in self.upstream_paths():
            self.assertEqual(path.read_bytes(), SENTINEL, path)
        check = asyncio.run(self.make_plugin().check_lsfg_vk_installed())
        self.assertFalse(check['installed'], check)


class MetadataIdentityTests(CoexistenceTestBase):
    def test_copied_launcher_expands_home_without_splitting_arguments(self):
        for home in (self.home / "ordinary", self.home / "Player's Home"):
            with self.subTest(home=home):
                home.mkdir(parents=True, exist_ok=True)
                script = home / "lsfg-arm64"
                script.write_text('#!/bin/sh\nfor arg in "$@"; do printf "%s\\n" "$arg"; done\n')
                script.chmod(0o755)

                self.decky.DECKY_USER_HOME = str(home)
                with mock.patch.dict(os.environ, {"HOME": str(home)}):
                    launch_option = asyncio.run(self.make_plugin().get_launch_option())["launch_option"]
                self.assertEqual(launch_option, "~/lsfg-arm64 %command%")

                completed = subprocess.run(
                    ["/bin/sh", "-c", launch_option.replace("%command%", "'argument with spaces'")],
                    env=dict(os.environ, HOME=str(home)),
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 0)
                self.assertEqual(completed.stdout, "argument with spaces\n")

        with self.subTest(decky_user_home=""):
            self.decky.DECKY_USER_HOME = ""
            self.assertEqual(asyncio.run(self.make_plugin().get_launch_option())["launch_option"], "~/lsfg-arm64 %command%")

    def test_wrong_enable_flag_is_rejected_and_repaired_in_owned_manifest(self):
        self.seed_upstream()
        plugin = self.make_plugin()
        self.run_main(plugin)
        manifest = json.loads(self.json_path().read_text())
        manifest['layer']['enable_environment'] = {'ENABLE_LSFGVK': '1'}
        self.json_path().write_text(json.dumps(manifest))
        self.assertFalse(plugin.installation_service.check_installation()['installed'])
        self.run_main(plugin)
        self.assertEqual(json.loads(self.json_path().read_text())['layer']['enable_environment'],
                         {'ENABLE_LSFGVK_ARM64': '1'})
        for path in self.upstream_paths():
            self.assertEqual(path.read_bytes(), SENTINEL, path)

    def test_metadata_and_layer_identity_are_unique_to_this_fork(self):
        meta = json.loads((ROOT / 'plugin.json').read_text())
        self.assertEqual(meta['name'], 'LSFG-VK ARM64')
        self.assertEqual(json.loads((ROOT / 'package.json').read_text())['name'],
                         'decky-lsfg-vk-arm64')
        self.assertIn('LSFG-VK ARM64', str(meta))

        self.seed_upstream()
        self.run_main(self.make_plugin())

        manifest = json.loads(self.json_path().read_text())
        self.assertEqual(manifest['layer']['name'], OWN_LAYER)
        self.assertNotIn(UPSTREAM_LAYER, self.json_path().read_text())
        self.enable_frame_generation()
        enabled = self.child_env()
        self.assertEqual(enabled['ENABLE_LSFGVK_ARM64'], '1')
        self.assertIsNone(enabled['ENABLE_LSFGVK'])

        profile_data = {
            'current_profile': 'decky-lsfg-vk-arm64',
            'profiles': {'decky-lsfg-vk-arm64': dict(
                ConfigurationManager.get_defaults(), multiplier=1)},
            'global_config': {'dll': '', 'no_fp16': False},
        }
        self.conf_path().write_text(
            ConfigurationManager.generate_toml_content_multi_profile(profile_data))
        self.make_plugin().configuration_service.update_lsfg_script_from_profile_data(profile_data)

        bypass = self.child_env()
        self.assertIsNone(bypass['ENABLE_LSFGVK_ARM64'],
                          'bypass must not enable the own layer')
        self.assertIsNone(bypass['ENABLE_LSFGVK'],
                          'bypass must not enable the upstream layer either')
        self.assertEqual(self.upstream_json().read_bytes(), SENTINEL)


if __name__ == '__main__':
    unittest.main()
