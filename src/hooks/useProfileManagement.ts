import { useState, useEffect, useCallback } from "react";
import {
  getProfiles,
  createProfile,
  deleteProfile,
  renameProfile,
  setCurrentProfile,
  updateProfileConfig,
  type ProfilesResult,
  type ProfileResult,
  type ConfigUpdateResult
} from "../api/lsfgApi";
import { ConfigurationData } from "../config/configSchema";
import { showSuccessToast, showErrorToast } from "../utils/toastUtils";
import t from "../i18n/i18n";

export function useProfileManagement() {
  const [profiles, setProfiles] = useState<string[]>([]);
  const [currentProfile, setCurrentProfileState] = useState<string>("decky-lsfg-vk");
  const [isLoading, setIsLoading] = useState(false);

  // Load profiles on hook initialization
  const loadProfiles = useCallback(async () => {
    try {
      const result: ProfilesResult = await getProfiles();
      if (result.success && result.profiles) {
        setProfiles(result.profiles);
        if (result.current_profile) {
          setCurrentProfileState(result.current_profile);
        }
        return result;
      } else {
        console.error("Failed to load profiles:", result.error);
        showErrorToast(t('TOAST_PROFILE_LOAD_FAILED_TITLE', 'Failed to load profiles'), result.error || t('TOAST_UNKNOWN_ERROR', 'Unknown error occurred'));
        return result;
      }
    } catch (error) {
      console.error("Error loading profiles:", error);
      showErrorToast(t('TOAST_PROFILE_LOAD_ERROR_TITLE', 'Error loading profiles'), String(error));
      return { success: false, error: String(error) };
    }
  }, []);

  // Create a new profile
  const handleCreateProfile = useCallback(async (profileName: string, sourceProfile?: string) => {
    setIsLoading(true);
    try {
      const result: ProfileResult = await createProfile(profileName, sourceProfile || currentProfile);
      if (result.success) {
        // Use the normalized name returned from backend (spaces converted to dashes)
        const actualProfileName = result.profile_name || profileName;
        showSuccessToast(t('TOAST_PROFILE_CREATE_SUCCESS_TITLE', 'Profile created'), `${t('TOAST_PROFILE_CREATE_SUCCESS_BODY_PREFIX', 'Created profile:')} ${actualProfileName}`);
        await loadProfiles();
        return result;
      } else {
        console.error("Failed to create profile:", result.error);
        showErrorToast(t('TOAST_PROFILE_CREATE_FAILED_TITLE', 'Failed to create profile'), result.error || t('TOAST_UNKNOWN_ERROR', 'Unknown error occurred'));
        return result;
      }
    } catch (error) {
      console.error("Error creating profile:", error);
      showErrorToast(t('TOAST_PROFILE_CREATE_ERROR_TITLE', 'Error creating profile'), String(error));
      return { success: false, error: String(error) };
    } finally {
      setIsLoading(false);
    }
  }, [currentProfile, loadProfiles]);

  // Delete a profile
  const handleDeleteProfile = useCallback(async (profileName: string) => {
    if (profileName === "decky-lsfg-vk") {
      showErrorToast(t('PROFILE_CANNOT_DELETE_TITLE', 'Cannot delete default profile'), t('PROFILE_CANNOT_DELETE_MSG', 'The default profile cannot be deleted'));
      return { success: false, error: "Cannot delete default profile" };
    }

    setIsLoading(true);
    try {
      const result: ProfileResult = await deleteProfile(profileName);
      if (result.success) {
        showSuccessToast(t('TOAST_PROFILE_DELETE_SUCCESS_TITLE', 'Profile deleted'), `${t('TOAST_PROFILE_DELETE_SUCCESS_BODY_PREFIX', 'Deleted profile:')} ${profileName}`);
        await loadProfiles();
        // If we deleted the current profile, it should have switched to default
        if (currentProfile === profileName) {
          setCurrentProfileState("decky-lsfg-vk");
        }
        return result;
      } else {
        console.error("Failed to delete profile:", result.error);
        showErrorToast(t('TOAST_PROFILE_DELETE_FAILED_TITLE', 'Failed to delete profile'), result.error || t('TOAST_UNKNOWN_ERROR', 'Unknown error occurred'));
        return result;
      }
    } catch (error) {
      console.error("Error deleting profile:", error);
      showErrorToast(t('TOAST_PROFILE_DELETE_ERROR_TITLE', 'Error deleting profile'), String(error));
      return { success: false, error: String(error) };
    } finally {
      setIsLoading(false);
    }
  }, [currentProfile, loadProfiles]);

  // Rename a profile
  const handleRenameProfile = useCallback(async (oldName: string, newName: string) => {
    if (oldName === "decky-lsfg-vk") {
      showErrorToast(t('PROFILE_CANNOT_RENAME_TITLE', 'Cannot rename default profile'), t('PROFILE_CANNOT_RENAME_MSG', 'The default profile cannot be renamed'));
      return { success: false, error: "Cannot rename default profile" };
    }

    setIsLoading(true);
    try {
      const result: ProfileResult = await renameProfile(oldName, newName);
      if (result.success) {
        // Use the normalized name returned from backend (spaces converted to dashes)
        const actualNewName = result.profile_name || newName;
        showSuccessToast(t('TOAST_PROFILE_RENAME_SUCCESS_TITLE', 'Profile renamed'), `${t('TOAST_PROFILE_RENAME_SUCCESS_BODY_PREFIX', 'Renamed profile to:')} ${actualNewName}`);
        await loadProfiles();
        // Update current profile if it was renamed
        if (currentProfile === oldName) {
          setCurrentProfileState(actualNewName);
        }
        return result;
      } else {
        console.error("Failed to rename profile:", result.error);
        showErrorToast(t('TOAST_PROFILE_RENAME_FAILED_TITLE', 'Failed to rename profile'), result.error || t('TOAST_UNKNOWN_ERROR', 'Unknown error occurred'));
        return result;
      }
    } catch (error) {
      console.error("Error renaming profile:", error);
      showErrorToast(t('TOAST_PROFILE_RENAME_ERROR_TITLE', 'Error renaming profile'), String(error));
      return { success: false, error: String(error) };
    } finally {
      setIsLoading(false);
    }
  }, [currentProfile, loadProfiles]);

  // Set the current active profile
  const handleSetCurrentProfile = useCallback(async (profileName: string) => {
    setIsLoading(true);
    try {
      const result: ProfileResult = await setCurrentProfile(profileName);
      if (result.success) {
        setCurrentProfileState(profileName);
        showSuccessToast(t('TOAST_PROFILE_SWITCH_SUCCESS_TITLE', 'Profile switched'), `${t('TOAST_PROFILE_SWITCH_SUCCESS_BODY_PREFIX', 'Switched to profile:')} ${profileName}`);
        return result;
      } else {
        console.error("Failed to switch profile:", result.error);
        showErrorToast(t('TOAST_PROFILE_SWITCH_FAILED_TITLE', 'Failed to switch profile'), result.error || t('TOAST_UNKNOWN_ERROR', 'Unknown error occurred'));
        return result;
      }
    } catch (error) {
      console.error("Error switching profile:", error);
      showErrorToast(t('TOAST_PROFILE_SWITCH_ERROR_TITLE', 'Error switching profile'), String(error));
      return { success: false, error: String(error) };
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Update configuration for a specific profile
  const handleUpdateProfileConfig = useCallback(async (profileName: string, config: ConfigurationData) => {
    setIsLoading(true);
    try {
      const result: ConfigUpdateResult = await updateProfileConfig(profileName, config);
      if (result.success) {
        return result;
      } else {
        console.error("Failed to update profile config:", result.error);
        showErrorToast(t('TOAST_PROFILE_UPDATE_FAILED_TITLE', 'Failed to update profile config'), result.error || t('TOAST_UNKNOWN_ERROR', 'Unknown error occurred'));
        return result;
      }
    } catch (error) {
      console.error("Error updating profile config:", error);
      showErrorToast(t('TOAST_PROFILE_UPDATE_ERROR_TITLE', 'Error updating profile config'), String(error));
      return { success: false, error: String(error) };
    } finally {
      setIsLoading(false);
    }
  }, [currentProfile]);

  // Initialize profiles on mount
  useEffect(() => {
    loadProfiles();
  }, [loadProfiles]);

  return {
    profiles,
    currentProfile,
    isLoading,
    loadProfiles,
    createProfile: handleCreateProfile,
    deleteProfile: handleDeleteProfile,
    renameProfile: handleRenameProfile,
    setCurrentProfile: handleSetCurrentProfile,
    updateProfileConfig: handleUpdateProfileConfig
  };
}
