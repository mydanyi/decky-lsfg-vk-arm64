import { useState } from "react";
import { installLsfgVk, uninstallLsfgVk } from "../api/lsfgApi";
import { 
  showInstallSuccessToast, 
  showInstallErrorToast,
  showUninstallSuccessToast, 
  showUninstallErrorToast 
} from "../utils/toastUtils";
import t from "../i18n/i18n";

export function useInstallationActions() {
  const [isInstalling, setIsInstalling] = useState<boolean>(false);
  const [isUninstalling, setIsUninstalling] = useState<boolean>(false);

  const handleInstall = async (
    setIsInstalled: (value: boolean) => void,
    setInstallationStatus: (value: string) => void,
    reloadConfig?: () => Promise<void>
  ) => {
    setIsInstalling(true);
    setInstallationStatus(t('STATUS_INSTALLING_LSFG', 'Installing lsfg-vk...'));

    try {
      const result = await installLsfgVk();
      if (result.success) {
        setIsInstalled(true);
        setInstallationStatus(t('STATUS_INSTALLED_LSFG', 'lsfg-vk installed'));
        showInstallSuccessToast();

        // Reload lsfg config after installation
        if (reloadConfig) {
          await reloadConfig();
        }
      } else {
        // Keep the raw backend error detail; only the fixed prefix is translated.
        setInstallationStatus(`${t('STATUS_INSTALL_FAILED_PREFIX', 'Installation failed:')} ${result.error}`);
        showInstallErrorToast(result.error);
      }
    } catch (error) {
      setInstallationStatus(`${t('STATUS_INSTALL_FAILED_PREFIX', 'Installation failed:')} ${error}`);
      showInstallErrorToast(String(error));
    } finally {
      setIsInstalling(false);
    }
  };

  const handleUninstall = async (
    setIsInstalled: (value: boolean) => void,
    setInstallationStatus: (value: string) => void
  ) => {
    setIsUninstalling(true);
    setInstallationStatus(t('STATUS_UNINSTALLING_LSFG', 'Uninstalling lsfg-vk...'));

    try {
      const result = await uninstallLsfgVk();
      if (result.success) {
        setIsInstalled(false);
        setInstallationStatus(t('STATUS_UNINSTALLED_LSFG', 'lsfg-vk uninstalled successfully!'));
        showUninstallSuccessToast();
      } else {
        // Keep the raw backend error detail; only the fixed prefix is translated.
        setInstallationStatus(`${t('STATUS_UNINSTALL_FAILED_PREFIX', 'Uninstallation failed:')} ${result.error}`);
        showUninstallErrorToast(result.error);
      }
    } catch (error) {
      setInstallationStatus(`${t('STATUS_UNINSTALL_FAILED_PREFIX', 'Uninstallation failed:')} ${error}`);
      showUninstallErrorToast(String(error));
    } finally {
      setIsUninstalling(false);
    }
  };

  return {
    isInstalling,
    isUninstalling,
    handleInstall,
    handleUninstall
  };
}
