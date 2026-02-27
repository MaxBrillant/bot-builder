import { memo } from "react";
import { MessageSquare } from "lucide-react";
import NodeWrapper from "./NodeWrapper";
import NodeHandles from "./NodeHandles";
import NodeTypeSelector from "../NodeTypeSelector";
import type { NodeType, FlowNode, VariableInfo } from "@/lib/types";

// Type aliases for reactflow (v11 export issues)
type NodeProps<T = any> = { data: T; id: string; selected?: boolean };

interface PromptNodeData {
  name?: string;
  nodeId?: string;
  flowNode?: FlowNode;
  allNodes?: Record<string, FlowNode>;
  config?: {
    text?: string;
    save_to_variable?: string;
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
  availableVariables?: VariableInfo[];
  outputHandleIds?: string[];
}

function PromptNode({
  data,
}: NodeProps<PromptNodeData>) {
  const name = data?.name || "Prompt";
  const variable = data?.config?.save_to_variable || "user_input";

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
          {/* Position trigger at right edge of node */}
          <div style={{ position: 'absolute', left: 220, top: 40, width: 0, height: 0, opacity: 0, pointerEvents: 'none' }} />
        </NodeTypeSelector>
      )}

      <div
        className={`bg-card rounded-md border-2 border-border hover:border-node-prompt/50 w-[200px] h-[80px] transition-all cursor-pointer hover:shadow-lg`}
      >
        {/* New handle system: single left input + dynamic outputs */}
        {data?.flowNode && data?.allNodes && (
          <NodeHandles node={data.flowNode} allNodes={data.allNodes} outputHandleIds={data.outputHandleIds} />
        )}

        <div className="h-full flex items-center gap-3 p-4">
          {/* Large icon on the left */}
          <div className="flex-shrink-0">
            <MessageSquare className="w-8 h-8 text-node-prompt" />
          </div>

          {/* Two-line text on the right */}
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold truncate">{name}</h3>
            <p className="text-xs text-muted-foreground truncate">Saves to {variable}</p>
          </div>
        </div>
      </div>
    </NodeWrapper>
  );
}

export default memo(PromptNode);
