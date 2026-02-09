import { ArrowLeft, Settings, MessageCircle, Save, Loader2, Undo2, Redo2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UserDropdown } from "@/components/auth/UserDropdown";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useNavigate } from "react-router-dom";

interface FlowToolbarProps {
  botName?: string;
  onBotSettings?: () => void;
  onTestChat?: () => void;
  onSaveFlow?: () => void;
  hasUnsavedChanges?: boolean;
  isSaving?: boolean;
  checkUnsavedChanges?: (action: () => void) => () => void;
  onBeforeLogout?: () => Promise<boolean>;
  canUndo?: boolean;
  canRedo?: boolean;
  onUndo?: () => void;
  onRedo?: () => void;
}

export default function FlowToolbar({
  botName = "Untitled Bot",
  onBotSettings,
  onTestChat,
  onSaveFlow,
  hasUnsavedChanges = false,
  isSaving = false,
  checkUnsavedChanges,
  onBeforeLogout,
  canUndo = false,
  canRedo = false,
  onUndo,
  onRedo,
}: FlowToolbarProps) {
  const navigate = useNavigate();

  // Wrap handlers with unsaved changes check if provided
  const handleBackToBots = checkUnsavedChanges
    ? checkUnsavedChanges(() => navigate("/bots"))
    : () => navigate("/bots");

  // Test Chat and Bot Settings don't need unsaved changes checks
  // since they open non-destructive dialogs that can be closed
  const handleTestChat = onTestChat;
  const handleBotSettings = onBotSettings;

  return (
    <div className="bg-background border-b p-4 flex justify-between items-center">
      <div className="flex items-center gap-4">
        <Button
          variant="link"
          size="sm"
          onClick={handleBackToBots}
          className="gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Bots
        </Button>
        <h2 className="text-lg font-semibold">{botName}</h2>
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
              Save Flow
            </>
          )}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleTestChat}
          className="gap-2"
          title="Test your bot in a chat simulator"
        >
          <MessageCircle className="w-4 h-4" />
          Test Chat
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleBotSettings}
          className="gap-2"
          title="Bot Settings"
        >
          <Settings className="w-4 h-4" />
          Bot Settings
        </Button>
        <ThemeToggle />
        <UserDropdown onBeforeLogout={onBeforeLogout} />
      </div>
    </div>
  );
}
