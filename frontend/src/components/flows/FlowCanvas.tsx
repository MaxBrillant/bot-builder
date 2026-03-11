import React from "react";
import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import "reactflow/dist/style.css";
import { EdgeHoverContext } from "@/contexts/EdgeHoverContext";
import { GRID_SIZE } from "@/utils/canvasPositioningUtils";

// Type aliases for reactflow (v11 export issues)
type Node = any;
type Edge = any;
type NodeTypes = any;
type EdgeTypes = any;

// BackgroundVariant enum for reactflow v11
enum BackgroundVariant {
  Lines = "lines",
  Dots = "dots",
  Cross = "cross",
}

interface FlowCanvasProps {
  nodes: Node[];
  edges: Edge[];
  nodeTypes: NodeTypes;
  edgeTypes: EdgeTypes;
  onNodeClick: (event: React.MouseEvent, node: Node) => void;
  onPaneClick: () => void;
  onNodesChange?: (changes: any[]) => void;
  onNodeDragStart?: (event: React.MouseEvent, node: Node) => void;
  onNodeDrag?: (event: React.MouseEvent, node: Node) => void;
  onNodeDragStop?: (event: React.MouseEvent, node: Node, nodes: Node[]) => void;
  onEdgeMouseEnter?: (event: React.MouseEvent, edge: Edge) => void;
  onEdgeMouseLeave?: (event: React.MouseEvent, edge: Edge) => void;
  pendingNodeSelection: boolean;
  hoveredEdgeId?: string | null;
  isDraggingNode?: boolean;
  skipFitView?: boolean;
}

/**
 * FlowCanvas component - Pure React Flow rendering
 * Handles the visual display of the flow without business logic
 */
export function FlowCanvas({
  nodes,
  edges,
  nodeTypes,
  edgeTypes,
  onNodeClick,
  onPaneClick,
  onNodesChange,
  onNodeDragStart,
  onNodeDrag,
  onNodeDragStop,
  onEdgeMouseEnter,
  onEdgeMouseLeave,
  pendingNodeSelection,
  hoveredEdgeId = null,
  isDraggingNode = false,
  skipFitView = false,
}: FlowCanvasProps) {
  return (
    <EdgeHoverContext.Provider value={{ edgeId: hoveredEdgeId, isDragging: isDraggingNode }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        nodesDraggable={true} // Enable dragging
        nodesConnectable={false} // No manual connections
        autoPanOnNodeDrag={true} // Pan canvas when dragging nodes to edge
        elementsSelectable={true}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onNodesChange={onNodesChange}
        onNodeDragStart={onNodeDragStart}
        onNodeDrag={onNodeDrag}
        onNodeDragStop={onNodeDragStop}
        onEdgeMouseEnter={onEdgeMouseEnter}
        onEdgeMouseLeave={onEdgeMouseLeave}
        fitView={nodes.length > 0 && !pendingNodeSelection && !skipFitView}
        fitViewOptions={{ padding: 0.2 }}
        snapToGrid={true}
        snapGrid={[GRID_SIZE, GRID_SIZE]}
        deleteKeyCode={null} // Disable delete key
        className="bg-muted/30"
      >
        <Background variant={BackgroundVariant.Dots} gap={GRID_SIZE} size={1.5} color="#cbd5e1" />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(node: Node) => {
            const colors: Record<string, string> = {
              PROMPT: "#3b82f6",
              MENU: "#a855f7",
              API_ACTION: "#22c55e",
              LOGIC_EXPRESSION: "#f97316",
              TEXT: "#06b6d4",
              SET_VARIABLE: "#d946ef",
            };
            return colors[node.type || ""] || "#6b7280";
          }}
          className="!bg-background !border !border-border"
        />
      </ReactFlow>
    </EdgeHoverContext.Provider>
  );
}
