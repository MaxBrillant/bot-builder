import type { FlowNode } from "./types";

/**
 * Handle position configuration
 * - LEFT: Single input handle at 50% height
 * - RIGHT: 3 output positions (25%, 50%, 75%)
 * - TOP: 5 output positions (10%, 30%, 50%, 70%, 90%)
 * - BOTTOM: 5 output positions (10%, 30%, 50%, 70%, 90%)
 * Total capacity: 13 handles (exceeds max 8 routes per node)
 */
export const HANDLE_POSITIONS = {
  INPUT: {
    side: "left" as const,
    position: 0.5,
  },
  RIGHT: [
    { position: 0.25, id: "right-0" },
    { position: 0.5, id: "right-1" },
    { position: 0.75, id: "right-2" },
  ],
  TOP: [
    { position: 0.1, id: "top-0" },
    { position: 0.3, id: "top-1" },
    { position: 0.5, id: "top-2" },
    { position: 0.7, id: "top-3" },
    { position: 0.9, id: "top-4" },
  ],
  BOTTOM: [
    { position: 0.1, id: "bottom-0" },
    { position: 0.3, id: "bottom-1" },
    { position: 0.5, id: "bottom-2" },
    { position: 0.7, id: "bottom-3" },
    { position: 0.9, id: "bottom-4" },
  ],
} as const;

export type HandleSide = "left" | "right" | "top" | "bottom";

export interface HandleAssignment {
  routeIndex: number;
  side: HandleSide;
  handleId: string;
  position: number;
}

export interface RouteHandleInfo {
  sourceHandle: string;
  targetHandle: string;
  sourcePosition: HandleSide;
  targetPosition: HandleSide;
}

type RouteInfo = {
  routeIndex: number;
  targetPos: { x: number; y: number };
  sourcePos: { x: number; y: number };
  route: { condition: string; target_node: string };
};

/**
 * Determine primary exit side for a route based on spatial relationship
 */
function determineRouteSide(
  sourcePos: { x: number; y: number },
  targetPos: { x: number; y: number }
): Exclude<HandleSide, "left"> {
  const deltaX = targetPos.x - sourcePos.x;
  const deltaY = targetPos.y - sourcePos.y;
  const absX = Math.abs(deltaX);
  const absY = Math.abs(deltaY);

  if (absX > absY) {
    return deltaX > 0 ? "right" : (deltaY >= 0 ? "bottom" : "top");
  } else {
    return deltaY > 0 ? "bottom" : "top";
  }
}

/**
 * Determine overflow side when primary side is at capacity
 */
function determineOverflowSide(
  primarySide: Exclude<HandleSide, "left">,
  sourcePos: { x: number; y: number },
  targetPos: { x: number; y: number },
  availableCapacity: { right: number; top: number; bottom: number }
): Exclude<HandleSide, "left"> {
  const deltaX = targetPos.x - sourcePos.x;
  const deltaY = targetPos.y - sourcePos.y;

  if (primarySide === "right") {
    if (deltaY < 0 && availableCapacity.top > 0) return "top";
    if (availableCapacity.bottom > 0) return "bottom";
    if (availableCapacity.top > 0) return "top";
  } else if (primarySide === "top") {
    if (deltaX > 0 && availableCapacity.right > 0) return "right";
    if (availableCapacity.bottom > 0) return "bottom";
    if (availableCapacity.right > 0) return "right";
  } else if (primarySide === "bottom") {
    if (deltaX > 0 && availableCapacity.right > 0) return "right";
    if (availableCapacity.top > 0) return "top";
    if (availableCapacity.right > 0) return "right";
  }

  // Fallback to any available side
  if (availableCapacity.right > 0) return "right";
  if (availableCapacity.bottom > 0) return "bottom";
  return availableCapacity.top > 0 ? "top" : primarySide;
}

/**
 * Sort routes by spatial position relative to source
 * RIGHT: top-to-bottom | TOP/BOTTOM: left-to-right
 * IMPORTANT: Stub routes get specific positions:
 *   - RIGHT side: stub sorts last (bottom)
 *   - TOP/BOTTOM sides: stub sorts first (leftmost)
 */
function sortBySpatialPosition(
  routes: RouteInfo[],
  side: Exclude<HandleSide, "left">
): RouteInfo[] {
  return routes.sort((a, b) => {
    // Stub positioning based on side
    if (side === "right") {
      // Right side: stub goes last (bottom)
      if (a.route.condition === 'stub') return 1;
      if (b.route.condition === 'stub') return -1;
    } else {
      // Top/Bottom sides: stub goes first (leftmost)
      if (a.route.condition === 'stub') return -1;
      if (b.route.condition === 'stub') return 1;
    }

    // Normal spatial sorting for non-stub routes
    if (side === "right") {
      const deltaYa = a.targetPos.y - a.sourcePos.y;
      const deltaYb = b.targetPos.y - b.sourcePos.y;
      return deltaYa - deltaYb;
    } else {
      const deltaXa = a.targetPos.x - a.sourcePos.x;
      const deltaXb = b.targetPos.x - b.sourcePos.x;
      return deltaXa - deltaXb;
    }
  });
}

/**
 * Get handle position indices based on route count
 * Returns which physical positions to use (not a scrambled order)
 */
function getHandlePositionIndices(count: number, maxPositions: number): number[] {
  if (maxPositions === 3) {
    // RIGHT side (3 positions)
    if (count === 1) return [1];       // center
    if (count === 2) return [0, 2];    // top, bottom
    return [0, 1, 2];                   // all three
  } else {
    // TOP/BOTTOM sides (5 positions)
    if (count === 1) return [2];             // center
    if (count === 2) return [1, 3];          // 30%, 70%
    if (count === 3) return [1, 2, 3];       // 30%, 50%, 70%
    if (count === 4) return [0, 1, 3, 4];    // skip center
    return [0, 1, 2, 3, 4];                   // all five
  }
}

/**
 * Calculate handle assignments for all routes of a node
 * Algorithm:
 * 1. Categorize routes by primary direction (right/top/bottom)
 * 2. Sort each group by spatial position relative to source
 * 3. Assign handles sequentially based on position
 * 4. Handle overflow by redirecting to adjacent sides
 */
export function calculateHandleAssignments(
  sourceNode: FlowNode,
  allNodes: Record<string, FlowNode>
): HandleAssignment[] {
  if (!sourceNode.routes || sourceNode.routes.length === 0) {
    return [];
  }

  // Categorize routes by direction (skip routes to END nodes - they're hidden from UI)
  // Exception: stub routes (condition === 'stub') point to temporary END nodes and should be included
  const routesBySide: Record<Exclude<HandleSide, "left">, RouteInfo[]> = {
    right: [],
    top: [],
    bottom: [],
  };

  sourceNode.routes.forEach((route, index) => {
    const targetNode = allNodes[route.target_node];

    // Skip routes to END nodes unless it's a stub route
    if (targetNode?.type === "END" && route.condition !== "stub") {
      return;
    }

    const sourcePos = sourceNode.position || { x: 0, y: 0 };
    const targetPos = targetNode?.position || { x: 0, y: 0 };

    const side = determineRouteSide(sourcePos, targetPos);
    routesBySide[side].push({ routeIndex: index, targetPos, sourcePos, route });
  });

  // Sort each side by spatial position and stub priority
  routesBySide.right = sortBySpatialPosition(routesBySide.right, "right");
  routesBySide.top = sortBySpatialPosition(routesBySide.top, "top");
  routesBySide.bottom = sortBySpatialPosition(routesBySide.bottom, "bottom");

  // Track handle capacity for each side
  const maxCapacity: Record<"right" | "top" | "bottom", number> = {
    right: HANDLE_POSITIONS.RIGHT.length,
    top: HANDLE_POSITIONS.TOP.length,
    bottom: HANDLE_POSITIONS.BOTTOM.length,
  };
  const availableCapacity: Record<"right" | "top" | "bottom", number> = { ...maxCapacity };
  const assignments: HandleAssignment[] = [];

  // Pass 1: Redistribute overflow routes to available sides
  const processOverflow = (routes: RouteInfo[], primarySide: Exclude<HandleSide, "left">) => {
    const capacity = availableCapacity[primarySide];
    const overflowRoutes = routes.slice(capacity);

    // Keep only routes that fit on primary side
    routesBySide[primarySide] = routes.slice(0, capacity);
    availableCapacity[primarySide] = 0;

    // Redirect overflow routes to other sides
    overflowRoutes.forEach((route) => {
      const targetSide = determineOverflowSide(
        primarySide,
        route.sourcePos,
        route.targetPos,
        availableCapacity
      );

      routesBySide[targetSide].push(route);
      availableCapacity[targetSide]--;
    });
  };

  // Process overflow for each side (right has highest priority)
  processOverflow(routesBySide.right, "right");
  processOverflow(routesBySide.top, "top");
  processOverflow(routesBySide.bottom, "bottom");

  // Re-sort after overflow redistribution to maintain spatial ordering
  routesBySide.right = sortBySpatialPosition(routesBySide.right, "right");
  routesBySide.top = sortBySpatialPosition(routesBySide.top, "top");
  routesBySide.bottom = sortBySpatialPosition(routesBySide.bottom, "bottom");

  // Pass 2: Assign handles to all routes (original + redistributed overflow)
  const assignHandles = (routes: RouteInfo[], side: Exclude<HandleSide, "left">) => {
    if (routes.length === 0) return;

    const maxPositions = side === "right" ? 3 : 5;
    const positionIndices = getHandlePositionIndices(routes.length, maxPositions);
    const positions = side === "right" ? HANDLE_POSITIONS.RIGHT :
                     side === "top" ? HANDLE_POSITIONS.TOP :
                     HANDLE_POSITIONS.BOTTOM;

    routes.forEach((route, idx) => {
      const handle = positions[positionIndices[idx]];
      assignments.push({
        routeIndex: route.routeIndex,
        side,
        handleId: handle.id,
        position: handle.position,
      });
    });
  };

  assignHandles(routesBySide.right, "right");
  assignHandles(routesBySide.top, "top");
  assignHandles(routesBySide.bottom, "bottom");

  return assignments.sort((a, b) => a.routeIndex - b.routeIndex);
}

/**
 * Get handle information for a specific route (used by edge rendering)
 */
export function getRouteHandleInfo(
  sourceNode: FlowNode,
  routeIndex: number,
  allNodes: Record<string, FlowNode>
): RouteHandleInfo {
  const assignments = calculateHandleAssignments(sourceNode, allNodes);
  const assignment = assignments.find((a) => a.routeIndex === routeIndex);

  if (!assignment) {
    return {
      sourceHandle: "right-1",
      targetHandle: "left",
      sourcePosition: "right",
      targetPosition: "left",
    };
  }

  return {
    sourceHandle: assignment.handleId,
    targetHandle: "left",
    sourcePosition: assignment.side,
    targetPosition: "left",
  };
}

/**
 * Get all active output handles for a node (for rendering visible handles)
 * Renders the exact handles that were assigned to edges (passed as array of handle IDs)
 */
export function getActiveOutputHandles(
  handleIds: string[]
): Array<{ side: HandleSide; handleId: string; position: number }> {
  const handles: Array<{ side: HandleSide; handleId: string; position: number }> = [];

  handleIds.forEach(handleId => {
    const handleParts = handleId.split('-');
    if (handleParts.length === 2) {
      const sideStr = handleParts[0] as 'right' | 'top' | 'bottom';
      const index = parseInt(handleParts[1], 10);

      let position = 0.5; // fallback
      if (sideStr === 'right' && HANDLE_POSITIONS.RIGHT[index]) {
        position = HANDLE_POSITIONS.RIGHT[index].position;
      } else if (sideStr === 'top' && HANDLE_POSITIONS.TOP[index]) {
        position = HANDLE_POSITIONS.TOP[index].position;
      } else if (sideStr === 'bottom' && HANDLE_POSITIONS.BOTTOM[index]) {
        position = HANDLE_POSITIONS.BOTTOM[index].position;
      }

      handles.push({
        side: sideStr,
        handleId,
        position,
      });
    }
  });

  return handles;
}

/**
 * Check if a node has incoming connections (determines input handle visibility)
 */
export function hasIncomingConnections(
  nodeId: string,
  allNodes: Record<string, FlowNode>
): boolean {
  return Object.values(allNodes).some((node) =>
    node.routes?.some((route) => route.target_node === nodeId)
  );
}
