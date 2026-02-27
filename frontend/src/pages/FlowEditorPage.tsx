import { useMemo, useState, useEffect, useRef, useCallback } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ConditionSelector } from "@/components/flows/config/shared/ConditionSelector";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { getLastOpenedFlowId, setLastOpenedFlowId } from "@/lib/flowStorage";
import { FlowEditorProvider, useFlowEditor } from "@/contexts/FlowEditorContext";
import { ReactFlowProvider, useReactFlow, applyNodeChanges } from "reactflow";
import "reactflow/dist/style.css";

// Type alias for reactflow (v11 export issues)
type Node = any;

// Custom node components
import PromptNode from "@/components/flows/nodes/PromptNode";
import MenuNode from "@/components/flows/nodes/MenuNode";
import ApiActionNode from "@/components/flows/nodes/ApiActionNode";
import LogicExpressionNode from "@/components/flows/nodes/LogicExpressionNode";
import TextNode from "@/components/flows/nodes/TextNode";

// Custom edge components
import CustomEdge from "@/components/flows/edges/CustomEdge";
import StubEdge from "@/components/flows/edges/StubEdge";

// UI components
import FlowToolbar from "@/components/flows/FlowToolbar";
import FlowSidebar from "@/components/flows/FlowSidebar";
import NodeTypeSelector from "@/components/flows/NodeTypeSelector";
import { NodeConfigurationPanel, type NodeConfigurationPanelRef } from "@/components/flows/config/NodeConfigurationPanel";
import { FlowSettingsPanel } from "@/components/flows/config/FlowSettingsPanel";
import CreateFlowDialog from "@/components/flows/CreateFlowDialog";
import EditBotDialog from "@/components/bots/EditBotDialog";
import { ChatSimulator } from "@/components/flows/ChatSimulator";
import { FlowCanvas } from "@/components/flows/FlowCanvas";
import { KeyboardShortcutsHelpDialog } from "@/components/flows/KeyboardShortcutsHelpDialog";
import { ContextualShortcutsHint } from "@/components/flows/ContextualShortcutsHint";
import { NotFound } from "@/components/NotFound";
import { canAddRoute, isBranchingNode } from "@/lib/routeConditionUtils";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

// Layout utilities
import {
  convertFlowToReactFlow,
  generateNodeName,
  ensureLeafNodesRouteToEnd,
  moveNodeLeft,
  moveNodeRight,
  connectRouteToExistingNode,
} from "@/lib/flowLayoutUtils";
import {
  calculateEdgeBounds,
  findClosestEdge,
} from "@/lib/edgeDetectionUtils";
import type { Flow, NodeType } from "@/lib/types";
import { toast } from "sonner";

// Keyboard shortcuts utilities
import {
  findNodeAbove,
  findNodeBelow,
  findNodeLeft,
  findNodeRight,
} from "@/utils/nodeNavigationUtils";
import { POSITION_NUDGE, POSITION_NUDGE_LARGE, snapToGrid } from "@/utils/canvasPositioningUtils";

// Custom hooks
import { useDialogState } from "@/hooks/useDialogState";
import { useFlowsQuery } from "@/hooks/queries/useFlowsQuery";
import { useBotQuery } from "@/hooks/queries/useBotQuery";
import { useQueryClient } from "@tanstack/react-query";
import { useRegenerateWebhookSecretMutation, botsKeys } from "@/hooks/queries/useBotsQuery";

const nodeTypes = {
  PROMPT: PromptNode,
  MENU: MenuNode,
  API_ACTION: ApiActionNode,
  LOGIC_EXPRESSION: LogicExpressionNode,
  TEXT: TextNode,
};

const edgeTypes = {
  default: CustomEdge,
  stub: StubEdge,
};

/**
 * Migrate old flows that don't have node names
 * Adds auto-generated names to all nodes that are missing them
 */
function migrateFlowNodeNames(flow: Flow): Flow {
  if (!flow || !flow.nodes) return flow;

  let hasChanges = false;
  const updatedNodes = { ...flow.nodes };

  // Check if any nodes are missing names
  for (const [nodeId, node] of Object.entries(updatedNodes)) {
    if (!node.name) {
      hasChanges = true;
      // Generate name based on current nodes
      updatedNodes[nodeId] = {
        ...node,
        name: generateNodeName(node.type, updatedNodes),
      };
    }
  }

  // Return updated flow if changes were made
  if (hasChanges) {
    return {
      ...flow,
      nodes: updatedNodes,
    };
  }

  return flow;
}

function FlowEditorContent() {
  const { botId, flowId } = useParams<{ botId: string; flowId?: string }>();
  useAuth(); // For auth state
  const navigate = useNavigate();
  const reactFlowInstance = useReactFlow();
  const queryClient = useQueryClient();

  // Use the FlowEditor context for all flow/node state management
  const {
    flows,
    activeFlowIndex,
    setFlows,
    setActiveFlowIndex,
    draftState: activeFlow,
    selectedNodeId,
    selectedNode,
    isDirty: hasUnsavedChanges,
    isSaving,
    canSave,
    availableNodes,
    availableVariables,
    selectNode,
    clearSelection,
    updateFlowSettings,
    updateNode,
    updateNodePosition,
    updateMultipleNodePositions,
    insertNode,
    deleteNode,
    moveLeft,
    moveRight,
    moveNodeBetweenEdge,
    save,
    deleteActiveFlow,
    canUndo,
    canRedo,
    undo,
    redo,
    syncKey,
    pendingNodeSelectionRef,
    getNodeErrorCount,
  } = useFlowEditor();

  // State
  const scrollTimeoutRef = useRef<number | null>(null);
  const [reactFlowNodes, setReactFlowNodes] = useState<Node[]>([]);
  const isDraggingRef = useRef(false);
  const rafRef = useRef<number | null>(null);
  const pendingChangesRef = useRef<any[]>([]);

  // State for drag-to-insert reordering
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);
  const draggedNodeRef = useRef<string | null>(null);
  const filteredEdgeBoundsRef = useRef<any[]>([]);


  // Per-flow viewport storage (flow_id -> { x, y, zoom })
  const viewportsByFlowRef = useRef<Map<string, { x: number; y: number; zoom: number }>>(new Map());
  const [skipFitView, setSkipFitView] = useState(false);
  const previousFlowIdRef = useRef<string | null>(null);

  // Store last selected node per flow (flow_id -> last selected node id)
  const lastSelectedNodeByFlowRef = useRef<Map<string, string>>(new Map());

  // Refs for current flow and selection state (declared early for use in callbacks)
  const activeFlowRef = useRef(activeFlow);
  const selectedNodeIdRef = useRef(selectedNodeId);

  // State for controlling which node's selector is open via keyboard
  const [keyboardOpenSelectorNodeId, setKeyboardOpenSelectorNodeId] = useState<string | null>(null);
  const [preSelectedNodeType, setPreSelectedNodeType] = useState<NodeType | null>(null);

  // State for keyboard shortcuts help dialog
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);

  // State for pending delete confirmation
  const [pendingDeleteNodeId, setPendingDeleteNodeId] = useState<string | null>(null);

  // State for stub drag-to-connect (creating cycles)
  const [pendingConnection, setPendingConnection] = useState<{
    sourceNodeId: string;
    targetNodeId: string;
    anchorPosition: { x: number; y: number }; // Screen coordinates for popover positioning
  } | null>(null);
  const [pendingCondition, setPendingCondition] = useState("");
  const [simulatorKey, setSimulatorKey] = useState(0);
  const [simulatorInitialMessage, setSimulatorInitialMessage] = useState<string | null>(null);

  // React Query hooks for data fetching
  const { data: bot, isLoading: isBotLoading, isError: isBotError } = useBotQuery(botId);
  const { data: rawFlows = [], isLoading: isFlowsLoading } =
    useFlowsQuery(botId);

  // Custom hooks
  const dialogState = useDialogState();
  const regenerateSecretMutation = useRegenerateWebhookSecretMutation();

  // Handle node configuration changes (update context state directly)
  const handleNodeConfigChange = useCallback(
    (data: {
      nodeId: string;
      nodeName: string;
      config: any;
      routes: any[];
      isValid: boolean;
      errors: any[];
    }) => {
      if (!activeFlow) return;
      updateNode(data.nodeId, {
        name: data.nodeName,
        config: data.config,
        routes: data.routes,
      });
    },
    [activeFlow, updateNode]
  );

  // Handle flow settings changes (update context state directly)
  const handleFlowSettingsChange = useCallback(
    (data: {
      name: string;
      triggerKeywords: string[];
      variables: Record<string, { type: string; default: any }>;
      defaults: any;
      isValid: boolean;
    }) => {
      if (!activeFlow) return;
      updateFlowSettings({
        name: data.name,
        trigger_keywords: data.triggerKeywords,
        variables: data.variables as Flow['variables'],
        defaults: data.defaults,
      });
    },
    [activeFlow, updateFlowSettings]
  );

  // Global save handler - saves current flow state to API
  const handleGlobalSave = useCallback(async () => {
    if (!botId) {
      toast.error("Cannot save flow");
      return;
    }
    await save(botId);
  }, [botId, save]);

  // Ref for node configuration panel to focus name input
  const nodeConfigPanelRef = useRef<NodeConfigurationPanelRef>(null);

  // Refs to store latest values for stable handlers
  const selectNodeRef = useRef(selectNode);
  const moveLeftRef = useRef(moveLeft);
  const moveRightRef = useRef(moveRight);
  const dialogStateRef = useRef(dialogState);

  useEffect(() => {
    selectNodeRef.current = selectNode;
    moveLeftRef.current = moveLeft;
    moveRightRef.current = moveRight;
    dialogStateRef.current = dialogState;
    // Update refs used in clearSelectionWithHistory and keyboard handlers
    activeFlowRef.current = activeFlow;
    selectedNodeIdRef.current = selectedNodeId;
  });

  // Stable handler maps for different node actions
  const nodeClickHandlersRef = useRef<Map<string, () => void>>(new Map());
  const nodeDeleteHandlersRef = useRef<Map<string, () => void>>(new Map());
  const nodeMoveLeftHandlersRef = useRef<Map<string, () => void>>(new Map());
  const nodeMoveRightHandlersRef = useRef<Map<string, () => void>>(new Map());
  const nodeSelectorChangeHandlersRef = useRef<Map<string, (open: boolean) => void>>(new Map());

  // Get or create a stable click handler for a node
  const getNodeClickHandler = useCallback((nodeId: string) => {
    if (!nodeClickHandlersRef.current.has(nodeId)) {
      nodeClickHandlersRef.current.set(nodeId, () => {
        selectNodeRef.current(nodeId);
      });
    }
    return nodeClickHandlersRef.current.get(nodeId)!;
  }, []);

  // Get or create a stable delete handler for a node
  const getNodeDeleteHandler = useCallback((nodeId: string) => {
    if (!nodeDeleteHandlersRef.current.has(nodeId)) {
      nodeDeleteHandlersRef.current.set(nodeId, () => {
        setPendingDeleteNodeId(nodeId);
        dialogStateRef.current.openDialog("deleteConfirmation");
      });
    }
    return nodeDeleteHandlersRef.current.get(nodeId)!;
  }, []);

  // Get or create a stable move left handler for a node
  const getNodeMoveLeftHandler = useCallback((nodeId: string) => {
    if (!nodeMoveLeftHandlersRef.current.has(nodeId)) {
      nodeMoveLeftHandlersRef.current.set(nodeId, () => {
        moveLeftRef.current(nodeId);
      });
    }
    return nodeMoveLeftHandlersRef.current.get(nodeId)!;
  }, []);

  // Get or create a stable move right handler for a node
  const getNodeMoveRightHandler = useCallback((nodeId: string) => {
    if (!nodeMoveRightHandlersRef.current.has(nodeId)) {
      nodeMoveRightHandlersRef.current.set(nodeId, () => {
        moveRightRef.current(nodeId);
      });
    }
    return nodeMoveRightHandlersRef.current.get(nodeId)!;
  }, []);

  // Get or create a stable selector change handler for a node
  const getNodeSelectorChangeHandler = useCallback((nodeId: string) => {
    if (!nodeSelectorChangeHandlersRef.current.has(nodeId)) {
      nodeSelectorChangeHandlersRef.current.set(nodeId, (open: boolean) => {
        setKeyboardOpenSelectorNodeId(open ? nodeId : null);
        if (!open) setPreSelectedNodeType(null);
      });
    }
    return nodeSelectorChangeHandlersRef.current.get(nodeId)!;
  }, []);

  // Process and migrate flows when they're loaded
  useEffect(() => {
    if (isFlowsLoading) return;

    if (rawFlows.length === 0) {
      setFlows([]);
    } else {
      // Migrate flows to add names if missing (backward compatibility)
      const migratedFlows = rawFlows.map((flow: Flow) => {
        const namesMigrated = migrateFlowNodeNames(flow);

        // Ensure END node exists
        const endNode = Object.values(namesMigrated.nodes || {}).find(
          (n) => n.type === "END"
        );
        if (!endNode) {
          console.error("Flow must have exactly one END node");
          return namesMigrated;
        }

        // Ensure leaf nodes route to END
        const updatedNodes = ensureLeafNodesRouteToEnd(namesMigrated.nodes);
        return {
          ...namesMigrated,
          nodes: updatedNodes,
        };
      });

      setFlows(migratedFlows);
    }
  }, [rawFlows, isFlowsLoading, setFlows]);

  // Sync activeFlowIndex with URL flowId (URL is source of truth)
  useEffect(() => {
    if (isFlowsLoading || !botId || flows.length === 0) return;

    // Case 1: No flowId in URL - redirect to appropriate flow
    if (!flowId) {
      const lastFlowId = getLastOpenedFlowId(botId);

      // Try last opened flow first
      if (lastFlowId) {
        const flowIndex = flows.findIndex(f => f.flow_id === lastFlowId);
        if (flowIndex !== -1) {
          navigate(`/bots/${botId}/flows/${lastFlowId}`, { replace: true });
          return;
        }
      }

      // Fallback to first flow
      const firstFlow = flows[0];
      if (firstFlow?.flow_id) {
        navigate(`/bots/${botId}/flows/${firstFlow.flow_id}`, { replace: true });
      }
      return;
    }

    // Case 2: flowId in URL - find and set corresponding index
    const targetIndex = flows.findIndex(f => f.flow_id === flowId);

    if (targetIndex === -1) {
      // Invalid flowId - redirect to first flow
      toast.error("Flow not found, redirected to first available flow");
      const firstFlow = flows[0];
      if (firstFlow?.flow_id) {
        navigate(`/bots/${botId}/flows/${firstFlow.flow_id}`, { replace: true });
      }
      return;
    }

    // Valid flowId - update activeFlowIndex and localStorage
    const currentFlow = flows[activeFlowIndex];
    const isAlreadyOnCorrectFlow = currentFlow?.flow_id === flowId;

    if (!isAlreadyOnCorrectFlow) {
      setActiveFlowIndex(targetIndex);
      setLastOpenedFlowId(botId, flowId);
    }
  }, [flowId, flows, botId, isFlowsLoading, navigate, setActiveFlowIndex]);

  // Warn user before closing/refreshing tab with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        // Chrome requires returnValue to be set
        e.returnValue = '';
        return '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [hasUnsavedChanges]);

  const isLoadingFlows = isBotLoading || isFlowsLoading;

  // Handle flow deletion
  const handleDeleteFlow = useCallback(async () => {
    if (botId) {
      await deleteActiveFlow(botId);
    }
  }, [botId, deleteActiveFlow]);

  // Handle unsaved changes guard - simplified since we track dirty state in context
  const withUnsavedChangesGuard = useCallback(
    (action: () => void) => {
      return () => {
        if (hasUnsavedChanges) {
          // Store the action to execute after confirmation
          pendingActionRef.current = action;
          dialogState.openDialog("unsavedWarning");
        } else {
          action();
        }
      };
    },
    [hasUnsavedChanges, dialogState]
  );

  // Ref to store pending action for unsaved changes dialog
  const pendingActionRef = useRef<(() => void) | null>(null);

  // Create route to existing node (called after condition selection or directly)
  const createRouteToExistingNode = useCallback(
    (sourceNodeId: string, targetNodeId: string, condition: string) => {
      if (!activeFlow) return;

      const sourceNode = activeFlow.nodes[sourceNodeId];
      const originalRouteCount = sourceNode?.routes?.length || 0;

      // Check route limit (but allow if condition already exists - that's a re-route, not add)
      const conditionExists = sourceNode?.routes?.some(
        r => r.condition.trim().toLowerCase() === condition.trim().toLowerCase()
      );
      if (!conditionExists && sourceNode && !canAddRoute(sourceNode, activeFlow.nodes)) {
        toast.error("Cannot add more routes to this node (maximum reached)");
        setPendingConnection(null);
        setPendingCondition("");
        return;
      }

      const updatedFlow = connectRouteToExistingNode(
        activeFlow,
        sourceNodeId,
        targetNodeId,
        condition
      );

      if (updatedFlow) {
        const newRouteCount = updatedFlow.nodes[sourceNodeId]?.routes?.length || 0;

        // Only update if routes actually changed (silently ignore duplicates)
        if (newRouteCount > originalRouteCount) {
          const sourceNode = updatedFlow.nodes[sourceNodeId];
          updateNode(sourceNodeId, { routes: sourceNode.routes });
          toast.success("Route created");
        }
        // If route count unchanged, condition already existed - silently ignore
      } else {
        toast.error("Cannot create route: would create invalid cycle (cycles must include a PROMPT or MENU node)");
      }

      // Clear pending state
      setPendingConnection(null);
      setPendingCondition("");
    },
    [activeFlow, updateNode]
  );

  // Handle stub dropped on node (creating route to existing node)
  const handleStubDropOnNode = useCallback(
    (sourceNodeId: string, targetNodeId: string, dropPosition?: { x: number; y: number }) => {
      if (!activeFlow) return;

      const sourceNode = activeFlow.nodes[sourceNodeId];
      if (!sourceNode) return;

      // Prevent self-routing
      if (sourceNodeId === targetNodeId) {
        toast.error("Cannot route a node to itself");
        return;
      }

      // For branching nodes, need condition - show selector
      const needsCondition = isBranchingNode(sourceNode.type, sourceNode.config);

      // Check route limit before showing condition dialog
      if (!canAddRoute(sourceNode, activeFlow.nodes)) {
        toast.error("Cannot add more routes to this node (maximum reached)");
        return;
      }

      if (needsCondition) {
        // Calculate anchor position for the popover (below the target node)
        let anchorPosition = dropPosition || { x: window.innerWidth / 2, y: window.innerHeight / 2 };

        // Try to get target node position and convert to screen coordinates
        const targetNode = reactFlowInstance.getNode(targetNodeId);
        if (targetNode) {
          const nodePosition = targetNode.position;
          const nodeHeight = targetNode.height || 100;
          const nodeWidth = targetNode.width || 200;

          // Position below the center of the node
          const flowPosition = {
            x: nodePosition.x + nodeWidth / 2,
            y: nodePosition.y + nodeHeight + 10, // 10px below the node
          };

          anchorPosition = reactFlowInstance.flowToScreenPosition(flowPosition);
        }

        // Show condition dialog, then create route
        setPendingConnection({ sourceNodeId, targetNodeId, anchorPosition });
        setPendingCondition("");
      } else {
        // Direct connection (non-branching: PROMPT, TEXT use "true")
        createRouteToExistingNode(sourceNodeId, targetNodeId, "true");
      }
    },
    [activeFlow, createRouteToExistingNode, reactFlowInstance]
  );

  // Open chat simulator (toolbar button)
  const handleTestChat = useCallback(() => {
    if (!bot || !activeFlow) {
      toast.error("No active flow selected");
      return;
    }

    if (!bot.webhook_secret) {
      toast.info("Generating webhook secret...");
      regenerateSecretMutation.mutate(bot.bot_id, {
        onSuccess: () => {
          setTimeout(() => {
            setSimulatorInitialMessage(null);
            dialogState.openDialog("chatSimulator");
          }, 500);
        },
      });
    } else {
      setSimulatorInitialMessage(null);
      dialogState.openDialog("chatSimulator");
    }
  }, [bot, activeFlow, regenerateSecretMutation, dialogState]);

  // Test flow from start node - saves if needed, then opens fresh simulator and auto-sends trigger
  const handleTestFlowFromNode = useCallback(async () => {
    if (!bot || !activeFlow || !botId) {
      toast.error("No active flow selected");
      return;
    }

    const firstTrigger = activeFlow.trigger_keywords?.[0];
    if (!firstTrigger) {
      toast.error("No trigger keyword configured for this flow");
      return;
    }

    // Auto-save if there are unsaved changes
    if (hasUnsavedChanges) {
      const saved = await save(botId);
      if (!saved) {
        return; // Save failed, don't proceed with testing
      }
    }

    const openSimulator = () => {
      setSimulatorKey(k => k + 1); // Force fresh mount
      setSimulatorInitialMessage(firstTrigger);
      dialogState.openDialog("chatSimulator");
    };

    if (!bot.webhook_secret) {
      toast.info("Generating webhook secret...");
      regenerateSecretMutation.mutate(bot.bot_id, {
        onSuccess: () => {
          setTimeout(openSimulator, 500);
        },
      });
    } else {
      openSimulator();
    }
  }, [bot, activeFlow, botId, hasUnsavedChanges, save, regenerateSecretMutation, dialogState]);

  // Ref to avoid circular dependency in useMemo
  const handleTestFlowFromNodeRef = useRef(handleTestFlowFromNode);
  useEffect(() => {
    handleTestFlowFromNodeRef.current = handleTestFlowFromNode;
  }, [handleTestFlowFromNode]);

  // Convert flow JSON to React Flow format (only depends on flow data, not selection)
  const { nodes: baseNodes, edges } = useMemo(() => {
    if (!activeFlow) {
      return { nodes: [], edges: [] };
    }

    // Convert to React Flow format (positions already included in nodes)
    const { nodes: rawNodes, edges: rawEdges } = convertFlowToReactFlow(
      activeFlow
    );
    // No automatic layout - positions come from stored data
    const layoutedNodes = rawNodes;

    // Enhance edges with inline insertion handlers and hover state
    const edgesWithHandlers = rawEdges.map((edge) => {
      if (edge.type === 'stub') {
        const sourceNodeId = edge.data?.sourceNodeId;
        const sourceNode = activeFlow.nodes[sourceNodeId];

        // Check if this stub has a pending connection awaiting condition input
        const isPendingSource = pendingConnection?.sourceNodeId === sourceNodeId;

        return {
          ...edge,
          data: {
            ...edge.data,
            sourceNode,
            availableVariables,
            onInsertBetween: (nodeType: NodeType, condition?: string) => {
              insertNode("after", sourceNodeId, nodeType, condition);
            },
            onConnectToNode: (targetNodeId: string, screenPosition: { x: number; y: number }) => {
              handleStubDropOnNode(sourceNodeId, targetNodeId, screenPosition);
            },
            pendingTargetNodeId: isPendingSource ? pendingConnection?.targetNodeId : null,
          },
        };
      }

      // Regular edges
      const edgeIdParts = edge.id.split('-');
      const routeIndex = parseInt(edgeIdParts[edgeIdParts.length - 1], 10);
      const sourceNodeId = edge.source;
      const sourceNode = activeFlow.nodes[sourceNodeId];
      const condition = sourceNode?.routes?.[routeIndex]?.condition;
      const handleIndex = edge.data?.handleIndex ?? 0;
      const cumulativeLabelOffset = edge.data?.cumulativeLabelOffset ?? 0;

      // Only allow route deletion for branching nodes with multiple routes
      const canDeleteRoute = sourceNode &&
        isBranchingNode(sourceNode.type, sourceNode.config) &&
        (sourceNode.routes?.length || 0) > 1;

      return {
        ...edge,
        data: {
          sourceNodeId,
          routeIndex,
          handleIndex,
          cumulativeLabelOffset,
          condition,
          sourceNode,
          availableVariables,
          onInsertBetween: (nodeType: NodeType, editedCondition?: string) => {
            const finalCondition = editedCondition !== undefined ? editedCondition : condition;
            insertNode("after", sourceNodeId, nodeType, finalCondition);
          },
          onUpdateCondition: (newCondition: string) => {
            // Use ref to get fresh state (avoid stale closure)
            const currentFlow = activeFlowRef.current;
            if (!currentFlow) return;

            const node = currentFlow.nodes[sourceNodeId];
            if (!node?.routes || routeIndex >= node.routes.length) return;

            // Check for conflicts (another route with same condition)
            const conflictIndex = node.routes.findIndex(
              (r, i) => i !== routeIndex && r.condition.trim().toLowerCase() === newCondition.trim().toLowerCase()
            );

            const updatedRoutes = [...node.routes];

            if (conflictIndex !== -1) {
              // Conflict found
              if (node.type === "MENU" || node.type === "API_ACTION") {
                // Swap conditions for MENU/API_ACTION (targets stay the same)
                const currentCondition = updatedRoutes[routeIndex].condition;

                // Current route gets the new condition (keeps its target)
                updatedRoutes[routeIndex] = {
                  ...updatedRoutes[routeIndex],
                  condition: newCondition,
                };
                // Conflict route gets the old condition (keeps its target)
                updatedRoutes[conflictIndex] = {
                  ...updatedRoutes[conflictIndex],
                  condition: currentCondition,
                };

                toast.success("Conditions swapped");
              } else {
                // Block for LOGIC_EXPRESSION
                toast.error("A route with this condition already exists");
                return;
              }
            } else {
              // No conflict, just update
              updatedRoutes[routeIndex] = {
                ...updatedRoutes[routeIndex],
                condition: newCondition,
              };
            }

            updateNode(sourceNodeId, { routes: updatedRoutes });
          },
          // Only add delete handler for branching nodes with multiple routes
          ...(canDeleteRoute && {
            onDeleteRoute: () => {
              // Use ref to get fresh state (avoid stale closure)
              const currentFlow = activeFlowRef.current;
              if (!currentFlow) return;

              const node = currentFlow.nodes[sourceNodeId];
              if (!node?.routes || routeIndex >= node.routes.length) return;

              // Filter out the route at this index
              const updatedRoutes = node.routes.filter((_, i) => i !== routeIndex);

              updateNode(sourceNodeId, { routes: updatedRoutes });
              toast.success("Route deleted");
            },
          }),
        },
      };
    });

    // Extract output handle IDs from edges for rendering
    const outputHandlesByNode = new Map<string, string[]>();
    edgesWithHandlers.forEach((edge) => {
      if (edge.sourceHandle) {
        const nodeId = edge.source;
        if (!outputHandlesByNode.has(nodeId)) {
          outputHandlesByNode.set(nodeId, []);
        }
        outputHandlesByNode.get(nodeId)!.push(edge.sourceHandle);
      }
    });

    // Add action handlers to node data
    const nodesWithHandlers = layoutedNodes.map((node) => {
      const flowNode = activeFlow.nodes[node.id];

      const baseData = {
        ...node.data,
        name: flowNode?.name,
        nodeId: node.id,
        nodeType: flowNode?.type,
        flowNode: flowNode,
        allNodes: activeFlow.nodes,
        outputHandleIds: outputHandlesByNode.get(node.id),
        isStartNode: node.id === activeFlow.start_node_id,
        onTestFlow: () => handleTestFlowFromNodeRef.current?.(),
        errorCount: getNodeErrorCount(node.id),
      };

      // Multi-route parent nodes (nodes with 2+ routes) cannot move at all
      if (flowNode?.routes && flowNode.routes.length >= 2) {
        return {
          ...node,
          data: {
            ...baseData,
            onInsertAfter: (nodeType: NodeType, condition?: string) =>
              insertNode("after", node.id, nodeType, condition),
            parentNode: flowNode,
            onDelete: getNodeDeleteHandler(node.id),
            onMoveLeft: getNodeMoveLeftHandler(node.id),
            onMoveRight: getNodeMoveRightHandler(node.id),
            canMoveLeft: false,
            canMoveRight: false,
            onNodeClick: getNodeClickHandler(node.id),
            openSelector: keyboardOpenSelectorNodeId === node.id,
            onSelectorOpenChange: getNodeSelectorChangeHandler(node.id),
            preSelectedType: keyboardOpenSelectorNodeId === node.id ? preSelectedNodeType : undefined,
            availableVariables,
          },
        };
      }

      // Regular nodes - use actual move functions to check if move is possible
      // This ensures UI matches the actual behavior
      const canMoveLeftVal = moveNodeLeft(activeFlow, node.id) !== null;
      const canMoveRightVal = moveNodeRight(activeFlow, node.id) !== null;

      // Check if this is a branching node type (for condition input)
      const isBranching = flowNode ? isBranchingNode(flowNode.type, flowNode.config) : false;

      return {
        ...node,
        data: {
          ...baseData,
          onInsertAfter: (nodeType: NodeType, condition?: string) =>
            insertNode("after", node.id, nodeType, condition),
          // Pass parentNode for branching nodes to show condition selector
          ...(isBranching && { parentNode: flowNode }),
          onDelete: getNodeDeleteHandler(node.id),
          onMoveLeft: getNodeMoveLeftHandler(node.id),
          onMoveRight: getNodeMoveRightHandler(node.id),
          canMoveLeft: canMoveLeftVal,
          canMoveRight: canMoveRightVal,
          onNodeClick: getNodeClickHandler(node.id),
          openSelector: keyboardOpenSelectorNodeId === node.id,
          onSelectorOpenChange: getNodeSelectorChangeHandler(node.id),
          preSelectedType: keyboardOpenSelectorNodeId === node.id ? preSelectedNodeType : undefined,
          availableVariables,
        },
      };
    });

    return {
      nodes: nodesWithHandlers,
      edges: edgesWithHandlers,
    };
  }, [
    activeFlow,
    availableVariables,
    insertNode,
    getNodeClickHandler,
    getNodeDeleteHandler,
    getNodeMoveLeftHandler,
    getNodeMoveRightHandler,
    getNodeSelectorChangeHandler,
    keyboardOpenSelectorNodeId,
    preSelectedNodeType,
    handleStubDropOnNode,
    pendingConnection,
    getNodeErrorCount,
  ]);

  // Add selection state to nodes (only recalculates isSelected, not handlers)
  const nodes = useMemo(() => {
    return baseNodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        isSelected: node.id === selectedNodeId,
      },
    }));
  }, [baseNodes, selectedNodeId]);

  // Sync computed nodes to reactFlowNodes when nodes memo changes (not during drag)
  // The memo already handles all the primitive dependencies, so we just need to sync when it changes
  useEffect(() => {
    if (!isDraggingRef.current) {
      setReactFlowNodes(nodes);
    }
  }, [nodes]);

  // Save/restore viewport when switching flows
  useEffect(() => {
    const currentFlowId = activeFlow?.flow_id || null;
    const previousFlowId = previousFlowIdRef.current;

    // Skip on initial mount (no previous flow to save)
    if (previousFlowId === null && currentFlowId !== null) {
      previousFlowIdRef.current = currentFlowId;
      return;
    }

    // Skip if flow hasn't changed
    if (previousFlowId === currentFlowId) {
      return;
    }

    // Save viewport for the previous flow
    if (previousFlowId && reactFlowInstance) {
      const viewport = reactFlowInstance.getViewport();
      viewportsByFlowRef.current.set(previousFlowId, viewport);
    }

    // Update ref to current flow
    previousFlowIdRef.current = currentFlowId;

    // Restore viewport for the new flow if we have one saved
    if (currentFlowId && reactFlowInstance) {
      const savedViewport = viewportsByFlowRef.current.get(currentFlowId);
      // Skip prop-based fitView - we'll handle viewport ourselves
      setSkipFitView(true);

      // Use setTimeout to let the new nodes render first
      setTimeout(() => {
        if (savedViewport) {
          // Restore saved viewport
          reactFlowInstance.setViewport(savedViewport, { duration: 0 });
        } else {
          // No saved viewport - fit to show all nodes
          reactFlowInstance.fitView({ padding: 0.2, duration: 0 });
        }
        // Reset skipFitView after viewport is set
        setTimeout(() => setSkipFitView(false), 50);
      }, 50); // Give nodes time to render
    }
  }, [activeFlow?.flow_id, reactFlowInstance]);

  // Handle node click - free navigation within flow
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (selectedNodeId !== node.id) {
        selectNode(node.id);
      }
    },
    [selectedNodeId, selectNode]
  );

  // Wrapper to save selection history before clearing (stable - uses refs internally)
  const clearSelectionWithHistory = useCallback(() => {
    // Save current selection as "last" before clearing
    const currentSelectedNodeId = selectedNodeIdRef.current;
    const currentActiveFlow = activeFlowRef.current;

    if (currentSelectedNodeId && currentActiveFlow?.flow_id) {
      lastSelectedNodeByFlowRef.current.set(currentActiveFlow.flow_id, currentSelectedNodeId);
    }
    clearSelection();
  }, [clearSelection]);

  // Handle pane click (deselect) - free navigation within flow
  const onPaneClick = useCallback(() => {
    if (selectedNodeId) {
      clearSelectionWithHistory();
    }
  }, [selectedNodeId, clearSelectionWithHistory]);

  // Handle node drag start - calculate filtered edge bounds once
  const handleNodeDragStart = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      draggedNodeRef.current = node.id;
      isDraggingRef.current = true;

      // Calculate filtered edge bounds once (excluding edges connected to dragged node)
      filteredEdgeBoundsRef.current = calculateEdgeBounds(
        edges,
        nodes,
        30,
        node.id
      );
    },
    [edges, nodes]
  );

  // Handle node drag - detect edge hover for drag-to-insert
  const handleNodeDrag = useCallback(
    (_event: React.MouseEvent, _node: Node) => {
      if (!reactFlowInstance) return;

      // Get mouse position in flow coordinates
      const flowPos = reactFlowInstance.screenToFlowPosition({
        x: _event.clientX,
        y: _event.clientY,
      });

      // Find edge under cursor (use cached filtered bounds)
      const edgeId = findClosestEdge(
        flowPos.x,
        flowPos.y,
        filteredEdgeBoundsRef.current
      );

      setHoveredEdgeId(edgeId);
    },
    [reactFlowInstance]
  );

  // Ref for debouncing position updates
  const positionUpdateTimeoutRef = useRef<number | null>(null);

  // Handle node changes - optimized for smooth dragging with RAF throttling
  const handleNodesChange = useCallback(
    (changes: any[]) => {
      // Track if we're dragging
      const hasDragStart = changes.some(
        (c) => c.type === "position" && c.dragging === true
      );
      if (hasDragStart) {
        isDraggingRef.current = true;
      }

      // Fast path for position changes during drag - use RAF throttling
      const positionChanges = changes.filter(
        (change) => change.type === "position" && change.dragging
      );

      if (positionChanges.length > 0) {
        // Merge new changes with pending changes (keep latest position per node)
        const existingChanges = pendingChangesRef.current.filter(
          (c) => !positionChanges.some((pc) => pc.id === c.id)
        );
        pendingChangesRef.current = [...existingChanges, ...positionChanges];

        // Schedule RAF if not already scheduled
        if (rafRef.current === null) {
          rafRef.current = requestAnimationFrame(() => {
            // Apply accumulated changes
            const changesToApply = pendingChangesRef.current;
            pendingChangesRef.current = [];
            rafRef.current = null;

            setReactFlowNodes((nds) => {
              // Only update positions, keep other node properties unchanged
              // Use mutable update for better performance during drag
              const updated = [...nds];
              changesToApply.forEach((change) => {
                const index = updated.findIndex((n) => n.id === change.id);
                if (index !== -1 && change.position) {
                  updated[index] = { ...updated[index], position: change.position };
                }
              });
              return updated;
            });
          });
        }
        return;
      }

      // For other changes (selection, dimensions, etc.), use React Flow utility
      setReactFlowNodes((nds) => applyNodeChanges(changes, nds));
    },
    []
  );

  // Handle drag stop - save positions to backend
  const handleNodeDragStop = useCallback(
    async (_event: React.MouseEvent, _node: Node, dragNodes: Node[]) => {
      if (!activeFlow) return;

      // Only proceed if we were actually dragging (not just clicking)
      if (!isDraggingRef.current) {
        return;
      }

      // Check if dropped on edge for drag-to-insert reordering
      if (hoveredEdgeId && draggedNodeRef.current && activeFlow) {
        // Cancel any pending RAF without applying (effect will sync after flag clear)
        if (rafRef.current !== null) {
          cancelAnimationFrame(rafRef.current);
          rafRef.current = null;
          pendingChangesRef.current = []; // Clear without applying
        }

        // Attempt reorder via context
        const success = moveNodeBetweenEdge(draggedNodeRef.current, hoveredEdgeId);

        if (success) {
          // Also update positions for all dragged nodes (snapped to grid)
          const positions: Record<string, { x: number; y: number }> = {};
          dragNodes.forEach((node) => {
            if (node.position) {
              positions[node.id] = {
                x: snapToGrid(node.position.x),
                y: snapToGrid(node.position.y),
              };
            }
          });
          updateMultipleNodePositions(positions);

          // Clear dragging flag
          isDraggingRef.current = false;
          draggedNodeRef.current = null;

          toast.success("Node reordered successfully");

          // Clear state and return early
          setHoveredEdgeId(null);
          return;
        } else {
          // Invalid drop: show specific error message
          const node = activeFlow.nodes[draggedNodeRef.current];

          if (!node) {
            toast.error("Node no longer exists in the flow");
          } else if (!node.routes || node.routes.length === 0) {
            toast.error("Cannot move END nodes");
          } else if (node.routes.length > 1) {
            toast.error("Cannot move nodes with multiple routes");
          } else if (node.routes[0].condition !== "true") {
            toast.error("Cannot move nodes with conditional routes");
          } else {
            toast.error("Cannot reorder: would create circular reference");
          }
        }
      }

      // Standard drag stop (no reorder): apply RAF changes and save positions
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;

        if (pendingChangesRef.current.length > 0) {
          const changesToApply = pendingChangesRef.current;
          pendingChangesRef.current = [];

          setReactFlowNodes((nds) =>
            nds.map((node) => {
              const posChange = changesToApply.find((c) => c.id === node.id);
              if (posChange && posChange.position) {
                return { ...node, position: posChange.position };
              }
              return node;
            })
          );
        }
      }

      // Clear drag state
      setHoveredEdgeId(null);
      draggedNodeRef.current = null;
      filteredEdgeBoundsRef.current = [];
      isDraggingRef.current = false;

      // Update positions via context (snapped to grid)
      const positions: Record<string, { x: number; y: number }> = {};
      dragNodes.forEach((node) => {
        if (activeFlow.nodes[node.id] && node.position) {
          positions[node.id] = {
            x: snapToGrid(node.position.x),
            y: snapToGrid(node.position.y),
          };
        }
      });
      updateMultipleNodePositions(positions);
    },
    [activeFlow, moveNodeBetweenEdge, updateMultipleNodePositions, hoveredEdgeId]
  );

  // Cleanup position update timeout and RAF on unmount
  useEffect(() => {
    return () => {
      if (positionUpdateTimeoutRef.current) {
        clearTimeout(positionUpdateTimeoutRef.current);
      }
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
      // Clear all drag-related refs
      isDraggingRef.current = false;
      draggedNodeRef.current = null;
      filteredEdgeBoundsRef.current = [];
      pendingChangesRef.current = [];
    };
  }, []);

  // Ref to store logout Promise resolve function
  const logoutResolveRef = useRef<((value: boolean) => void) | null>(null);

  // Handle unsaved changes confirmation
  const handleUnsavedChangesConfirm = useCallback(() => {
    // If logout was pending, resolve with true to allow logout
    if (logoutResolveRef.current) {
      logoutResolveRef.current(true);
      logoutResolveRef.current = null;
    } else if (pendingActionRef.current) {
      // Execute the pending action
      pendingActionRef.current();
      pendingActionRef.current = null;
    }
    dialogState.closeDialog("unsavedWarning");
  }, [dialogState]);

  // Handle unsaved changes cancel
  const handleUnsavedChangesCancel = useCallback(() => {
    // If logout was pending, resolve with false to cancel logout
    if (logoutResolveRef.current) {
      logoutResolveRef.current(false);
      logoutResolveRef.current = null;
    }
    pendingActionRef.current = null;
    dialogState.closeDialog("unsavedWarning");

    // Restore focus to the name input after a brief delay
    // (delay needed for dialog to finish closing animation)
    setTimeout(() => {
      if (selectedNodeId) {
        nodeConfigPanelRef.current?.focusNameInput();
      }
    }, 100);
  }, [dialogState, selectedNodeId]);

  // Handle before logout - check for unsaved changes
  const handleBeforeLogout = useCallback(async (): Promise<boolean> => {
    if (!hasUnsavedChanges) {
      return true; // No unsaved changes, allow logout
    }

    // Show unsaved warning dialog and wait for user choice
    dialogState.openDialog("unsavedWarning");

    // Create a promise that resolves when user makes a choice
    return new Promise<boolean>((resolve) => {
      logoutResolveRef.current = resolve;
    });
  }, [hasUnsavedChanges, dialogState]);

  // Calculate nodes that will be deleted (for branching nodes)
  const nodesToBeDeleted = useMemo(() => {
    if (!pendingDeleteNodeId || !activeFlow) return [];

    const nodeToDelete = activeFlow.nodes[pendingDeleteNodeId];
    if (!nodeToDelete) return [];

    // Check if this is a branch node with multiple routes
    const hasMultipleRoutes = (nodeToDelete.routes?.length || 0) > 1;

    if (!isBranchingNode(nodeToDelete.type, nodeToDelete.config) || !hasMultipleRoutes) return [];

    // Find the "true" condition child (will be preserved)
    const trueRoute = nodeToDelete.routes?.find(
      (r) => r.condition.toLowerCase() === "true"
    );
    if (!trueRoute) return [];

    const trueChildId = trueRoute.target_node;
    // Include the node being deleted so parentsInDeleteSet counts correctly
    const nodesToDeleteSet = new Set<string>([pendingDeleteNodeId]);
    const visited = new Set<string>();

    // Count incoming edges to a node
    const countIncomingEdges = (targetNodeId: string): number => {
      let count = 0;
      Object.values(activeFlow!.nodes).forEach((node) => {
        node.routes?.forEach((route) => {
          if (route.target_node === targetNodeId) {
            count++;
          }
        });
      });
      return count;
    };

    // Collect descendants recursively (with cycle detection)
    // Only delete children that have no other parent nodes outside the delete set
    const collectDescendants = (nodeId: string) => {
      if (visited.has(nodeId)) return; // Prevent infinite recursion on cycles
      visited.add(nodeId);

      const node = activeFlow!.nodes[nodeId];
      if (!node) return;

      // Check if this node has parents outside the delete set
      const incomingEdges = countIncomingEdges(nodeId);
      const parentsInDeleteSet = Array.from(nodesToDeleteSet).filter(
        deletedId => activeFlow!.nodes[deletedId]?.routes?.some(r => r.target_node === nodeId)
      ).length;

      // Only delete if all parents are being deleted
      if (incomingEdges > parentsInDeleteSet) {
        return; // Has parents outside delete set, preserve this node
      }

      nodesToDeleteSet.add(nodeId);

      node.routes?.forEach((route) => {
        const childNode = activeFlow!.nodes[route.target_node];
        if (
          childNode &&
          childNode.type !== "END" &&
          route.target_node !== trueChildId &&
          route.target_node !== activeFlow!.start_node_id
        ) {
          collectDescendants(route.target_node);
        }
      });
    };

    // Collect all non-true children and their descendants
    nodeToDelete.routes
      ?.filter((r) => r.target_node !== trueChildId)
      .forEach((route) => {
        const childNode = activeFlow!.nodes[route.target_node];
        if (childNode && childNode.type !== "END" && route.target_node !== activeFlow!.start_node_id) {
          collectDescendants(route.target_node);
        }
      });

    // Return only the cascaded children (exclude the node being explicitly deleted)
    return Array.from(nodesToDeleteSet)
      .filter((id) => id !== pendingDeleteNodeId)
      .map((id) => activeFlow!.nodes[id].name);
  }, [pendingDeleteNodeId, activeFlow]);

  // Handle delete node confirmation
  const handleDeleteNodeConfirm = useCallback(async () => {
    if (pendingDeleteNodeId && activeFlow?.flow_id) {
      // Clear from last selected tracking if this was the last selected
      if (lastSelectedNodeByFlowRef.current.get(activeFlow.flow_id) === pendingDeleteNodeId) {
        lastSelectedNodeByFlowRef.current.delete(activeFlow.flow_id);
      }
      deleteNode(pendingDeleteNodeId);
      setPendingDeleteNodeId(null);
    }
    dialogState.closeDialog("deleteConfirmation");
  }, [pendingDeleteNodeId, activeFlow, deleteNode, dialogState]);

  // Utility to check if user is typing in an input field
  const isTypingInInput = useCallback(() => {
    const activeElement = document.activeElement;
    const tagName = activeElement?.tagName;
    return (
      tagName === 'INPUT' ||
      tagName === 'TEXTAREA' ||
      activeElement?.getAttribute('contenteditable') === 'true' ||
      activeElement?.getAttribute('role') === 'textbox'
    );
  }, []);

  // Check if focus is on an interactive control that needs arrow keys (dropdowns, listboxes, etc.)
  const isArrowKeyControlFocused = useCallback(() => {
    const activeElement = document.activeElement;
    if (!activeElement || activeElement === document.body) return false;

    // Check for elements that use arrow keys for their own navigation
    const role = activeElement.getAttribute('role');
    const arrowKeyRoles = ['listbox', 'menu', 'menubar', 'tree', 'grid', 'combobox', 'radiogroup', 'tablist'];
    if (role && arrowKeyRoles.includes(role)) return true;

    // Check if inside a dropdown/popover that's open (radix uses data-state="open")
    const isInOpenPopover = activeElement.closest('[data-state="open"]') !== null ||
                            activeElement.closest('[role="listbox"]') !== null ||
                            activeElement.closest('[role="menu"]') !== null;
    if (isInOpenPopover) return true;

    // Check for select elements
    if (activeElement.tagName === 'SELECT') return true;

    return false;
  }, []);

  // Check if focus is on an element where Enter key has meaning (buttons, links)
  const isEnterKeyControlFocused = useCallback(() => {
    const activeElement = document.activeElement;
    if (!activeElement || activeElement === document.body) return false;

    // Allow Enter when focused on React Flow nodes (after clicking to select)
    // React Flow sets role="button" on nodes, but we still want Enter to focus the name input
    if (activeElement.classList.contains('react-flow__node') ||
        activeElement.closest('.react-flow__node')) {
      return false;
    }

    const tagName = activeElement.tagName;
    const role = activeElement.getAttribute('role');

    // Buttons and links use Enter to activate
    if (tagName === 'BUTTON' || tagName === 'A') return true;
    if (role === 'button' || role === 'link' || role === 'menuitem') return true;

    return false;
  }, []);

  // Check if a shortcut is global (works anywhere)
  const isGlobalShortcut = useCallback((event: KeyboardEvent) => {
    const ctrl = event.ctrlKey || event.metaKey;
    const shift = event.shiftKey;
    const alt = event.altKey;

    // Help (? or Shift+/)
    if (event.key === '?' || (event.key === '/' && shift)) return true;

    // Settings (Ctrl+,)
    if (ctrl && !shift && !alt && event.code === 'Comma') return true;

    // Test chat (Ctrl+Shift+T)
    if (ctrl && shift && !alt && event.key.toLowerCase() === 't') return true;

    // Flow navigation (Ctrl+[ or Ctrl+])
    if (ctrl && !shift && !alt && (event.key === '[' || event.key === ']')) return true;

    // Jump to flow (Ctrl+1-9)
    if (ctrl && !shift && !alt && /^[1-9]$/.test(event.key)) return true;

    // New flow (Ctrl+Alt+N)
    if (ctrl && alt && !shift && event.key.toLowerCase() === 'n') return true;

    // Zoom (+ / -)
    if (!ctrl && !shift && !alt && (event.key === '+' || event.key === '=' || event.key === '-')) return true;

    return false;
  }, []);

  // Quick node insert handler
  const handleQuickNodeInsert = useCallback((nodeType: NodeType | null) => {
    const currentSelectedNodeId = selectedNodeIdRef.current;
    const currentActiveFlow = activeFlowRef.current;

    if (!currentSelectedNodeId || !currentActiveFlow) return;

    const selectedNode = currentActiveFlow.nodes[currentSelectedNodeId];
    if (!selectedNode) return;

    const needsConditionSelector = isBranchingNode(selectedNode.type, selectedNode.config);

    if (nodeType === null) {
      // For generic N key, open selector without pre-selection
      setPreSelectedNodeType(null);
      setKeyboardOpenSelectorNodeId(currentSelectedNodeId);
    } else if (needsConditionSelector) {
      // For branching nodes (except dynamic menu) with specific type, open selector with pre-selected type
      setPreSelectedNodeType(nodeType);
      setKeyboardOpenSelectorNodeId(currentSelectedNodeId);
    } else {
      // For non-branching nodes or dynamic menus with specific type, directly insert
      insertNodeRef.current('after', currentSelectedNodeId, nodeType);
    }
  }, []);

  // Node navigation handler
  const handleNodeNavigation = useCallback((direction: string) => {
    const currentSelectedNodeId = selectedNodeIdRef.current;
    const currentActiveFlow = activeFlowRef.current;
    const reactFlowInstance = reactFlowInstanceRef.current;
    const reactFlowNodes = reactFlowNodesRef.current;

    if (!currentSelectedNodeId || !currentActiveFlow) return;

    let nextNodeId: string | null = null;

    switch (direction) {
      case 'ArrowUp':
        nextNodeId = findNodeAbove(currentSelectedNodeId, currentActiveFlow.nodes, reactFlowNodes);
        break;
      case 'ArrowDown':
        nextNodeId = findNodeBelow(currentSelectedNodeId, currentActiveFlow.nodes, reactFlowNodes);
        break;
      case 'ArrowLeft':
        nextNodeId = findNodeLeft(currentSelectedNodeId, currentActiveFlow.nodes, reactFlowNodes);
        break;
      case 'ArrowRight':
        nextNodeId = findNodeRight(currentSelectedNodeId, currentActiveFlow.nodes, reactFlowNodes);
        break;
    }

    if (nextNodeId) {
      // Free navigation within flow - no unsaved warnings
      selectNodeRef2.current(nextNodeId);
      // Scroll to node
      const node = reactFlowInstance.getNode(nextNodeId);
      if (node) {
        // Capture stable zoom only if we haven't navigated recently (no timeout pending)
        if (!navigationTimeoutRef.current) {
          stableZoomRef.current = reactFlowInstance.getZoom();
        }

        // Clear existing timeout and set new one to update zoom after navigation stops
        if (navigationTimeoutRef.current) {
          clearTimeout(navigationTimeoutRef.current);
        }
        navigationTimeoutRef.current = window.setTimeout(() => {
          const instance = reactFlowInstanceRef.current;
          stableZoomRef.current = instance.getZoom();
          navigationTimeoutRef.current = null;
        }, 500);

        const x = node.position.x + (node.width || 0) / 2;
        const y = node.position.y + (node.height || 0) / 2;
        reactFlowInstance.setCenter(x, y, {
          zoom: stableZoomRef.current,
          duration: 400,
        });
      }
    }
  }, []);

  // Auto-select node when arrow key pressed with no selection
  // Priority: last selected node for this flow -> start node (fallback)
  const handleAutoSelectStart = useCallback(() => {
    const currentActiveFlow = activeFlowRef.current;
    const reactFlowInstance = reactFlowInstanceRef.current;

    if (!currentActiveFlow || !currentActiveFlow.start_node_id || !currentActiveFlow.flow_id) return;

    // Try to restore last selected node for this flow
    const lastSelectedId = lastSelectedNodeByFlowRef.current.get(currentActiveFlow.flow_id);
    if (lastSelectedId) {
      const lastSelectedNode = currentActiveFlow.nodes[lastSelectedId];
      // Only restore if node still exists and is not END
      if (lastSelectedNode && lastSelectedNode.type !== "END") {
        selectNodeRef2.current(lastSelectedId);

        // Scroll to last selected node
        const node = reactFlowInstance.getNode(lastSelectedId);
        if (node) {
          if (!navigationTimeoutRef.current) {
            stableZoomRef.current = reactFlowInstance.getZoom();
          }
          const x = node.position.x + (node.width || 0) / 2;
          const y = node.position.y + (node.height || 0) / 2;
          reactFlowInstance.setCenter(x, y, {
            zoom: stableZoomRef.current,
            duration: 400,
          });
        }
        return; // Early return - we restored last selected
      }
    }

    // Fallback: select start node (current behavior)
    const startNodeId = currentActiveFlow.start_node_id;
    const startNode = currentActiveFlow.nodes[startNodeId];

    if (startNode && startNode.type !== "END") {
      selectNodeRef2.current(startNodeId);

      // Scroll to start node
      const node = reactFlowInstance.getNode(startNodeId);
      if (node) {
        if (!navigationTimeoutRef.current) {
          stableZoomRef.current = reactFlowInstance.getZoom();
        }
        const x = node.position.x + (node.width || 0) / 2;
        const y = node.position.y + (node.height || 0) / 2;
        reactFlowInstance.setCenter(x, y, {
          zoom: stableZoomRef.current,
          duration: 400,
        });
      }
    }
  }, []);

  // Refs for position updates
  const positionSaveTimeoutRef = useRef<number | null>(null);

  // Store stable zoom level to prevent drift during rapid navigation
  const stableZoomRef = useRef<number>(1);
  const navigationTimeoutRef = useRef<number | null>(null);

  // Store latest values to avoid re-registering keyboard handler on every render
  // Note: activeFlowRef and selectedNodeIdRef are declared earlier in the file
  const hasUnsavedChangesRef = useRef(hasUnsavedChanges);
  const selectNodeRef2 = useRef(selectNode);
  const clearSelectionRef = useRef(clearSelectionWithHistory);
  const moveLeftRef2 = useRef(moveLeft);
  const moveRightRef2 = useRef(moveRight);
  const insertNodeRef = useRef(insertNode);
  const updateNodePositionRef = useRef(updateNodePosition);
  const dialogStateRef2 = useRef(dialogState);
  const reactFlowInstanceRef = useRef(reactFlowInstance);
  const reactFlowNodesRef = useRef(reactFlowNodes);
  const handleGlobalSaveRef = useRef(handleGlobalSave);
  const isSavingRef = useRef(isSaving);
  const canSaveRef = useRef(canSave);
  const canUndoRef = useRef(canUndo);
  const canRedoRef = useRef(canRedo);
  const undoRef = useRef(undo);
  const redoRef = useRef(redo);

  // Update refs on every render to have latest values
  // Note: activeFlowRef and selectedNodeIdRef are updated in an earlier useEffect
  useEffect(() => {
    hasUnsavedChangesRef.current = hasUnsavedChanges;
    selectNodeRef2.current = selectNode;
    clearSelectionRef.current = clearSelectionWithHistory;
    moveLeftRef2.current = moveLeft;
    moveRightRef2.current = moveRight;
    insertNodeRef.current = insertNode;
    updateNodePositionRef.current = updateNodePosition;
    dialogStateRef2.current = dialogState;
    reactFlowInstanceRef.current = reactFlowInstance;
    reactFlowNodesRef.current = reactFlowNodes;
    handleGlobalSaveRef.current = handleGlobalSave;
    isSavingRef.current = isSaving;
    canSaveRef.current = canSave;
    canUndoRef.current = canUndo;
    canRedoRef.current = canRedo;
    undoRef.current = undo;
    redoRef.current = redo;
  });

  // Node positioning handler
  const handleNodePositioning = useCallback((direction: string, nudgeAmount: number = POSITION_NUDGE) => {
    const currentSelectedNodeId = selectedNodeIdRef.current;
    const currentActiveFlow = activeFlowRef.current;

    if (!currentSelectedNodeId || !currentActiveFlow) return;

    let deltaX = 0;
    let deltaY = 0;

    switch (direction) {
      case 'ArrowUp': deltaY = -nudgeAmount; break;
      case 'ArrowDown': deltaY = nudgeAmount; break;
      case 'ArrowLeft': deltaX = -nudgeAmount; break;
      case 'ArrowRight': deltaX = nudgeAmount; break;
    }

    // Get current position and calculate new position (snapped to grid)
    const node = currentActiveFlow.nodes[currentSelectedNodeId];
    if (!node?.position) return;

    const newPosition = {
      x: snapToGrid(node.position.x + deltaX),
      y: snapToGrid(node.position.y + deltaY),
    };

    // Update position via context
    updateNodePositionRef.current(currentSelectedNodeId, newPosition);
  }, []);

  // Flow switching handler - uses navigation to update URL
  const handleFlowSwitch = useCallback((index: number) => {
    const targetFlow = flows[index];
    if (targetFlow?.flow_id && botId) {
      navigate(`/bots/${botId}/flows/${targetFlow.flow_id}`, { replace: true });
      // URL change triggers useEffect which updates activeFlowIndex and localStorage
    }
  }, [flows, botId, navigate]);

  // Flow navigation handlers
  const handleNextFlow = useCallback(() => {
    if (activeFlowIndex < flows.length - 1) {
      const nextIndex = activeFlowIndex + 1;
      if (hasUnsavedChangesRef.current) {
        pendingActionRef.current = () => handleFlowSwitch(nextIndex);
        dialogStateRef2.current.openDialog('unsavedWarning');
      } else {
        handleFlowSwitch(nextIndex);
      }
    }
  }, [activeFlowIndex, flows.length, handleFlowSwitch]);

  const handlePreviousFlow = useCallback(() => {
    if (activeFlowIndex > 0) {
      const prevIndex = activeFlowIndex - 1;
      if (hasUnsavedChangesRef.current) {
        pendingActionRef.current = () => handleFlowSwitch(prevIndex);
        dialogStateRef2.current.openDialog('unsavedWarning');
      } else {
        handleFlowSwitch(prevIndex);
      }
    }
  }, [activeFlowIndex, handleFlowSwitch]);

  const handleJumpToFlow = useCallback((index: number) => {
    if (index >= 0 && index < flows.length) {
      if (hasUnsavedChangesRef.current) {
        pendingActionRef.current = () => handleFlowSwitch(index);
        dialogStateRef2.current.openDialog('unsavedWarning');
      } else {
        handleFlowSwitch(index);
      }
    }
  }, [flows.length, handleFlowSwitch]);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (positionSaveTimeoutRef.current) {
        clearTimeout(positionSaveTimeoutRef.current);
      }
      if (navigationTimeoutRef.current) {
        clearTimeout(navigationTimeoutRef.current);
      }
    };
  }, []);


  // Comprehensive keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Skip if IME composition is in progress (for CJK languages)
      // keyCode 229 is fallback for older browsers (deprecated but necessary for compatibility)
      if (event.isComposing || event.keyCode === 229) {
        return;
      }

      // Get latest values from refs
      const dialogState = dialogStateRef2.current;
      const reactFlowInstance = reactFlowInstanceRef.current;
      const currentSelectedNodeId = selectedNodeIdRef.current;
      const currentActiveFlow = activeFlowRef.current;

      // Skip if typing in input field
      if (isTypingInInput()) {
        // Only allow Ctrl+Enter when typing (for form submission)
        if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
          // Form submission handled by individual forms
          return;
        }
        if (event.key === 'Escape') {
          (document.activeElement as HTMLElement)?.blur();
          return;
        }
        return;
      }

      // General Escape handler: blur any focused element (works for buttons, selects, etc.)
      if (event.key === 'Escape' && document.activeElement && document.activeElement !== document.body) {
        // Only blur if it's a focusable UI element (not canvas elements)
        const activeElement = document.activeElement;
        const isReactFlowElement =
          activeElement.classList.contains('react-flow__pane') ||
          activeElement.classList.contains('react-flow__node') ||
          activeElement.closest('.react-flow') !== null;

        if (!isReactFlowElement) {
          (document.activeElement as HTMLElement)?.blur();
          event.preventDefault();
          return;
        }
      }

      const ctrl = event.ctrlKey || event.metaKey;
      const shift = event.shiftKey;
      const alt = event.altKey;

      // ========== HANDLE GLOBAL SHORTCUTS (work anywhere) ==========

      // Global Save (Ctrl+S) - highest priority, works anywhere
      if (ctrl && !shift && !alt && event.key === 's') {
        event.preventDefault();
        if (canSaveRef.current) {
          handleGlobalSaveRef.current();
        }
        return;
      }

      // Undo (Ctrl+Z) - works anywhere
      if (ctrl && !shift && !alt && event.key === 'z') {
        event.preventDefault();
        if (canUndoRef.current) {
          undoRef.current();
        }
        return;
      }

      // Redo (Ctrl+Y or Ctrl+Shift+Z) - works anywhere
      if (ctrl && !alt && (event.key === 'y' || (shift && event.key === 'z') || (shift && event.key === 'Z'))) {
        event.preventDefault();
        if (canRedoRef.current) {
          redoRef.current();
        }
        return;
      }

      if (isGlobalShortcut(event)) {
        // Help dialog (? key or Shift + /)
        if (event.key === '?' || (event.key === '/' && shift)) {
          event.preventDefault();
          setShowKeyboardHelp(prev => !prev);
          return;
        }

        // Bot settings (Ctrl + ,)
        if (ctrl && !shift && !alt && event.code === 'Comma') {
          event.preventDefault();
          dialogState.openDialog('botSettings');
          return;
        }

        // Test chat (Ctrl + Shift + T)
        if (ctrl && shift && !alt && event.key.toLowerCase() === 't') {
          event.preventDefault();
          handleTestFlowFromNode();
          return;
        }

        // Flow navigation (Ctrl + [ or ])
        if (ctrl && !shift && !alt) {
          if (event.key === ']') {
            event.preventDefault();
            handleNextFlow();
            return;
          }
          if (event.key === '[') {
            event.preventDefault();
            handlePreviousFlow();
            return;
          }
        }

        // Jump to flow (Ctrl + 1-9)
        if (ctrl && !shift && !alt) {
          const num = parseInt(event.key);
          if (!isNaN(num) && num >= 1 && num <= 9) {
            event.preventDefault();
            handleJumpToFlow(num - 1);
            return;
          }
        }

        // New flow (Ctrl + Alt + N)
        if (ctrl && alt && !shift && event.key.toLowerCase() === 'n') {
          event.preventDefault();
          // Check for unsaved changes before creating new flow
          if (hasUnsavedChangesRef.current) {
            pendingActionRef.current = () => dialogState.openDialog('createFlow');
            dialogState.openDialog('unsavedWarning');
          } else {
            dialogState.openDialog('createFlow');
          }
          return;
        }

        // Zoom controls
        if (!ctrl && !shift && !alt) {
          if (event.key === '+' || event.key === '=') {
            event.preventDefault();
            reactFlowInstance.zoomIn({ duration: 200 });
            return;
          }
          if (event.key === '-') {
            event.preventDefault();
            reactFlowInstance.zoomOut({ duration: 200 });
            return;
          }
        }
      }

      // ========== EDITOR SHORTCUTS (work throughout the editor) ==========

      // Skip if any dialog is open (except for Escape to close)
      // Note: chatSimulator is not included here as it handles its own Escape key
      // Check if event originated from inside a dialog
      const targetElement = event.target as HTMLElement;
      const isInsideDialog = targetElement?.closest('[role="dialog"]') !== null ||
                             targetElement?.closest('[role="alertdialog"]') !== null;

      const anyTrackedDialogOpen = dialogState.isDialogOpen('createFlow') ||
                                    dialogState.isDialogOpen('botSettings') ||
                                    dialogState.isDialogOpen('deleteConfirmation') ||
                                    dialogState.isDialogOpen('unsavedWarning');

      if ((isInsideDialog || anyTrackedDialogOpen) && event.key !== 'Escape') {
        return;
      }

      // Block all shortcuts when chat simulator is open (except Escape which it handles itself)
      if (dialogState.isDialogOpen('chatSimulator') && event.key !== 'Escape') {
        return;
      }

      // Skip if node selector is open (except for Escape to close)
      if (keyboardOpenSelectorNodeId && event.key !== 'Escape') {
        return;
      }

      // Quick node insert (P, M, T, A, L, N) - single keys without modifiers
      if (!ctrl && !shift && !alt && currentSelectedNodeId) {
        const nodeTypeMap: Record<string, NodeType | null> = {
          'p': 'PROMPT',
          'm': 'MENU',
          't': 'TEXT',
          'a': 'API_ACTION',
          'l': 'LOGIC_EXPRESSION',
          'n': null, // Generic palette
        };

        const key = event.key.toLowerCase();
        if (key in nodeTypeMap) {
          event.preventDefault();
          handleQuickNodeInsert(nodeTypeMap[key]);
          return;
        }
      }

      // Arrow key navigation (Figma-style: auto-select start node if nothing selected)
      // Skip if focus is on a control that uses arrow keys (dropdowns, listboxes, etc.)
      if (!ctrl && !shift && !alt) {
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
          if (isArrowKeyControlFocused()) return;
          event.preventDefault();

          if (currentSelectedNodeId) {
            // Node is selected - navigate through flow
            handleNodeNavigation(event.key);
          } else {
            // Nothing selected - auto-select start node (Figma-style)
            handleAutoSelectStart();
          }
          return;
        }
      }

      // Large node positioning (Shift + Arrow)
      if (!ctrl && shift && !alt && currentSelectedNodeId) {
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
          if (isArrowKeyControlFocused()) return;
          event.preventDefault();
          handleNodePositioning(event.key, POSITION_NUDGE_LARGE);
          return;
        }
      }

      // Small node positioning (Ctrl + Arrow)
      if (ctrl && !shift && !alt && currentSelectedNodeId) {
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
          if (isArrowKeyControlFocused()) return;
          event.preventDefault();
          handleNodePositioning(event.key);
          return;
        }
      }

      // Node reordering (Ctrl + Shift + Left/Right) - free movement within flow
      if (ctrl && shift && !alt && currentSelectedNodeId) {
        if (event.key === 'ArrowLeft') {
          if (isArrowKeyControlFocused()) return;
          event.preventDefault();
          moveLeftRef2.current(currentSelectedNodeId);
          return;
        }
        if (event.key === 'ArrowRight') {
          if (isArrowKeyControlFocused()) return;
          event.preventDefault();
          moveRightRef2.current(currentSelectedNodeId);
          return;
        }
      }

      // Delete flow (Shift + Delete) - only when no node selected
      if (!ctrl && shift && !alt && event.key === 'Delete' && !currentSelectedNodeId) {
        event.preventDefault();
        if (currentActiveFlow) {
          // Check for unsaved changes before deleting flow
          if (hasUnsavedChangesRef.current) {
            pendingActionRef.current = handleDeleteFlow;
            dialogState.openDialog('unsavedWarning');
          } else {
            handleDeleteFlow();
          }
        }
        return;
      }

      // Focus name input (Enter key when node is selected)
      // Skip if focus is on a button/link that uses Enter to activate
      if (event.key === "Enter" && !ctrl && !shift && !alt && currentSelectedNodeId) {
        if (isEnterKeyControlFocused()) return;
        event.preventDefault();
        // Focus the node name input in the configuration panel
        nodeConfigPanelRef.current?.focusNameInput();
        return;
      }

      // Handle Escape key - priority order: close dialogs > close selector > deselect node
      if (event.key === "Escape") {
        // First priority: close dialogs (let Dialog component handle it)
        // Check if the event target is inside a dialog (catches all dialogs including nested ones)
        const targetElement = event.target as HTMLElement;
        const isInsideDialog = targetElement?.closest('[role="dialog"]') !== null ||
                               targetElement?.closest('[role="alertdialog"]') !== null;

        // Also check for tracked dialogs
        const anyTrackedDialogOpen = dialogState.isDialogOpen('createFlow') ||
                                      dialogState.isDialogOpen('botSettings') ||
                                      dialogState.isDialogOpen('deleteConfirmation') ||
                                      dialogState.isDialogOpen('unsavedWarning');

        if (isInsideDialog || anyTrackedDialogOpen) {
          // Don't preventDefault - let the Dialog component handle Escape
          return;
        }

        // Chat simulator is checked separately (it handles Escape itself)
        if (dialogState.isDialogOpen('chatSimulator')) {
          // Let chat simulator handle it
          return;
        }

        // Second priority: close selector if open
        if (keyboardOpenSelectorNodeId) {
          setKeyboardOpenSelectorNodeId(null);
          return;
        }

        // Third priority: deselect node - free navigation within flow
        if (currentSelectedNodeId) {
          clearSelectionRef.current();
          return;
        }
      }

      // Handle Delete/Backspace key to delete node
      // Skip if focus is on a button/link to prevent accidental deletion
      if (
        (event.key === "Delete" || event.key === "Backspace") &&
        currentSelectedNodeId &&
        currentActiveFlow
      ) {
        if (isEnterKeyControlFocused()) return;
        const selectedNode = currentActiveFlow.nodes[currentSelectedNodeId];
        if (selectedNode && selectedNode.type !== "END") {
          event.preventDefault();
          setPendingDeleteNodeId(currentSelectedNodeId);
          dialogState.openDialog("deleteConfirmation");
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    // Stable callbacks (all use refs internally, so don't change)
    isTypingInInput,
    isArrowKeyControlFocused,
    isEnterKeyControlFocused,
    isGlobalShortcut,
    handleQuickNodeInsert,
    handleNodeNavigation,
    handleAutoSelectStart,
    handleNodePositioning,
    handleNextFlow,
    handlePreviousFlow,
    handleJumpToFlow,
    handleTestChat,
    handleTestFlowFromNode,
    handleDeleteFlow,
    // State setters (stable by React guarantee)
    setShowKeyboardHelp,
    // Local state that needs to trigger re-registration
    keyboardOpenSelectorNodeId,
  ]);

  // Handle pending node selection and scroll after flow update
  useEffect(() => {
    if (
      pendingNodeSelectionRef.current &&
      activeFlow?.nodes[pendingNodeSelectionRef.current]
    ) {
      const newNodeId = pendingNodeSelectionRef.current;
      pendingNodeSelectionRef.current = null;

      // Select the newly created node
      selectNode(newNodeId);

      // Scroll to the new node after a brief delay
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
      scrollTimeoutRef.current = window.setTimeout(() => {
        try {
          const node = reactFlowInstance.getNode(newNodeId);
          if (node) {
            // Capture stable zoom only if we haven't navigated recently
            if (!navigationTimeoutRef.current) {
              stableZoomRef.current = reactFlowInstance.getZoom();
            }

            const x = node.position.x + (node.width || 0) / 2;
            const y = node.position.y + (node.height || 0) / 2;
            reactFlowInstance.setCenter(x, y, {
              zoom: stableZoomRef.current,
              duration: 800,
            });
          }
        } catch (err) {
          console.warn("Could not scroll to new node:", err);
        }
      }, 100);
    }
  }, [
    activeFlow,
    reactFlowInstance,
    pendingNodeSelectionRef,
    selectNode,
  ]);

  // Cleanup scroll timeout on unmount
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  // Show loading state
  if (isLoadingFlows) {
    return (
      <div className="flex flex-col h-screen bg-muted/30 items-center justify-center">
        <LoadingSpinner size="md" className="mb-4" />
        <p className="mt-4 text-muted-foreground">Loading bot and flows...</p>
      </div>
    );
  }

  // Show 404 if bot doesn't exist
  if (isBotError || !bot) {
    return (
      <NotFound
        title="Bot Not Found"
        message="The bot you're looking for doesn't exist or you don't have access to it."
      />
    );
  }

  return (
    <div className="flex flex-col h-screen bg-muted/30">
      {/* Top Bar */}
      <FlowToolbar
        botName={bot?.name || "Untitled Bot"}
        onBotSettings={() => dialogState.openDialog("botSettings")}
        onSaveFlow={handleGlobalSave}
        hasUnsavedChanges={hasUnsavedChanges}
        isSaving={isSaving}
        checkUnsavedChanges={withUnsavedChangesGuard}
        onBeforeLogout={handleBeforeLogout}
        onTestChat={handleTestChat}
        canUndo={canUndo}
        canRedo={canRedo}
        onUndo={undo}
        onRedo={redo}
      />

      {/* Main Editor */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Flows */}
        <FlowSidebar
          flows={flows}
          activeIndex={activeFlowIndex}
          onSelectFlow={handleFlowSwitch}
          onCreateFlow={() => dialogState.openDialog("createFlow")}
          onDeleteFlow={handleDeleteFlow}
          botId={botId}
          checkUnsavedChanges={withUnsavedChangesGuard}
        />

        {/* Center Canvas */}
        <div className="flex-1 relative bg-muted">
          {!activeFlow ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-muted-foreground mb-4">No flows available</p>
                <Button onClick={() => dialogState.openDialog("createFlow")}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create First Flow
                </Button>
              </div>
            </div>
          ) : (
            <>
              <FlowCanvas
                nodes={reactFlowNodes}
                edges={edges}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                onNodeClick={onNodeClick}
                onPaneClick={onPaneClick}
                onNodesChange={handleNodesChange}
                onNodeDragStart={handleNodeDragStart}
                onNodeDrag={handleNodeDrag}
                onNodeDragStop={handleNodeDragStop}
                onEdgeMouseEnter={(_, edge) => {
                  // Only set hover if not dragging a node
                  if (!isDraggingRef.current) {
                    setHoveredEdgeId(edge.id);
                  }
                }}
                onEdgeMouseLeave={() => {
                  // Only clear hover if not dragging a node
                  if (!isDraggingRef.current) {
                    setHoveredEdgeId(null);
                  }
                }}
                pendingNodeSelection={!!pendingNodeSelectionRef.current}
                hoveredEdgeId={hoveredEdgeId}
                isDraggingNode={isDraggingRef.current}
                skipFitView={skipFitView}
              />

              {/* Contextual shortcuts hint */}
              {reactFlowNodes.length > 0 && (
                <ContextualShortcutsHint
                  hasNodeSelected={!!selectedNodeId}
                  onShowAllShortcuts={() => setShowKeyboardHelp(true)}
                />
              )}

              {/* Empty state - Add first node */}
              {reactFlowNodes.length === 0 && (
                <EmptyFlowState
                  onSelectNodeType={(type) =>
                    insertNode("start", undefined, type)
                  }
                />
              )}
            </>
          )}
        </div>

        {/* Right Sidebar - Node/Flow Configuration */}
        {activeFlow && (
          <div className="w-80 bg-background border-l border-border overflow-y-auto">
            {selectedNode ? (
              <NodeConfigurationPanel
                ref={nodeConfigPanelRef}
                nodeId={selectedNodeId!}
                nodeType={selectedNode.type}
                nodeName={selectedNode.name}
                initialConfig={selectedNode.config}
                initialRoutes={selectedNode.routes || []}
                onChange={handleNodeConfigChange}
                availableNodes={availableNodes}
                variables={Object.entries(
                  activeFlow.variables || {}
                ).map(([name, def]) => ({
                  name,
                  type: def.type,
                }))}
                botId={botId}
                onCreateVariable={async (variable) => {
                  updateFlowSettings({
                    variables: {
                      ...activeFlow.variables,
                      [variable.name]: {
                        type: variable.type as Flow['variables'][string]['type'],
                        default: variable.default,
                      },
                    },
                  });
                }}
                syncKey={syncKey}
              />
            ) : (
              <FlowSettingsPanel
                flow={activeFlow}
                onChange={handleFlowSettingsChange}
                botId={botId!}
                nodes={Object.values(activeFlow.nodes || {}).map(node => ({
                  id: node.id,
                  name: node.name,
                }))}
                existingFlowNames={flows
                  .filter((f) => f.flow_id !== activeFlow.flow_id)
                  .map((f) => f.name)}
                existingTriggerKeywords={new Map(
                  flows
                    .filter((f) => f.flow_id !== activeFlow.flow_id)
                    .flatMap((f) =>
                      f.trigger_keywords.map((kw) => [kw.toUpperCase(), f.name])
                    )
                )}
                syncKey={syncKey}
              />
            )}
          </div>
        )}
      </div>

      {/* Dialogs */}
      <CreateFlowDialog
        open={dialogState.createFlowDialogOpen}
        onOpenChange={dialogState.setCreateFlowDialogOpen}
        onSuccess={async (newFlow) => {
          setFlows([...flows, newFlow]);
          // Navigate to the newly created flow
          if (newFlow.flow_id && botId) {
            navigate(`/bots/${botId}/flows/${newFlow.flow_id}`, { replace: true });
          }
        }}
        botId={botId!}
        existingFlowNames={flows.map((f) => f.name)}
        existingTriggerKeywords={
          new Map(
            flows.flatMap((f) =>
              f.trigger_keywords.map((kw) => [kw.toUpperCase(), f.name])
            )
          )
        }
      />

      <EditBotDialog
        open={dialogState.botSettingsDialogOpen}
        onOpenChange={dialogState.setBotSettingsDialogOpen}
        bot={bot}
        onSuccess={() => {
          // Invalidate bot query to refetch updated data
          queryClient.invalidateQueries({ queryKey: botsKeys.detail(botId!) });
        }}
      />

      <ChatSimulator
        key={simulatorKey}
        open={dialogState.chatSimulatorOpen}
        onOpenChange={dialogState.setChatSimulatorOpen}
        bot={bot}
        flow={activeFlow}
        flows={flows}
        initialMessage={simulatorInitialMessage}
      />

      {/* Unsaved Changes Warning */}
      <AlertDialog
        open={dialogState.showUnsavedWarning}
        onOpenChange={dialogState.setShowUnsavedWarning}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Unsaved Changes</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved changes in this node's configuration. Do you want
              to discard these changes?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleUnsavedChangesCancel}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleUnsavedChangesConfirm}>
              Discard Changes
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Node Confirmation */}
      <AlertDialog
        open={dialogState.showDeleteConfirmation}
        onOpenChange={dialogState.setShowDeleteConfirmation}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Node</AlertDialogTitle>
            <AlertDialogDescription>
              {nodesToBeDeleted.length > 0 ? (
                <div className="space-y-2">
                  <p>
                    Deleting this branching node will also delete the following{" "}
                    {nodesToBeDeleted.length} child node{nodesToBeDeleted.length > 1 ? "s" : ""}:
                  </p>
                  <ul className="list-disc list-inside pl-2 text-sm max-h-32 overflow-y-auto">
                    {nodesToBeDeleted.map((name, index) => (
                      <li key={index} className="text-foreground">{name}</li>
                    ))}
                  </ul>
                  <p className="text-xs text-muted-foreground mt-2">
                    The main flow path (true condition) will be preserved.
                  </p>
                </div>
              ) : (
                "Are you sure you want to delete this node? This action cannot be undone."
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => dialogState.closeDialog("deleteConfirmation")}
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteNodeConfirm}
              className="bg-destructive hover:bg-destructive focus:ring-destructive"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Keyboard Shortcuts Help Dialog */}
      <KeyboardShortcutsHelpDialog
        open={showKeyboardHelp}
        onOpenChange={setShowKeyboardHelp}
      />

      {/* Condition Popover for Stub Drag-to-Connect */}
      <Popover
        open={!!pendingConnection}
        onOpenChange={(open) => {
          if (!open) {
            // Save on close if condition is valid
            if (pendingConnection && pendingCondition.trim()) {
              createRouteToExistingNode(
                pendingConnection.sourceNodeId,
                pendingConnection.targetNodeId,
                pendingCondition.trim()
              );
            } else {
              setPendingConnection(null);
              setPendingCondition("");
            }
          }
        }}
      >
        {/* Invisible anchor positioned below the target node */}
        <PopoverTrigger asChild>
          <span
            className="fixed w-0 h-0"
            style={{
              left: pendingConnection?.anchorPosition?.x ?? '50%',
              top: pendingConnection?.anchorPosition?.y ?? '50%',
            }}
            aria-hidden="true"
          />
        </PopoverTrigger>
        <PopoverContent
          className="w-80 p-3 bg-background max-h-[60vh] overflow-y-auto"
          align="start"
          side="right"
          sideOffset={8}
          collisionPadding={16}
          avoidCollisions={true}
        >
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">
              Route Condition
            </div>
            {pendingConnection && activeFlow && (
              <ConditionSelector
                nodeType={activeFlow.nodes[pendingConnection.sourceNodeId]?.type || "LOGIC_EXPRESSION"}
                nodeConfig={activeFlow.nodes[pendingConnection.sourceNodeId]?.config}
                value={pendingCondition}
                onChange={setPendingCondition}
                placeholder={
                  activeFlow.nodes[pendingConnection.sourceNodeId]?.type === "MENU"
                    ? "Select menu option"
                    : activeFlow.nodes[pendingConnection.sourceNodeId]?.type === "API_ACTION"
                    ? "Select condition"
                    : "e.g. context.value == true"
                }
                availableVariables={availableVariables}
              />
            )}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}

// Empty flow state component
function EmptyFlowState({
  onSelectNodeType,
}: {
  onSelectNodeType: (type: NodeType, condition?: string) => void;
}) {
  const [selectorOpen, setSelectorOpen] = useState(false);

  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div className="text-center pointer-events-auto">
        <NodeTypeSelector
          open={selectorOpen}
          onOpenChange={setSelectorOpen}
          onSelect={(type, condition) => {
            onSelectNodeType(type, condition);
            setSelectorOpen(false);
          }}
          parentNode={undefined}
        />
      </div>
    </div>
  );
}

// Main export with providers
export default function FlowEditorPage() {
  return (
    <FlowEditorProvider>
      <ReactFlowProvider>
        <FlowEditorContent />
      </ReactFlowProvider>
    </FlowEditorProvider>
  );
}
