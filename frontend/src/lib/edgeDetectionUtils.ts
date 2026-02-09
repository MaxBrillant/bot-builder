/**
 * Edge Detection Utilities
 *
 * Provides utilities for detecting when a dragged node hovers over an edge.
 * Uses the actual edge label position (calculated by React Flow) for accurate detection
 * on both bezier curves and smooth step paths.
 */

import { getBezierPath, getSmoothStepPath } from 'reactflow';

// Local Position enum to avoid reactflow type export issues
enum Position {
  Left = 'left',
  Top = 'top',
  Right = 'right',
  Bottom = 'bottom',
}

// Type aliases for reactflow
type Edge = any;
type Node = any;

export interface EdgeBounds {
  edgeId: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  labelX: number;  // Actual label position on the visual path
  labelY: number;  // Actual label position on the visual path
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

/**
 * Determines whether an edge should use smooth step path instead of bezier.
 * Matches the logic in CustomEdge.tsx to ensure consistent behavior.
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
  if (targetX < sourceX - 50) {
    return true;
  }

  // Case 2: Vertical handle (top/bottom) connecting to horizontal handle (left)
  if (
    (sourcePosition === Position.Top || sourcePosition === Position.Bottom) &&
    targetPosition === Position.Left
  ) {
    return true;
  }

  // Case 3: Right to left with sharp vertical angle
  if (sourcePosition === Position.Right && targetPosition === Position.Left) {
    const deltaY = Math.abs(targetY - sourceY);
    const deltaX = Math.abs(targetX - sourceX);

    if (deltaY > deltaX * 1.5) {
      return true;
    }
  }

  return false;
}

/**
 * Calculate bounding boxes for all edges with tolerance expansion.
 * Uses React Flow's label position calculation for accurate detection on both
 * bezier curves and smooth step paths.
 *
 * @param edges - React Flow edges
 * @param nodes - React Flow nodes (for position lookup)
 * @param tolerance - Pixels to expand bounding box for easier targeting (default: 30)
 * @param excludeNodeId - Optional node ID to exclude edges connected to this node
 * @returns Array of edge bounds with actual label positions
 */
export function calculateEdgeBounds(
  edges: Edge[],
  nodes: Node[],
  tolerance: number = 30,
  excludeNodeId?: string | null
): EdgeBounds[] {
  // Create node position lookup map
  const nodePositions = new Map<string, { x: number; y: number }>();
  nodes.forEach((node) => {
    if (node.position) {
      // Node center (assuming 200x80 node size)
      nodePositions.set(node.id, {
        x: node.position.x + 100, // Center X (200/2)
        y: node.position.y + 40,  // Center Y (80/2)
      });
    }
  });

  return edges
    .filter(edge => {
      // Exclude stub edges
      if (edge.type === 'stub') return false;

      // Exclude edges connected to the excluded node
      if (excludeNodeId && (edge.source === excludeNodeId || edge.target === excludeNodeId)) {
        return false;
      }

      return true;
    })
    .map((edge) => {
      const sourcePos = nodePositions.get(edge.source);
      const targetPos = nodePositions.get(edge.target);

      // Fallback to 0,0 if positions not found
      const sourceX = sourcePos?.x ?? 0;
      const sourceY = sourcePos?.y ?? 0;
      const targetX = targetPos?.x ?? 0;
      const targetY = targetPos?.y ?? 0;

      // Convert string positions from edge data to Position enum
      // Edge positions are set by flowLayoutUtils.ts: "right", "left", "top", "bottom"
      const sourcePosition =
        edge.sourcePosition === 'top' ? Position.Top
        : edge.sourcePosition === 'bottom' ? Position.Bottom
        : edge.sourcePosition === 'left' ? Position.Left
        : Position.Right;

      const targetPosition =
        edge.targetPosition === 'top' ? Position.Top
        : edge.targetPosition === 'bottom' ? Position.Bottom
        : edge.targetPosition === 'right' ? Position.Right
        : Position.Left;

      // Calculate actual label position using React Flow's path functions
      const useSmoothStep = shouldUseSmoothStep(
        sourceX,
        sourceY,
        targetX,
        targetY,
        sourcePosition,
        targetPosition
      );

      // Get handleIndex and cumulativeLabelOffset from edge data (set in flowLayoutUtils.ts)
      const edgeData = edge.data as { handleIndex?: number; cumulativeLabelOffset?: number } | undefined;
      const handleIndex = edgeData?.handleIndex ?? 0;
      const cumulativeLabelOffset = edgeData?.cumulativeLabelOffset ?? 0;

      // Apply same offset as CustomEdge.tsx for consistency
      const baseOffset = (handleIndex + 1) * 18;
      const backwardOffset = useSmoothStep ? baseOffset + cumulativeLabelOffset : 0;

      const [, labelX, labelY] = useSmoothStep
        ? getSmoothStepPath({
            sourceX,
            sourceY,
            sourcePosition,
            targetX,
            targetY,
            targetPosition,
            borderRadius: 8,
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

      return {
        edgeId: edge.id,
        sourceX,
        sourceY,
        targetX,
        targetY,
        labelX,  // Use actual label position instead of simple midpoint
        labelY,  // Use actual label position instead of simple midpoint
        minX: Math.min(sourceX, targetX) - tolerance,
        maxX: Math.max(sourceX, targetX) + tolerance,
        minY: Math.min(sourceY, targetY) - tolerance,
        maxY: Math.max(sourceY, targetY) + tolerance,
      };
    });
}

/**
 * Calculate distance from a point to the edge's label position.
 * The label position is calculated by React Flow to be on the actual visual path.
 *
 * @param px - Point X coordinate
 * @param py - Point Y coordinate
 * @param bounds - Edge bounds (with labelX, labelY)
 * @returns Distance from point to edge label position
 */
function distanceToEdgeLabel(
  px: number,
  py: number,
  bounds: EdgeBounds
): number {
  const dx = px - bounds.labelX;
  const dy = py - bounds.labelY;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Find the closest edge to a point using the actual edge label position.
 * The label position is on the visual path (works for both bezier and smooth step).
 * Returns null if no edges are within the distance threshold.
 *
 * @param x - X coordinate
 * @param y - Y coordinate
 * @param edgeBounds - Array of edge bounds with label positions
 * @param threshold - Maximum distance from edge label to consider (default: 80 pixels)
 * @returns Edge ID of closest edge, or null
 */
export function findClosestEdge(
  x: number,
  y: number,
  edgeBounds: EdgeBounds[],
  threshold: number = 80
): string | null {
  let closestEdge: EdgeBounds | null = null;
  let minDistance = threshold;

  for (const bounds of edgeBounds) {
    // Calculate distance to edge label position (on the actual visual path)
    const distance = distanceToEdgeLabel(x, y, bounds);

    // Keep track of closest edge within threshold
    if (distance < minDistance) {
      minDistance = distance;
      closestEdge = bounds;
    }
  }

  return closestEdge?.edgeId ?? null;
}
