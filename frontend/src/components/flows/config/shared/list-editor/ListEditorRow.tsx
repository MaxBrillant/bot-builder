import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ListEditorRowProps {
  // Either a single summary or array of columns
  summary?: ReactNode;
  columns?: ReactNode[];
  prefix?: ReactNode;
  isActive: boolean;
  hasError: boolean;
  onClick: () => void;
  onDelete: () => void;
}

export function ListEditorRow({
  summary,
  columns,
  prefix,
  isActive,
  hasError,
  onClick,
  onDelete,
}: ListEditorRowProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md",
        "border transition-colors",
        isActive
          ? "border-primary bg-accent/50"
          : "border-border bg-card hover:bg-accent/50",
        hasError && !isActive && "border-destructive/50"
      )}
    >
      <button
        type="button"
        onClick={onClick}
        className="flex-1 flex items-center gap-2 px-3 py-2 text-left text-sm min-w-0"
      >
        {prefix && (
          <span className="text-muted-foreground shrink-0">{prefix}</span>
        )}
        {columns ? (
          // Render as aligned columns
          columns.map((col, i) => (
            <span key={i} className="flex-1 min-w-0 truncate">
              {col}
            </span>
          ))
        ) : (
          // Render as single summary
          <span className="flex-1 min-w-0 truncate">{summary}</span>
        )}
      </button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="h-9 w-9 p-0 shrink-0 text-muted-foreground hover:text-destructive"
      >
        <X className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
