"""
Installation service for lsfg-vk.
"""

import platform
import shutil
import traceback
import json
import filecmp
from pathlib import Path
from typing import Dict, Any, Optional

from .base_service import BaseService
from .constants import (
    LIB_FILENAME, JSON_FILENAME, BIN_DIR, ARMADA_DEVICE_ENV
)
from .config_schema import ConfigurationManager
from . import runtime_v2
from .types import InstallationResponse, UninstallationResponse, InstallationCheckResponse


class InstallationService(BaseService):
    """Service for handling lsfg-vk installation and uninstallation"""

    def __init__(self, logger=None):
        super().__init__(logger)

        self.lib_file = self.local_lib_dir / LIB_FILENAME
        self.json_file = self.local_share_dir / JSON_FILENAME
        # Last installation failure, surfaced through the check API until a
        # successful (manual) install retry clears it.
        self.last_error: Optional[str] = None

    def _bundled_native_binary(self) -> Optional[Path]:
        """Return the bundled 2.0 native binary shipped with the plugin, if any."""
        plugin_dir = Path(__file__).parent.parent.parent
        native_v2 = plugin_dir / BIN_DIR / runtime_v2.ARM_BINARY
        return native_v2 if native_v2.exists() else None

    def install(self) -> InstallationResponse:
        """Install the bundled lsfg-vk 2.0 ARM64 runtime to ~/.local."""
        try:
            native_v2 = self._bundled_native_binary()
            if native_v2 is None:
                error_msg = (f"Missing ARM64 native payload: {BIN_DIR}/{runtime_v2.ARM_BINARY} "
                             "was not found in the plugin package. The legacy ZIP engine is "
                             "not supported; supply the ARM64 runtime payload and retry.")
                self.log.error(error_msg)
                self.last_error = error_msg
                return self._error_response(InstallationResponse, error_msg, message="")
            if not self._is_arm_architecture():
                error_msg = (f"Bundled {runtime_v2.ARM_BINARY} requires an ARM64 host; "
                             "refusing to install on this architecture")
                self.log.error(error_msg)
                self.last_error = error_msg
                return self._error_response(InstallationResponse, error_msg, message="")
            self._ensure_directories()
            self._install_v2_files(native_v2)
            self._create_config_file()
            self._create_lsfg_launch_script()
            self.last_error = None
            self.log.info("lsfg-vk 2.0.0 ARM64 installed successfully")
            return self._success_response(InstallationResponse, "Installed lsfg-vk 2.0.0 ARM64")
        except (OSError, shutil.Error) as e:
            self.last_error = str(e)
            self.log.error(f"Error installing lsfg-vk: {e}")
            return self._error_response(InstallationResponse, str(e), message="")
        except Exception as e:
            self.last_error = str(e)
            self.log.error(f"Unexpected error installing lsfg-vk: {e}")
            return self._error_response(InstallationResponse, str(e), message="")

    def _install_v2_files(self, binary: Path) -> None:
        # Replacing the inode leaves any already mapped library intact until game exit.
        staged = self.lib_file.with_suffix('.so.new')
        self._copy_plugin_file(binary, staged)
        staged.replace(self.lib_file)
        self._write_file(self.json_file, json.dumps(runtime_v2.manifest(self.lib_file), indent=2), 0o644)

    def _is_arm_architecture(self) -> bool:
        """Check if running on ARM architecture

        Returns:
            True if running on ARM (aarch64), False otherwise
        """
        if platform.machine().lower() in ('aarch64', 'arm64'):
            return True

        # Decky runs through FEX on Armada, so Python reports x86_64 even
        # though the host is AArch64. Armada exposes this native helper only
        # on its ARM image, including inside Decky's FEX rootfs.
        if ARMADA_DEVICE_ENV.is_file():
            self.log.info("Detected native AArch64 Armada host through device-env")
            return True

        # Fall back to the native PID 1 ELF header. e_machine 183 is AArch64.
        try:
            with Path('/proc/1/exe').open('rb') as host_executable:
                elf_header = host_executable.read(20)
            if elf_header[:4] == b'\x7fELF' and elf_header[5] in (1, 2):
                byte_order = 'little' if elf_header[5] == 1 else 'big'
                if int.from_bytes(elf_header[18:20], byte_order) == 183:
                    self.log.info("Detected native AArch64 host through PID 1")
                    return True
        except OSError as e:
            self.log.debug(f"Could not inspect native host architecture: {e}")

        return False

    @staticmethod
    def _copy_plugin_file(src_file: Path, dst_file: Path) -> None:
        """Copy plugin content without preserving FEX-incompatible metadata."""
        shutil.copyfile(src_file, dst_file)
        dst_file.chmod(0o644)

    def _create_config_file(self) -> None:
        """Create or update the TOML config file in ~/.config/lsfg-vk-arm64 with default configuration and detected DLL path
        
        If a config file already exists, preserve existing profiles and only update global settings like DLL path.
        """
        # Import here to avoid circular imports
        from .dll_detection import DllDetectionService
        
        # Try to detect DLL path
        dll_service = DllDetectionService(self.log)
        
        # Check if config file already exists
        if self.config_file_path.exists():
            try:
                # Read existing config to preserve user profiles
                content = self.config_file_path.read_text(encoding='utf-8')
                existing_profile_data = ConfigurationManager.parse_toml_content_multi_profile(content)
                self.log.info(f"Found existing config file, preserving user profiles")
                
                # Create merged profile data that preserves user settings but adds any new fields
                merged_profile_data = self._merge_config_with_defaults(existing_profile_data, dll_service)
                
                # Generate TOML content with merged profiles
                toml_content = ConfigurationManager.generate_toml_content_multi_profile(merged_profile_data)
                
            except Exception as e:
                # Never destroy a user config we failed to read: fail the
                # install instead so the original file is preserved.
                self.log.error(f"Failed to parse existing config file: {str(e)}; "
                               "refusing to overwrite it")
                raise
        else:
            # No existing config file, create a new one with defaults
            config = ConfigurationManager.get_defaults_with_dll_detection(dll_service)
            toml_content = ConfigurationManager.generate_toml_content(config)
            self.log.info(f"Creating new config file")
        
        # Write config file
        self._write_file(self.config_file_path, toml_content, 0o644)
        self.log.info(f"Created config file at {self.config_file_path}")
        
        # Log detected DLL path if found - USE GENERATED CONSTANTS
        from .config_schema_generated import DLL
        try:
            # Try to parse the written content to get the DLL path
            final_content = self.config_file_path.read_text(encoding='utf-8')
            final_config = ConfigurationManager.parse_toml_content(final_content)
            if final_config.get(DLL):
                self.log.info(f"Configured DLL path: {final_config[DLL]}")
        except (OSError, IOError, ValueError, KeyError) as e:
            # Don't fail installation if we can't log the DLL path
            self.log.debug(f"Could not log DLL path: {e}")
    
    def _create_lsfg_launch_script(self) -> None:
        """Create the ~/lsfg-arm64 launch script for easier game setup"""
        # Use the default configuration for the initial script
        from .config_schema import ConfigurationManager
        default_config = ConfigurationManager.get_defaults()
        
        # Create configuration service to generate the script
        from .configuration import ConfigurationService
        config_service = ConfigurationService(logger=self.log)
        config_service.user_home = self.user_home
        config_service.lsfg_script_path = self.lsfg_launch_script_path
        config_service.config_dir = self.config_dir
        config_service.config_file_path = self.config_file_path
        config_service.local_share_dir = self.local_share_dir
        
        # Generate script content with default configuration
        script_content = config_service._generate_script_content_for_profile(config_service._get_profile_data())
        
        # Write the script file
        self._write_file(self.lsfg_launch_script_path, script_content, 0o755)
        self.log.info(f"Created lsfg launch script at {self.lsfg_launch_script_path}")
    
    def get_launch_script_path(self) -> str:
        """Get the path to the lsfg launch script
        
        Returns:
            String path to the launch script file
        """
        return str(self.lsfg_launch_script_path)

    def check_installation(self) -> InstallationCheckResponse:
        """Check if lsfg-vk is already installed

        When the plugin ships a bundled 2.0 native binary, the check must not
        accept a stale 1.x engine just because the files exist: the layer
        manifest must be the 2.0 engine, the installed library must be byte
        identical to the bundled binary, and the launcher plus generated
        runtime configuration must exist.

        Returns:
            InstallationCheckResponse with installation status and file paths
        """
        try:
            lib_exists = self.lib_file.is_file()
            json_exists = self.json_file.is_file()
            config_exists = self.config_file_path.is_file()
            launcher_exists = self.lsfg_launch_script_path.is_file()

            installed = (lib_exists and json_exists and launcher_exists
                         and config_exists and self.last_error is None)

            bundled = self._bundled_native_binary()
            if installed:
                runtime_config = self.config_dir / runtime_v2.RUNTIME_FILENAME
                manifest = json.loads(self.json_file.read_text()) if json_exists else {}
                layer = manifest.get('layer', {})
                installed = (
                    runtime_v2.is_v2_manifest(self.json_file)
                    # Owned manifest contract only; obsolete own manifests rejected.
                    and layer.get('enable_environment') == {'ENABLE_LSFGVK_ARM64': '1'}
                    and layer.get('disable_environment') == {'DISABLE_LSFGVK': '1'}
                    and layer.get('library_path') == str(self.lib_file)
                    and (bundled is None or filecmp.cmp(bundled, self.lib_file, shallow=False))
                    and runtime_config.is_file()
                    # r4 shipped the same core, but its launcher enabled the
                    # regressing experimental scheduler and zeroed driver caps.
                    and not any(line.strip().startswith('export LSFGVK_PACE_FPS=')
                                for line in self.lsfg_launch_script_path.read_text().splitlines())
                )

            self.log.info(f"Installation check: lib={lib_exists}, json={json_exists}, "
                          f"config={config_exists}, launcher={launcher_exists}, installed={installed}")

            return {
                "installed": installed,
                "lib_exists": lib_exists,
                "json_exists": json_exists,
                "script_exists": config_exists,  # Keep script_exists for backward compatibility
                "lib_path": str(self.lib_file),
                "json_path": str(self.json_file),
                "script_path": str(self.config_file_path),  # Keep script_path for backward compatibility
                "error": None if installed else self.last_error
            }

        except Exception as e:
            error_msg = f"Error checking lsfg-vk installation: {str(e)}"
            self.log.error(error_msg)
            return {
                "installed": False,
                "lib_exists": False,
                "json_exists": False,
                "script_exists": False,
                "lib_path": str(self.lib_file),
                "json_path": str(self.json_file),
                "script_path": str(self.config_file_path),
                "error": str(e)
            }
    
    def uninstall(self) -> UninstallationResponse:
        """Uninstall lsfg-vk by removing the installed files
        
        Note: The config file (conf.toml) is preserved to maintain user's custom profiles
        
        Returns:
            UninstallationResponse with success status and removed files list
        """
        try:
            removed_files = []
            # Remove core lsfg-vk files, but preserve config file to maintain user's custom profiles
            files_to_remove = [self.lib_file, self.json_file, self.lsfg_launch_script_path]
            
            for file_path in files_to_remove:
                if self._remove_if_exists(file_path):
                    removed_files.append(str(file_path))
            
            # Coexistence: never remove the original plugin's ~/lsfg script.
            
            # Don't remove config directory since we're preserving the config file
            
            if not removed_files:
                return self._success_response(UninstallationResponse,
                                            "No lsfg-vk files found to remove",
                                            removed_files=None)
            
            self.log.info("lsfg-vk uninstalled successfully")
            return self._success_response(UninstallationResponse, 
                                        f"lsfg-vk uninstalled successfully. Removed {len(removed_files)} files.",
                                        removed_files=removed_files)
            
        except OSError as e:
            error_msg = f"Error uninstalling lsfg-vk: {str(e)}"
            self.log.error(error_msg)
            return self._error_response(UninstallationResponse, str(e), 
                                      message="", removed_files=None)
    
    def cleanup_on_uninstall(self) -> None:
        """Clean up lsfg-vk files when the plugin is uninstalled
        
        Note: The config file (conf.toml) is preserved to maintain user's custom profiles
        """
        try:
            self.log.info("Checking for lsfg-vk files to clean up:")
            self.log.info(f"  Library file: {self.lib_file}")
            self.log.info(f"  JSON file: {self.json_file}")
            self.log.info(f"  Config file: {self.config_file_path} (preserved)")
            self.log.info(f"  Launch script: {self.lsfg_launch_script_path}")
            
            removed_files = []
            # Remove core lsfg-vk files, but preserve config file to maintain user's custom profiles
            files_to_remove = [self.lib_file, self.json_file, self.lsfg_launch_script_path]
            
            for file_path in files_to_remove:
                try:
                    if self._remove_if_exists(file_path):
                        removed_files.append(str(file_path))
                except OSError as e:
                    self.log.error(f"Failed to remove {file_path}: {e}")
            
            # Don't remove config directory since we're preserving the config file
            
            if removed_files:
                self.log.info(f"Cleaned up {len(removed_files)} lsfg-vk files during plugin uninstall: {removed_files}")
            else:
                self.log.info("No lsfg-vk files found to clean up during plugin uninstall")
                
        except Exception as e:
            self.log.error(f"Error cleaning up lsfg-vk files during uninstall: {str(e)}")
            self.log.error(f"Traceback: {traceback.format_exc()}")

    def _merge_config_with_defaults(self, existing_profile_data, dll_service):
        """Merge existing user config with current schema defaults
        
        This ensures that:
        1. User's custom profiles and values are preserved
        2. Any new fields added to the schema get their default values
        3. Global settings like DLL path are updated as needed
        
        Args:
            existing_profile_data: The user's existing ProfileData
            dll_service: DLL detection service for updating DLL path
            
        Returns:
            ProfileData with merged configuration
        """
        from .config_schema import ProfileData
        
        # Get current schema defaults
        default_config = ConfigurationManager.get_defaults_with_dll_detection(dll_service)
        default_global_config = {
            "dll": default_config.get("dll", ""),
            "no_fp16": False
        }
        
        # Start with existing data
        merged_data: ProfileData = {
            "current_profile": existing_profile_data.get("current_profile", "decky-lsfg-vk-arm64"),
            "global_config": existing_profile_data.get("global_config", {}).copy(),
            "profiles": {}
        }
        
        # Merge global config: preserve user values, add missing fields, update DLL
        for key, default_value in default_global_config.items():
            if key not in merged_data["global_config"]:
                merged_data["global_config"][key] = default_value
                self.log.info(f"Added missing global field '{key}' with default value: {default_value}")
        
        # Update DLL path if detected
        dll_result = dll_service.check_lossless_scaling_dll()
        if dll_result.get("detected") and dll_result.get("path"):
            old_dll = merged_data["global_config"].get("dll")
            merged_data["global_config"]["dll"] = dll_result["path"]
            if old_dll != dll_result["path"]:
                self.log.info(f"Updated DLL path from '{old_dll}' to: {dll_result['path']}")
        
        # Merge each profile: preserve user values, add missing fields
        existing_profiles = existing_profile_data.get("profiles", {})
        
        for profile_name, existing_profile_config in existing_profiles.items():
            merged_profile_config = existing_profile_config.copy()
            
            # Add any missing fields from current schema with default values
            added_fields = []
            for key, default_value in default_config.items():
                if key not in merged_profile_config and key not in ["dll", "no_fp16"]:  # Skip global fields
                    merged_profile_config[key] = default_value
                    added_fields.append(key)
            
            if added_fields:
                self.log.info(f"Profile '{profile_name}': Added missing fields {added_fields}")
            
            merged_data["profiles"][profile_name] = merged_profile_config
        
        # If no profiles exist, create the default one
        if not merged_data["profiles"]:
            merged_data["profiles"]["decky-lsfg-vk-arm64"] = {
                k: v for k, v in default_config.items() 
                if k not in ["dll", "no_fp16"]  # Exclude global fields
            }
            merged_data["current_profile"] = "decky-lsfg-vk-arm64"
            self.log.info("No existing profiles found, created default profile")
        
        return merged_data
