/**
 * Centralized toast notification utilities
 * Provides consistent success/error messaging patterns
 */

import { toaster } from "@decky/api";
import t from "../i18n/i18n";

export interface ToastOptions {
  title: string;
  body: string;
}

/**
 * Show a success toast notification
 */
export function showSuccessToast(title: string, body: string): void {
  toaster.toast({
    title,
    body
  });
}

/**
 * Show an error toast notification
 */
export function showErrorToast(title: string, body: string): void {
  toaster.toast({
    title,
    body
  });
}

/**
 * Show a toast with dynamic error message
 */
export function showErrorToastWithMessage(title: string, error: unknown): void {
  const errorMessage = error instanceof Error ? error.message : String(error);
  showErrorToast(title, errorMessage);
}

/**
 * Show installation success toast
 */
export function showInstallSuccessToast(): void {
  showSuccessToast(
    t('TOAST_INSTALL_SUCCESS_TITLE', 'Installation Complete'),
    t('TOAST_INSTALL_SUCCESS_BODY', 'lsfg-vk has been installed successfully')
  );
}

/**
 * Show installation error toast. The supplied backend error is shown verbatim;
 * only the fallback body is translated.
 */
export function showInstallErrorToast(error?: string): void {
  showErrorToast(
    t('TOAST_INSTALL_ERROR_TITLE', 'Installation Failed'),
    error || t('TOAST_UNKNOWN_ERROR', 'Unknown error occurred')
  );
}

/**
 * Show uninstallation success toast
 */
export function showUninstallSuccessToast(): void {
  showSuccessToast(
    t('TOAST_UNINSTALL_SUCCESS_TITLE', 'Uninstallation Complete'),
    t('TOAST_UNINSTALL_SUCCESS_BODY', 'lsfg-vk has been uninstalled successfully')
  );
}

/**
 * Show uninstallation error toast. The supplied backend error is shown verbatim;
 * only the fallback body is translated.
 */
export function showUninstallErrorToast(error?: string): void {
  showErrorToast(
    t('TOAST_UNINSTALL_ERROR_TITLE', 'Uninstallation Failed'),
    error || t('TOAST_UNKNOWN_ERROR', 'Unknown error occurred')
  );
}

/**
 * Show configuration update error toast. The supplied backend error is shown
 * verbatim; only the fallback body is translated.
 */
export function showConfigUpdateErrorToast(error?: string): void {
  showErrorToast(
    t('TOAST_CONFIG_UPDATE_ERROR_TITLE', 'Update Failed'),
    error || t('TOAST_CONFIG_UPDATE_ERROR_BODY', 'Failed to update configuration')
  );
}

/**
 * Show clipboard success toast
 */
export function showClipboardSuccessToast(): void {
  showSuccessToast(
    t('TOAST_CLIPBOARD_SUCCESS_TITLE', 'Copied to Clipboard!'),
    t('TOAST_CLIPBOARD_SUCCESS_BODY', 'Launch option ready to paste')
  );
}

/**
 * Show clipboard error toast
 */
export function showClipboardErrorToast(): void {
  showErrorToast(
    t('TOAST_CLIPBOARD_ERROR_TITLE', 'Copy Failed'),
    t('TOAST_CLIPBOARD_ERROR_BODY', 'Unable to copy to clipboard')
  );
}
