import { memo } from "react";
import { MessageCircle } from "lucide-react";
import NodeWrapper from "./NodeWrapper";
import NodeHandles from "./NodeHandles";
import NodeTypeSelector from "../NodeTypeSelector";
import type { NodeType, FlowNode } from "@/lib/types";

// Type aliases for reactflow (v11 export issues)
type NodeProps<T = any> = { data: T; id: string; selected?: boolean };

interface TextNodeData {
  name?: string;
  nodeId?: string;
  flowNode?: FlowNode;
  allNodes?: Record<string, FlowNode>;
  config?: {
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

function TextNode({
  data,
}: NodeProps<TextNodeData>) {
  const name = data?.name || "Text";
  const text = data?.config?.text || "Your text here";
  const truncatedText = text.length > 30 ? text.substring(0, 30) + "..." : text;

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
        className={`bg-card rounded-md border-2 border-border hover:border-node-text/50 w-[200px] h-[80px] transition-all cursor-pointer hover:shadow-lg`}
      >
        {/* New handle system: single left input + dynamic outputs */}
        {data?.flowNode && data?.allNodes && (
          <NodeHandles node={data.flowNode} allNodes={data.allNodes} outputHandleIds={data.outputHandleIds} />
        )}

        <div className="h-full flex items-center gap-3 p-4">
          {/* Large icon on the left */}
          <div className="flex-shrink-0">
            <MessageCircle className="w-8 h-8 text-node-text" />
          </div>

          {/* Two-line text on the right */}
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold truncate">{name}</h3>
            <p className="text-xs text-muted-foreground truncate">{truncatedText}</p>
          </div>
        </div>
      </div>
    </NodeWrapper>
  );
}

export default memo(TextNode);
