import { useState } from 'react';

/**
 * Hook for managing a confirmation dialog with pending actions
 *
 * @example
 * ```typescript
 * const confirmDialog = useConfirmDialog();
 *
 * <Button onClick={() => confirmDialog.confirm(() => deleteBot(id))}>
 *   Delete
 * </Button>
 *
 * <AlertDialog open={confirmDialog.isOpen} onOpenChange={confirmDialog.handleCancel}>
 *   <AlertDialogContent>
 *     <AlertDialogTitle>Are you sure?</AlertDialogTitle>
 *     <AlertDialogFooter>
 *       <AlertDialogCancel onClick={confirmDialog.handleCancel}>Cancel</AlertDialogCancel>
 *       <AlertDialogAction onClick={confirmDialog.handleConfirm}>Confirm</AlertDialogAction>
 *     </AlertDialogFooter>
 *   </AlertDialogContent>
 * </AlertDialog>
 * ```
 */
export function useConfirmDialog() {
  const [isOpen, setIsOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);

  const confirm = (action: () => void) => {
    setPendingAction(() => action);
    setIsOpen(true);
  };

  const handleConfirm = () => {
    pendingAction?.();
    setIsOpen(false);
    setPendingAction(null);
  };

  const handleCancel = () => {
    setIsOpen(false);
    setPendingAction(null);
  };

  return {
    isOpen,
    confirm,
    handleConfirm,
    handleCancel,
  };
}
