import { memo } from "react";
import { List } from "lucide-react";
import NodeWrapper from "./NodeWrapper";
import NodeHandles from "./NodeHandles";
import NodeTypeSelector from "../NodeTypeSelector";
import type { NodeType, FlowNode } from "@/lib/types";

// Type aliases for reactflow (v11 export issues)
type NodeProps<T = any> = { data: T; id: string; selected?: boolean };

interface MenuNodeData {
  name?: string;
  nodeId?: string;
  flowNode?: FlowNode;
  allNodes?: Record<string, FlowNode>;
  config?: {
    source_type?: "STATIC" | "DYNAMIC";
    static_options?: Array<{ id: string; text: string }>;
    text?: string;
  };
  onInsertAfter?: (nodeType: NodeType, condition?: string) => void;
  parentNode?: any;
  canMoveLeft?: boolean;
  canMoveRight?: boolean;
  onMoveLeft?: () => void;
  onMoveRight?: () => void;
  isSelected?: boolean;
  onNodeClick?: () => void;
  openSelector?: boolean;
  onSelectorOpenChange?: (open: boolean) => void;
  preSelectedType?: NodeType;
  availableVariables?: string[];
  outputHandleIds?: string[];
}

function MenuNode({ data, selected }: NodeProps<MenuNodeData>) {
  const name = data?.name || "Menu";
  const nodeId = data?.nodeId || "";
  const sourceType = data?.config?.source_type || "STATIC";
  const optionsCount = data?.config?.static_options?.length || 0;
  const text = data?.config?.text || "Select an option";
  const truncatedText = text.length > 30 ? text.substring(0, 30) + "..." : text;
  const displayText =
    sourceType === "DYNAMIC"
      ? "Dynamic menu"
      : `${optionsCount} option${optionsCount !== 1 ? "s" : ""}`;

  return (
    <NodeWrapper
      canMoveLeft={data?.canMoveLeft}
      canMoveRight={data?.canMoveRight}
      onMoveLeft={data?.onMoveLeft}
      onMoveRight={data?.onMoveRight}
      isSelected={data?.isSelected}
      onNodeClick={data?.onNodeClick}
      data={data}
    >
      {data?.openSelector && (
        <NodeTypeSelector
          open={data.openSelector}
          onOpenChange={data?.onSelectorOpenChange || (() => {})}
          onSelectType={(type, condition) => data?.onInsertAfter?.(type, condition)}
          parentNode={data?.flowNode}
          preSelectedType={data?.preSelectedType}
          availableVariables={data?.availableVariables}
        >
          <div style={{ position: 'absolute', width: 0, height: 0, opacity: 0, pointerEvents: 'none' }} />
        </NodeTypeSelector>
      )}

      <div
        className={`bg-card rounded-md border-2 border-border hover:border-node-menu/50 w-[200px] h-[80px] transition-all cursor-pointer hover:shadow-lg`}
      >
        {/* New handle system: single left input + dynamic outputs */}
        {data?.flowNode && data?.allNodes && (
          <NodeHandles node={data.flowNode} allNodes={data.allNodes} outputHandleIds={data.outputHandleIds} />
        )}

        <div className="h-full flex items-center gap-3 p-4">
          {/* Large icon on the left */}
          <div className="flex-shrink-0">
            <List className="w-8 h-8 text-node-menu" />
          </div>

          {/* Two-line text on the right */}
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold truncate">{name}</h3>
            <p className="text-xs text-muted-foreground truncate">{displayText}</p>
          </div>
        </div>
      </div>
    </NodeWrapper>
  );
}

export default memo(MenuNode);
