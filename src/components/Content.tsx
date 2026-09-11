import { useEffect } from "react";
import { PanelSection, showModal, ButtonItem, PanelSectionRow } from "@decky/ui";
import { useInstallationStatus, useDllDetection, useLsfgConfig } from "../hooks/useLsfgHooks";
import { useProfileManagement } from "../hooks/useProfileManagement";
import { useInstallationActions } from "../hooks/useInstallationActions";
import { StatusDisplay } from "./StatusDisplay";
import { InstallationButton } from "./InstallationButton";
import { ConfigurationSection } from "./ConfigurationSection";
import { ProfileManagement } from "./ProfileManagement";
import { UsageInstructions } from "./UsageInstructions";
import { SmartClipboardButton } from "./SmartClipboardButton";
import { FpsMultiplierControl } from "./FpsMultiplierControl";
import { NerdStuffModal } from "./NerdStuffModal";
import { ConfigurationData } from "../config/configSchema";
import t from '../i18n/i18n';

export function Content() {
  const {
    isInstalled,
    installationStatus,
    setIsInstalled,
    setInstallationStatus
  } = useInstallationStatus();

  const { dllDetected, dllDetectionStatus } = useDllDetection();

  const {
    config,
    runtimeV2,
    configError,
    configLoaded,
    loadLsfgConfig,
    updateField
  } = useLsfgConfig();

  const {
    currentProfile,
    updateProfileConfig,
    loadProfiles
  } = useProfileManagement();

  const { isInstalling, isUninstalling, handleInstall, handleUninstall } = useInstallationActions();

  useEffect(() => {
    if (isInstalled) {
      loadLsfgConfig();
    }
  }, [isInstalled, loadLsfgConfig]);

  const handleConfigChange = async (fieldName: keyof ConfigurationData, value: boolean | number | string) => {
    if (currentProfile) {
      const newConfig = { ...config, [fieldName]: value };
      const result = await updateProfileConfig(currentProfile, newConfig);
      if (result.success) {
        await loadLsfgConfig();
      }
    } else {
      await updateField(fieldName, value);
    }
  };

  const onInstall = () => {
    handleInstall(setIsInstalled, setInstallationStatus, loadLsfgConfig);
  };

  const onUninstall = () => {
    handleUninstall(setIsInstalled, setInstallationStatus);
  };

  const handleShowNerdStuff = () => {
    showModal(<NerdStuffModal />);
  };

  const handleRetryConfig = () => {
    loadLsfgConfig();
  };

  return (
    <PanelSection>
      {!isInstalled && (
        <>
          <InstallationButton
            isInstalled={isInstalled}
            isInstalling={isInstalling}
            isUninstalling={isUninstalling}
            onInstall={onInstall}
            onUninstall={onUninstall}
          />

          <StatusDisplay
            dllDetected={dllDetected}
            dllDetectionStatus={dllDetectionStatus}
            isInstalled={isInstalled}
            installationStatus={installationStatus}
          />
        </>
      )}

      {isInstalled && configError && (
        <PanelSectionRow>
          <div
            style={{
              color: "#F44336",
              fontSize: "12px",
              lineHeight: "1.4",
              marginBottom: "6px"
            }}
          >
            {t('CONFIG_LOAD_FAILED_PREFIX', 'Configuration error:')} {configError}
          </div>
        </PanelSectionRow>
      )}

      {isInstalled && configError && (
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={handleRetryConfig}
          >
            {t('CONFIG_RETRY', 'Retry reading configuration')}
          </ButtonItem>
        </PanelSectionRow>
      )}

      {/* Editable controls are withheld until a configuration read succeeds;
          the retry button above and install/uninstall below stay available. */}
      {isInstalled && configLoaded && !configError && (
        <>
          <PanelSectionRow>
            <div
              style={{
                fontSize: "14px",
                fontWeight: "bold",
                marginTop: "8px",
                marginBottom: "6px",
                borderBottom: "1px solid rgba(255, 255, 255, 0.2)",
                paddingBottom: "3px",
                color: "white"
              }}
            >
              {t('CONTENT_FPS_MULTIPLIER', 'FPS Multiplier')}
            </div>
          </PanelSectionRow>

          <FpsMultiplierControl
            config={config}
            onConfigChange={handleConfigChange}
          />

          {runtimeV2 && (
            <PanelSectionRow>
              <div
                style={{
                  fontSize: "11px",
                  lineHeight: "1.3",
                  opacity: 0.7,
                  textAlign: "center"
                }}
              >
                {t('CONTENT_RUNTIME_V2', 'Runtime: lsfg-vk 2.0')}
              </div>
            </PanelSectionRow>
          )}
        </>
      )}

      {isInstalled && configLoaded && !configError && (
        <ProfileManagement
          currentProfile={currentProfile}
          onProfileChange={async () => {
            await loadProfiles();
            await loadLsfgConfig();
          }}
        />
      )}

      {isInstalled && configLoaded && !configError && (
        <ConfigurationSection
          config={config}
          onConfigChange={handleConfigChange}
        />
      )}

      {isInstalled && configLoaded && !configError && <SmartClipboardButton />}

      <UsageInstructions />

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={handleShowNerdStuff}
        >
          {t('CONTENT_NERD_STUFF', 'Nerd Stuff')}
        </ButtonItem>
      </PanelSectionRow>

      {/* DeckyFG (fgmod) and the Flatpak runtime extensions are 1.x-only and
          have no place in the 2.0 UI, so they are removed entirely. */}

      {isInstalled && (
        <>
          <StatusDisplay
            dllDetected={dllDetected}
            dllDetectionStatus={dllDetectionStatus}
            isInstalled={isInstalled}
            installationStatus={installationStatus}
          />

          <InstallationButton
            isInstalled={isInstalled}
            isInstalling={isInstalling}
            isUninstalling={isUninstalling}
            onInstall={onInstall}
            onUninstall={onUninstall}
          />
        </>
      )}
    </PanelSection>
  );
}
