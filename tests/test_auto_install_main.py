"""First-phase regression tests for the auto-install behaviour of Plugin._main.

These tests describe the approved behaviour BEFORE the implementation exists:
most of them are expected to FAIL until Plugin._main installs the bundled
lsfg-vk 2.0 runtime (see ../AUTO-INSTALL-TESTS.md for the expected-failure
list and rationale).

Mocked boundaries (and nothing else):
  - the external `decky` module (stub with DECKY_USER_HOME / logger / migrations)
  - the host CPU architecture (the Docker test host is x86_64; the plugin runs
    on aarch64, where install() picks the bundled v2 binary)
  - installation.__file__, so the fixture plugin root provides the bundled
    bin/liblsfg-vk-v2-arm64.so

Everything else runs for real: InstallationService, ConfigurationService,
ConfigurationManager, the manifest/launcher/runtime writes, and the actual
files created inside a temporary user home are all asserted directly.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import tomllib
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'py_modules'))

# Decky itself is external; the stub carries everything the lifecycle touches.
sys.modules.setdefault('decky', types.SimpleNamespace(
    logger=logging.getLogger('test'),
    DECKY_USER_HOME='',
    DECKY_HOME='',
    migrate_logs=lambda *args, **kwargs: None,
    migrate_settings=lambda *args, **kwargs: None,
    migrate_runtime=lambda *args, **kwargs: None,
))

import lsfg_vk.installation as installation_module
from lsfg_vk import runtime_v2
from lsfg_vk.config_schema import ConfigurationManager
from lsfg_vk.constants import CONFIG_FILENAME, JSON_FILENAME, LIB_FILENAME, VULKAN_LAYER_DIR

FIXTURE_BINARY = b'\x7fELF' + b'decky-lsfg-v2-test-binary'
LEGACY_LAYER_NAME = 'VK_LAYER_LS_frame_generation'


class AutoInstallTestBase(unittest.TestCase):
    """Temporary user home + fixture plugin root with the bundled v2 binary."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

        self.plugin_root = self.home / 'plugin'
        bundled = self.plugin_root / 'bin'
        bundled.mkdir(parents=True)
        (bundled / runtime_v2.ARM_BINARY).write_bytes(FIXTURE_BINARY)

        self.decky = sys.modules['decky']
        self.set_homes(self.home, self.home)

        # install() derives the bundled-binary location from __file__.
        file_patch = mock.patch.object(
            installation_module, '__file__',
            str(self.plugin_root / 'py_modules' / 'lsfg_vk' / 'installation.py'))
        file_patch.start()
        self.addCleanup(file_patch.stop)

    def set_homes(self, env_home: Path, decky_home: Path):
        """Point HOME/Path.home() at env_home and decky.DECKY_USER_HOME at decky_home."""
        previous = getattr(self.decky, 'DECKY_USER_HOME', '')
        self.decky.DECKY_USER_HOME = str(decky_home)
        self.addCleanup(lambda: setattr(self.decky, 'DECKY_USER_HOME', previous))
        env_patch = mock.patch.dict(os.environ, {'HOME': str(env_home)})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        home_patch = mock.patch('pathlib.Path.home', return_value=env_home)
        home_patch.start()
        self.addCleanup(home_patch.stop)

    def run_main(self, plugin):
        """Run Plugin._main with the host architecture mocked as aarch64."""
        with mock.patch('platform.machine', return_value='aarch64'):
            asyncio.run(plugin._main())

    def make_plugin(self):
        from lsfg_vk.plugin import Plugin
        return Plugin()

    def lib_path(self, base=None):
        return (base or self.home) / '.local/lib' / LIB_FILENAME

    def json_path(self, base=None):
        return (base or self.home) / VULKAN_LAYER_DIR / JSON_FILENAME

    def conf_path(self, base=None):
        return (base or self.home) / '.config/lsfg-vk-arm64' / CONFIG_FILENAME

    def runtime_path(self, base=None):
        return (base or self.home) / '.config/lsfg-vk-arm64' / runtime_v2.RUNTIME_FILENAME

    def launcher_path(self, base=None):
        return (base or self.home) / 'lsfg-arm64'


class FreshStartupAutoInstallTests(AutoInstallTestBase):
    """A fresh startup must install the bundled 2.0 runtime end to end."""

    def test_fresh_startup_installs_bundled_runtime_and_config(self):
        plugin = self.make_plugin()

        self.run_main(plugin)

        # Assert existence before reading so failures name the missing file.
        self.assertTrue(self.lib_path().exists(), 'lib was not installed')
        self.assertTrue(self.json_path().exists(), 'layer manifest was not installed')
        self.assertTrue(self.conf_path().exists(), 'profile store was not created')
        self.assertTrue(self.runtime_path().exists(), 'runtime config was not generated')
        self.assertTrue(self.launcher_path().exists(), 'launcher was not created')

        self.assertEqual(self.lib_path().read_bytes(), FIXTURE_BINARY)
        manifest = json.loads(self.json_path().read_text())
        self.assertEqual(manifest['layer']['name'], runtime_v2.LAYER_NAME)
        self.assertEqual(manifest['layer']['library_path'], str(self.lib_path()))
        runtime = tomllib.loads(self.runtime_path().read_text())
        self.assertEqual(runtime['version'], 2)
        self.assertEqual(runtime['profile'][0]['multiplier'],
                         ConfigurationManager.get_defaults()['multiplier'])
        launcher = self.launcher_path().read_text()
        self.assertIn('LSFGVK_CONFIG', launcher)

        check = asyncio.run(plugin.check_lsfg_vk_installed())
        self.assertTrue(check['installed'], check)

    def test_decky_user_home_takes_precedence_over_root_home(self):
        root_home = self.home / 'root-home'
        decky_home = self.home / 'decky-home'
        root_home.mkdir()
        decky_home.mkdir()
        # Stacked patches win over the setUp defaults: HOME stays at root_home
        # while decky.DECKY_USER_HOME points elsewhere.
        self.set_homes(root_home, decky_home)

        self.run_main(self.make_plugin())

        self.assertTrue(self.lib_path(decky_home).exists())
        self.assertTrue(self.json_path(decky_home).exists())
        self.assertTrue(self.runtime_path(decky_home).exists())
        self.assertTrue(self.launcher_path(decky_home).exists())
        self.assertFalse(self.lib_path(root_home).exists())


class LegacyEngineUpgradeTests(AutoInstallTestBase):
    """An installed 1.x engine must be upgraded in place, keeping user profiles."""

    def install_legacy_engine(self):
        self.lib_path().parent.mkdir(parents=True)
        self.json_path().parent.mkdir(parents=True)
        self.conf_path().parent.mkdir(parents=True)
        self.lib_path().write_bytes(b'OLD-V1-ENGINE')
        self.json_path().write_text(json.dumps(
            {'layer': {'name': LEGACY_LAYER_NAME, 'library_path': str(self.lib_path())}}))
        profile_data = {
            'current_profile': 'my-game',
            'profiles': {
                'my-game': dict(ConfigurationManager.get_defaults(), multiplier=3, flow_scale=0.6),
                'decky-lsfg-vk-arm64': ConfigurationManager.get_defaults(),
            },
            'global_config': {'dll': '/custom/Lossless.dll', 'no_fp16': True},
        }
        self.conf_path().write_text(
            ConfigurationManager.generate_toml_content_multi_profile(profile_data))

    def test_legacy_engine_is_upgraded_and_custom_profiles_survive(self):
        self.install_legacy_engine()

        self.run_main(self.make_plugin())

        self.assertEqual(self.lib_path().read_bytes(), FIXTURE_BINARY)
        manifest = json.loads(self.json_path().read_text())
        self.assertEqual(manifest['layer']['name'], runtime_v2.LAYER_NAME)

        parsed = ConfigurationManager.parse_toml_content_multi_profile(
            self.conf_path().read_text())
        self.assertEqual(parsed['current_profile'], 'my-game')
        self.assertEqual(parsed['profiles']['my-game']['multiplier'], 3)
        self.assertEqual(parsed['profiles']['my-game']['flow_scale'], 0.6)
        self.assertEqual(parsed['global_config']['dll'], '/custom/Lossless.dll')
        self.assertTrue(parsed['global_config']['no_fp16'])

        runtime = tomllib.loads(self.runtime_path().read_text())
        self.assertEqual(runtime['profile'][0]['multiplier'], 3)


class R4LauncherUpgradeTests(AutoInstallTestBase):
    def test_same_core_upgrade_removes_pacing_preserves_settings_and_stays_current(self):
        self.conf_path().parent.mkdir(parents=True)
        profile_data = {
            'current_profile': 'my-game',
            'profiles': {'my-game': dict(ConfigurationManager.get_defaults(),
                                         multiplier=2, dxvk_frame_rate=72, flow_scale=0.6)},
            'global_config': {'dll': '/custom/Lossless.dll', 'no_fp16': True},
        }
        self.conf_path().write_text(
            ConfigurationManager.generate_toml_content_multi_profile(profile_data))
        plugin = self.make_plugin()
        self.run_main(plugin)
        before_config = ConfigurationManager.parse_toml_content_multi_profile(
            self.conf_path().read_text())
        launcher = self.launcher_path().read_text()
        # Reproduce r4's launcher while the installed native core is already current.
        launcher = launcher.replace('armada_game_launch=',
            'export LSFGVK_PACE_FPS=72\nDXVK_FRAME_RATE=0\nVKD3D_FRAME_RATE=0\narmada_game_launch=', 1)
        self.launcher_path().write_text(launcher)
        self.assertEqual(self.lib_path().read_bytes(), FIXTURE_BINARY)

        self.run_main(plugin)

        child = subprocess.run(['bash', str(self.launcher_path()), sys.executable, '-c',
            'import os,json; print(json.dumps({k:os.getenv(k) for k in '
            '["LSFGVK_PACE_FPS","DXVK_FRAME_RATE","VKD3D_FRAME_RATE"]}))'],
            capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(child.stdout), {
            'LSFGVK_PACE_FPS': None, 'DXVK_FRAME_RATE': '72', 'VKD3D_FRAME_RATE': '72'})
        self.assertEqual(ConfigurationManager.parse_toml_content_multi_profile(
            self.conf_path().read_text()), before_config)
        runtime = tomllib.loads(self.runtime_path().read_text())
        self.assertEqual(runtime['profile'][0]['multiplier'], 2)
        self.assertEqual(runtime['profile'][0]['flow_scale'], 0.6)
        self.assertTrue(asyncio.run(plugin.check_lsfg_vk_installed())['installed'])
        watched = [self.lib_path(), self.json_path(), self.conf_path(),
                   self.runtime_path(), self.launcher_path()]
        before = {path: (path.stat().st_mtime_ns, path.read_bytes()) for path in watched}
        self.run_main(plugin)
        self.assertEqual(before, {path: (path.stat().st_mtime_ns, path.read_bytes())
                                  for path in watched})


class SecondStartupTests(AutoInstallTestBase):
    """When everything is already current, a restart must touch nothing."""

    def test_already_current_startup_leaves_files_and_settings_untouched(self):
        plugin = self.make_plugin()
        self.run_main(plugin)

        check = asyncio.run(plugin.check_lsfg_vk_installed())
        self.assertTrue(check['installed'], check)

        watched = [self.lib_path(), self.json_path(), self.conf_path(),
                   self.runtime_path(), self.launcher_path()]
        before = {path: (path.stat().st_mtime_ns, path.read_bytes())
                  for path in watched}

        self.run_main(plugin)

        for path in watched:
            self.assertTrue(path.exists(), path)
            after = (path.stat().st_mtime_ns, path.read_bytes())
            self.assertEqual(before[path], after,
                             f'{path} was rewritten on the second startup')


class InstallWriteFailureTests(AutoInstallTestBase):
    def test_install_write_failure_surfaces_as_not_installed(self):
        # conf.toml exists as a directory: the profile-store write fails after
        # the library/manifest staging, so the install must not claim success,
        # must report a meaningful error, and the check must say installed=false.
        self.conf_path().parent.mkdir(parents=True)
        self.conf_path().mkdir()
        plugin = self.make_plugin()

        self.run_main(plugin)

        check = asyncio.run(plugin.check_lsfg_vk_installed())
        self.assertFalse(check['installed'], check)
        self.assertTrue(check.get('error'), 'check must surface the installation error')
        self.assertIn('conf.toml', check['error'], check)


class ConfigurationParseErrorTests(AutoInstallTestBase):
    def test_parse_error_does_not_return_successful_editable_defaults(self):
        # Invalid UTF-8 in conf.toml hits the parse-error path; the plugin must
        # surface an error instead of success + editable defaults.
        self.conf_path().parent.mkdir(parents=True)
        self.conf_path().write_bytes(b'\xff\xfe\xff\x00 not valid toml \x00')
        plugin = self.make_plugin()

        result = asyncio.run(plugin.get_lsfg_config())

        self.assertFalse(result['success'], result)
        self.assertIsNone(result.get('config'))


class ManualRetryErrorSurfacingTests(AutoInstallTestBase):
    """A failed manual install must stay visible through the check API."""

    def manual_install(self, plugin):
        with mock.patch('platform.machine', return_value='aarch64'):
            return asyncio.run(plugin.install_lsfg_vk())

    def test_manual_failure_keeps_error_visible_then_retry_clears_it(self):
        plugin = self.make_plugin()
        self.run_main(plugin)
        self.assertTrue(asyncio.run(plugin.check_lsfg_vk_installed())['installed'])

        broken = b'\xff\xfe\xff\x00 not valid toml \x00'
        self.conf_path().write_bytes(broken)

        result = self.manual_install(plugin)
        self.assertFalse(result['success'], result)
        self.assertTrue(result.get('error'), result)

        # The unreadable config must be preserved byte for byte.
        self.assertEqual(self.conf_path().read_bytes(), broken)

        # The check must not claim installed while the last install failed.
        check = asyncio.run(plugin.check_lsfg_vk_installed())
        self.assertFalse(check['installed'], check)
        self.assertTrue(check.get('error'), 'check must surface the installation error')

        # Restoring a readable config lets the manual retry succeed and clears
        # the stored error.
        profile_data = {
            'current_profile': 'decky-lsfg-vk-arm64',
            'profiles': {'decky-lsfg-vk-arm64': ConfigurationManager.get_defaults()},
            'global_config': {'dll': '', 'no_fp16': False},
        }
        self.conf_path().write_text(
            ConfigurationManager.generate_toml_content_multi_profile(profile_data))

        retry = self.manual_install(plugin)
        self.assertTrue(retry['success'], retry)

        check = asyncio.run(plugin.check_lsfg_vk_installed())
        self.assertTrue(check['installed'], check)
        self.assertIsNone(check.get('error'))


class ManifestPathRepairTests(AutoInstallTestBase):
    """A drifted manifest library_path must be repaired on the next startup."""

    def test_next_startup_repairs_changed_manifest_library_path(self):
        plugin = self.make_plugin()
        self.run_main(plugin)
        self.assertTrue(asyncio.run(plugin.check_lsfg_vk_installed())['installed'])

        manifest = json.loads(self.json_path().read_text())
        manifest['layer']['library_path'] = '/missing/old.so'
        self.json_path().write_text(json.dumps(manifest))

        self.run_main(self.make_plugin())

        repaired = json.loads(self.json_path().read_text())
        self.assertEqual(repaired['layer']['name'], runtime_v2.LAYER_NAME)
        self.assertEqual(repaired['layer']['library_path'], str(self.lib_path()))
        self.assertEqual(self.lib_path().read_bytes(), FIXTURE_BINARY)

        check = asyncio.run(self.make_plugin().check_lsfg_vk_installed())
        self.assertTrue(check['installed'], check)


class UninstallReinstallFlowTests(AutoInstallTestBase):
    """cleanup_on_uninstall keeps profiles; the next startup restores the rest."""

    def test_cleanup_then_reinstall_restores_runtime_and_profiles(self):
        self.conf_path().parent.mkdir(parents=True)
        profile_data = {
            'current_profile': 'my-game',
            'profiles': {
                'my-game': dict(ConfigurationManager.get_defaults(), multiplier=3, flow_scale=0.6),
                'decky-lsfg-vk-arm64': ConfigurationManager.get_defaults(),
            },
            'global_config': {'dll': '/custom/Lossless.dll', 'no_fp16': True},
        }
        self.conf_path().write_text(
            ConfigurationManager.generate_toml_content_multi_profile(profile_data))

        self.run_main(self.make_plugin())
        self.assertTrue(self.lib_path().exists())

        plugin = self.make_plugin()
        plugin.installation_service.cleanup_on_uninstall()

        self.assertFalse(self.lib_path().exists())
        self.assertFalse(self.json_path().exists())
        self.assertFalse(self.launcher_path().exists())
        self.assertTrue(self.conf_path().exists(), 'profiles must survive cleanup')

        self.run_main(self.make_plugin())

        self.assertTrue(self.lib_path().exists())
        self.assertEqual(self.lib_path().read_bytes(), FIXTURE_BINARY)
        self.assertTrue(self.runtime_path().exists())
        self.assertTrue(self.launcher_path().exists())

        parsed = ConfigurationManager.parse_toml_content_multi_profile(
            self.conf_path().read_text())
        self.assertEqual(parsed['current_profile'], 'my-game')
        self.assertEqual(parsed['profiles']['my-game']['multiplier'], 3)
        self.assertEqual(parsed['profiles']['my-game']['flow_scale'], 0.6)

        check = asyncio.run(self.make_plugin().check_lsfg_vk_installed())
        self.assertTrue(check['installed'], check)


if __name__ == '__main__':
    unittest.main()
