import { useState } from 'react';
import { BaseEdge, EdgeLabelRenderer, getBezierPath, getSmoothStepPath } from 'reactflow';
import { Button } from '@/components/ui/button';
import { Plus, Trash2 } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import NodeTypeSelector from '../NodeTypeSelector';
import { ConditionSelector } from '../config/shared/ConditionSelector';
import type { NodeType, FlowNode } from '@/lib/types';
import { useEdgeHover } from '@/contexts/EdgeHoverContext';

// Local Position enum to avoid reactflow type export issues
enum Position {
  Left = 'left',
  Top = 'top',
  Right = 'right',
  Bottom = 'bottom',
}

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
interface CustomEdgeProps {
  id: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  sourcePosition: Position;
  targetPosition: Position;
  style?: React.CSSProperties;
  markerEnd?: string;
  label?: React.ReactNode;
  data?: {
    sourceNodeId?: string;
    routeIndex?: number;
    handleIndex?: number;
    cumulativeLabelOffset?: number;
    condition?: string;
    sourceNode?: FlowNode;
    onInsertBetween?: (nodeType: NodeType, condition?: string) => void;
    onUpdateCondition?: (newCondition: string) => void;
    onDeleteRoute?: () => void;
    availableVariables?: string[];
  };
}

/**
 * Custom edge with inline node insertion and condition editing.
 * - Uses bezier curves for natural flow
 * - Uses smooth step for backwards/problematic connections
 * - Shows clickable labels (click to edit condition) with "+" icon on hover (click to insert node)
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
  const [editOpen, setEditOpen] = useState(false);
  const [editCondition, setEditCondition] = useState(data?.condition || '');

  // Check if this edge is being hovered (drag or regular)
  const { edgeId: hoveredEdgeId, isDragging } = useEdgeHover();
  const isEdgeHovered = hoveredEdgeId === id;
  const isDragHovered = isEdgeHovered && isDragging;

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
  // For backward edges, use consistent offset steps based on handle position
  // cumulativeLabelOffset accounts for labels of edges above this one (lower handle indices)
  const handleIndex = data?.handleIndex ?? 0;
  const cumulativeLabelOffset = data?.cumulativeLabelOffset ?? 0;

  const baseOffset = (handleIndex + 1) * 18;
  const backwardOffset = useSmoothStep ? baseOffset + cumulativeLabelOffset : 0;

  const [edgePath, labelX, labelY] = useSmoothStep
    ? getSmoothStepPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
        borderRadius: 8, // Rounded corners for smooth step
        offset: backwardOffset,
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

  // Handle saving edited condition
  const handleSaveCondition = () => {
    const trimmed = editCondition.trim();
    if (trimmed && trimmed !== data?.condition && data?.onUpdateCondition) {
      data.onUpdateCondition(trimmed);
    }
  };

  // Reset edit condition when popover opens, save on close
  const handleEditOpenChange = (open: boolean) => {
    if (open) {
      setEditCondition(data?.condition || '');
    } else {
      handleSaveCondition();
    }
    setEditOpen(open);
  };

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        interactionWidth={20}
        style={{
          ...style,
          strokeWidth: isDragHovered ? 4 : 2,
          stroke: isDragHovered ? 'var(--node-prompt)' : isEdgeHovered ? 'var(--primary)' : style.stroke || 'var(--muted-foreground)',
        }}
      />

      {data?.onInsertBetween && (
        <EdgeLabelRenderer>
          {label ? (
            // Edge with label: Click label to edit, plus on right to insert
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
              <div
                className={`flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-medium break-words cursor-pointer ${
                  (isHovered || selectorOpen || editOpen) ? 'max-w-[166px]' : 'max-w-[150px]'
                }`}
              >
                {/* Label - click to edit */}
                <Popover open={editOpen} onOpenChange={handleEditOpenChange}>
                  <PopoverTrigger asChild>
                    <span className="hover:text-foreground line-clamp-3" title={typeof label === 'string' ? label : undefined}>{label}</span>
                  </PopoverTrigger>
                  <PopoverContent className="w-64 p-3" align="start">
                    <div className="space-y-2">
                      <div className="text-xs font-medium text-muted-foreground">
                        Edit Route Condition
                      </div>
                      {data.sourceNode && (
                        <ConditionSelector
                          nodeType={data.sourceNode.type}
                          nodeConfig={data.sourceNode.config}
                          value={editCondition}
                          onChange={setEditCondition}
                          placeholder="Enter condition"
                          availableVariables={data.availableVariables}
                        />
                      )}
                    </div>
                  </PopoverContent>
                </Popover>

                {/* Add button - on the right with separator, full height clickable */}
                {(isHovered || selectorOpen || editOpen) && (
                  <>
                    <span className="w-px self-stretch bg-border" />
                    <NodeTypeSelector
                      open={selectorOpen}
                      onOpenChange={setSelectorOpen}
                      onSelectType={handleInsert}
                      parentNode={data.sourceNode}
                      preSelectedType={undefined}
                      preFilledCondition={data.condition}
                      conditionReadOnly
                      availableVariables={data.availableVariables}
                    >
                      <span
                        title="Insert node"
                        className="flex items-center self-stretch hover:bg-accent hover:text-foreground cursor-pointer"
                      >
                        <Plus className="w-4 h-4 flex-shrink-0" />
                      </span>
                    </NodeTypeSelector>
                    {/* Delete button - only show if handler exists */}
                    {data?.onDeleteRoute && (
                      <>
                        <span className="w-px self-stretch bg-border" />
                        <span
                          onClick={(e) => {
                            e.stopPropagation();
                            data.onDeleteRoute?.();
                          }}
                          title="Delete route"
                          className="flex items-center self-stretch hover:bg-destructive/10 hover:text-destructive cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4 flex-shrink-0" />
                        </span>
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          ) : (
            // Edge without label: Always-visible plus button
            <div
              style={{
                position: 'absolute',
                transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
                pointerEvents: 'all',
              }}
              className="nodrag nopan flex items-center gap-1"
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
            >
              <NodeTypeSelector
                open={selectorOpen}
                onOpenChange={setSelectorOpen}
                onSelectType={handleInsert}
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
              {/* Delete button - show on hover */}
              {isHovered && data?.onDeleteRoute && (
                <Button
                  variant="outline"
                  size="icon"
                  onClick={(e) => {
                    e.stopPropagation();
                    data.onDeleteRoute?.();
                  }}
                  className="w-6 h-6 rounded-full bg-background border-2 border-destructive text-destructive shadow-md hover:shadow-lg hover:scale-110 transition-all flex items-center justify-center"
                  title="Delete route"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              )}
            </div>
          )}
        </EdgeLabelRenderer>
      )}
    </>
  );
}
