import dagre from "dagre";
import type { Flow, FlowNode, NodeType, Route } from "./types";
import { getConditionLabel, canAddRoute, isBranchingNode, getDefaultCondition } from "./routeConditionUtils";
import { getRouteHandleInfo, HANDLE_POSITIONS } from "./handlePositioning";
import { snapToGrid } from "@/utils/canvasPositioningUtils";

// Type aliases for reactflow (v11 export issues)
type Node = any;
type Edge = any;

// Constants for layout configuration
const NODE_WIDTH = 200;
const NODE_HEIGHT = 80;
const STUB_LENGTH = 30;

// Spacing constants for node insertion
const LINEAR_SPACING = 180;      // 380px total gap for linear nodes (PROMPT, TEXT)
const BRANCHING_SPACING = 300;   // 500px total gap for branching nodes (MENU, API_ACTION, LOGIC_EXPRESSION)
const VERTICAL_SPACING = 150;    // Vertical gap between branching routes

// Dagre layout spacing (used for auto-layout)
const DAGRE_HORIZONTAL_SPACING = 150;
const DAGRE_VERTICAL_SPACING = 100;


/**
 * Get descendants following only right-side children at each level.
 * Left-side children (x < parent.x + NODE_WIDTH) are on wrapped rows and skipped entirely,
 * along with all their descendants.
 */
function getRightSideDescendants(nodes: Record<string, FlowNode>, startNodeId: string): Set<string> {
  const descendants = new Set<string>();
  const queue = [startNodeId];
  const visited = new Set<string>();

  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    if (visited.has(nodeId)) continue;
    visited.add(nodeId);

    const node = nodes[nodeId];
    if (!node?.routes || !node.position) continue;

    const parentRightEdge = node.position.x + NODE_WIDTH;

    for (const route of node.routes) {
      if (route.target_node && !visited.has(route.target_node)) {
        const child = nodes[route.target_node];
        // Only follow right-side children (left-side are on wrapped rows)
        if (child?.position && child.position.x >= parentRightEdge) {
          descendants.add(route.target_node);
          queue.push(route.target_node);
        }
        // Left-side children and all their descendants are skipped
      }
    }
  }

  return descendants;
}

// Node type display labels for name generation
const NODE_TYPE_LABELS: Record<NodeType, string> = {
  PROMPT: "Prompt",
  MENU: "Menu",
  API_ACTION: "API Action",
  LOGIC_EXPRESSION: "Logic",
  TEXT: "Text",
};

/**
 * Generate an auto-incremented name for a node based on its type and existing nodes
 * @param type The type of the node
 * @param existingNodes Object containing all existing flow nodes
 * @returns A formatted name like "Prompt 1", "Menu 2", etc.
 */
export function generateNodeName(
  type: NodeType,
  existingNodes: Record<string, FlowNode>
): string {
  const label = NODE_TYPE_LABELS[type];

  // Get all existing node names
  const existingNames = new Set(
    Object.values(existingNodes).map((n) => n.name)
  );

  // Start counter at number of same-type nodes + 1
  const sameTypeNodes = Object.values(existingNodes).filter(
    (n) => n.type === type
  );
  let counter = sameTypeNodes.length + 1;

  // Keep incrementing until we find a unique name
  let candidateName = `${label} ${counter}`;
  while (existingNames.has(candidateName)) {
    counter++;
    candidateName = `${label} ${counter}`;
  }

  return candidateName;
}

// Default node configurations
export const DEFAULT_NODE_CONFIGS: Record<NodeType, any> = {
  PROMPT: {
    type: "PROMPT",
    text: "Enter your prompt text",
    save_to_variable: "user_input",
  },
  MENU: {
    type: "MENU",
    text: "Select an option",
    source_type: "STATIC",
    static_options: [
      {
        label: "Option 1",
      },
    ],
  },
  API_ACTION: {
    type: "API_ACTION",
    request: {
      method: "GET",
      url: "",
    },
  },
  LOGIC_EXPRESSION: {
    type: "LOGIC_EXPRESSION",
  },
  TEXT: {
    type: "TEXT",
    text: "Your text here",
  },
};

/**
 * Convert backend flow JSON to React Flow nodes and edges
 */
export function convertFlowToReactFlow(flowJson: Flow): {
  nodes: Node[];
  edges: Edge[];
} {
  if (!flowJson || !flowJson.nodes) {
    return { nodes: [], edges: [] };
  }

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // Convert each flow node to React Flow node
  Object.entries(flowJson.nodes)
    .forEach(([nodeId, flowNode]) => {
    nodes.push({
      id: nodeId,
      type: flowNode.type,
      position: flowNode.position, // Use stored position from flow data
      data: {
        config: flowNode.config,
      },
    });

    // Determine if stub edge should be shown (route capacity remaining)
    const hasStub = shouldShowStub(flowNode);

    // Prepare for unified handle calculation (includes stub if present)
    let tempNode = flowNode;
    let tempNodes = flowJson.nodes;
    let stubTargetId: string | undefined;

    if (hasStub) {
      stubTargetId = `stub-target-${nodeId}`;
      // Count routes for stub positioning
      const visibleRouteCount = flowNode.routes?.length || 0;

      // Position stub to guide handle assignment (right → bottom → top priority)
      const initialStubPosition = calculateInitialStubPosition(flowNode, visibleRouteCount);

      // Add stub as temporary route for unified handle calculation
      tempNode = {
        ...flowNode,
        routes: [...(flowNode.routes || []), { condition: 'stub', target_node: stubTargetId }]
      };
      tempNodes = {
        ...flowJson.nodes,
        [stubTargetId]: {
          id: stubTargetId,
          type: 'TEXT' as NodeType, // Use TEXT as placeholder type for stub targets
          name: 'stub',
          config: { type: 'TEXT', text: '' },
          position: initialStubPosition
        } as FlowNode
      };
    }

    // Convert routes to edges (using unified handle calculation if stub exists)
    if (flowNode.routes && flowNode.routes.length > 0) {
      // Helper to estimate label height based on text length
      const estimateLabelHeight = (label: string | undefined): number => {
        if (!label) return 0;
        const charsPerLine = 25; // ~25 chars per line at 9px font, 150px max-width
        const lineHeight = 10;
        const maxLines = 3; // Labels are clamped to 3 lines in UI
        const lines = Math.min(Math.ceil(label.length / charsPerLine) || 1, maxLines);
        return (lines - 1) * lineHeight;
      };

      // First pass: collect route info with handle indices and labels
      const routeInfos: Array<{
        index: number;
        route: typeof flowNode.routes[0];
        handleInfo: ReturnType<typeof getRouteHandleInfo>;
        handleIndex: number;
        handleSide: string;
        label: string | undefined;
        shouldShowLabel: boolean;
      }> = [];

      flowNode.routes.forEach((route, index) => {
        const friendlyLabel = getConditionLabel(
          flowNode.type,
          route.condition,
          flowNode.config
        );

        const isBranching = isBranchingNode(flowNode.type, flowNode.config);
        const isTrueCondition = route.condition.trim().toLowerCase() === "true";

        const shouldShowLabel =
          flowNode.type === "LOGIC_EXPRESSION" ||
          (isBranching && !isTrueCondition) ||
          (!isTrueCondition && friendlyLabel !== "Next");

        const handleInfo = getRouteHandleInfo(tempNode, index, tempNodes);
        const handleParts = handleInfo.sourceHandle.split('-');
        const handleSide = handleParts[0];
        const handleIndex = parseInt(handleParts[1], 10) || 0;

        routeInfos.push({
          index,
          route,
          handleInfo,
          handleIndex,
          handleSide,
          label: shouldShowLabel ? friendlyLabel : undefined,
          shouldShowLabel,
        });
      });

      // Group by handle side and sort by handle index within each side
      const bySide: Record<string, typeof routeInfos> = {};
      for (const info of routeInfos) {
        if (!bySide[info.handleSide]) bySide[info.handleSide] = [];
        bySide[info.handleSide].push(info);
      }
      for (const side of Object.keys(bySide)) {
        bySide[side].sort((a, b) => a.handleIndex - b.handleIndex);
      }

      // Calculate cumulative label offsets per side
      // Each edge's offset includes its own label height (so long labels push themselves out)
      const cumulativeOffsets = new Map<number, number>(); // routeIndex -> cumulativeOffset
      for (const side of Object.keys(bySide)) {
        let cumulative = 0;
        for (const info of bySide[side]) {
          cumulative += estimateLabelHeight(info.label);
          cumulativeOffsets.set(info.index, cumulative);
        }
      }

      // Second pass: create edges with cumulative offsets
      for (const info of routeInfos) {
        edges.push({
          id: `${nodeId}-${info.route.target_node}-${info.index}`,
          source: nodeId,
          target: info.route.target_node,
          sourceHandle: info.handleInfo.sourceHandle,
          targetHandle: info.handleInfo.targetHandle,
          sourcePosition: info.handleInfo.sourcePosition,
          targetPosition: info.handleInfo.targetPosition,
          label: info.label,
          type: "default",
          animated: false,
          markerEnd: {
            type: 'arrowclosed',
            width: 12,
            height: 12,
            color: 'var(--muted-foreground)',
          },
          style: {
            strokeWidth: 2,
            stroke: 'var(--muted-foreground)',
          },
          data: {
            handleIndex: info.handleIndex,
            cumulativeLabelOffset: cumulativeOffsets.get(info.index) ?? 0,
          },
        });
      }
    }

    // Create stub edge if node has route capacity
    if (hasStub && stubTargetId) {
      // Stub is appended after all original routes in tempNode.routes
      const stubRouteIndex = flowNode.routes?.length || 0;

      // Get actual handle assignment from unified calculation
      const stubHandleInfo = getRouteHandleInfo(tempNode, stubRouteIndex, tempNodes);

      // Position stub perpendicular to assigned handle
      const perpendicularPosition = calculatePerpendicularStubPosition(flowNode, stubHandleInfo);

      // Create invisible stub target node
      nodes.push({
        id: stubTargetId,
        type: 'default',
        position: perpendicularPosition,
        data: { isStubTarget: true },
        style: {
          opacity: 0,
          pointerEvents: 'none',
          width: 1,
          height: 1,
        },
        draggable: false,
        selectable: false,
        connectable: false,
      });

      // Create stub edge
      edges.push({
        id: `stub-${nodeId}`,
        source: nodeId,
        target: stubTargetId,
        sourceHandle: stubHandleInfo.sourceHandle,
        targetHandle: stubHandleInfo.targetHandle,
        sourcePosition: stubHandleInfo.sourcePosition,
        targetPosition: stubHandleInfo.targetPosition,
        type: "stub",
        animated: false,
        data: {
          sourceNodeId: nodeId,
        },
        style: {
          strokeWidth: 2,
          stroke: 'var(--muted-foreground)',
        },
      });
    }
  });

  return { nodes, edges };
}

/**
 * Calculate node positions using Dagre (horizontal layout)
 */
export function calculateLayout(nodes: Node[], edges: Edge[]): Node[] {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  // Configure graph for horizontal left-to-right layout
  dagreGraph.setGraph({
    rankdir: "LR", // Left to Right
    nodesep: DAGRE_HORIZONTAL_SPACING,
    ranksep: DAGRE_VERTICAL_SPACING,
    marginx: 50,
    marginy: 50,
  });

  // Add nodes to dagre graph
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, {
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    });
  });

  // Add edges to dagre graph
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Calculate layout
  dagre.layout(dagreGraph);

  // Update node positions based on dagre layout
  return nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    };
  });
}

/**
 * Insertion point type
 */
export interface InsertionPoint {
  id: string;
  position: "start" | "after" | "before" | "between";
  targetNodeId?: string;
  x: number;
  y: number;
}

/**
 * Find valid insertion points for "+" buttons
 */
export function getInsertionPoints(
  flowJson: Flow,
  layoutNodes: Node[]
): InsertionPoint[] {
  const insertionPoints: InsertionPoint[] = [];

  if (!flowJson || !flowJson.nodes) {
    // If no nodes, show start insertion point
    return [
      {
        id: "start",
        position: "start",
        x: 100,
        y: 200,
      },
    ];
  }

  const nodeCount = Object.keys(flowJson.nodes).length;

  // If no nodes, show start insertion point
  if (nodeCount === 0) {
    return [
      {
        id: "start",
        position: "start",
        x: 100,
        y: 200,
      },
    ];
  }

  // For each node, add an "after" insertion point
  layoutNodes.forEach((node) => {
    insertionPoints.push({
      id: `after-${node.id}`,
      position: "after",
      targetNodeId: node.id,
      x: node.position.x + NODE_WIDTH + 30,
      y: node.position.y + NODE_HEIGHT / 2,
    });
  });

  // Add start insertion point if no start node
  if (!flowJson.start_node_id || !flowJson.nodes[flowJson.start_node_id]) {
    insertionPoints.push({
      id: "start",
      position: "start",
      x: 100,
      y: 200,
    });
  }

  return insertionPoints;
}

/**
 * Insert new node at specific position in flow JSON
 * Returns both the updated flow and the new node ID
 *
 * @param routeIndex - Optional: When inserting "after" a branching node, specifies which route to insert on
 *                     If provided, the new node will be inserted INTO that specific route (universal overtaking)
 *                     If not provided, a new branch will be created (old behavior)
 */
export function insertNodeInFlow(
  flowJson: Flow,
  position: "start" | "after" | "before" | "between",
  targetNodeId: string | undefined,
  newNodeType: NodeType,
  customCondition?: string,
  routeIndex?: number
): { flow: Flow; newNodeId: string } {
  const newNodeId = `node_${Date.now()}`;

  // Deep clone the flow JSON to avoid mutations
  const updatedFlow: Flow = JSON.parse(JSON.stringify(flowJson));

  // Initialize nodes if not present
  if (!updatedFlow.nodes) {
    updatedFlow.nodes = {};
  }

  // Generate the node name based on existing nodes
  const nodeName = generateNodeName(newNodeType, updatedFlow.nodes);

  // Calculate initial position for new node based on insertion context
  let initialPosition: { x: number; y: number };

  if (position === "after" && targetNodeId) {
    const targetNode = updatedFlow.nodes[targetNodeId];
    if (targetNode?.position) {
      let verticalOffset = 0;

      const isAddingNewRoute =
        routeIndex === undefined ||
        routeIndex < 0 ||
        !targetNode.routes ||
        routeIndex >= targetNode.routes.length;

      const isBranching = isBranchingNode(targetNode.type, targetNode.config);

      // Helper: get children that are to the right of the parent (left-side nodes are on wrapped rows, ignore them)
      const parentRightEdge = targetNode.position.x + NODE_WIDTH;
      const getRightSideChildren = () => targetNode.routes
        ?.map(route => updatedFlow.nodes[route.target_node])
        .filter(child =>
          child?.position &&
          child.position.x >= parentRightEdge
        ) ?? [];

      if (!isAddingNewRoute && targetNode.routes && routeIndex !== undefined) {
        // OVERTAKING existing route: inherit Y position from the node being overtaken
        // But only if it's to the right of parent (left-side nodes are on wrapped rows)
        const existingRoute = targetNode.routes[routeIndex];
        const existingTargetNode = updatedFlow.nodes[existingRoute.target_node];
        const isRightSide = existingTargetNode?.position &&
          existingTargetNode.position.x >= parentRightEdge;

        if (existingTargetNode?.position && isRightSide) {
          verticalOffset = existingTargetNode.position.y - targetNode.position.y;
        } else if (!isRightSide) {
          // Overtaking a left-side node: position below right-side children (like a new branch)
          const rightSideChildren = getRightSideChildren();
          if (rightSideChildren.length > 0) {
            const maxY = Math.max(...rightSideChildren.map(c => c!.position!.y));
            verticalOffset = maxY - targetNode.position.y + VERTICAL_SPACING;
          }
        }
      } else if (targetNode.routes && isBranching && isAddingNewRoute) {
        // NEW route on branching node: position below right-side children only
        const rightSideChildren = getRightSideChildren();

        if (rightSideChildren.length > 0) {
          const maxY = Math.max(...rightSideChildren.map(c => c!.position!.y));
          verticalOffset = maxY - targetNode.position.y + VERTICAL_SPACING;
        }
      }

      const horizontalSpacing = isBranching ? BRANCHING_SPACING : LINEAR_SPACING;

      initialPosition = {
        x: targetNode.position.x + NODE_WIDTH + horizontalSpacing,
        y: targetNode.position.y + verticalOffset,
      };
    } else {
      initialPosition = { x: 100, y: 200 }; // Fallback position
    }
  } else if (position === "before" && targetNodeId) {
    const targetNode = updatedFlow.nodes[targetNodeId];
    if (targetNode?.position) {
      // Place new node to the left of target
      initialPosition = {
        x: targetNode.position.x - NODE_WIDTH - LINEAR_SPACING,
        y: targetNode.position.y,
      };
    } else {
      initialPosition = { x: 100, y: 200 }; // Fallback position
    }
  } else if (position === "start") {
    // Place at origin or to the left of existing start
    if (
      updatedFlow.start_node_id &&
      updatedFlow.nodes[updatedFlow.start_node_id]?.position
    ) {
      const existingStart = updatedFlow.nodes[updatedFlow.start_node_id];
      initialPosition = {
        x: existingStart.position.x - NODE_WIDTH - LINEAR_SPACING,
        y: existingStart.position.y,
      };
    } else {
      initialPosition = { x: 100, y: 200 };
    }
  } else {
    // Default fallback position
    initialPosition = { x: 100, y: 200 };
  }

  const newNode: FlowNode = {
    id: newNodeId,
    type: newNodeType,
    name: nodeName,
    config: DEFAULT_NODE_CONFIGS[newNodeType],
    routes: [], // Terminal nodes simply have empty routes
    position: {
      x: snapToGrid(initialPosition.x),
      y: snapToGrid(initialPosition.y),
    },
  };

  // Determine which nodes to shift (only descendants of the specific route, respects graph structure)
  const nodesToShift = new Set<string>();

  if (position === "after" && targetNodeId) {
    const targetNode = updatedFlow.nodes[targetNodeId];
    if (targetNode?.routes && targetNode.routes.length > 0) {
      // Determine which route we're inserting into
      let effectiveRouteIndex: number | undefined = routeIndex;

      // For non-branching nodes, no routeIndex is passed but they implicitly insert into route[0]
      if (routeIndex === undefined && !isBranchingNode(targetNode.type, targetNode.config)) {
        effectiveRouteIndex = 0;
      }

      if (effectiveRouteIndex !== undefined && effectiveRouteIndex >= 0 && effectiveRouteIndex < targetNode.routes.length) {
        // Inserting into a SPECIFIC route: only shift that route's target and its descendants
        // But first check if branch root is right-side (left-side branches are on wrapped rows - ignore entirely)
        const specificRoute = targetNode.routes[effectiveRouteIndex];
        const branchRoot = specificRoute?.target_node ? updatedFlow.nodes[specificRoute.target_node] : null;
        const parentRightEdgeForShift = (targetNode.position?.x ?? 0) + NODE_WIDTH;
        const isBranchRightSide = branchRoot?.position && branchRoot.position.x >= parentRightEdgeForShift;

        if (specificRoute?.target_node && isBranchRightSide) {
          // Right-side branch: shift root + right-side descendants only
          // (left-side descendants at any level are on wrapped rows, skip them)
          nodesToShift.add(specificRoute.target_node);
          const descendants = getRightSideDescendants(updatedFlow.nodes, specificRoute.target_node);
          descendants.forEach(id => nodesToShift.add(id));
        }
        // Left-side branch: skip entirely (it's on a wrapped row, not our concern)
      }
      // If no effectiveRouteIndex (adding new branch to branching node), don't shift anything
    }
  } else if (position === "before" && targetNodeId) {
    // For "before": shift the target and its right-side descendants only
    // (left-side descendants are on wrapped rows, not our concern)
    nodesToShift.add(targetNodeId);
    const descendants = getRightSideDescendants(updatedFlow.nodes, targetNodeId);
    descendants.forEach(id => nodesToShift.add(id));
  } else if (position === "start" && updatedFlow.start_node_id) {
    // For "start": shift existing start and its right-side descendants only
    // (left-side descendants are on wrapped rows, not our concern)
    nodesToShift.add(updatedFlow.start_node_id);
    const descendants = getRightSideDescendants(updatedFlow.nodes, updatedFlow.start_node_id);
    descendants.forEach(id => nodesToShift.add(id));
  }

  // Calculate the minimum shift needed based on new node's position
  // Gap from new node to its descendants always uses LINEAR_SPACING (branching spacing is only for parent → new node)
  const minRequiredX = newNode.position.x + NODE_WIDTH + LINEAR_SPACING;

  // Find the leftmost node to shift to determine shift amount
  let minDescendantX = Infinity;
  for (const nodeId of nodesToShift) {
    const node = updatedFlow.nodes[nodeId];
    if (node?.position && node.position.x < minDescendantX) {
      minDescendantX = node.position.x;
    }
  }

  // Calculate shift: only shift if nodes are too close to new node
  const shiftAmount = minDescendantX < Infinity
    ? Math.max(0, minRequiredX - minDescendantX)
    : 0;

  // Apply uniform shift (preserves relative spacing)
  if (shiftAmount > 0) {
    for (const nodeId of nodesToShift) {
      const node = updatedFlow.nodes[nodeId];
      if (node?.position) {
        updatedFlow.nodes[nodeId] = {
          ...node,
          position: {
            x: snapToGrid(node.position.x + shiftAmount),
            y: snapToGrid(node.position.y),
          },
        };
      }
    }
  }

  switch (position) {
    case "start":
      // Insert as start node
      if (
        updatedFlow.start_node_id &&
        updatedFlow.nodes[updatedFlow.start_node_id]
      ) {
        // Connect new node to existing start node
        newNode.routes = [
          {
            condition: customCondition || getDefaultCondition(newNode, []),
            target_node: updatedFlow.start_node_id,
          },
        ];
      }
      updatedFlow.start_node_id = newNodeId;
      updatedFlow.nodes[newNodeId] = newNode;
      break;

    case "after":
      if (!targetNodeId) {
        throw new Error("targetNodeId is required for 'after' position");
      }

      const targetNode = updatedFlow.nodes[targetNodeId];
      if (!targetNode) {
        throw new Error(`Target node ${targetNodeId} not found`);
      }

      // Insert node after target
      if (targetNode.routes && targetNode.routes.length > 0) {
        // Determine if this is a branching node type
        const isBranching = isBranchingNode(targetNode.type, targetNode.config);

        if (isBranching) {
          // Check if we're inserting ON a specific route (universal overtaking)
          if (
            routeIndex !== undefined &&
            routeIndex >= 0 &&
            routeIndex < targetNode.routes.length
          ) {
            // UNIVERSAL ROUTE OVERTAKING: Insert INTO existing route
            const existingRoute = targetNode.routes[routeIndex];
            const originalTarget = existingRoute.target_node;
            const originalCondition = existingRoute.condition;

            // Parent's route now points to new node (preserving original condition)
            targetNode.routes[routeIndex] = {
              condition: originalCondition,
              target_node: newNodeId,
            };

            // New node routes to original target
            newNode.routes = [
              {
                condition: getDefaultCondition(newNode, []),
                target_node: originalTarget,
              },
            ];
          } else {
            // Check if we can add another route to this node
            if (!canAddRoute(targetNode)) {
              throw new Error(
                `Cannot add more routes to this ${targetNode.type} node (maximum reached)`
              );
            }

            // Create new branch (leaf node with empty routes = terminal)
            newNode.routes = [];

            // For LOGIC_EXPRESSION nodes, generate a unique condition placeholder
            let branchCondition = customCondition;
            if (!branchCondition && targetNode.type === "LOGIC_EXPRESSION") {
              // Generate unique condition placeholder for LOGIC_EXPRESSION
              const existingConditions = targetNode.routes.map(r => r.condition.toLowerCase());
              let counter = 1;
              do {
                branchCondition = `condition_${counter}`;
                counter++;
              } while (existingConditions.includes(branchCondition.toLowerCase()));
            } else if (!branchCondition) {
              branchCondition = getDefaultCondition(targetNode, targetNode.routes || []);
            }

            // Add new branch route
            targetNode.routes.push({
              condition: branchCondition,
              target_node: newNodeId,
            });
          }
        } else {
          // Non-branching nodes: linear insertion between target and its route
          const firstRoute = targetNode.routes[0];
          newNode.routes = [
            {
              condition: getDefaultCondition(newNode, []),
              target_node: firstRoute.target_node,
            },
          ];
          // Replace the first route (prevents duplicate routes)
          targetNode.routes[0] = {
            condition: customCondition || "true",
            target_node: newNodeId,
          };
        }
      } else {
        // If target has no routes, connect it to new node
        targetNode.routes = [
          {
            condition: customCondition || getDefaultCondition(targetNode, []),
            target_node: newNodeId,
          },
        ];
      }

      updatedFlow.nodes[newNodeId] = newNode;
      break;

    case "before":
      if (!targetNodeId) {
        throw new Error("targetNodeId is required for 'before' position");
      }

      // Find all nodes that route to target and update them to route to new node
      Object.values(updatedFlow.nodes).forEach((node) => {
        if (node.routes) {
          node.routes.forEach((route) => {
            if (route.target_node === targetNodeId) {
              route.target_node = newNodeId;
            }
          });
        }
      });

      // New node routes to target
      newNode.routes = [
        {
          condition: getDefaultCondition(newNode, []),
          target_node: targetNodeId,
        },
      ];

      // Update start_node_id if target was the start node
      if (updatedFlow.start_node_id === targetNodeId) {
        updatedFlow.start_node_id = newNodeId;
      }

      updatedFlow.nodes[newNodeId] = newNode;
      break;

    case "between":
      // This is complex - for now, treat it like "after"
      if (!targetNodeId) {
        throw new Error("targetNodeId is required for 'between' position");
      }

      const betweenTargetNode = updatedFlow.nodes[targetNodeId];
      if (!betweenTargetNode) {
        throw new Error(`Target node ${targetNodeId} not found`);
      }

      if (betweenTargetNode.routes && betweenTargetNode.routes.length > 0) {
        const firstRoute = betweenTargetNode.routes[0];
        newNode.routes = [
          {
            condition: getDefaultCondition(newNode, []),
            target_node: firstRoute.target_node,
          },
        ];
        betweenTargetNode.routes[0] = {
          ...firstRoute,
          target_node: newNodeId,
        };
      } else {
        betweenTargetNode.routes = [
          {
            condition: customCondition || getDefaultCondition(betweenTargetNode, []),
            target_node: newNodeId,
          },
        ];
      }

      updatedFlow.nodes[newNodeId] = newNode;
      break;
  }

  return { flow: updatedFlow, newNodeId };
}

/**
 * Remove duplicate target routes from all nodes
 * If a node has multiple routes pointing to the same target, keep only the first one
 */
function removeDuplicateTargetRoutes(flow: Flow): void {
  Object.values(flow.nodes).forEach((node) => {
    if (!node.routes || node.routes.length <= 1) return;

    // Group routes by target
    const routesByTarget = new Map<string, Route[]>();
    node.routes.forEach((route) => {
      const existing = routesByTarget.get(route.target_node) || [];
      existing.push(route);
      routesByTarget.set(route.target_node, existing);
    });

    const uniqueRoutes: typeof node.routes = [];

    // For each target, keep only one route (prioritize "true" condition)
    routesByTarget.forEach((routes) => {
      if (routes.length === 1) {
        // No duplicates for this target
        uniqueRoutes.push(routes[0]);
      } else {
        // Duplicates exist - prioritize "true" (catch-all) condition
        const trueRoute = routes.find(
          (r) => r.condition.trim().toLowerCase() === "true"
        );
        uniqueRoutes.push(trueRoute || routes[0]);
      }
    });

    // Update routes only if duplicates were found
    if (uniqueRoutes.length < node.routes.length) {
      node.routes = uniqueRoutes;
    }
  });
}

/**
 * Count how many nodes have routes pointing to the target node
 */
function countIncomingEdges(flow: Flow, targetNodeId: string): number {
  let count = 0;
  Object.values(flow.nodes).forEach((node) => {
    node.routes?.forEach((route) => {
      if (route.target_node === targetNodeId) {
        count++;
      }
    });
  });
  return count;
}

/**
 * Get all shiftable descendants from a starting node
 * Only includes nodes with exactly 1 incoming edge (single parent)
 * Stops at merge points (nodes with 2+ incoming edges)
 */
function getShiftableDescendants(flow: Flow, startNodeId: string): Set<string> {
  const toShift = new Set<string>();
  const queue = [startNodeId];
  const visited = new Set<string>();

  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    if (visited.has(nodeId)) continue;
    visited.add(nodeId);

    const node = flow.nodes[nodeId];
    if (!node) continue;

    // Count incoming edges to this node
    const incomingCount = countIncomingEdges(flow, nodeId);

    if (incomingCount === 1) {
      // Single parent - shift this node
      toShift.add(nodeId);

      // Continue traversing to children
      node.routes?.forEach((route) => {
        queue.push(route.target_node);
      });
    }
    // If incomingCount > 1 (merge point), stop traversing
    // Don't shift this node or anything beyond it
  }

  return toShift;
}

/**
 * Delete node from flow JSON
 * Handles: start node protection and branch node cascading
 */
export function deleteNodeFromFlow(flowJson: Flow, nodeId: string): Flow {
  const updatedFlow: Flow = JSON.parse(JSON.stringify(flowJson));

  if (!updatedFlow.nodes[nodeId]) {
    throw new Error(`Node ${nodeId} not found`);
  }

  const nodeToDelete = updatedFlow.nodes[nodeId];

  // Capture deleted node's X position for later shifting
  const deletedNodeX = nodeToDelete.position?.x;

  // Prevent deletion of start node
  if (updatedFlow.start_node_id === nodeId) {
    throw new Error(
      "Cannot delete the start node - it is the entry point of the flow"
    );
  }

  // Branching nodes with multiple routes cannot be deleted directly.
  // User must delete the child branches first.
  const hasMultipleRoutes = (nodeToDelete.routes?.length || 0) > 1;

  if (isBranchingNode(nodeToDelete.type, nodeToDelete.config) && hasMultipleRoutes) {
    throw new Error(
      `Cannot delete node with multiple branches. Delete the connected nodes first.`
    );
  }

  // Original deletion logic for normal nodes
  // If the node points to itself (self-loop), treat as terminal — redirecting parents to a
  // deleted self-referencing node would leave them with a dangling route.
  const rawTargetNodeId = nodeToDelete.routes?.[0]?.target_node;
  const targetNodeId = rawTargetNodeId === nodeId ? undefined : rawTargetNodeId;
  const targetNode = targetNodeId ? updatedFlow.nodes[targetNodeId] : null;

  // Find all nodes that route to this node and update them
  Object.values(updatedFlow.nodes).forEach((node) => {
    if (!node.routes) return;

    // Check if this parent is a branching node
    const parentIsBranching = isBranchingNode(node.type, node.config);

    // For branching nodes with no target to redirect to, remove the route entirely
    // (the deleted node was terminal, so the parent becomes terminal on that branch)
    if (parentIsBranching && !targetNodeId) {
      node.routes = node.routes.filter((r) => r.target_node !== nodeId);
    } else {
      // Redirect routes to the deleted node's target
      node.routes.forEach((route) => {
        if (route.target_node === nodeId) {
          if (targetNodeId && targetNodeId !== node.id) {
            route.target_node = targetNodeId;
          } else {
            // Remove route: either no target (terminal) or redirect would create a self-loop
            node.routes = node.routes?.filter((r) => r.target_node !== nodeId);
          }
        }
      });
    }
  });

  // Update start_node_id if the deleted node was the start
  if (updatedFlow.start_node_id === nodeId) {
    updatedFlow.start_node_id = targetNodeId || "";
  }

  // Calculate shift amount based on next node's position
  let shiftAmount = 0;
  if (deletedNodeX !== undefined && targetNode?.position?.x !== undefined) {
    // The next node will take the deleted node's position
    // All other nodes shift by the distance the next node moved
    shiftAmount = targetNode.position.x - deletedNodeX;
  }

  // Delete the node
  delete updatedFlow.nodes[nodeId];

  // Remove any duplicate target routes created by rewiring
  removeDuplicateTargetRoutes(updatedFlow);

  // Shift nodes using graph-structure based algorithm
  // Only shifts single-parent descendants until merge points
  if (shiftAmount > 0 && targetNodeId && deletedNodeX !== undefined) {
    // Get all shiftable descendants (stops at merge points)
    const nodesToShift = getShiftableDescendants(updatedFlow, targetNodeId);

    // Shift all nodes in the chain (snapped to grid)
    nodesToShift.forEach((id) => {
      const node = updatedFlow.nodes[id];
      if (!node?.position) return;

      updatedFlow.nodes[id] = {
        ...node,
        position: {
          x: snapToGrid(node.position.x - shiftAmount),
          y: snapToGrid(node.position.y),
        },
      };
    });
  }

  return updatedFlow;
}

/**
 * Helper function to find the parent node that routes to the given nodeId
 */
function findParentNode(
  flow: Flow,
  targetNodeId: string
): { parentId: string; routeIndex: number } | null {
  // Check if it's the start node (no parent)
  if (flow.start_node_id === targetNodeId) {
    return null;
  }

  // Find which node routes to the target
  for (const [nodeId, node] of Object.entries(flow.nodes)) {
    if (node.routes) {
      const routeIndex = node.routes.findIndex(
        (route) => route.target_node === targetNodeId
      );
      if (routeIndex !== -1) {
        return { parentId: nodeId, routeIndex };
      }
    }
  }

  return null;
}

// Node types that collect user input (allow loops to be user-driven)
const INPUT_NODE_TYPES: NodeType[] = ["PROMPT", "MENU"];

/**
 * Check if adding an edge nodeToMove → targetNode would create a loop with no
 * user interaction. Such loops always crash the conversation after hitting the
 * auto-progression limit (10 steps), so they are blocked.
 *
 * Loops containing at least one PROMPT or MENU are allowed — the user drives
 * them and can break out by responding.
 *
 * Uses a path set (add on entry, remove on backtrack) so nodes explored in
 * dead-end branches can be revisited via other paths — matching the backend
 * algorithm in validators.py.
 *
 * @returns true if the move should be blocked (loop with no input node)
 */
function wouldCreateCircularReference(
  flow: Flow,
  nodeToMove: string,
  targetNode: string
): boolean {
  const inPath = new Set<string>();
  const cyclePath: string[] = [];

  function checkPath(currentId: string): boolean {
    if (currentId === nodeToMove) {
      cyclePath.push(currentId);
      return true;
    }
    if (inPath.has(currentId)) return false;

    inPath.add(currentId);
    cyclePath.push(currentId);

    const current = flow.nodes[currentId];
    if (!current?.routes) {
      cyclePath.pop();
      inPath.delete(currentId);
      return false;
    }

    for (const route of current.routes) {
      if (checkPath(route.target_node)) return true;
    }

    cyclePath.pop();
    inPath.delete(currentId);
    return false;
  }

  const hasCycle = checkPath(targetNode);

  if (!hasCycle) return false;

  // Check if cycle includes an input node - if so, allow it
  const hasInputNode = cyclePath.some((nodeId) => {
    const node = flow.nodes[nodeId];
    return node && INPUT_NODE_TYPES.includes(node.type);
  });

  // Block only if NO input node in cycle
  return !hasInputNode;
}

/**
 * Swap X positions of two nodes.
 */
function swapNodePositions(
  flow: Flow,
  nodeId1: string,
  nodeId2: string
): void {
  const node1 = flow.nodes[nodeId1];
  const node2 = flow.nodes[nodeId2];

  if (node1?.position && node2?.position) {
    const tempX = node1.position.x;
    node1.position.x = node2.position.x;
    node2.position.x = tempX;
  }
}

/**
 * Unified node reordering function.
 * Moves nodeToMove to be inserted after moveNextToNode at the specified route.
 *
 * @param flowJson - The flow to modify
 * @param nodeToMove - ID of node being moved (must have 1 route with condition "true")
 * @param moveNextToNode - ID of node to insert after
 * @param routeIndex - Which route of moveNextToNode to insert into (0-based)
 * @returns Updated flow or null if move is invalid
 *
 * @example
 * // BEFORE: A → B → C and D → E
 * // AFTER:  A → C and D → B → E
 * moveNode(flow, "B", "D", 0)
 */
export function moveNode(
  flowJson: Flow,
  nodeToMove: string,
  moveNextToNode: string,
  routeIndex: number
): Flow | null {
  // Fast validation before expensive deep clone
  const nodeToMoveObj = flowJson.nodes[nodeToMove];
  const moveNextToNodeObj = flowJson.nodes[moveNextToNode];

  if (!nodeToMoveObj || !moveNextToNodeObj) {
    return null;
  }

  if (
    !nodeToMoveObj.routes ||
    nodeToMoveObj.routes.length !== 1 ||
    nodeToMoveObj.routes[0].condition !== "true"
  ) {
    return null;
  }

  if (!moveNextToNodeObj.routes?.[routeIndex]) {
    return null;
  }

  // Validation passed - now deep clone
  const updatedFlow: Flow = JSON.parse(JSON.stringify(flowJson));
  const updatedNodeToMove = updatedFlow.nodes[nodeToMove];
  const updatedMoveNextToNode = updatedFlow.nodes[moveNextToNode];

  // Extract nodeToMove from current position first
  const parentInfo = findParentNode(updatedFlow, nodeToMove);
  const childOfMovingNode = updatedNodeToMove.routes![0].target_node;

  // If node's child is its own parent, extracting it would create a self-loop on the parent
  if (parentInfo && childOfMovingNode === parentInfo.parentId) return null;

  if (parentInfo) {
    updatedFlow.nodes[parentInfo.parentId].routes![parentInfo.routeIndex].target_node = childOfMovingNode;
  } else {
    updatedFlow.start_node_id = childOfMovingNode;
  }

  // NOW check for circular reference after extraction
  const targetAfterInsertion = updatedMoveNextToNode.routes![routeIndex].target_node;

  // Explicit self-loop guard — wouldCreateCircularReference allows cycles with input nodes
  // but a node routing to itself is never valid regardless of type
  if (targetAfterInsertion === nodeToMove) return null;

  if (wouldCreateCircularReference(updatedFlow, nodeToMove, targetAfterInsertion)) {
    return null;
  }

  // Insert nodeToMove after moveNextToNode
  updatedNodeToMove.routes![0].target_node = targetAfterInsertion;
  updatedNodeToMove.routes![0].condition = "true";
  updatedMoveNextToNode.routes![routeIndex].target_node = nodeToMove;

  // Position updates handled by wrappers

  return updatedFlow;
}

/**
 * Move a node one position earlier in the flow sequence (swap with previous node).
 */
export function moveNodeLeft(flowJson: Flow, nodeId: string): Flow | null {
  const parentInfo = findParentNode(flowJson, nodeId);
  if (!parentInfo) return null;

  const parent = flowJson.nodes[parentInfo.parentId];
  if (!parent.routes || parent.routes.length !== 1) return null;

  const grandparentInfo = findParentNode(flowJson, parentInfo.parentId);

  let result: Flow | null;

  if (grandparentInfo) {
    // Normal case: move after grandparent
    result = moveNode(flowJson, nodeId, grandparentInfo.parentId, grandparentInfo.routeIndex);
  } else {
    // Parent is START - manually swap to make nodeId the new START
    const clonedFlow: Flow = JSON.parse(JSON.stringify(flowJson));
    const node = clonedFlow.nodes[nodeId];
    const parentNode = clonedFlow.nodes[parentInfo.parentId];

    // Node must have exactly one route to be moveable
    if (!node.routes || node.routes.length !== 1) return null;

    // If node's child is the parent itself, swapping would create a self-loop on the parent
    const nodeChild = node.routes[0].target_node;
    if (nodeChild === parentInfo.parentId) return null;

    // Extract node from parent
    parentNode.routes![0].target_node = nodeChild;

    // Make node point to parent
    node.routes[0].target_node = parentInfo.parentId;
    node.routes[0].condition = "true";

    // Make node the new START
    clonedFlow.start_node_id = nodeId;
    result = clonedFlow;
  }

  if (result) {
    swapNodePositions(result, nodeId, parentInfo.parentId);
  }

  return result;
}

/**
 * Move a node one position later in the flow sequence (swap with next node).
 */
export function moveNodeRight(flowJson: Flow, nodeId: string): Flow | null {
  const currentNode = flowJson.nodes[nodeId];
  if (!currentNode?.routes || currentNode.routes.length !== 1) return null;

  const nextNodeId = currentNode.routes[0].target_node;
  const nextNode = flowJson.nodes[nextNodeId];
  if (!nextNode?.routes || nextNode.routes.length !== 1) return null;

  const result = moveNode(flowJson, nodeId, nextNodeId, 0);
  if (result) {
    swapNodePositions(result, nodeId, nextNodeId);
  }

  return result;
}

/**
 * Move a node to be inserted between two nodes connected by an edge.
 * Edge ID format: "sourceId-targetId-routeIndex"
 */
export function moveNodeBetween(
  flowJson: Flow,
  nodeId: string,
  edgeId: string
): Flow | null {
  const edgeParts = edgeId.split("-");
  if (edgeParts.length < 3) return null;

  const routeIndex = parseInt(edgeParts[edgeParts.length - 1], 10);
  const sourceNodeId = edgeParts.slice(0, edgeParts.length - 2).join("-");

  return moveNode(flowJson, nodeId, sourceNodeId, routeIndex);
}

/**
 * Determine if node should show stub edge based on route capacity.
 * Delegates to canAddRoute() for consistent logic across the codebase.
 */
function shouldShowStub(node: FlowNode): boolean {
  return canAddRoute(node);
}

/**
 * Calculate initial stub position to guide handle assignment
 * Priority: right (0-2 routes) → bottom (3-7 routes) → top (8+ routes)
 */
function calculateInitialStubPosition(
  sourceNode: FlowNode,
  routeCount: number
): { x: number; y: number } {
  const nodeX = sourceNode.position.x;
  const nodeY = sourceNode.position.y;

  // Right side: 3 handle slots
  if (routeCount < 3) {
    return {
      x: nodeX + NODE_WIDTH + STUB_LENGTH,
      y: nodeY,
    };
  }
  // Bottom side: 5 handle slots
  else if (routeCount < 8) {
    return {
      x: nodeX + (routeCount - 3) * 40,
      y: nodeY + NODE_HEIGHT + STUB_LENGTH,
    };
  }
  // Top side: overflow
  else {
    return {
      x: nodeX + NODE_WIDTH / 2,
      y: nodeY - STUB_LENGTH,
    };
  }
}

/**
 * Calculate perpendicular stub position from assigned handle
 * Extends STUB_LENGTH perpendicular from handle's center point
 */
function calculatePerpendicularStubPosition(
  sourceNode: FlowNode,
  handleInfo: { sourceHandle: string; sourcePosition: string }
): { x: number; y: number } {
  const [side, indexStr] = handleInfo.sourceHandle.split('-');
  const handleIndex = parseInt(indexStr, 10);

  // Handle is 12px (w-3 h-3), centered requires +6px offset
  // CSS top/left positions the edge, not center
  const HANDLE_CENTER_OFFSET = 6;

  const nodeX = sourceNode.position.x;
  const nodeY = sourceNode.position.y;

  switch (side) {
    case 'right': {
      const handlePos = HANDLE_POSITIONS.RIGHT[handleIndex]?.position ?? 0.5;
      return {
        x: nodeX + NODE_WIDTH + STUB_LENGTH,
        y: nodeY + handlePos * NODE_HEIGHT + HANDLE_CENTER_OFFSET,
      };
    }

    case 'top': {
      const handlePos = HANDLE_POSITIONS.TOP[handleIndex]?.position ?? 0.5;
      return {
        x: nodeX + handlePos * NODE_WIDTH + HANDLE_CENTER_OFFSET,
        y: nodeY - STUB_LENGTH,
      };
    }

    case 'bottom': {
      const handlePos = HANDLE_POSITIONS.BOTTOM[handleIndex]?.position ?? 0.5;
      return {
        x: nodeX + handlePos * NODE_WIDTH + HANDLE_CENTER_OFFSET,
        y: nodeY + NODE_HEIGHT + STUB_LENGTH,
      };
    }

    default:
      return {
        x: nodeX + NODE_WIDTH + STUB_LENGTH,
        y: nodeY + NODE_HEIGHT / 2,
      };
  }
}

/**
 * Connect a route from source node to an existing target node.
 * Used for creating cycles by dragging stub to existing node.
 */
export function connectRouteToExistingNode(
  flow: Flow,
  sourceNodeId: string,
  targetNodeId: string,
  condition: string
): Flow | null {
  const sourceNode = flow.nodes[sourceNodeId];
  if (!sourceNode) return null;

  // Prevent self-loops
  if (sourceNodeId === targetNodeId) return null;

  // Validate target node exists
  if (!flow.nodes[targetNodeId]) return null;

  // If route with this condition already exists, silently ignore
  const conditionExists = sourceNode.routes?.some(
    r => r.condition.trim().toLowerCase() === condition.trim().toLowerCase()
  );
  if (conditionExists) {
    return flow;
  }

  // If route to this target already exists, silently ignore (no duplicate target)
  const targetExists = sourceNode.routes?.some(
    r => r.target_node === targetNodeId
  );
  if (targetExists) {
    return flow;
  }

  // Validate: would this create an invalid cycle?
  if (wouldCreateCircularReference(flow, sourceNodeId, targetNodeId)) {
    return null; // Cycle without input node - not allowed
  }

  // Check if we can add another route to this node
  if (!canAddRoute(sourceNode)) {
    return null; // Max routes reached
  }

  // Add new route
  const updatedRoutes = [...(sourceNode.routes || []), {
    condition,
    target_node: targetNodeId,
  }];

  const updatedFlow = {
    ...flow,
    nodes: {
      ...flow.nodes,
      [sourceNodeId]: {
        ...sourceNode,
        routes: updatedRoutes,
      },
    },
  };

  return updatedFlow;
}
