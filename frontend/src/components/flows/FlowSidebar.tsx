import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type { Flow } from "@/lib/types";
import { useState } from "react";

interface FlowSidebarProps {
  flows: Flow[];
  activeIndex: number;
  onSelectFlow: (index: number) => void;
  onCreateFlow: () => void;
  onDeleteFlow: (index: number) => void;
  botId?: string;
  checkUnsavedChanges?: (action: () => void) => () => void;
}

export default function FlowSidebar({
  flows,
  activeIndex,
  onSelectFlow,
  onCreateFlow,
  onDeleteFlow,
  checkUnsavedChanges,
}: FlowSidebarProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [flowToDelete, setFlowToDelete] = useState<number | null>(null);

  const handleDeleteClick = (index: number, e: React.MouseEvent) => {
    e.stopPropagation();

    // Check for unsaved changes before opening delete confirmation
    if (checkUnsavedChanges) {
      checkUnsavedChanges(() => {
        setFlowToDelete(index);
        setDeleteDialogOpen(true);
      })();
    } else {
      setFlowToDelete(index);
      setDeleteDialogOpen(true);
    }
  };

  // Wrap handlers with unsaved changes check if provided
  const handleSelectFlow = (index: number) => {
    if (checkUnsavedChanges) {
      checkUnsavedChanges(() => onSelectFlow(index))();
    } else {
      onSelectFlow(index);
    }
  };

  const handleCreateFlow = checkUnsavedChanges
    ? checkUnsavedChanges(onCreateFlow)
    : onCreateFlow;

  const handleConfirmDelete = () => {
    if (flowToDelete !== null) {
      onDeleteFlow(flowToDelete);
      setFlowToDelete(null);
    }
    setDeleteDialogOpen(false);
  };

  const handleCancelDelete = () => {
    setFlowToDelete(null);
    setDeleteDialogOpen(false);
  };

  return (
    <>
      <div className="w-40 bg-background border-r flex flex-col h-full">
        {/* Sidebar Header */}
        <div className="w-full flex flex-row justify-between items-center p-4">
          <h2 className="text-sm font-semibold text-foreground">Flows</h2>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleCreateFlow}
            className="w-8 h-8 p-0 hover:bg-muted"
            title="Create new flow"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>

        {/* Flows List */}
        <div className="flex-1 overflow-y-auto">
          {flows.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No flows yet. Create your first flow to get started.
            </div>
          ) : (
            <div className="p-2">
              {flows.map((flow, index) => (
                <button
                  key={index}
                  onClick={() => handleSelectFlow(index)}
                  className={`w-full text-left px-3 py-2 rounded-md mb-1 flex items-center justify-between group transition-colors ${
                    activeIndex === index
                      ? "bg-accent text-primary font-medium"
                      : "hover:bg-muted text-foreground"
                  }`}
                >
                  <span className="truncate flex-1 text-sm">{flow.name}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => handleDeleteClick(index, e)}
                    className="ml-2 h-6 w-6 hover:bg-destructive hover:text-destructive-foreground opacity-0 group-hover:opacity-100"
                    title="Delete flow"
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Flow</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the flow "
              {flowToDelete !== null && flows[flowToDelete]?.name}"? This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancelDelete}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
