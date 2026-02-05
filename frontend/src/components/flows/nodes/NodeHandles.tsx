import { Handle } from "reactflow";
import type { FlowNode } from "@/lib/types";
import { HANDLE_POSITIONS, getActiveOutputHandles, hasIncomingConnections } from "@/lib/handlePositioning";

interface NodeHandlesProps {
  node: FlowNode;
  allNodes: Record<string, FlowNode>;
  isEndNode?: boolean;
  outputHandleIds?: string[]; // Exact handle IDs assigned to edges
}

/**
 * Renders visible handles for a node based on the new handle system:
 * - Single LEFT input handle (only if node has incoming connections)
 * - Output handles on RIGHT/TOP/BOTTOM (renders the exact handles assigned to edges)
 *
 * Both regular and stub edges use the same handle positioning system
 */
export default function NodeHandles({ node, allNodes, isEndNode = false, outputHandleIds }: NodeHandlesProps) {
  // Render the exact handles that were assigned to edges
  const outputHandles = isEndNode || !outputHandleIds ? [] : getActiveOutputHandles(outputHandleIds);
  const showInputHandle = hasIncomingConnections(node.id, allNodes);

  return (
    <>
      {/* INPUT HANDLE - Only visible if node has incoming connections - SQUARE to differentiate */}
      {showInputHandle && (
        <Handle
          id="left"
          type="target"
          position={"left" as any}
          className="!w-3 !h-3 !border-0 !bg-muted-foreground hover:!bg-foreground transition-colors !rounded-none"
          style={{
            top: `${HANDLE_POSITIONS.INPUT.position * 100}%`,
            left: "-6px",
          }}
        />
      )}

      {/* OUTPUT HANDLES - Only render for active routes - CIRCULAR */}
      {outputHandles.map((handle) => {
        let style: React.CSSProperties = {};

        switch (handle.side) {
          case "right":
            style = {
              top: `${handle.position * 100}%`,
              right: "-6px",
            };
            break;
          case "top":
            style = {
              left: `${handle.position * 100}%`,
              top: "-6px",
            };
            break;
          case "bottom":
            style = {
              left: `${handle.position * 100}%`,
              bottom: "-6px",
            };
            break;
          default:
            style = {
              top: `${handle.position * 100}%`,
              right: "-6px",
            };
        }

        return (
          <Handle
            key={handle.handleId}
            id={handle.handleId}
            type="source"
            position={(handle.side || "right") as any}
            className="!w-3 !h-3 !border-0 !bg-muted-foreground hover:!bg-foreground transition-colors !rounded-full"
            style={style}
          />
        );
      })}
    </>
  );
}
