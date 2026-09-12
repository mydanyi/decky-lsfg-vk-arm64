"""
Constants for the lsfg-vk plugin.
"""

from pathlib import Path

LOCAL_LIB = ".local/lib"
LOCAL_SHARE_BASE = ".local/share"
VULKAN_LAYER_DIR = ".local/share/vulkan/implicit_layer.d"
CONFIG_DIR = ".config/lsfg-vk-arm64"

SCRIPT_NAME = "lsfg-arm64"
CONFIG_FILENAME = "conf.toml"
LIB_FILENAME = "liblsfg-vk-arm64.so"
JSON_FILENAME = "VkLayer_LSFGVK_ARM64_frame_generation.json"
ZIP_FILENAME = "lsfg-vk_noui.zip"
ARM_LIB_FILENAME = "liblsfg-vk-arm64.so"

FLATPAK_23_08_FILENAME = "org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak"
FLATPAK_24_08_FILENAME = "org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak"
FLATPAK_25_08_FILENAME = "org.freedesktop.Platform.VulkanLayer.lsfg_vk_25.08.flatpak"

SO_EXT = ".so"
JSON_EXT = ".json"

BIN_DIR = "bin"

ARMADA_DEVICE_ENV = Path("/usr/libexec/armada/device-env")
ARMADA_GAME_LAUNCH = Path("/usr/libexec/armada/armada-game-launch")

STEAM_COMMON_PATH = Path("steamapps/common/Lossless Scaling")
LOSSLESS_DLL_NAME = "Lossless.dll"
# This fork runs the lsfg-vk 2.0 engine only, which loads lsfg-vk.dll. The
# original engine's Lossless.dll is not interchangeable and is never accepted.
LSFG_VK_DLL_NAME = "lsfg-vk.dll"

ENV_LSFG_DLL_PATH = "LSFG_DLL_PATH"
ENV_XDG_DATA_HOME = "XDG_DATA_HOME"
ENV_HOME = "HOME"

