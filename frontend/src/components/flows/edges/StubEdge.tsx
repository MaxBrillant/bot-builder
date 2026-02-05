import { useState } from 'react';
import { BaseEdge, EdgeLabelRenderer, EdgeProps, getBezierPath } from 'reactflow';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import NodeTypeSelector from '../NodeTypeSelector';
import type { NodeType, FlowNode } from '@/lib/types';

/**
 * Stub edge props
 */
interface StubEdgeProps extends EdgeProps {
  data?: {
    sourceNodeId?: string;
    sourceNode?: FlowNode;
    onInsertBetween?: (nodeType: NodeType, condition?: string) => void;
    availableVariables?: string[];
  };
}

/**
 * Stub edge showing available route capacity
 * Displays a "+" button at terminus for adding new routes
 */
export default function StubEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  data,
}: StubEdgeProps) {
  const [selectorOpen, setSelectorOpen] = useState(false);

  // Shorten line to connect smoothly with button border
  const buttonRadius = 12; // w-6 = 24px, half = 12px
  const borderWidth = 2;
  const shortenBy = buttonRadius - borderWidth;

  const deltaX = targetX - sourceX;
  const deltaY = targetY - sourceY;
  const length = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
  const ratio = Math.max(0, (length - shortenBy) / length);

  const adjustedTargetX = sourceX + deltaX * ratio;
  const adjustedTargetY = sourceY + deltaY * ratio;

  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX: adjustedTargetX,
    targetY: adjustedTargetY,
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
      <BaseEdge id={id} path={edgePath} style={style} />

      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${targetX}px,${targetY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan flex items-center justify-center"
        >
          <NodeTypeSelector
            open={selectorOpen}
            onOpenChange={setSelectorOpen}
            onSelectType={handleInsert}
            parentNode={data?.sourceNode}
            availableVariables={data?.availableVariables}
          >
            <Button
              variant="outline"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                setSelectorOpen(true);
              }}
              className="w-6 h-6 rounded-full bg-background border-2 border-muted-foreground shadow-md hover:shadow-lg hover:scale-110 transition-all"
              title="Add new route"
            >
              <Plus className="w-3.5 h-3.5" />
            </Button>
          </NodeTypeSelector>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
