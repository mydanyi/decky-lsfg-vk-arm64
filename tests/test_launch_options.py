import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from launch_options import KNOWN_LEGACY_ENTRIES, UNIFIED_ENTRY, unify_launch_options

OFFICIAL_ENTRY = KNOWN_LEGACY_ENTRIES[0]
CODEX_ENTRY = KNOWN_LEGACY_ENTRIES[1]
ARMADA_LAUNCH = '/usr/libexec/armada/armada-game-launch'
CANONICAL = f'{UNIFIED_ENTRY} {ARMADA_LAUNCH}'


class AddEntryTests(unittest.TestCase):
    """Every game must end up with the LSFG entry, even without prior config."""

    def test_empty_input_generates_the_full_entry(self):
        for value in ('', '   ', None):
            with self.subTest(value=value):
                result = unify_launch_options(value)
                self.assertTrue(result['success'], result)
                self.assertTrue(result['changed'])
                self.assertEqual(result['reason'], 'added')
                self.assertEqual(result['launch_options'], f'{CANONICAL} %command%')

    def test_bare_command_placeholder_gets_the_full_entry(self):
        result = unify_launch_options('%command%')
        self.assertTrue(result['success'], result)
        self.assertEqual(result['launch_options'], f'{CANONICAL} %command%')
        self.assertEqual(result['reason'], 'added')

    def test_existing_armada_wrapper_gets_lsfg_without_duplicating_armada(self):
        result = unify_launch_options(f'{ARMADA_LAUNCH} %command%')
        self.assertTrue(result['success'], result)
        self.assertTrue(result['changed'])
        self.assertEqual(result['reason'], 'added')
        self.assertEqual(result['launch_options'], f'{CANONICAL} %command%')

    def test_env_position_and_trailing_args_are_preserved(self):
        options = 'FOO=bar %command% -dx11'
        result = unify_launch_options(options)
        self.assertTrue(result['success'], result)
        self.assertEqual(result['launch_options'], f'FOO=bar {CANONICAL} %command% -dx11')

    def test_multiple_env_assignments_keep_order_and_args_are_kept(self):
        options = 'ENABLE_GAMESCOPE_WSI=0 DXVK_HDR=0 %command% -dx11 --launcher-skip'
        result = unify_launch_options(options)
        self.assertTrue(result['success'], result)
        self.assertEqual(
            result['launch_options'],
            f'ENABLE_GAMESCOPE_WSI=0 DXVK_HDR=0 {CANONICAL} %command% -dx11 --launcher-skip',
        )

    def test_quoted_ordinary_argument_is_preserved(self):
        result = unify_launch_options('%command% "--windowed"')
        self.assertTrue(result['success'], result)
        self.assertEqual(result['launch_options'], f'{CANONICAL} %command% "--windowed"')


class NormaliseEntryTests(unittest.TestCase):
    def test_replaces_official_entry_keeping_env_and_armada(self):
        options = f'ENABLE_GAMESCOPE_WSI=0 DXVK_HDR=0 {OFFICIAL_ENTRY} {ARMADA_LAUNCH} %command%'
        result = unify_launch_options(options)
        self.assertTrue(result['success'], result)
        self.assertTrue(result['changed'])
        self.assertEqual(result['reason'], 'unified')
        self.assertEqual(
            result['launch_options'],
            f'ENABLE_GAMESCOPE_WSI=0 DXVK_HDR=0 {CANONICAL} %command%',
        )

    def test_replaces_old_codex_entry(self):
        result = unify_launch_options(f'{CODEX_ENTRY} %command%')
        self.assertTrue(result['success'], result)
        self.assertTrue(result['changed'])
        self.assertEqual(result['reason'], 'unified')
        self.assertEqual(result['launch_options'], f'{CANONICAL} %command%')

    def test_recognises_relative_lsfg_alias(self):
        result = unify_launch_options('~/lsfg %command%')
        self.assertTrue(result['success'], result)
        self.assertTrue(result['changed'])
        self.assertEqual(result['reason'], 'unified')
        self.assertEqual(result['launch_options'], f'{CANONICAL} %command%')

    def test_already_canonical_is_unchanged(self):
        options = f'{CANONICAL} %command%'
        result = unify_launch_options(options)
        self.assertTrue(result['success'], result)
        self.assertFalse(result['changed'])
        self.assertEqual(result['reason'], 'already-canonical')
        self.assertEqual(result['launch_options'], options)

    def test_already_canonical_with_env_and_args_is_unchanged(self):
        options = f'FOO=bar {CANONICAL} %command% -dx11'
        result = unify_launch_options(options)
        self.assertTrue(result['success'], result)
        self.assertFalse(result['changed'])
        self.assertEqual(result['reason'], 'already-canonical')
        self.assertEqual(result['launch_options'], options)

    def test_is_idempotent(self):
        first = unify_launch_options(f'DXVK_FRAME_RATE=30 {OFFICIAL_ENTRY} %command%')
        self.assertTrue(first['success'], first)
        self.assertTrue(first['changed'])
        second = unify_launch_options(first['launch_options'])
        self.assertTrue(second['success'], second)
        self.assertFalse(second['changed'])
        self.assertEqual(second['reason'], 'already-canonical')
        self.assertEqual(second['launch_options'], first['launch_options'])


class RefusalTests(unittest.TestCase):
    def assert_refused(self, options, reason):
        result = unify_launch_options(options)
        self.assertFalse(result['success'], result)
        self.assertEqual(result['reason'], reason)
        self.assertEqual(result['launch_options'], options)
        return result

    def test_missing_command_placeholder_is_refused(self):
        self.assert_refused(OFFICIAL_ENTRY, 'missing-command-placeholder')

    def test_multiple_command_placeholders_are_refused(self):
        self.assert_refused(f'{OFFICIAL_ENTRY} %command% %command%', 'multiple-command-placeholders')

    def test_unknown_lsfg_entry_is_refused(self):
        options = '/var/home/armada/.local/share/lsfg-vk-future-20990101/launch-lsfg-later.sh %command%'
        self.assert_refused(options, 'unknown-lsfg-entry')

    def test_quoted_legacy_path_argument_is_not_rewritten(self):
        # A quoted argument that merely contains the old path is not an entry.
        options = f'%command% "{OFFICIAL_ENTRY}"'
        self.assert_refused(options, 'unknown-lsfg-entry')

    def test_quoted_legacy_entry_is_refused(self):
        self.assert_refused(f'"{OFFICIAL_ENTRY}" %command%', 'unknown-lsfg-entry')

    def test_legacy_entry_glued_into_env_assignment_is_refused(self):
        self.assert_refused(f'LSFG_ENTRY={CODEX_ENTRY} %command%', 'unknown-lsfg-entry')

    def test_multiple_lsfg_entries_are_refused(self):
        self.assert_refused(f'{OFFICIAL_ENTRY} {CODEX_ENTRY} %command%', 'multiple-lsfg-entries')

    def test_unified_entry_next_to_legacy_entry_is_refused(self):
        self.assert_refused(f'{UNIFIED_ENTRY} {OFFICIAL_ENTRY} %command%', 'multiple-lsfg-entries')

    def test_multiple_armada_wrappers_are_refused(self):
        self.assert_refused(f'{ARMADA_LAUNCH} {ARMADA_LAUNCH} %command%', 'multiple-armada-entries')

    def test_unknown_launcher_chain_is_refused(self):
        # fgmod is a 1.x-only wrapper; it cannot be canonicalised safely.
        self.assert_refused('~/fgmod/fgmod ~/lsfg %command%', 'unsupported-launcher-chain')

    def test_unknown_argument_before_command_is_refused(self):
        self.assert_refused('-dx11 %command%', 'unsupported-launcher-chain')

    def test_shell_operators_are_refused(self):
        self.assert_refused(f'{OFFICIAL_ENTRY} %command% && echo hi', 'unsupported-shell-syntax')
        self.assert_refused(f'{OFFICIAL_ENTRY} %command% | tee log', 'unsupported-shell-syntax')


if __name__ == '__main__':
    unittest.main()
