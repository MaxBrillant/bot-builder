import { useState, useEffect, useCallback, useRef } from 'react';
import { BaseEdge, EdgeLabelRenderer, getBezierPath, useReactFlow } from 'reactflow';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import NodeTypeSelector from '../NodeTypeSelector';
import type { NodeType, FlowNode, Route } from '@/lib/types';

// Local Position enum to avoid reactflow type export issues
enum Position {
  Left = 'left',
  Top = 'top',
  Right = 'right',
  Bottom = 'bottom',
}

interface StubEdgeProps {
  id: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  sourcePosition: Position;
  targetPosition: Position;
  style?: React.CSSProperties;
  data?: {
    sourceNodeId?: string;
    sourceNode?: FlowNode;
    onInsertBetween?: (nodeType: NodeType, condition?: string) => void;
    onConnectToNode?: (targetNodeId: string, screenPosition: { x: number; y: number }) => void;
    availableVariables?: string[];
    // When set, edge stays connected to this node (awaiting condition input)
    pendingTargetNodeId?: string | null;
  };
}

/**
 * Stub edge showing available route capacity
 * Displays a "+" button at terminus for adding new routes
 * Supports drag-to-connect with visual feedback
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
  const [dragState, setDragState] = useState<{
    mouseX: number;
    mouseY: number;
    hoveredNodeId: string | null;
  } | null>(null);

  // Track if we just finished dragging to prevent click from firing after drag
  const wasDraggingRef = useRef(false);

  // Ref to access latest dragState in event handlers without recreating them
  const dragStateRef = useRef(dragState);
  useEffect(() => {
    dragStateRef.current = dragState;
  }, [dragState]);

  // Auto-pan interval ref for cleanup
  const autoPanIntervalRef = useRef<number | null>(null);

  const reactFlowInstance = useReactFlow();

  // Get pending target node position if awaiting condition input
  const pendingTargetNode = data?.pendingTargetNodeId
    ? reactFlowInstance.getNode(data.pendingTargetNodeId)
    : null;

  // Shorten line to connect smoothly with button border
  const buttonRadius = 12;
  const borderWidth = 2;
  const shortenBy = buttonRadius - borderWidth;

  // Calculate edge path:
  // - When dragging: follows mouse cursor
  // - When pending target: connects to target node's left center
  // - Otherwise: connects to stub button position
  let effectiveTargetX = targetX;
  let effectiveTargetY = targetY;
  let effectiveTargetPosition = targetPosition;

  if (dragState) {
    effectiveTargetX = dragState.mouseX;
    effectiveTargetY = dragState.mouseY;
    effectiveTargetPosition = Position.Left;
  } else if (pendingTargetNode) {
    // Connect to left-center of target node
    effectiveTargetX = pendingTargetNode.position.x;
    effectiveTargetY = pendingTargetNode.position.y + (pendingTargetNode.height || 80) / 2;
    effectiveTargetPosition = Position.Left;
  }

  const deltaX = effectiveTargetX - sourceX;
  const deltaY = effectiveTargetY - sourceY;
  const length = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
  // Don't shorten when dragging or connected to pending target
  const shouldShorten = !dragState && !pendingTargetNode;
  const ratio = shouldShorten ? Math.max(0, (length - shortenBy) / length) : 1;

  const adjustedTargetX = sourceX + deltaX * ratio;
  const adjustedTargetY = sourceY + deltaY * ratio;

  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX: adjustedTargetX,
    targetY: adjustedTargetY,
    targetPosition: effectiveTargetPosition,
  });

  // Find node under cursor using DOM inspection
  const findNodeUnderCursor = useCallback((clientX: number, clientY: number): string | null => {
    const elements = document.elementsFromPoint(clientX, clientY);

    for (const el of elements) {
      // React Flow nodes have data-id attribute
      const nodeElement = el.closest('[data-id]');
      if (nodeElement) {
        const nodeId = nodeElement.getAttribute('data-id');
        if (nodeId && nodeId !== data?.sourceNodeId) {
          // Check if this would be a valid target (no duplicate route)
          const sourceRoutes = data?.sourceNode?.routes || [];
          const targetExists = sourceRoutes.some((r: Route) => r.target_node === nodeId);
          if (!targetExists) {
            return nodeId;
          }
        }
      }
    }
    return null;
  }, [data?.sourceNodeId, data?.sourceNode?.routes]);

  // Store last mouse position for auto-pan
  const lastMousePosRef = useRef<{ clientX: number; clientY: number } | null>(null);

  // Auto-pan constants
  const PAN_SPEED = 15;
  const EDGE_THRESHOLD = 50;

  // Cache container rect to avoid repeated DOM queries
  const containerRectRef = useRef<DOMRect | null>(null);

  // Get pan delta based on cursor proximity to edges
  const getPanDelta = useCallback((clientX: number, clientY: number): { dx: number; dy: number } => {
    const rect = containerRectRef.current;
    if (!rect) return { dx: 0, dy: 0 };

    let dx = 0;
    let dy = 0;

    if (clientX - rect.left < EDGE_THRESHOLD) {
      dx = PAN_SPEED;
    } else if (rect.right - clientX < EDGE_THRESHOLD) {
      dx = -PAN_SPEED;
    }

    if (clientY - rect.top < EDGE_THRESHOLD) {
      dy = PAN_SPEED;
    } else if (rect.bottom - clientY < EDGE_THRESHOLD) {
      dy = -PAN_SPEED;
    }

    return { dx, dy };
  }, []);

  // Auto-pan animation frame
  const autoPanFrame = useCallback(() => {
    const currentPos = lastMousePosRef.current;
    if (!currentPos) {
      autoPanIntervalRef.current = null;
      return;
    }

    const { dx, dy } = getPanDelta(currentPos.clientX, currentPos.clientY);
    if (dx === 0 && dy === 0) {
      // Cursor moved away from edge, stop panning
      autoPanIntervalRef.current = null;
      return;
    }

    // Update viewport
    const viewport = reactFlowInstance.getViewport();
    reactFlowInstance.setViewport({
      x: viewport.x + dx,
      y: viewport.y + dy,
      zoom: viewport.zoom,
    });

    // Update drag position (skip findNodeUnderCursor during pan for performance)
    const flowPosition = reactFlowInstance.screenToFlowPosition({
      x: currentPos.clientX,
      y: currentPos.clientY,
    });
    setDragState(prev => ({
      mouseX: flowPosition.x,
      mouseY: flowPosition.y,
      hoveredNodeId: prev?.hoveredNodeId ?? null, // Keep last known value
    }));

    // Schedule next frame
    autoPanIntervalRef.current = requestAnimationFrame(autoPanFrame);
  }, [getPanDelta, reactFlowInstance]);

  // Start auto-pan when cursor is near viewport edges
  const startAutoPan = useCallback((clientX: number, clientY: number) => {
    // Update container rect (only on mouse move, not every frame)
    const container = document.querySelector('.react-flow');
    if (container) {
      containerRectRef.current = container.getBoundingClientRect();
    }

    const { dx, dy } = getPanDelta(clientX, clientY);

    if (dx !== 0 || dy !== 0) {
      // Start panning if not already
      if (!autoPanIntervalRef.current) {
        autoPanIntervalRef.current = requestAnimationFrame(autoPanFrame);
      }
    } else {
      // Stop panning if cursor moved away from edge
      if (autoPanIntervalRef.current) {
        cancelAnimationFrame(autoPanIntervalRef.current);
        autoPanIntervalRef.current = null;
      }
    }
  }, [getPanDelta, autoPanFrame]);

  // Handle drag move
  const handleMouseMove = useCallback((e: MouseEvent) => {
    // Mark that we've moved (distinguishes drag from click)
    wasDraggingRef.current = true;

    // Store position for auto-pan interval
    lastMousePosRef.current = { clientX: e.clientX, clientY: e.clientY };

    const flowPosition = reactFlowInstance.screenToFlowPosition({
      x: e.clientX,
      y: e.clientY,
    });

    const hoveredNodeId = findNodeUnderCursor(e.clientX, e.clientY);

    setDragState({
      mouseX: flowPosition.x,
      mouseY: flowPosition.y,
      hoveredNodeId,
    });

    // Check if we need to auto-pan
    startAutoPan(e.clientX, e.clientY);
  }, [reactFlowInstance, findNodeUnderCursor, startAutoPan]);

  // Handle drag end
  const handleMouseUp = useCallback((e: MouseEvent) => {
    const currentDragState = dragStateRef.current;
    if (currentDragState?.hoveredNodeId && data?.onConnectToNode) {
      data.onConnectToNode(currentDragState.hoveredNodeId, { x: e.clientX, y: e.clientY });
    }
    setDragState(null);
  }, [data]);

  // Attach/detach document listeners when dragging starts/stops
  const isDragging = dragState !== null;
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      // Add grabbing cursor to body while dragging
      document.body.style.cursor = 'grabbing';

      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = '';
        // Clean up auto-pan animation frame
        if (autoPanIntervalRef.current) {
          cancelAnimationFrame(autoPanIntervalRef.current);
          autoPanIntervalRef.current = null;
        }
        lastMousePosRef.current = null;
        containerRectRef.current = null;
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Track mousedown position and cleanup functions for drag detection
  const mouseDownPosRef = useRef<{ x: number; y: number } | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  // Cleanup temporary listeners on unmount
  useEffect(() => {
    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
        cleanupRef.current = null;
      }
    };
  }, []);

  // Start drag on mousedown - but don't set dragState yet (wait for movement)
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    e.stopPropagation();

    // Reset drag tracking - we haven't moved yet
    wasDraggingRef.current = false;
    mouseDownPosRef.current = { x: e.clientX, y: e.clientY };

    // Add temporary listeners to detect drag vs click
    const handleMouseMoveStart = (moveEvent: MouseEvent) => {
      if (!mouseDownPosRef.current) return;
      const dx = moveEvent.clientX - mouseDownPosRef.current.x;
      const dy = moveEvent.clientY - mouseDownPosRef.current.y;
      const distance = Math.sqrt(dx * dx + dy * dy);

      // Only start drag if moved more than 5 pixels
      if (distance > 5) {
        wasDraggingRef.current = true;
        const flowPosition = reactFlowInstance.screenToFlowPosition({
          x: moveEvent.clientX,
          y: moveEvent.clientY,
        });
        setDragState({
          mouseX: flowPosition.x,
          mouseY: flowPosition.y,
          hoveredNodeId: null,
        });
        cleanup();
      }
    };

    const handleMouseUpStart = () => {
      // Mouse released without enough movement - it's a click
      mouseDownPosRef.current = null;
      cleanup();
    };

    const cleanup = () => {
      document.removeEventListener('mousemove', handleMouseMoveStart);
      document.removeEventListener('mouseup', handleMouseUpStart);
      cleanupRef.current = null;
    };

    // Store cleanup function for unmount case
    cleanupRef.current = cleanup;

    document.addEventListener('mousemove', handleMouseMoveStart);
    document.addEventListener('mouseup', handleMouseUpStart);
  };

  const handleInsert = (nodeType: NodeType, condition?: string) => {
    if (data?.onInsertBetween) {
      data.onInsertBetween(nodeType, condition);
    }
    setSelectorOpen(false);
  };

  const handleClick = (e: React.MouseEvent) => {
    // Only open selector if we weren't dragging
    // (dragState is cleared by mouseup before click fires, so we use the ref)
    if (!wasDraggingRef.current) {
      e.stopPropagation();
      setSelectorOpen(true);
    }
    // Reset for next interaction
    wasDraggingRef.current = false;
  };

  const isValidTarget = dragState?.hoveredNodeId != null;
  const isPending = !!pendingTargetNode;
  const isActive = dragState || isPending;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: isActive
            ? (isValidTarget || isPending ? 'var(--primary)' : 'var(--muted-foreground)')
            : style.stroke,
          strokeDasharray: dragState && !isValidTarget ? '5,5' : undefined,
        }}
      />

      <EdgeLabelRenderer>
        {/* Button - hidden when dragging or pending connection */}
        {!isActive && (
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
                onMouseDown={handleMouseDown}
                onClick={handleClick}
                className="w-6 h-6 rounded-full bg-background border-2 border-muted-foreground shadow-md hover:shadow-lg hover:scale-110 transition-all cursor-grab"
                title="Click to add node, drag to connect to existing node"
              >
                <Plus className="w-3.5 h-3.5" />
              </Button>
            </NodeTypeSelector>
          </div>
        )}

        {/* Drag cursor indicator - only while actively dragging */}
        {dragState && (
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${dragState.mouseX}px,${dragState.mouseY}px)`,
              pointerEvents: 'none',
            }}
            className="flex items-center justify-center"
          >
            <div
              className={`w-4 h-4 rounded-full ${
                isValidTarget
                  ? 'bg-primary'
                  : 'bg-muted-foreground'
              }`}
            />
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  );
}
