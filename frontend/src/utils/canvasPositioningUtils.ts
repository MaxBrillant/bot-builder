import type { Flow } from "@/lib/types";

// Grid size for snap-to-grid (divides evenly into NODE_WIDTH=200 and NODE_HEIGHT=80)
export const GRID_SIZE = 20;

// Small nudge distance for Ctrl + Arrow keys (1 grid unit)
export const POSITION_NUDGE = GRID_SIZE;

// Large nudge distance for Shift + Arrow keys (4 grid units)
export const POSITION_NUDGE_LARGE = GRID_SIZE * 4;

/**
 * Snap a value to the nearest grid position
 */
export function snapToGrid(value: number, gridSize: number = GRID_SIZE): number {
  return Math.round(value / gridSize) * gridSize;
}

/**
 * Snap a position to the nearest grid position
 */
export function snapPositionToGrid(
  position: { x: number; y: number },
  gridSize: number = GRID_SIZE
): { x: number; y: number } {
  return {
    x: snapToGrid(position.x, gridSize),
    y: snapToGrid(position.y, gridSize),
  };
}

/**
 * Move a node's position by delta pixels
 * Returns a new Flow object with the updated node position
 */
export function moveNodePosition(
  flow: Flow,
  nodeId: string,
  deltaX: number,
  deltaY: number
): Flow {
  const node = flow.nodes[nodeId];
  if (!node) {
    return flow;
  }

  // Get current position or default to (0, 0)
  const currentPosition = node.position || { x: 0, y: 0 };

  // Calculate new position, snapped to grid
  const newPosition = snapPositionToGrid({
    x: currentPosition.x + deltaX,
    y: currentPosition.y + deltaY,
  });

  // Return new flow with updated node position
  return {
    ...flow,
    nodes: {
      ...flow.nodes,
      [nodeId]: {
        ...node,
        position: newPosition,
      },
    },
  };
}
