import { useState, useEffect, useCallback } from "react";
import {
  checkLsfgVkInstalled,
  checkLosslessScalingDll,
  getLsfgConfig,
  updateLsfgConfigFromObject,
  type ConfigUpdateResult
} from "../api/lsfgApi";
import { ConfigurationData, getDefaults } from "../config/configSchema";
import { showConfigUpdateErrorToast } from "../utils/toastUtils";
import t from "../i18n/i18n";

export function useInstallationStatus() {
  const [isInstalled, setIsInstalled] = useState<boolean>(false);
  const [installationStatus, setInstallationStatus] = useState<string>("");

  const checkInstallation = async () => {
    try {
      const status = await checkLsfgVkInstalled();
      setIsInstalled(status.installed);
      if (status.installed) {
        setInstallationStatus(t('STATUS_LSFG_INSTALLED', 'lsfg-vk Installed'));
      } else if (status.error) {
        setInstallationStatus(`${t('STATUS_INSTALL_FAILED_PREFIX', 'Installation failed:')} ${status.error}`);
      } else {
        setInstallationStatus(t('STATUS_LSFG_NOT_INSTALLED', 'lsfg-vk Not Installed'));
      }
      return status.installed;
    } catch (error) {
      setInstallationStatus(t('STATUS_LSFG_NOT_INSTALLED', 'lsfg-vk Not Installed'));
      return false;
    }
  };

  useEffect(() => {
    checkInstallation();
  }, []);

  return {
    isInstalled,
    installationStatus,
    setIsInstalled,
    setInstallationStatus,
    checkInstallation
  };
}

export function useDllDetection() {
  const [dllDetected, setDllDetected] = useState<boolean>(false);
  const [dllDetectionStatus, setDllDetectionStatus] = useState<string>("");

  const checkDllDetection = async () => {
    try {
      const result = await checkLosslessScalingDll();
      setDllDetected(result.detected);
      if (result.detected) {
        setDllDetectionStatus(t('STATUS_LOSSLESS_INSTALLED', 'Lossless Scaling Installed'));
      } else {
        setDllDetectionStatus(t('STATUS_LOSSLESS_NOT_INSTALLED', 'Lossless Scaling Not Installed'));
      }
    } catch (error) {
      setDllDetectionStatus(t('STATUS_LOSSLESS_NOT_INSTALLED', 'Lossless Scaling Not Installed'));
    }
  };

  useEffect(() => {
    checkDllDetection();
  }, []);

  return {
    dllDetected,
    dllDetectionStatus
  };
}

export function useLsfgConfig() {
  const [config, setConfig] = useState<ConfigurationData>(() => getDefaults());
  const [runtimeV2, setRuntimeV2] = useState<boolean>(false);
  // When the config cannot be read, the UI must show the error and withhold
  // the editable controls instead of silently presenting default sliders.
  // configLoaded stays false until the first successful read so the initial
  // defaults never flash as editable state.
  const [configError, setConfigError] = useState<string | null>(null);
  const [configLoaded, setConfigLoaded] = useState<boolean>(false);

  const loadLsfgConfig = useCallback(async () => {
    try {
      const result = await getLsfgConfig();
      setRuntimeV2(result.runtime_v2 === true);
      if (result.success && result.config) {
        setConfig(result.config);
        setConfigError(null);
        setConfigLoaded(true);
      } else {
        setConfigError(result.error || t('CONFIG_LOAD_FAILED', 'Failed to read the lsfg-vk configuration'));
        setConfigLoaded(false);
      }
    } catch (error) {
      console.error("Error loading lsfg config:", error);
      setRuntimeV2(false);
      setConfigError(String(error));
      setConfigLoaded(false);
    }
  }, []);

  const updateConfig = useCallback(async (newConfig: ConfigurationData): Promise<ConfigUpdateResult> => {
    try {
      const result = await updateLsfgConfigFromObject(newConfig);
      if (result.success) {
        setConfig(newConfig);
      } else {
        showConfigUpdateErrorToast(result.error);
      }
      return result;
    } catch (error) {
      showConfigUpdateErrorToast(String(error));
      return { success: false, error: String(error) };
    }
  }, []);

  const updateField = useCallback(async (fieldName: keyof ConfigurationData, value: boolean | number | string): Promise<ConfigUpdateResult> => {
    const newConfig = { ...config, [fieldName]: value };
    return updateConfig(newConfig);
  }, [config, updateConfig]);

  useEffect(() => {
    loadLsfgConfig();
  }, []);

  return {
    config,
    runtimeV2,
    configError,
    configLoaded,
    setConfig,
    loadLsfgConfig,
    updateConfig,
    updateField
  };
}
