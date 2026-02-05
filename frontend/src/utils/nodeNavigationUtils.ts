import type { FlowNode } from "@/lib/types";

type ReactFlowNode = {
  id: string;
  position: { x: number; y: number };
  width?: number;
  height?: number;
};

// Direction constants
const DIR_UP = 0;
const DIR_DOWN = 1;
const DIR_LEFT = 2;
const DIR_RIGHT = 3;

// Spatial navigation constants
const PERP_WEIGHT = 3;                // Weight for perpendicular distance (2-5 typical, higher = center more dominant)
const CONNECTIVITY_BONUS = 50;        // Bonus (subtracted from score) for connected nodes

/**
 * Weighted Distance Algorithm for spatial navigation.
 * Common in game UI and smart TV navigation.
 *
 * ALGORITHM OBJECTIVES:
 * 1. Find the best candidate node in a given direction (up/down/left/right)
 * 2. Prefer nodes that are well-aligned with the navigation axis (center line)
 * 3. Among aligned nodes, prefer closer ones
 * 4. A close but off-center node can still beat a far but centered node
 * 5. Connected nodes (via routes) get a bonus preference
 *
 * SCORING FORMULA:
 *   score = axialDist + PERP_WEIGHT × perpDist
 *   - axialDist: distance along navigation direction (e.g., horizontal for Left/Right)
 *   - perpDist: perpendicular distance from center line (e.g., vertical for Left/Right)
 *   - PERP_WEIGHT: multiplier that penalizes off-center nodes (default: 3)
 *   - Lower score = better candidate
 *
 * EXAMPLE (navigating Right, PERP_WEIGHT=3):
 *   Node A at (100, 50):  score = 100 + 3×50 = 250
 *   Node B at (150, 0):   score = 150 + 3×0  = 150  ← Winner (aligned)
 *   Node C at (50, 80):   score = 50 + 3×80  = 290  (close but too off-center)
 *
 * DIRECTION FILTER (45° cone):
 *   Only nodes within 45° of the navigation axis are considered.
 *   This means perpDist must be <= axialDist (tan(45°) = 1).
 *   - Right: dx > 0 AND |dy| <= dx
 *   - Left:  dx < 0 AND |dy| <= |dx|
 *   - Down:  dy > 0 AND |dx| <= dy
 *   - Up:    dy < 0 AND |dx| <= |dy|
 */
function findNodeInDirection(
  currentNodeId: string,
  nodes: Record<string, FlowNode>,
  reactFlowNodes: ReactFlowNode[],
  dir: number
): string | null {
  const currentNode = nodes[currentNodeId];
  if (!currentNode) return null;

  const rfNodes = reactFlowNodes;
  const len = rfNodes.length;

  // Find current RF node position and dimensions
  let cx = 0, cy = 0, currentIdx = -1;
  for (let i = 0; i < len; i++) {
    const rf = rfNodes[i];
    if (rf.id === currentNodeId) {
      cx = rf.position.x + (rf.width || 200) * 0.5;
      cy = rf.position.y + (rf.height || 80) * 0.5;
      currentIdx = i;
      break;
    }
  }

  const currentRoutes = currentNode.routes;
  const isHorizontal = dir === DIR_LEFT || dir === DIR_RIGHT;
  const isPositive = dir === DIR_RIGHT || dir === DIR_DOWN;

  // Pre-compute set of outgoing route targets for O(1) lookup
  let routeTargets: Set<string> | null = null;
  if (currentRoutes && currentRoutes.length > 0) {
    routeTargets = new Set();
    for (let i = 0; i < currentRoutes.length; i++) {
      const target = currentRoutes[i].target_node;
      if (target) routeTargets.add(target);
    }
  }

  let bestId: string | null = null;
  let bestScore = Infinity;

  for (let i = 0; i < len; i++) {
    if (i === currentIdx) continue;

    const rf = rfNodes[i];
    const node = nodes[rf.id];
    if (!node || node.type === "END") continue;

    // Calculate delta to candidate center
    const dx = rf.position.x + (rf.width || 200) * 0.5 - cx;
    const dy = rf.position.y + (rf.height || 80) * 0.5 - cy;

    // Calculate axial and perpendicular distances
    const axial = isHorizontal ? dx : dy;
    const perp = isHorizontal ? dy : dx;
    const axialDist = axial > 0 ? axial : -axial;
    const perpDist = perp > 0 ? perp : -perp;

    // Direction filter (45° cone): node must be in correct direction
    // AND within 45° of axis (perpDist <= axialDist, since tan(45°) = 1)
    if (isPositive ? axial <= 0 : axial >= 0) continue;
    if (perpDist > axialDist) continue;

    // Weighted distance score: lower is better
    let score = axialDist + PERP_WEIGHT * perpDist;

    // Early exit: if base score can't beat best, skip connectivity checks
    if (score >= bestScore) continue;

    // Connectivity bonus: O(1) lookup using pre-computed Set
    if (routeTargets && routeTargets.has(rf.id)) {
      score -= CONNECTIVITY_BONUS;
    }

    // Lazy reverse connection check (only if score is close to best)
    if (score >= bestScore - CONNECTIVITY_BONUS) {
      const nodeRoutes = node.routes;
      if (nodeRoutes) {
        const routesLen = nodeRoutes.length;
        for (let j = 0; j < routesLen; j++) {
          if (nodeRoutes[j].target_node === currentNodeId) {
            score -= CONNECTIVITY_BONUS;
            break;
          }
        }
      }
    }

    if (score < bestScore) {
      bestScore = score;
      bestId = rf.id;
    }
  }

  return bestId;
}

export function findNodeAbove(
  currentNodeId: string,
  nodes: Record<string, FlowNode>,
  reactFlowNodes: ReactFlowNode[]
): string | null {
  return findNodeInDirection(currentNodeId, nodes, reactFlowNodes, DIR_UP);
}

export function findNodeBelow(
  currentNodeId: string,
  nodes: Record<string, FlowNode>,
  reactFlowNodes: ReactFlowNode[]
): string | null {
  return findNodeInDirection(currentNodeId, nodes, reactFlowNodes, DIR_DOWN);
}

export function findNodeLeft(
  currentNodeId: string,
  nodes: Record<string, FlowNode>,
  reactFlowNodes: ReactFlowNode[]
): string | null {
  return findNodeInDirection(currentNodeId, nodes, reactFlowNodes, DIR_LEFT);
}

export function findNodeRight(
  currentNodeId: string,
  nodes: Record<string, FlowNode>,
  reactFlowNodes: ReactFlowNode[]
): string | null {
  return findNodeInDirection(currentNodeId, nodes, reactFlowNodes, DIR_RIGHT);
}
