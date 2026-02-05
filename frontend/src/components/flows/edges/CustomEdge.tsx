import { useState } from 'react';
import { BaseEdge, EdgeLabelRenderer, EdgeProps, getBezierPath, getSmoothStepPath, Position } from 'reactflow';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import NodeTypeSelector from '../NodeTypeSelector';
import type { NodeType, FlowNode } from '@/lib/types';
import { useEdgeHover } from '@/contexts/EdgeHoverContext';

/**
 * Determines whether to use smooth step path instead of bezier.
 * Uses smooth step for backwards connections and problematic angles.
 */
function shouldUseSmoothStep(
  sourceX: number,
  sourceY: number,
  targetX: number,
  targetY: number,
  sourcePosition: Position,
  targetPosition: Position
): boolean {
  // Case 1: Going backwards (right to left) - most common problem
  if (targetX < sourceX - 50) {  // -50 for tolerance
    return true;
  }

  // Case 2: Vertical handle (top/bottom) connecting to horizontal handle (left)
  // These create nearly flat, invisible bezier curves
  if (
    (sourcePosition === Position.Top || sourcePosition === Position.Bottom) &&
    targetPosition === Position.Left
  ) {
    return true;
  }

  // Case 3: Right to left with sharp vertical angle
  // Creates flat curves that are hard to see
  if (sourcePosition === Position.Right && targetPosition === Position.Left) {
    const deltaY = Math.abs(targetY - sourceY);
    const deltaX = Math.abs(targetX - sourceX);

    // If more vertical than horizontal, use smooth step
    if (deltaY > deltaX * 1.5) {
      return true;
    }
  }

  return false;
}

/**
 * Extended edge props with insertion metadata.
 */
interface CustomEdgeProps extends EdgeProps {
  data?: {
    sourceNodeId?: string;
    routeIndex?: number;
    condition?: string;
    sourceNode?: FlowNode;
    onInsertBetween?: (nodeType: NodeType, condition?: string) => void;
    onUpdateCondition?: (newCondition: string) => void;
    availableVariables?: string[];
  };
}

/**
 * Custom edge with inline node insertion capability.
 * - Uses bezier curves for natural flow
 * - Uses smooth step for backwards/problematic connections
 * - Shows clickable labels with "+" icon on hover for edges with conditions
 * - Shows persistent "+" button for edges without labels
 */
export default function CustomEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  label,
  data,
}: CustomEdgeProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [selectorOpen, setSelectorOpen] = useState(false);

  // Check if this edge is being hovered during drag-to-reorder
  const hoveredEdgeId = useEdgeHover();
  const isDragHovered = hoveredEdgeId === id;

  // Determine which path type to use
  const useSmoothStep = shouldUseSmoothStep(
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition
  );

  // Calculate path using appropriate algorithm
  const [edgePath, labelX, labelY] = useSmoothStep
    ? getSmoothStepPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
        borderRadius: 8, // Rounded corners for smooth step
      })
    : getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
      });

  const handleInsert = (nodeType: NodeType, condition?: string) => {
    if (data?.onInsertBetween) {
      data.onInsertBetween(nodeType, condition);
    }
    setSelectorOpen(false);
  };

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          strokeWidth: isDragHovered ? 4 : 2,
          stroke: isDragHovered ? 'var(--primary)' : style.stroke || 'var(--muted-foreground)',
          opacity: isDragHovered ? 0.8 : 1,
        }}
      />

      {data?.onInsertBetween && (
        <EdgeLabelRenderer>
          {label ? (
            // Edge with label: Clickable label with plus icon on hover
            <div
              style={{
                position: 'absolute',
                transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
                pointerEvents: 'all',
              }}
              className="nodrag nopan"
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
            >
              <NodeTypeSelector
                open={selectorOpen}
                onOpenChange={setSelectorOpen}
                onSelectType={handleInsert}
                onUpdateCondition={data.onUpdateCondition}
                parentNode={data.sourceNode}
                preSelectedType={undefined}
                preFilledCondition={data.condition}
                availableVariables={data.availableVariables}
              >
                <div
                  className={`flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-medium break-words cursor-pointer ${
                    isHovered ? 'max-w-[166px]' : 'max-w-[150px]'
                  }`}
                >
                  {isHovered && <Plus className="w-3 h-3 flex-shrink-0" />}
                  <span>{label}</span>
                </div>
              </NodeTypeSelector>
            </div>
          ) : (
            // Edge without label: Always-visible plus button
            <div
              style={{
                position: 'absolute',
                transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
                pointerEvents: 'all',
              }}
              className="nodrag nopan flex items-center justify-center"
            >
              <NodeTypeSelector
                open={selectorOpen}
                onOpenChange={setSelectorOpen}
                onSelectType={handleInsert}
                onUpdateCondition={data.onUpdateCondition}
                parentNode={data.sourceNode}
                preSelectedType={undefined}
                preFilledCondition={data.condition}
                availableVariables={data.availableVariables}
              >
                <Button
                  variant="outline"
                  size="icon"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectorOpen(true);
                  }}
                  className="w-6 h-6 rounded-full bg-background border-2 border-muted-foreground shadow-md hover:shadow-lg hover:scale-110 transition-all flex items-center justify-center"
                  title="Insert node here"
                >
                  <Plus className="w-3.5 h-3.5" />
                </Button>
              </NodeTypeSelector>
            </div>
          )}
        </EdgeLabelRenderer>
      )}
    </>
  );
}
