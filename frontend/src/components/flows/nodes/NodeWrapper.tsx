import { ChevronLeft, ChevronRight, Trash2 } from "lucide-react";
import type { NodeType } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";

interface NodeWrapperProps {
  children: React.ReactNode;
  canMoveLeft?: boolean;
  canMoveRight?: boolean;
  onMoveLeft?: () => void;
  onMoveRight?: () => void;
  isSelected?: boolean;
  onNodeClick?: () => void;
  data?: {
    nodeType?: NodeType;
    onDelete?: () => void;
    name?: string;
  };
}

export default function NodeWrapper({
  children,
  canMoveLeft = false,
  canMoveRight = false,
  onMoveLeft,
  onMoveRight,
  isSelected = false,
  onNodeClick,
  data,
}: NodeWrapperProps) {

  const canDelete = data?.nodeType !== "END" && data?.onDelete;
  const hasContextMenu = canDelete || canMoveLeft || canMoveRight;

  const handleDeleteClick = () => {
    data?.onDelete?.();
  };

  const nodeContent = (
    <div
      className={cn(
        "relative cursor-pointer transition-all",
        isSelected && "ring-4 ring-foreground rounded-md"
      )}
      onClick={(e) => {
        e.stopPropagation();
        onNodeClick?.();
      }}
    >
      {children}
    </div>
  );

  return (
    <>
      {hasContextMenu ? (
        <ContextMenu>
          <ContextMenuTrigger asChild>{nodeContent}</ContextMenuTrigger>
          <ContextMenuContent>
            {canMoveLeft && onMoveLeft && (
              <ContextMenuItem
                className="cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  onMoveLeft();
                }}
              >
                <ChevronLeft className="mr-2 h-4 w-4" />
                Move Left
              </ContextMenuItem>
            )}
            {canMoveRight && onMoveRight && (
              <ContextMenuItem
                className="cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  onMoveRight();
                }}
              >
                <ChevronRight className="mr-2 h-4 w-4" />
                Move Right
              </ContextMenuItem>
            )}
            {(canMoveLeft || canMoveRight) && canDelete && <ContextMenuSeparator />}
            {canDelete && (
              <ContextMenuItem
                className="text-destructive focus:text-destructive cursor-pointer"
                onClick={handleDeleteClick}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </ContextMenuItem>
            )}
          </ContextMenuContent>
        </ContextMenu>
      ) : (
        nodeContent
      )}
    </>
  );
}
