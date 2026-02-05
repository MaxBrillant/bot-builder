import { Move, MoveHorizontal } from "lucide-react";
import { Kbd } from "@/components/ui/kbd";

interface ContextualShortcutsHintProps {
  hasNodeSelected: boolean;
  onShowAllShortcuts: () => void;
}

export function ContextualShortcutsHint({
  hasNodeSelected,
  onShowAllShortcuts,
}: ContextualShortcutsHintProps) {

  return (
    <div
      onClick={onShowAllShortcuts}
      className="absolute bottom-4 left-1/2 -translate-x-1/2 z-5
                 text-muted-foreground text-xs
                 cursor-pointer
                 flex items-center gap-3 select-none
                 hover:text-foreground transition-colors"
    >
      {hasNodeSelected ? (
        <>
          <span className="flex items-center gap-2">
            <Kbd>N</Kbd>
            <span>Add</span>
          </span>
          <span className="text-muted-foreground">•</span>
          <span className="flex items-center gap-2">
            <Kbd className="justify-center">
              <Move className="w-3 h-3" />
            </Kbd>
            <span>Navigate</span>
          </span>
          <span className="text-muted-foreground">•</span>
          <span className="flex items-center gap-2">
            <Kbd className="gap-2">
              <span>Shift+</span>
              <Move className="w-3 h-3" />
            </Kbd>
            <span>Move</span>
          </span>
          <span className="text-muted-foreground">•</span>
          <span className="flex items-center gap-2">
            <Kbd className="gap-2">
              <span>Ctrl+Shift+</span>
              <MoveHorizontal className="w-3 h-3" />
            </Kbd>
            <span>Reorder</span>
          </span>
          <span className="text-muted-foreground">•</span>
          <span className="flex items-center gap-2">
            <Kbd>?</Kbd>
            <span>All</span>
          </span>
        </>
      ) : (
        <>
          <span className="flex items-center gap-2">
            <Kbd className="justify-center">
              <Move className="w-3 h-3" />
            </Kbd>
            <span>Select</span>
          </span>
          <span className="text-muted-foreground">•</span>
          <span className="flex items-center gap-2">
            <Kbd>?</Kbd>
            <span>All</span>
          </span>
        </>
      )}
    </div>
  );
}
