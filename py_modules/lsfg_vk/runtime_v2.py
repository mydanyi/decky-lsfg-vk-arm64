"""Map Decky's saved profiles to the official lsfg-vk 2.0 runtime format."""

import json
from pathlib import Path
import shlex

LAYER_NAME = 'VK_LAYER_LSFGVK_frame_generation'
ARM_BINARY = 'liblsfg-vk-v2-arm64.so'
RUNTIME_FILENAME = 'decky-v2.toml'
RUNTIME_PROFILE = 'decky-active'


def is_v2_manifest(path: Path) -> bool:
    try:
        return json.loads(path.read_text())['layer']['name'] == LAYER_NAME
    except (OSError, ValueError, KeyError, TypeError):
        return False


def dll_path(value: str) -> str:
    if not value:
        return ''
    path = Path(value).expanduser()
    if path.name.lower() in ('lossless.dll', 'losslessscaling.dll'):
        path = path.with_name('lsfg-vk.dll')
    return str(path)


def runtime_toml(config: dict) -> str:
    multiplier = int(config.get('multiplier', 1))
    flow = float(config.get('flow_scale', 0.8))
    if multiplier < 1 or not 0.25 <= flow <= 1.0:
        raise ValueError('Invalid lsfg-vk multiplier or flow scale')
    boolean = lambda value: 'true' if value else 'false'
    lines = ['version = 2', '', '[global]',
             f'allow_fp16 = {boolean(not config.get("no_fp16", False))}',
             'log_level = "info"']
    dll = dll_path(config.get('dll', ''))
    if dll:
        lines.append(f'dll = {json.dumps(dll, ensure_ascii=False)}')
    lines.extend(['', '[[profile]]', f'name = "{RUNTIME_PROFILE}"',
                  'pacing_mode = "vsync"', 'override_present_mode = true',
                  f'multiplier = {multiplier}', f'flow_scale = {flow}',
                  f'performance_mode = {boolean(config.get("performance_mode", False))}', ''])
    return '\n'.join(lines)


def is_enabled(config: dict) -> bool:
    """Frame generation is active only above the 1x bypass multiplier."""
    return int(config.get('multiplier', 1)) > 1


def launch_lines(config: dict, path: Path) -> list[str]:
    lines = [
        # The previous test wrappers used env overrides. Never let them bypass this config.
        'unset LSFGVK_ENV LSFGVK_MULTIPLIER LSFGVK_FLOW_SCALE LSFGVK_PERFORMANCE_MODE',
        'unset LSFGVK_DLL_PATH LSFGVK_NO_FP16 LSFGVK_PACING_MODE LSFGVK_OVERRIDE_PRESENT_MODE',
        'unset LSFGVK_PRESERVE_SWAPCHAIN_IMAGE_COUNT LSFGVK_LOG_FILE LSFGVK_LOG_LEVEL',
        'unset LSFGVK_PACE_FPS LSFGVK_TIMING_TRIGGER',
        'export DISABLE_LSFG=1',
    ]
    if is_enabled(config):
        # Only the enable flag is set when active; DISABLE_LSFGVK must be absent
        # because the Vulkan loader disables the layer whenever that variable is
        # set to any value, including "0".
        lines.append('unset DISABLE_LSFGVK')
        lines.append('export ENABLE_LSFGVK=1')
    else:
        # When frame generation is off, inject nothing: leave ENABLE_LSFGVK
        # unset so the loader never loads the layer, and keep DISABLE_LSFGVK as
        # a belt-and-braces guard.
        lines.append('unset ENABLE_LSFGVK')
        lines.append('export DISABLE_LSFGVK=1')
    lines.extend([
        f'export LSFGVK_CONFIG={shlex.quote(str(path))}',
        f'export LSFGVK_PROFILE={RUNTIME_PROFILE}',
    ])
    multiplier = int(config.get('multiplier', 1))
    dxvk_frame_rate = int(config.get('dxvk_frame_rate', 0))
    if multiplier == 2 and 1 <= dxvk_frame_rate <= 72:
        # Keep the tested GPU policy, but leave ordinary driver caps intact.
        # Experimental paired pacing regressed high-FPS gameplay on the device.
        lines.append('export TU_AUTOTUNE_ALGO=prefer_gmem')
    return lines


def manifest(library: Path) -> dict:
    return {'file_format_version': '1.1.0', 'layer': {
        'name': LAYER_NAME, 'description': 'Lossless Scaling frame generation layer',
        'implementation_version': '2', 'library_path': str(library),
        'type': 'GLOBAL', 'api_version': '1.4.350',
        'enable_environment': {'ENABLE_LSFGVK': '1'},
        'disable_environment': {'DISABLE_LSFGVK': '1'},
    }}
