"""Pure helpers for adding/normalising the unified LSFG launch option.

On the ARM64 Armada image the plugin's launch script lives at
``/var/home/armada/lsfg-arm64`` and the host game wrapper is
``/usr/libexec/armada/armada-game-launch``. Every game that uses frame
generation needs both, exactly once, in front of ``%command%``::

    <env assignments> /var/home/armada/lsfg-arm64 /usr/libexec/armada/armada-game-launch %command% <args>

The functions in this module are pure: they never read or write files and do
not inspect the environment, which keeps them trivially testable and safe to
call from a review tool.
"""

import re

#: Canonical launch-script entry on the Armada ARM64 image.
UNIFIED_ENTRY = '/var/home/armada/lsfg-arm64'

#: Relative spelling of this fork's entry.
UNIFIED_ENTRY_ALIAS = '~/lsfg-arm64'
#: Invoking this utility explicitly converts pre-rename launchers.
LEGACY_UNIFIED_ENTRIES = ('/var/home/armada/lsfg', '~/lsfg')

#: Armada's host game wrapper, kept exactly once in the command chain.
ARMADA_LAUNCH = '/usr/libexec/armada/armada-game-launch'

#: Temp wrappers known to have been used during bring-up. Only these may be
#: rewritten; anything else that looks like an LSFG entry is refused.
KNOWN_LEGACY_ENTRIES = (
    '/var/home/armada/.local/share/lsfg-vk-official-20260910/launch-lsfg-official.sh',
    '/var/home/armada/.local/share/lsfg-vk-codex-20260910/launch-lsfg-test.sh',
)

#: Every token that counts as "the LSFG entry is already here".
LSFG_ALIASES = (UNIFIED_ENTRY, UNIFIED_ENTRY_ALIAS) + LEGACY_UNIFIED_ENTRIES + KNOWN_LEGACY_ENTRIES

COMMAND_PLACEHOLDER = '%command%'

#: Marker that identifies a token as an LSFG launcher, known or not.
_LEGACY_MARKER = 'launch-lsfg'

_ENV_ASSIGNMENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')

#: Shell operators / escaping make naive token handling unsafe.
_UNSUPPORTED_SYNTAX = (';', '|', '&', '`', '$(', '${', '>', '<', '\n', '\\')


def _result(success: bool, text: str, changed: bool, reason: str) -> dict:
    return {
        'success': success,
        'changed': changed,
        'launch_options': text,
        'reason': reason,
    }


def _chain_reason(lsfg_count: int) -> str:
    return 'added' if lsfg_count == 0 else 'unified'


def unify_launch_options(launch_options: str) -> dict:
    """Ensure the game's launch options contain the unified LSFG entry once.

    Leading environment assignments keep their position, pure game arguments
    (anything after ``%command%``) are preserved, and the Armada wrapper is
    never duplicated. The operation is idempotent; anything that cannot be
    rewritten with certainty is refused rather than guessed at.

    Args:
        launch_options: The raw launch-options string.

    Returns:
        ``{'success', 'changed', 'launch_options', 'reason'}``. ``success`` is
        ``False`` when the input was refused; ``launch_options`` then carries
        the untouched input.
    """
    text = launch_options or ''

    if any(operator in text for operator in _UNSUPPORTED_SYNTAX):
        return _result(False, text, False, 'unsupported-shell-syntax')

    tokens = [(match.start(), match.end(), match.group()) for match in re.finditer(r'\S+', text)]
    names = [token[2] for token in tokens]
    canonical = f'{UNIFIED_ENTRY} {ARMADA_LAUNCH}'

    # No launch options at all: add the full entry (frame generation must be
    # enabled for every game, not only the ones that already had an entry).
    if not names:
        updated = f'{canonical} {COMMAND_PLACEHOLDER}'
        return _result(True, updated, True, 'added')

    if COMMAND_PLACEHOLDER not in names:
        return _result(False, text, False, 'missing-command-placeholder')
    if names.count(COMMAND_PLACEHOLDER) > 1:
        return _result(False, text, False, 'multiple-command-placeholders')

    # An LSFG-looking token we do not know how to rewrite means the whole
    # string is unsafe. This also covers a legacy path wrapped in quotes (it
    # then no longer equals a known entry) so quoted arguments are never
    # rewritten.
    for name in names:
        if _LEGACY_MARKER in name and name not in KNOWN_LEGACY_ENTRIES:
            return _result(False, text, False, 'unknown-lsfg-entry')

    placeholder_index = names.index(COMMAND_PLACEHOLDER)

    prefix_count = 0
    while prefix_count < placeholder_index and _ENV_ASSIGNMENT.match(names[prefix_count]):
        prefix_count += 1

    chain = names[prefix_count:placeholder_index]
    lsfg_count = sum(1 for name in chain if name in LSFG_ALIASES)
    armada_count = sum(1 for name in chain if name == ARMADA_LAUNCH)

    if lsfg_count > 1:
        return _result(False, text, False, 'multiple-lsfg-entries')
    if armada_count > 1:
        return _result(False, text, False, 'multiple-armada-entries')
    for name in chain:
        if name not in LSFG_ALIASES and name != ARMADA_LAUNCH:
            return _result(False, text, False, 'unsupported-launcher-chain')

    if chain:
        chain_start = tokens[prefix_count][0]
        chain_end = tokens[placeholder_index - 1][1]
        updated = text[:chain_start] + canonical + text[chain_end:]
        reason = 'already-canonical' if updated == text else _chain_reason(lsfg_count)
    else:
        insert_at = tokens[placeholder_index][0]
        updated = text[:insert_at] + canonical + ' ' + text[insert_at:]
        reason = 'added'

    return _result(True, updated, updated != text, reason)
