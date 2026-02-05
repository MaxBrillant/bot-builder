import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  useRef,
  useEffect,
  type ReactNode,
} from 'react';
import isEqual from 'fast-deep-equal';
import { toast } from 'sonner';
import { updateFlow as updateFlowAPI, deleteFlow as deleteFlowAPI } from '@/lib/api';
import { useQueryClient } from '@tanstack/react-query';
import { flowsKeys } from '@/hooks/queries/useFlowsQuery';
import { botsKeys } from '@/hooks/queries/useBotsQuery';
import type { Flow, FlowNode, NodeType, Route, NodeConfig } from '@/lib/types';
import {
  insertNodeInFlow,
  deleteNodeFromFlow,
  moveNodeLeft,
  moveNodeRight,
  moveNodeBetween,
} from '@/lib/flowLayoutUtils';
import { snapToGrid } from '@/utils/canvasPositioningUtils';
import {
  createHistoryManager,
  CommandType,
  createCommand,
  generatePatchPair,
} from '@/lib/history';

// ============================================
// Types
// ============================================

interface FlowEditorContextType {
  // Multi-flow management
  flows: Flow[];
  activeFlowIndex: number;
  setFlows: (flows: Flow[]) => void;
  setActiveFlowIndex: (index: number) => void;

  // Core state
  serverState: Flow | null;
  draftState: Flow | null;
  selectedNodeId: string | null;
  isSaving: boolean;

  // Derived
  isDirty: boolean;
  selectedNode: FlowNode | null;
  canSave: boolean;
  availableNodes: Array<{ id: string; type: NodeType; name: string }>;
  availableVariables: string[];

  // Actions
  loadFlow: (flow: Flow) => void;
  reset: () => void;
  selectNode: (nodeId: string | null) => void;
  clearSelection: () => void;

  // Draft mutations - flow settings
  updateFlowSettings: (patch: Partial<Pick<Flow, 'name' | 'trigger_keywords' | 'variables' | 'defaults'>>) => void;

  // Draft mutations - node operations
  updateNode: (nodeId: string, patch: Partial<FlowNode>) => void;
  updateNodeConfig: (nodeId: string, config: NodeConfig) => void;
  updateNodeName: (nodeId: string, name: string) => void;
  updateNodeRoutes: (nodeId: string, routes: Route[]) => void;
  updateNodePosition: (nodeId: string, position: { x: number; y: number }) => void;
  updateMultipleNodePositions: (positions: Record<string, { x: number; y: number }>) => void;

  // Draft mutations - structural operations
  insertNode: (
    position: 'start' | 'after',
    targetId: string | undefined,
    nodeType: NodeType,
    condition?: string,
    routeIndex?: number
  ) => string | null;
  deleteNode: (nodeId: string) => boolean;
  moveLeft: (nodeId: string) => boolean;
  moveRight: (nodeId: string) => boolean;
  moveNodeBetweenEdge: (nodeId: string, edgeId: string) => boolean;

  // Persistence
  save: (botId: string) => Promise<boolean>;
  revert: () => void;
  deleteActiveFlow: (botId: string) => Promise<boolean>;

  // History (undo/redo)
  canUndo: boolean;
  canRedo: boolean;
  undo: () => void;
  redo: () => void;
  syncKey: number; // Increments on undo/redo to signal panels to re-sync

  // Utility refs for external access
  pendingNodeSelectionRef: React.MutableRefObject<string | null>;
}

const FlowEditorContext = createContext<FlowEditorContextType | undefined>(undefined);

// ============================================
// Helper to extract error messages
// ============================================

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const axiosError = error as any;
    if (axiosError.response?.data?.detail) {
      const details = axiosError.response.data.detail;
      if (Array.isArray(details)) {
        return details
          .map((err: any) => `${err.loc?.join('.')}: ${err.msg}`)
          .join(', ');
      }
      return details;
    }
  }
  return 'An unexpected error occurred';
}

// ============================================
// Provider
// ============================================

export function FlowEditorProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  // Multi-flow management
  const [flows, setFlowsState] = useState<Flow[]>([]);
  const [activeFlowIndex, setActiveFlowIndex] = useState(0);

  // Core state - serverState is the last saved state, draftState is working copy
  const [serverState, setServerState] = useState<Flow | null>(null);
  const [draftState, setDraftState] = useState<Flow | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Ref for pending node selection after insert operations
  const pendingNodeSelectionRef = useRef<string | null>(null);

  // ========== History Management ==========

  // Single instance of history manager for the lifetime of the provider
  const historyManagerRef = useRef(createHistoryManager());
  const historyManager = historyManagerRef.current;

  // Track history version to trigger re-renders when history changes
  const [historyVersion, setHistoryVersion] = useState(0);

  // Sync key increments on undo/redo to signal panels to re-sync from props
  const [syncKey, setSyncKey] = useState(0);

  // Debounce timer for config updates (to batch rapid typing)
  const debounceTimerRef = useRef<number | null>(null);
  const pendingCommandRef = useRef<{
    type: CommandType;
    flowId: string;
    description: string;
    baseState: Flow;
    affectedNodeIds?: string[];
  } | null>(null);

  // Track last commit time for coalescing across debounced/non-debounced commands
  const lastCommitTimestampRef = useRef<number>(0);
  const COALESCE_WINDOW_MS = 200;

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        window.clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Derived history state
  const canUndo = useMemo(() => {
    // Reference historyVersion to re-evaluate when history changes
    void historyVersion;
    if (!draftState?.flow_id) return false;
    return historyManager.canUndo(draftState.flow_id);
  }, [draftState?.flow_id, historyVersion, historyManager]);

  const canRedo = useMemo(() => {
    // Reference historyVersion to re-evaluate when history changes
    void historyVersion;
    if (!draftState?.flow_id) return false;
    return historyManager.canRedo(draftState.flow_id);
  }, [draftState?.flow_id, historyVersion, historyManager]);

  // Command types that should be debounced (continuous input like typing)
  // Note: UPDATE_FLOW_SETTINGS is NOT debounced - it's discrete actions (add keyword, add variable)
  const DEBOUNCED_COMMAND_TYPES = [
    CommandType.UPDATE_NODE_CONFIG,
    CommandType.UPDATE_NODE_POSITION,
  ];

  // Helper to actually commit a command to history
  const commitCommand = useCallback((
    commandType: CommandType,
    flowId: string,
    description: string,
    baseState: Flow,
    finalState: Flow,
    affectedNodeIds?: string[]
  ) => {
    const { patches, inversePatches } = generatePatchPair(baseState, finalState);

    if (patches.length > 0) {
      const command = createCommand({
        type: commandType,
        flowId,
        description,
        patches,
        inversePatches,
        affectedNodeIds,
      });
      historyManager.record(flowId, command);
      setHistoryVersion(historyManager.getVersion());
      lastCommitTimestampRef.current = Date.now();
    }
  }, [historyManager]);

  // Ref for latest draft state (for debounced commits)
  const draftStateRef = useRef(draftState);
  useEffect(() => {
    draftStateRef.current = draftState;
  }, [draftState]);

  // Helper to record a command and trigger re-render
  // For config updates, uses debouncing to batch rapid changes
  const recordCommand = useCallback((
    commandType: CommandType,
    description: string,
    oldState: Flow,
    newState: Flow,
    affectedNodeIds?: string[]
  ) => {
    if (!oldState.flow_id) return;

    // For debounced commands (config updates), use debouncing
    if (DEBOUNCED_COMMAND_TYPES.includes(commandType)) {
      // If a command was recently committed, skip debounce to allow coalescing
      const timeSinceLastCommit = Date.now() - lastCommitTimestampRef.current;
      if (timeSinceLastCommit < COALESCE_WINDOW_MS) {
        // Commit immediately so history manager can coalesce
        commitCommand(commandType, oldState.flow_id, description, oldState, newState, affectedNodeIds);
        return;
      }

      // If there's a pending command of a DIFFERENT type, commit it first
      if (pendingCommandRef.current && pendingCommandRef.current.type !== commandType) {
        const pending = pendingCommandRef.current;
        if (debounceTimerRef.current) {
          window.clearTimeout(debounceTimerRef.current);
          debounceTimerRef.current = null;
        }
        // Commit the pending command with oldState (state before current mutation)
        commitCommand(
          pending.type,
          pending.flowId,
          pending.description,
          pending.baseState,
          oldState,
          pending.affectedNodeIds
        );
        pendingCommandRef.current = null;
      }

      // If no pending command, start fresh
      if (!pendingCommandRef.current) {
        pendingCommandRef.current = {
          type: commandType,
          flowId: oldState.flow_id,
          description,
          baseState: oldState,
          affectedNodeIds,
        };
      }

      // Clear existing timer
      if (debounceTimerRef.current) {
        window.clearTimeout(debounceTimerRef.current);
      }

      // Set new timer to commit after delay
      debounceTimerRef.current = window.setTimeout(() => {
        const pending = pendingCommandRef.current;
        const currentState = draftStateRef.current;
        if (pending && currentState) {
          commitCommand(
            pending.type,
            pending.flowId,
            pending.description,
            pending.baseState,
            currentState,
            pending.affectedNodeIds
          );
        }
        pendingCommandRef.current = null;
        debounceTimerRef.current = null;
      }, 500); // 500ms debounce for typing

      return;
    }

    // For non-debounced commands (structural changes), commit immediately
    // But first, commit any pending debounced command
    if (pendingCommandRef.current) {
      const pending = pendingCommandRef.current;
      if (debounceTimerRef.current) {
        window.clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      // Commit pending command with the state before this new command
      commitCommand(
        pending.type,
        pending.flowId,
        pending.description,
        pending.baseState,
        oldState,
        pending.affectedNodeIds
      );
      pendingCommandRef.current = null;
    }

    // Now commit the new command immediately
    commitCommand(commandType, oldState.flow_id, description, oldState, newState, affectedNodeIds);
  }, [commitCommand]);

  // ========== Derived values ==========

  const isDirty = useMemo(() => {
    if (!serverState || !draftState) return false;
    return !isEqual(serverState, draftState);
  }, [serverState, draftState]);

  const selectedNode = useMemo(() => {
    if (!selectedNodeId || !draftState) return null;
    return draftState.nodes[selectedNodeId] ?? null;
  }, [selectedNodeId, draftState]);

  const canSave = isDirty && !isSaving;

  const availableNodes = useMemo(() => {
    if (!draftState?.nodes) return [];
    return Object.entries(draftState.nodes).map(([id, node]) => ({
      id,
      type: node.type,
      name: node.name,
    }));
  }, [draftState?.nodes]);

  const availableVariables = useMemo(() => {
    if (!draftState?.variables) return [];
    return Object.keys(draftState.variables);
  }, [draftState?.variables]);

  // ========== Multi-flow management ==========

  const setFlows = useCallback((newFlows: Flow[]) => {
    setFlowsState(newFlows);

    // If we have flows and an active index, sync to editor state
    if (newFlows.length > 0) {
      const currentIndex = Math.min(activeFlowIndex, newFlows.length - 1);
      const flow = newFlows[currentIndex];
      setServerState(flow);
      setDraftState(structuredClone(flow));
      setSelectedNodeId(null);
    } else {
      setServerState(null);
      setDraftState(null);
      setSelectedNodeId(null);
    }
  }, [activeFlowIndex]);

  // Sync when activeFlowIndex changes
  const handleSetActiveFlowIndex = useCallback((index: number) => {
    setActiveFlowIndex(index);
    if (flows[index]) {
      setServerState(flows[index]);
      setDraftState(structuredClone(flows[index]));
      setSelectedNodeId(null);
    }
  }, [flows]);

  // ========== Initialization ==========

  const loadFlow = useCallback((flow: Flow) => {
    setServerState(flow);
    setDraftState(structuredClone(flow));
    setSelectedNodeId(null);
  }, []);

  const reset = useCallback(() => {
    setServerState(null);
    setDraftState(null);
    setSelectedNodeId(null);
    setIsSaving(false);
  }, []);

  // ========== Selection ==========

  const selectNode = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  // ========== Draft Mutations - Flow Settings ==========

  const updateFlowSettings = useCallback((
    patch: Partial<Pick<Flow, 'name' | 'trigger_keywords' | 'variables' | 'defaults'>>
  ) => {
    setDraftState((prev) => {
      if (!prev) return prev;
      const newState = { ...prev, ...patch };

      // Record history
      recordCommand(
        CommandType.UPDATE_FLOW_SETTINGS,
        'Update flow settings',
        prev,
        newState
      );

      return newState;
    });
  }, [recordCommand]);

  // ========== Draft Mutations - Node Operations ==========

  const updateNode = useCallback((nodeId: string, patch: Partial<FlowNode>) => {
    setDraftState((prev) => {
      if (!prev || !prev.nodes[nodeId]) return prev;
      const newState = {
        ...prev,
        nodes: {
          ...prev.nodes,
          [nodeId]: { ...prev.nodes[nodeId], ...patch },
        },
      };

      // Record history
      recordCommand(
        CommandType.UPDATE_NODE_CONFIG,
        `Update node "${prev.nodes[nodeId].name}"`,
        prev,
        newState,
        [nodeId]
      );

      return newState;
    });
  }, [recordCommand]);

  const updateNodeConfig = useCallback((nodeId: string, config: NodeConfig) => {
    updateNode(nodeId, { config });
  }, [updateNode]);

  const updateNodeName = useCallback((nodeId: string, name: string) => {
    updateNode(nodeId, { name });
  }, [updateNode]);

  const updateNodeRoutes = useCallback((nodeId: string, routes: Route[]) => {
    updateNode(nodeId, { routes });
  }, [updateNode]);

  const updateNodePosition = useCallback((nodeId: string, position: { x: number; y: number }) => {
    setDraftState((prev) => {
      if (!prev || !prev.nodes[nodeId]) return prev;
      const newState = {
        ...prev,
        nodes: {
          ...prev.nodes,
          [nodeId]: {
            ...prev.nodes[nodeId],
            position: {
              x: snapToGrid(position.x),
              y: snapToGrid(position.y),
            },
          },
        },
      };

      // Record history
      recordCommand(
        CommandType.UPDATE_NODE_POSITION,
        `Move node "${prev.nodes[nodeId].name}"`,
        prev,
        newState,
        [nodeId]
      );

      return newState;
    });
  }, [recordCommand]);

  const updateMultipleNodePositions = useCallback((
    positions: Record<string, { x: number; y: number }>
  ) => {
    setDraftState((prev) => {
      if (!prev) return prev;
      const updatedNodes = { ...prev.nodes };
      for (const [nodeId, position] of Object.entries(positions)) {
        if (updatedNodes[nodeId]) {
          updatedNodes[nodeId] = {
            ...updatedNodes[nodeId],
            position: {
              x: snapToGrid(position.x),
              y: snapToGrid(position.y),
            },
          };
        }
      }
      const newState = { ...prev, nodes: updatedNodes };

      // Record history
      recordCommand(
        CommandType.BATCH_UPDATE_POSITIONS,
        `Move ${Object.keys(positions).length} node(s)`,
        prev,
        newState,
        Object.keys(positions)
      );

      return newState;
    });
  }, [recordCommand]);

  // ========== Draft Mutations - Structural Operations ==========

  const insertNode = useCallback((
    position: 'start' | 'after',
    targetId: string | undefined,
    nodeType: NodeType,
    condition?: string,
    routeIndex?: number
  ): string | null => {
    let newNodeId: string | null = null;

    setDraftState((prev) => {
      if (!prev) return prev;

      try {
        // Determine if we should use route overtaking
        let actualRouteIndex = routeIndex;
        if (position === 'after' && targetId && condition && actualRouteIndex === undefined) {
          const targetNode = prev.nodes[targetId];
          if (targetNode?.routes) {
            const foundIndex = targetNode.routes.findIndex(
              (route) => route.condition.trim().toLowerCase() === condition.trim().toLowerCase()
            );
            if (foundIndex !== -1) {
              actualRouteIndex = foundIndex;
            }
          }
        }

        const result = insertNodeInFlow(prev, position, targetId, nodeType, condition, actualRouteIndex);
        newNodeId = result.newNodeId;

        // Store for selection after render
        pendingNodeSelectionRef.current = newNodeId;

        // Record history
        recordCommand(
          CommandType.INSERT_NODE,
          `Insert ${nodeType} node`,
          prev,
          result.flow,
          [newNodeId]
        );

        return result.flow;
      } catch (error) {
        toast.error(`Failed to insert node: ${error instanceof Error ? error.message : 'Unknown error'}`);
        return prev;
      }
    });

    if (newNodeId) {
      toast.success(`${nodeType} node added`);
    }

    return newNodeId;
  }, [recordCommand]);

  const deleteNode = useCallback((nodeId: string): boolean => {
    let success = false;
    let nodeToDelete: FlowNode | undefined;
    let deletedCount = 0;

    setDraftState((prev) => {
      if (!prev) return prev;

      nodeToDelete = prev.nodes[nodeId];
      const originalCount = Object.keys(prev.nodes).length;

      try {
        const result = deleteNodeFromFlow(prev, nodeId);
        const newCount = Object.keys(result.nodes).length;
        deletedCount = originalCount - newCount;
        success = true;

        // Record history
        recordCommand(
          CommandType.DELETE_NODE,
          `Delete node "${nodeToDelete?.name}"`,
          prev,
          result,
          [nodeId]
        );

        return result;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';

        if (errorMessage.includes('start node')) {
          toast.error('Cannot delete the start node', {
            description: 'The start node is the entry point of the flow and cannot be deleted.',
          });
        } else if (errorMessage.includes('END node')) {
          toast.error('Cannot delete END nodes', {
            description: 'END nodes mark flow completion points and cannot be deleted.',
          });
        } else if (errorMessage.includes("'true' (catch-all) route")) {
          toast.error('Cannot delete branch node', {
            description: "Branch node must have a 'true' (catch-all) route.",
          });
        } else {
          toast.error(`Failed to delete node: ${errorMessage}`);
        }
        return prev;
      }
    });

    if (success) {
      // Clear selection if deleted node was selected
      if (selectedNodeId === nodeId) {
        setSelectedNodeId(null);
      }

      // Show appropriate success message
      const isBranchNode = nodeToDelete && ['MENU', 'API_ACTION', 'LOGIC_EXPRESSION'].includes(nodeToDelete.type);
      const hasMultipleRoutes = (nodeToDelete?.routes?.length || 0) > 1;

      if (isBranchNode && hasMultipleRoutes && deletedCount > 1) {
        toast.success(`Deleted ${deletedCount} node${deletedCount > 1 ? 's' : ''}`, {
          description: 'Preserved the main flow path (true condition).',
        });
      } else {
        toast.success('Node deleted');
      }
    }

    return success;
  }, [selectedNodeId, recordCommand]);

  const moveLeft = useCallback((nodeId: string): boolean => {
    let success = false;

    setDraftState((prev) => {
      if (!prev) return prev;
      const result = moveNodeLeft(prev, nodeId);
      if (result) {
        success = true;

        // Record history
        recordCommand(
          CommandType.MOVE_NODE_LEFT,
          `Move node "${prev.nodes[nodeId]?.name}" left`,
          prev,
          result,
          [nodeId]
        );

        return result;
      }
      return prev;
    });

    if (success) {
      toast.success('Node moved left');
    } else {
      toast.error('Cannot move node left');
    }

    return success;
  }, [recordCommand]);

  const moveRight = useCallback((nodeId: string): boolean => {
    let success = false;

    setDraftState((prev) => {
      if (!prev) return prev;
      const result = moveNodeRight(prev, nodeId);
      if (result) {
        success = true;

        // Record history
        recordCommand(
          CommandType.MOVE_NODE_RIGHT,
          `Move node "${prev.nodes[nodeId]?.name}" right`,
          prev,
          result,
          [nodeId]
        );

        return result;
      }
      return prev;
    });

    if (success) {
      toast.success('Node moved right');
    } else {
      toast.error('Cannot move node right');
    }

    return success;
  }, [recordCommand]);

  const moveNodeBetweenEdge = useCallback((nodeId: string, edgeId: string): boolean => {
    let success = false;

    setDraftState((prev) => {
      if (!prev) return prev;
      const result = moveNodeBetween(prev, nodeId, edgeId);
      if (result) {
        success = true;

        // Record history
        recordCommand(
          CommandType.MOVE_NODE_BETWEEN,
          `Reorder node "${prev.nodes[nodeId]?.name}"`,
          prev,
          result,
          [nodeId]
        );

        return result;
      }
      return prev;
    });

    return success;
  }, [recordCommand]);

  // ========== History Actions ==========

  // Helper to flush any pending debounced command
  const flushPendingCommand = useCallback(() => {
    if (pendingCommandRef.current && draftState) {
      const pending = pendingCommandRef.current;
      if (debounceTimerRef.current) {
        window.clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      commitCommand(
        pending.type,
        pending.flowId,
        pending.description,
        pending.baseState,
        draftState,
        pending.affectedNodeIds
      );
      pendingCommandRef.current = null;
    }
  }, [draftState, commitCommand]);

  const undo = useCallback(() => {
    if (!draftState?.flow_id) return;

    // Flush any pending command before undo
    flushPendingCommand();

    const newState = historyManager.undo(draftState.flow_id, draftState);

    if (newState) {
      setDraftState(newState);
      setHistoryVersion(historyManager.getVersion());
      setSyncKey((prev) => prev + 1); // Signal panels to re-sync
      toast.info('Undo');
    }
  }, [draftState, historyManager, flushPendingCommand]);

  const redo = useCallback(() => {
    if (!draftState?.flow_id) return;

    // Flush any pending command before redo
    flushPendingCommand();

    const newState = historyManager.redo(draftState.flow_id, draftState);

    if (newState) {
      setDraftState(newState);
      setHistoryVersion(historyManager.getVersion());
      setSyncKey((prev) => prev + 1); // Signal panels to re-sync
      toast.info('Redo');
    }
  }, [draftState, historyManager, flushPendingCommand]);

  // ========== Persistence ==========

  const save = useCallback(async (botId: string): Promise<boolean> => {
    if (!draftState || !draftState.flow_id) {
      toast.error('No flow to save');
      return false;
    }

    setIsSaving(true);

    try {
      const savedFlow = await updateFlowAPI(botId, draftState.flow_id, {
        name: draftState.name,
        trigger_keywords: draftState.trigger_keywords,
        variables: draftState.variables,
        defaults: draftState.defaults,
        start_node_id: draftState.start_node_id,
        nodes: draftState.nodes,
      });

      // Update both states to the saved version
      setServerState(savedFlow);
      setDraftState(structuredClone(savedFlow));

      // Update the flows array with the saved flow
      setFlowsState((prevFlows) =>
        prevFlows.map((f) => (f.flow_id === savedFlow.flow_id ? savedFlow : f))
      );

      // Invalidate cache for consistency
      queryClient.invalidateQueries({ queryKey: flowsKeys.list(botId) });

      toast.success('Flow saved');
      return true;
    } catch (error) {
      console.error('Failed to save flow:', error);
      toast.error(`Failed to save flow: ${getErrorMessage(error)}`);
      return false;
    } finally {
      setIsSaving(false);
    }
  }, [draftState, queryClient]);

  const revert = useCallback(() => {
    if (serverState) {
      setDraftState(structuredClone(serverState));
      toast.info('Changes reverted');
    }
  }, [serverState]);

  const deleteActiveFlow = useCallback(async (botId: string): Promise<boolean> => {
    if (!draftState || !draftState.flow_id) {
      toast.error('No flow to delete');
      return false;
    }

    try {
      await deleteFlowAPI(botId, draftState.flow_id);

      const deletedFlowId = draftState.flow_id;

      // Remove from flows array
      setFlowsState((prevFlows) => {
        const newFlows = prevFlows.filter((f) => f.flow_id !== deletedFlowId);

        // Update active index if needed
        if (newFlows.length > 0) {
          const newIndex = Math.min(activeFlowIndex, newFlows.length - 1);
          setActiveFlowIndex(newIndex);
          setServerState(newFlows[newIndex]);
          setDraftState(structuredClone(newFlows[newIndex]));
        } else {
          setServerState(null);
          setDraftState(null);
        }

        return newFlows;
      });

      setSelectedNodeId(null);

      // Invalidate caches
      queryClient.invalidateQueries({ queryKey: flowsKeys.list(botId) });
      queryClient.invalidateQueries({ queryKey: botsKeys.lists() });

      toast.success('Flow deleted');
      return true;
    } catch (error) {
      console.error('Failed to delete flow:', error);
      toast.error(`Failed to delete flow: ${getErrorMessage(error)}`);
      return false;
    }
  }, [draftState, activeFlowIndex, queryClient]);

  // ========== Context Value ==========

  const value = useMemo<FlowEditorContextType>(() => ({
    // Multi-flow management
    flows,
    activeFlowIndex,
    setFlows,
    setActiveFlowIndex: handleSetActiveFlowIndex,

    // Core state
    serverState,
    draftState,
    selectedNodeId,
    isSaving,

    // Derived
    isDirty,
    selectedNode,
    canSave,
    availableNodes,
    availableVariables,

    // Actions
    loadFlow,
    reset,
    selectNode,
    clearSelection,
    updateFlowSettings,
    updateNode,
    updateNodeConfig,
    updateNodeName,
    updateNodeRoutes,
    updateNodePosition,
    updateMultipleNodePositions,
    insertNode,
    deleteNode,
    moveLeft,
    moveRight,
    moveNodeBetweenEdge,
    save,
    revert,
    deleteActiveFlow,
    canUndo,
    canRedo,
    undo,
    redo,
    syncKey,
    pendingNodeSelectionRef,
  }), [
    flows,
    activeFlowIndex,
    setFlows,
    handleSetActiveFlowIndex,
    serverState,
    draftState,
    selectedNodeId,
    isSaving,
    isDirty,
    selectedNode,
    canSave,
    availableNodes,
    availableVariables,
    loadFlow,
    reset,
    selectNode,
    clearSelection,
    updateFlowSettings,
    updateNode,
    updateNodeConfig,
    updateNodeName,
    updateNodeRoutes,
    updateNodePosition,
    updateMultipleNodePositions,
    insertNode,
    deleteNode,
    moveLeft,
    moveRight,
    moveNodeBetweenEdge,
    save,
    revert,
    deleteActiveFlow,
    canUndo,
    canRedo,
    undo,
    redo,
    syncKey,
  ]);

  return (
    <FlowEditorContext.Provider value={value}>
      {children}
    </FlowEditorContext.Provider>
  );
}

// ============================================
// Hook
// ============================================

export function useFlowEditor() {
  const context = useContext(FlowEditorContext);
  if (!context) {
    throw new Error('useFlowEditor must be used within FlowEditorProvider');
  }
  return context;
}
