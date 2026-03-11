import { useState, useCallback } from 'react';

/**
 * Dialog types supported by the application
 */
export type DialogType = 'createFlow' | 'botSettings' | 'chatSimulator' | 'unsavedWarning' | 'exportFlow';

/**
 * Dialog state management hook
 * Centralizes all dialog open/close states and provides a clean API
 */
export function useDialogState() {
  const [createFlowDialogOpen, setCreateFlowDialogOpen] = useState(false);
  const [botSettingsDialogOpen, setBotSettingsDialogOpen] = useState(false);
  const [chatSimulatorOpen, setChatSimulatorOpen] = useState(false);
  const [showUnsavedWarning, setShowUnsavedWarning] = useState(false);
  const [exportFlowDialogOpen, setExportFlowDialogOpen] = useState(false);

  /**
   * Open a specific dialog by type
   */
  const openDialog = useCallback((dialog: DialogType) => {
    switch (dialog) {
      case 'createFlow':
        setCreateFlowDialogOpen(true);
        break;
      case 'botSettings':
        setBotSettingsDialogOpen(true);
        break;
      case 'chatSimulator':
        setChatSimulatorOpen(true);
        break;
      case 'unsavedWarning':
        setShowUnsavedWarning(true);
        break;
      case 'exportFlow':
        setExportFlowDialogOpen(true);
        break;
    }
  }, []);

  /**
   * Close a specific dialog by type
   */
  const closeDialog = useCallback((dialog: DialogType) => {
    switch (dialog) {
      case 'createFlow':
        setCreateFlowDialogOpen(false);
        break;
      case 'botSettings':
        setBotSettingsDialogOpen(false);
        break;
      case 'chatSimulator':
        setChatSimulatorOpen(false);
        break;
      case 'unsavedWarning':
        setShowUnsavedWarning(false);
        break;
      case 'exportFlow':
        setExportFlowDialogOpen(false);
        break;
    }
  }, []);

  /**
   * Check if a specific dialog is open
   */
  const isDialogOpen = useCallback((dialog: DialogType): boolean => {
    switch (dialog) {
      case 'createFlow':
        return createFlowDialogOpen;
      case 'botSettings':
        return botSettingsDialogOpen;
      case 'chatSimulator':
        return chatSimulatorOpen;
      case 'unsavedWarning':
        return showUnsavedWarning;
      case 'exportFlow':
        return exportFlowDialogOpen;
      default:
        return false;
    }
  }, [createFlowDialogOpen, botSettingsDialogOpen, chatSimulatorOpen, showUnsavedWarning, exportFlowDialogOpen]);

  return {
    // Individual dialog states (for backward compatibility)
    createFlowDialogOpen,
    setCreateFlowDialogOpen,
    botSettingsDialogOpen,
    setBotSettingsDialogOpen,
    chatSimulatorOpen,
    setChatSimulatorOpen,
    showUnsavedWarning,
    setShowUnsavedWarning,
    exportFlowDialogOpen,
    setExportFlowDialogOpen,

    // New unified API
    openDialog,
    closeDialog,
    isDialogOpen,
  };
}
