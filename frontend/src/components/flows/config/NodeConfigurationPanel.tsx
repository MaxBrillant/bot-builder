import {
  useState,
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
} from "react";
import isEqual from "fast-deep-equal";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { AlertCircle, ChevronRight } from "lucide-react";
import { TextConfigForm } from "./forms/TextConfigForm";
import { LogicExpressionConfigForm } from "./forms/LogicExpressionConfigForm";
import { PromptConfigForm } from "./forms/PromptConfigForm";
import { MenuConfigForm } from "./forms/MenuConfigForm";
import { ApiActionConfigForm } from "./forms/ApiActionConfigForm";
import { RouteEditor } from "./shared/RouteEditor";
import {
  validateNodeConfig,
  validateRoutes,
} from "@/lib/validators/nodeConfigValidators";
import { sortRoutes } from "@/lib/routeConditionUtils";
import type {
  NodeType,
  NodeConfig,
  TextNodeConfig,
  LogicExpressionNodeConfig,
  PromptNodeConfig,
  MenuNodeConfig,
  APIActionNodeConfig,
  ValidationError,
  Route,
  VariableType,
  VariableInfo,
} from "@/lib/types";
import { cn } from "@/lib/utils";

export interface NodeConfigurationPanelRef {
  focusNameInput: () => void;
}

interface NodeConfigurationPanelProps {
  nodeId: string;
  nodeType: NodeType;
  nodeName: string;
  initialConfig: NodeConfig;
  initialRoutes?: Route[];
  // onChange is debounced (500ms) to prevent cascade re-renders on every keystroke
  // Validation errors update immediately in local state, context updates are batched
  onChange?: (data: {
    nodeId: string;
    nodeName: string;
    config: NodeConfig;
    routes: Route[];
    isValid: boolean;
    errors: ValidationError[];
  }) => void;
  availableVariables?: VariableInfo[];
  availableNodes?: Array<{ id: string; type: NodeType; name: string }>;
  variables?: Array<{ name: string; type: VariableType }>;
  onCreateVariable: (variable: {
    name: string;
    type: VariableType;
    default: any;
  }) => Promise<void>;
  botId?: string;
  syncKey?: number; // Increments on undo/redo to signal re-sync from props
}

// Node types that support manual branching/routing via route editor
// Routes are now managed visually on the canvas for all node types
const BRANCHING_NODE_TYPES: NodeType[] = [];

export const NodeConfigurationPanel = forwardRef<
  NodeConfigurationPanelRef,
  NodeConfigurationPanelProps
>(function NodeConfigurationPanel(
  {
    nodeId,
    nodeType,
    nodeName,
    initialConfig,
    initialRoutes = [],
    onChange,
    availableVariables,
    availableNodes,
    variables = [],
    onCreateVariable,
    botId,
    syncKey,
  },
  ref,
) {
  // Derive availableVariables from variables array (which has { name, type })
  // variables prop already has the same shape as VariableInfo[]
  const derivedAvailableVariables: VariableInfo[] = variables.map((v) => ({
    name: v.name,
    type: v.type,
  }));

  // Use passed availableVariables if provided, otherwise use derived
  // This maintains backward compatibility
  const safeAvailableVariables: VariableInfo[] =
    availableVariables ?? derivedAvailableVariables;
  const safeAvailableNodes = availableNodes ?? [];

  const [config, setConfig] = useState<NodeConfig>(initialConfig);
  const [routes, setRoutes] = useState<Route[]>(initialRoutes);
  const [errors, setErrors] = useState<ValidationError[]>([]);

  // Node name editing state
  const [editedNodeName, setEditedNodeName] = useState(nodeName);
  const [nameError, setNameError] = useState<string | null>(null);

  // Routes collapsible state
  const [isRoutesOpen, setIsRoutesOpen] = useState(false);

  // Track if we've made any edits to prevent unwanted resets
  const hasLocalEditsRef = useRef(false);

  // Track the last values we sent via onChange to prevent loops
  const lastSentValuesRef = useRef<{
    nodeName: string;
    config: any;
    routes: any[];
  } | null>(null);

  // Ref for node name input to enable auto-focus
  const nodeNameInputRef = useRef<HTMLInputElement>(null);

  // Debounce timer for context propagation (prevents re-renders on every keystroke)
  const debounceTimerRef = useRef<number | null>(null);

  // Expose imperative handle for parent to focus name input
  useImperativeHandle(ref, () => ({
    focusNameInput: () => {
      if (nodeNameInputRef.current) {
        nodeNameInputRef.current.focus();
        nodeNameInputRef.current.select();
      }
    },
  }));

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        window.clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Reset when switching to a different node (nodeId changes)
  useEffect(() => {
    // Clear any pending debounced changes for the previous node
    if (debounceTimerRef.current) {
      window.clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }

    setConfig(initialConfig);
    // Pre-sort routes to avoid triggering dirty state from auto-sort
    const sortedRoutes = initialRoutes.length > 1 ? sortRoutes(initialRoutes, nodeType) : initialRoutes;
    setRoutes(sortedRoutes);
    setErrors([]);
    setEditedNodeName(nodeName);
    setNameError(null);
    hasLocalEditsRef.current = false; // Clear edit flag on node change
    lastSentValuesRef.current = null; // Reset last sent values
  }, [nodeId]);

  // No auto-focus - user can press Enter to focus name input via keyboard shortcut

  // Also reset when initial props change AND we haven't made local edits yet
  // This handles the case where a newly created node gets updated with backend data
  useEffect(() => {
    if (!hasLocalEditsRef.current) {
      setConfig(initialConfig);
      // Pre-sort routes to avoid triggering dirty state from auto-sort
      const sortedRoutes = initialRoutes.length > 1 ? sortRoutes(initialRoutes, nodeType) : initialRoutes;
      setRoutes(sortedRoutes);
      setEditedNodeName(nodeName);
    }
  }, [initialConfig, initialRoutes, nodeName, nodeType]);

  // Auto-open routes collapsible when routes exist
  useEffect(() => {
    if (routes && routes.length > 0) {
      setIsRoutesOpen(true);
    }
  }, [routes]);

  // Reset local state when syncKey changes (undo/redo happened)
  useEffect(() => {
    if (syncKey === undefined || syncKey === 0) return;

    // Clear any pending debounced changes - critical to prevent stale updates after undo/redo
    if (debounceTimerRef.current) {
      window.clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }

    // Force re-initialization from props
    setConfig(initialConfig);
    // Pre-sort routes to avoid triggering dirty state from auto-sort
    const sortedRoutes = initialRoutes.length > 1 ? sortRoutes(initialRoutes, nodeType) : initialRoutes;
    setRoutes(sortedRoutes);
    setEditedNodeName(nodeName);
    setErrors([]);
    setNameError(null);

    // Reset tracking refs
    hasLocalEditsRef.current = false;
    lastSentValuesRef.current = null;
  }, [syncKey]); // Only depend on syncKey, not props (to avoid conflicts)

  // Note: Dirty state tracking removed - using unified onChange approach

  const handleConfigChange = (newConfig: NodeConfig) => {
    hasLocalEditsRef.current = true; // Mark that user has made edits
    setConfig(newConfig);
    // Clear errors when user makes changes
    if (errors.length > 0) {
      setErrors([]);
    }
  };

  const handleRoutesChange = (newRoutes: Route[]) => {
    hasLocalEditsRef.current = true; // Mark that user has made edits
    setRoutes(newRoutes);
    // Clear errors when user makes changes
    if (errors.length > 0) {
      setErrors([]);
    }
  };

  const handleNameChange = (newName: string) => {
    hasLocalEditsRef.current = true; // Mark that user has made edits
    setEditedNodeName(newName);
    setNameError(null);
  };

  // Store onChange in a ref to avoid infinite loops
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  // Validate and notify parent of changes whenever local state changes
  // Context propagation is debounced to prevent re-renders on every keystroke
  useEffect(() => {
    if (!hasLocalEditsRef.current) return; // Skip validation on initial mount

    // Check if current values match what we last sent (prevent loop)
    const currentValues = {
      nodeName: editedNodeName.trim(),
      config,
      routes,
    };

    if (lastSentValuesRef.current && isEqual(currentValues, lastSentValuesRef.current)) {
      return; // Already sent these exact values
    }

    // Validate name (synchronous - shows errors immediately)
    const trimmedName = editedNodeName.trim();
    let nameErrors: string[] = [];

    if (!trimmedName) {
      nameErrors.push("Node name is required");
      setNameError("Node name is required");
    } else if (trimmedName.length > 50) {
      nameErrors.push("Node name must be 50 characters or less");
      setNameError("Node name must be 50 characters or less");
    } else {
      setNameError(null);
    }

    // Validate config
    const configResult = validateNodeConfig(config, nodeType);

    // Validate routes (pass config for context-aware validation)
    const availableNodeIds = safeAvailableNodes.map((n) => n.id);
    const routesResult = validateRoutes(
      routes,
      nodeType,
      availableNodeIds,
      config,
    );

    // Combine all errors
    const allErrors = [
      ...nameErrors.map((msg) => ({ field: "name", message: msg })),
      ...configResult.errors,
      ...routesResult.errors,
    ];

    setErrors(allErrors);

    // Clear any pending debounce timer
    if (debounceTimerRef.current) {
      window.clearTimeout(debounceTimerRef.current);
    }

    // Debounce context propagation (500ms) to prevent cascade re-renders on every keystroke
    // Local state and validation errors update immediately, but context updates are batched
    debounceTimerRef.current = window.setTimeout(() => {
      // Store current values as last sent
      lastSentValuesRef.current = currentValues;

      // Notify parent of changes (even if invalid)
      if (onChangeRef.current) {
        onChangeRef.current({
          nodeId,
          nodeName: trimmedName,
          config,
          routes,
          isValid: allErrors.length === 0,
          errors: allErrors,
        });
      }
    }, 500);
  }, [
    editedNodeName,
    config,
    routes,
    nodeType,
    nodeId,
    safeAvailableNodes,
  ]);

  // Note: Keyboard shortcuts removed - save is now handled globally via FlowEditorPage

  const renderForm = () => {
    switch (nodeType) {
      case "TEXT":
        return (
          <TextConfigForm
            config={config as TextNodeConfig}
            onChange={handleConfigChange}
            errors={errors}
            availableVariables={safeAvailableVariables}
            nodeName={editedNodeName}
            onNodeNameChange={handleNameChange}
            nodeNameError={nameError || undefined}
            nodeNameInputRef={nodeNameInputRef}
          />
        );
      case "LOGIC_EXPRESSION":
        return (
          <LogicExpressionConfigForm
            config={config as LogicExpressionNodeConfig}
            onChange={handleConfigChange}
            errors={errors}
            nodeName={editedNodeName}
            onNodeNameChange={handleNameChange}
            nodeNameError={nameError || undefined}
            nodeNameInputRef={nodeNameInputRef}
          />
        );
      case "PROMPT":
        return (
          <PromptConfigForm
            config={config as PromptNodeConfig}
            onChange={handleConfigChange}
            errors={errors}
            availableVariables={safeAvailableVariables}
            availableNodes={safeAvailableNodes.map((n) => ({
              id: n.id,
              name: n.name,
            }))}
            variables={variables}
            onCreateVariable={onCreateVariable}
            nodeName={editedNodeName}
            onNodeNameChange={handleNameChange}
            nodeNameError={nameError || undefined}
            nodeNameInputRef={nodeNameInputRef}
          />
        );
      case "MENU":
        return (
          <MenuConfigForm
            config={config as MenuNodeConfig}
            onChange={handleConfigChange}
            errors={errors}
            availableVariables={safeAvailableVariables}
            availableNodes={safeAvailableNodes.map((n) => ({
              id: n.id,
              name: n.name,
            }))}
            variables={variables}
            onCreateVariable={onCreateVariable}
            nodeName={editedNodeName}
            onNodeNameChange={handleNameChange}
            nodeNameError={nameError || undefined}
            nodeNameInputRef={nodeNameInputRef}
          />
        );
      case "API_ACTION":
        return (
          <ApiActionConfigForm
            config={config as APIActionNodeConfig}
            onChange={handleConfigChange}
            errors={errors}
            availableVariables={safeAvailableVariables}
            variables={variables}
            onCreateVariable={onCreateVariable}
            nodeName={editedNodeName}
            onNodeNameChange={handleNameChange}
            nodeNameError={nameError || undefined}
            nodeNameInputRef={nodeNameInputRef}
            botId={botId}
          />
        );
      default:
        return (
          <div className="text-center py-6 text-muted-foreground">
            Unknown node type: {nodeType}
          </div>
        );
    }
  };

  const hasErrors = errors.length > 0;
  const isBranchingNode = BRANCHING_NODE_TYPES.includes(nodeType);

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Form Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {renderForm()}

        {/* Routes Section - only for branching nodes */}
        {isBranchingNode && (
          <>
            <Separator />
            <Collapsible open={isRoutesOpen} onOpenChange={setIsRoutesOpen}>
              <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
                <div className="flex items-center gap-2">
                  <ChevronRight
                    className={cn(
                      "h-4 w-4 text-muted-foreground transition-transform duration-200",
                      isRoutesOpen && "rotate-90",
                    )}
                  />
                  <span className="text-sm font-semibold text-foreground">
                    Routes
                    {nodeType === "LOGIC_EXPRESSION" && (
                      <span className="text-destructive ml-1">*</span>
                    )}
                  </span>
                  {routes && routes.length > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {routes.length}
                    </Badge>
                  )}
                </div>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="py-3 space-y-3">
                  <RouteEditor
                    routes={routes}
                    availableNodes={safeAvailableNodes}
                    onChange={handleRoutesChange}
                    errors={errors}
                    nodeType={nodeType}
                    nodeConfig={config}
                    availableVariables={safeAvailableVariables}
                  />
                </div>
              </CollapsibleContent>
            </Collapsible>
          </>
        )}

        {/* Validation Errors - moved to bottom */}
        {hasErrors && (
          <>
            <Separator />
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>
                {errors.length} {errors.length === 1 ? "error" : "errors"}
              </AlertTitle>
              <AlertDescription>
                <ul className="list-disc list-inside space-y-1 mt-2">
                  {errors.map((error, idx) => (
                    <li key={idx} className="text-sm">
                      {error.message}
                    </li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          </>
        )}
      </div>

      {/* Footer removed - Save is now handled globally via unified Save Flow button */}
    </div>
  );
});
