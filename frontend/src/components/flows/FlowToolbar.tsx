import { ArrowLeft, Settings, Save, Loader2, Undo2, Redo2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UserDropdown } from "@/components/auth/UserDropdown";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useNavigate } from "react-router-dom";

interface FlowToolbarProps {
  botName?: string;
  onBotSettings?: () => void;
  onSaveFlow?: () => void;
  hasUnsavedChanges?: boolean;
  isSaving?: boolean;
  checkUnsavedChanges?: (action: () => void) => () => void;
  onBeforeLogout?: () => Promise<boolean>;
  onExportFlow?: () => void;
  hasValidationErrors?: boolean;
  canUndo?: boolean;
  canRedo?: boolean;
  onUndo?: () => void;
  onRedo?: () => void;
}

export default function FlowToolbar({
  botName = "Untitled Bot",
  onBotSettings,
  onSaveFlow,
  hasUnsavedChanges = false,
  isSaving = false,
  checkUnsavedChanges,
  onBeforeLogout,
  onExportFlow,
  hasValidationErrors = false,
  canUndo = false,
  canRedo = false,
  onUndo,
  onRedo,
}: FlowToolbarProps) {
  const navigate = useNavigate();

  const handleBackToBots = checkUnsavedChanges
    ? checkUnsavedChanges(() => navigate("/bots"))
    : () => navigate("/bots");

  return (
    <div className="bg-background border-b p-4 flex justify-between items-center">
      <div className="flex items-center gap-4 min-w-0 flex-1">
        <Button
          variant="link"
          size="sm"
          onClick={handleBackToBots}
          className="gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Bots
        </Button>
        <h2 className="text-lg font-semibold whitespace-nowrap truncate min-w-0">{botName}</h2>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={onUndo}
          disabled={!canUndo}
          title="Undo (Ctrl+Z)"
          className="h-8 w-8"
        >
          <Undo2 className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={onRedo}
          disabled={!canRedo}
          title="Redo (Ctrl+Y)"
          className="h-8 w-8"
        >
          <Redo2 className="w-4 h-4" />
        </Button>
        <Button
          variant={hasUnsavedChanges ? "default" : "outline"}
          size="sm"
          onClick={onSaveFlow}
          disabled={!hasUnsavedChanges || isSaving || !onSaveFlow}
          className="gap-2"
          title={hasUnsavedChanges ? "Save all changes (Ctrl+S)" : "No changes to save"}
        >
          {isSaving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Save
            </>
          )}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={onExportFlow}
          disabled={!onExportFlow || hasValidationErrors}
          className="gap-2"
          title={hasValidationErrors ? "Fix validation errors before exporting" : "Export current flow as JSON"}
        >
          <Upload className="w-4 h-4" />
          Export
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={onBotSettings}
          title="Bot Settings (Ctrl+,)"
          className="h-9 w-9 p-0"
        >
          <Settings className="h-4 w-4" />
        </Button>
        <ThemeToggle />
        <UserDropdown onBeforeLogout={onBeforeLogout} />
      </div>
    </div>
  );
}
