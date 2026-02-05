import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Move, MoveHorizontal } from "lucide-react";

interface ShortcutGroup {
  title: string;
  shortcuts: { keys: string | React.ReactNode; description: string }[];
}

const shortcutGroups: ShortcutGroup[] = [
  {
    title: "Insert Nodes",
    shortcuts: [
      { keys: "P", description: "Prompt node" },
      { keys: "M", description: "Menu node" },
      { keys: "T", description: "Message node" },
      { keys: "A", description: "API Action node" },
      { keys: "L", description: "Logic node" },
      { keys: "N", description: "Node palette" },
    ],
  },
  {
    title: "Node Actions",
    shortcuts: [
      { keys: <Move className="w-3.5 h-3.5" />, description: "Navigate nodes" },
      { keys: <span className="flex items-center gap-2"><span>Ctrl +</span><Move className="w-3.5 h-3.5" /></span>, description: "Move 10px" },
      { keys: <span className="flex items-center gap-2"><span>Shift +</span><Move className="w-3.5 h-3.5" /></span>, description: "Move 100px" },
      { keys: <span className="flex items-center gap-2"><span>Ctrl + Shift +</span><MoveHorizontal className="w-3.5 h-3.5" /></span>, description: "Reorder in flow" },
      { keys: "Enter", description: "Edit node" },
      { keys: "Delete", description: "Delete node" },
      { keys: "Escape", description: "Deselect node" },
    ],
  },
  {
    title: "Flows",
    shortcuts: [
      { keys: "Ctrl + [", description: "Previous flow" },
      { keys: "Ctrl + ]", description: "Next flow" },
      { keys: "Ctrl + 1-9", description: "Jump to flow" },
      { keys: "Ctrl + Alt + N", description: "New flow" },
      { keys: "Shift + Delete", description: "Delete flow" },
    ],
  },
  {
    title: "Canvas",
    shortcuts: [
      { keys: "+ / -", description: "Zoom in/out" },
      { keys: "Space + Drag", description: "Pan canvas" },
    ],
  },
  {
    title: "Other",
    shortcuts: [
      { keys: "Ctrl + ,", description: "Settings" },
      { keys: "Ctrl + Shift + T", description: "Test chat" },
      { keys: "?", description: "Show shortcuts" },
    ],
  },
];

interface KeyboardShortcutsHelpDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function KeyboardShortcutsHelpDialog({
  open,
  onOpenChange,
}: KeyboardShortcutsHelpDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-4">
          {shortcutGroups.map((group) => (
            <div key={group.title} className="space-y-2">
              <h3 className="font-semibold text-sm text-foreground uppercase tracking-wide">
                {group.title}
              </h3>
              <div className="space-y-2">
                {group.shortcuts.map((shortcut, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between text-sm py-1"
                  >
                    <span className="text-muted-foreground">{shortcut.description}</span>
                    <kbd className="px-2 py-1 text-xs font-semibold text-foreground bg-muted border border-border rounded flex items-center justify-center">
                      {shortcut.keys}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
