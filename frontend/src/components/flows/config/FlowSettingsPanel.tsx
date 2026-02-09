import { useState, useEffect, useRef } from "react";
import isEqual from "fast-deep-equal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronRight, Plus, X } from "lucide-react";
import { VariablesEditor } from "./shared/VariablesEditor";
import { RetryLogicEditor } from "./shared/RetryLogicEditor";
import { FieldHelp } from "./shared/FieldHelp";
import { isValidTriggerKeyword } from "@/lib/validators/commonValidators";
import type { Flow } from "@/lib/types";
import { cn } from "@/lib/utils";

interface FlowSettingsPanelProps {
  flow: Flow;
  onChange?: (data: {
    name: string;
    triggerKeywords: string[];
    variables: Record<string, { type: string; default: any }>;
    defaults: any;
    isValid: boolean;
  }) => void;
  onClose?: () => void;
  existingFlowNames?: string[];
  existingTriggerKeywords?: Map<string, string>;
  nodes?: Array<{ id: string; name: string }>;
  botId: string;
  syncKey?: number; // Increments on undo/redo to signal re-sync from props
}

interface FlowVariable {
  name: string;
  type: string;
  default: any;
  defaultError?: string | null;
}

export function FlowSettingsPanel({
  flow,
  onChange,
  existingFlowNames = [],
  existingTriggerKeywords = new Map(),
  nodes = [],
  syncKey,
}: FlowSettingsPanelProps) {

  // Collapsible state
  const [isVariablesOpen, setIsVariablesOpen] = useState(false);
  const [isRetryLogicOpen, setIsRetryLogicOpen] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [triggerKeywords, setTriggerKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [variables, setVariables] = useState<FlowVariable[]>([]);
  const [maxAttempts, setMaxAttempts] = useState<number>(3);
  const [counterText, setCounterText] = useState<string>(
    "(Attempt {{current_attempt}} of {{max_attempts}})"
  );
  const [failRoute, setFailRoute] = useState("");

  // Validation state
  const [nameError, setNameError] = useState<string | null>(null);
  const [keywordError, setKeywordError] = useState<string | null>(null);
  const [triggerKeywordsError, setTriggerKeywordsError] = useState<string | null>(null);

  // Track initial values
  const [initialValues, setInitialValues] = useState<any>(null);
  const lastFlowIdRef = useRef<string | undefined>(undefined);

  // Track if we've made any edits to prevent unwanted notifications on mount
  const hasLocalEditsRef = useRef(false);

  // Track the last values we sent via onChange to prevent loops
  const lastSentValuesRef = useRef<{
    name: string;
    triggerKeywords: string[];
    variables: any[];
    maxAttempts: number;
    counterText: string;
    failRoute: string;
  } | null>(null);

  // Initialize form when flow changes
  useEffect(() => {
    if (flow && flow.flow_id !== lastFlowIdRef.current) {
      lastFlowIdRef.current = flow.flow_id;

      const flowName = flow.name || "";
      const flowKeywords = flow.trigger_keywords || [];
      const flowVariables = Object.entries(flow.variables || {}).map(
        ([name, config]) => ({
          name,
          type: config.type || "STRING",
          default: config.default ?? "",
        })
      );
      const flowMaxAttempts = flow.defaults?.retry_logic?.max_attempts ?? 3;
      const flowCounterText =
        flow.defaults?.retry_logic?.counter_text ??
        "(Attempt {{current_attempt}} of {{max_attempts}})";

      const endNode = flow.nodes
        ? Object.values(flow.nodes).find((node) => node.type === "END")
        : null;
      const flowFailRoute =
        flow.defaults?.retry_logic?.fail_route ||
        (endNode ? endNode.id : nodes.length > 0 ? nodes[0].id : "");

      setName(flowName);
      setTriggerKeywords(flowKeywords);
      setVariables(flowVariables);
      setMaxAttempts(flowMaxAttempts);
      setCounterText(flowCounterText);
      setFailRoute(flowFailRoute);
      setKeywordInput("");
      setNameError(null);
      setKeywordError(null);
      setTriggerKeywordsError(null);

      setInitialValues({
        name: flowName,
        triggerKeywords: flowKeywords,
        variables: flowVariables,
        maxAttempts: flowMaxAttempts,
        counterText: flowCounterText,
        failRoute: flowFailRoute,
      });

      // Reset tracking refs when flow changes
      hasLocalEditsRef.current = false;
      lastSentValuesRef.current = null;
    }
  }, [flow, nodes]);

  // Reset local state when syncKey changes (undo/redo happened)
  useEffect(() => {
    if (syncKey === undefined || syncKey === 0) return;

    // Force re-initialization from flow props
    if (flow) {
      const flowName = flow.name || "";
      const flowKeywords = flow.trigger_keywords || [];
      const flowVariables = Object.entries(flow.variables || {}).map(
        ([name, config]) => ({
          name,
          type: config.type || "STRING",
          default: config.default ?? "",
        })
      );
      const flowMaxAttempts = flow.defaults?.retry_logic?.max_attempts ?? 3;
      const flowCounterText =
        flow.defaults?.retry_logic?.counter_text ??
        "(Attempt {{current_attempt}} of {{max_attempts}})";

      const endNode = flow.nodes
        ? Object.values(flow.nodes).find((node) => node.type === "END")
        : null;
      const flowFailRoute =
        flow.defaults?.retry_logic?.fail_route ||
        (endNode ? endNode.id : nodes.length > 0 ? nodes[0].id : "");

      setName(flowName);
      setTriggerKeywords(flowKeywords);
      setVariables(flowVariables);
      setMaxAttempts(flowMaxAttempts);
      setCounterText(flowCounterText);
      setFailRoute(flowFailRoute);
      setKeywordInput("");
      setNameError(null);
      setKeywordError(null);
      setTriggerKeywordsError(null);

      // Reset tracking refs
      hasLocalEditsRef.current = false;
      lastSentValuesRef.current = null;
    }
  }, [syncKey]); // Only depend on syncKey, not flow (to avoid conflicts)

  // Keep collapsibles closed by default - users can open them when needed

  // Note: Dirty state tracking removed - using unified onChange approach

  // Note: Keyboard shortcuts removed - save is now handled globally via FlowEditorPage

  // Validate name
  const validateName = (value: string): string | null => {
    if (!value.trim()) return "Flow name is required";
    if (value.length < 1 || value.length > 96) {
      return "Flow name must be between 1 and 96 characters";
    }
    if (flow && value.trim() !== flow.name && existingFlowNames.includes(value.trim())) {
      return "A flow with this name already exists";
    }
    return null;
  };

  // Handle name change
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    hasLocalEditsRef.current = true;
    const value = e.target.value;
    setName(value);
    setNameError(validateName(value));
  };

  // Add keyword
  const handleAddKeyword = () => {
    const keyword = keywordInput.trim();
    if (!keyword) {
      setKeywordError("Keyword cannot be empty");
      return;
    }
    hasLocalEditsRef.current = true;

    const isWildcard = keyword === "*";
    if (!isWildcard && !isValidTriggerKeyword(keyword)) {
      setKeywordError(
        "Keyword can only contain letters, numbers, spaces, underscores, and hyphens"
      );
      return;
    }

    if (triggerKeywords.some((k) => k.toLowerCase() === keyword.toLowerCase())) {
      setKeywordError("Keyword already exists in this flow");
      return;
    }

    const keywordUpper = keyword.toUpperCase();
    if (existingTriggerKeywords.has(keywordUpper)) {
      const flowName = existingTriggerKeywords.get(keywordUpper);
      setKeywordError(`Keyword already used by flow "${flowName}"`);
      return;
    }

    if (isWildcard) {
      setTriggerKeywords(["*"]);
    } else {
      if (triggerKeywords.includes("*")) {
        setTriggerKeywords([keyword]);
      } else {
        setTriggerKeywords([...triggerKeywords, keyword]);
      }
    }

    setKeywordInput("");
    setKeywordError(null);
    setTriggerKeywordsError(null);
  };

  // Remove keyword
  const handleRemoveKeyword = (keyword: string) => {
    hasLocalEditsRef.current = true;
    const newKeywords = triggerKeywords.filter((k) => k !== keyword);
    setTriggerKeywords(newKeywords);
    if (newKeywords.length === 0) {
      setTriggerKeywordsError("At least one trigger keyword is required");
    }
  };

  // Handle keyword input key press
  const handleKeywordKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddKeyword();
    }
  };

  // Wrapped handlers for child components (to track edits)
  const handleVariablesChange = (newVariables: FlowVariable[]) => {
    hasLocalEditsRef.current = true;
    setVariables(newVariables);
  };

  const handleMaxAttemptsChange = (value: number) => {
    hasLocalEditsRef.current = true;
    setMaxAttempts(value);
  };

  const handleCounterTextChange = (value: string) => {
    hasLocalEditsRef.current = true;
    setCounterText(value);
  };

  const handleFailRouteChange = (value: string) => {
    hasLocalEditsRef.current = true;
    setFailRoute(value);
  };

  // Check if retry logic is configured (non-default)
  const isRetryLogicConfigured = (): boolean => {
    return (
      maxAttempts !== 3 ||
      counterText !== "(Attempt {{current_attempt}} of {{max_attempts}})" ||
      (failRoute !== "" && failRoute !== undefined)
    );
  };


  // Store onChange in a ref to avoid infinite loops
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  // Validate and notify parent of changes whenever state changes
  useEffect(() => {
    if (!initialValues) return;
    if (!hasLocalEditsRef.current) return; // Skip notification on initial mount

    // Check if current values match what we last sent (prevent loop)
    const currentValues = {
      name: name.trim(),
      triggerKeywords,
      variables,
      maxAttempts,
      counterText,
      failRoute,
    };

    if (lastSentValuesRef.current && isEqual(currentValues, lastSentValuesRef.current)) {
      return; // Already sent these exact values
    }

    const variablesObj = variables.reduce((acc, variable) => {
      if (variable.name.trim()) {
        acc[variable.name.trim()] = {
          type: variable.type,
          default: processDefaultValue(variable.type, variable.default),
        };
      }
      return acc;
    }, {} as Record<string, { type: string; default: any }>);

    const defaultsObj = {
      retry_logic: {
        max_attempts: maxAttempts,
        counter_text: counterText,
        fail_route: failRoute,
      },
    };

    // Check if valid
    const valid =
      !nameError &&
      name.trim() !== "" &&
      triggerKeywords.length > 0 &&
      variables.every(v => v.name.trim() && !v.defaultError) &&
      maxAttempts >= 1 &&
      maxAttempts <= 10 &&
      failRoute &&
      failRoute.trim() !== "";

    // Store current values as last sent
    lastSentValuesRef.current = currentValues;

    // Notify parent of changes
    if (onChangeRef.current) {
      onChangeRef.current({
        name: name.trim(),
        triggerKeywords,
        variables: variablesObj,
        defaults: defaultsObj,
        isValid: valid as boolean,
      });
    }
  }, [name, nameError, triggerKeywords, variables, maxAttempts, counterText, failRoute, initialValues]);

  // Process default value for submission (convert empty strings to null)
  const processDefaultValue = (varType: string, value: any): any => {
    // Empty string or "null" becomes null
    if (typeof value === 'string' && (value.trim() === "" || value.toLowerCase() === "null")) {
      return null;
    }

    // Normalize type to uppercase for comparison
    const normalizedType = varType.toUpperCase();

    // For string type, return as-is
    if (normalizedType === "STRING") {
      return value;
    }

    // For number type, ensure it's a number
    if (normalizedType === "NUMBER") {
      if (typeof value === 'number') return value;
      if (typeof value === 'string') return parseFloat(value.trim());
      return value;
    }

    // For boolean type, ensure it's boolean
    if (normalizedType === "BOOLEAN") {
      if (typeof value === 'boolean') return value;
      if (typeof value === 'string') return value.toLowerCase().trim() === "true";
      return value;
    }

    // For array type, ensure it's parsed
    if (normalizedType === "ARRAY") {
      if (Array.isArray(value)) return value;
      if (typeof value === 'string') {
        try {
          return JSON.parse(value);
        } catch {
          return value;
        }
      }
      return value;
    }

    return value;
  };

  // Note: Save is now handled globally via FlowEditorPage

  // Error dictionary for child components
  const errorDict: Record<string, string> = {};

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto p-3">
        {/* Header */}
        <span className="text-sm font-semibold text-foreground block mb-3">
          Flow Configuration
        </span>

        <Separator />

        {/* Flow Name & Trigger Keywords */}
        <div className="py-3 space-y-7">
          {/* Flow Name */}
          <div className="space-y-2">
            <Label htmlFor="flow-name" className="text-xs">
              Flow Name
            </Label>
            <Input
              id="flow-name"
              value={name}
              onChange={handleNameChange}
              placeholder="Enter flow name"
              maxLength={96}
              className={cn(
                nameError && "border-destructive focus-visible:ring-destructive"
              )}
            />
            {nameError && <p className="text-sm text-destructive">{nameError}</p>}
          </div>

          {/* Trigger Keywords */}
          <div className="space-y-3">
          {/* Section Title */}
          <Label className="text-xs">
            Trigger Keywords
          </Label>
          {/* Trigger Keywords Input */}
          <div className="space-y-2">
            <div className="flex gap-2">
              <Input
                value={keywordInput}
                onChange={(e) => {
                  setKeywordInput(e.target.value);
                  setKeywordError(null);
                }}
                onKeyDown={handleKeywordKeyDown}
                placeholder="Enter keyword (e.g., START, HELP)"
                className={cn(
                  keywordError && "border-destructive focus-visible:ring-destructive"
                )}
              />
              <Button
                type="button"
                onClick={handleAddKeyword}
                size="sm"
                className="shrink-0"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add
              </Button>
            </div>
            {keywordError && (
              <p className="text-sm text-destructive">{keywordError}</p>
            )}
            {triggerKeywordsError && (
              <p className="text-sm text-destructive">{triggerKeywordsError}</p>
            )}
          </div>

          {/* Keywords Display */}
          <div className="space-y-1">
            {triggerKeywords.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {triggerKeywords.map((keyword) => (
                  <Badge
                    key={keyword}
                    variant="secondary"
                    className="flex items-center gap-1 pl-2 pr-1"
                  >
                    {keyword === "*" ? "* (accepts any message)" : keyword}
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveKeyword(keyword)}
                      className="ml-1 h-5 w-5 hover:bg-muted"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-sm text-destructive">
                No keywords added. At least one trigger keyword is required.
              </p>
            )}
            <FieldHelp
              text="Words that start this flow when a user sends them"
              tooltip={
                <>
                  <p className="mb-2">
                    When a user sends a message matching any of these keywords, this flow will start. Matching ignores capitalization (START = start = Start).
                  </p>
                  <p className="text-xs font-medium mt-2">Examples:</p>
                  <p className="mt-1 text-xs">
                    <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                      START
                    </code>
                    ,{" "}
                    <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                      HELP
                    </code>
                    ,{" "}
                    <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                      SUPPORT
                    </code>
                  </p>
                  <p className="text-xs font-medium mt-2">Catch-all option:</p>
                  <p className="mt-1 text-xs">
                    Use{" "}
                    <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                      *
                    </code>{" "}
                    to start this flow for any message. Note: this should be the only keyword when used.
                  </p>
                </>
              }
            />
          </div>
          </div>
        </div>
        {/* End Trigger Keywords */}

        <Separator />

        {/* VARIABLES - Collapsible */}
        <Collapsible open={isVariablesOpen} onOpenChange={setIsVariablesOpen}>
          <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
            <div className="flex items-center gap-2">
              <ChevronRight
                className={cn(
                  "h-4 w-4 text-muted-foreground transition-transform duration-200",
                  isVariablesOpen && "rotate-90"
                )}
              />
              <span className="text-sm font-semibold text-foreground">Variables</span>
              {variables.length > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {variables.length}
                </Badge>
              )}
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="py-3 space-y-3">
              <VariablesEditor
                value={variables}
                onChange={handleVariablesChange}
                errors={errorDict}
              />
            </div>
          </CollapsibleContent>
        </Collapsible>

        <Separator />

        {/* RETRY LOGIC - Collapsible */}
        <Collapsible open={isRetryLogicOpen} onOpenChange={setIsRetryLogicOpen}>
          <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
            <div className="flex items-center gap-2">
              <ChevronRight
                className={cn(
                  "h-4 w-4 text-muted-foreground transition-transform duration-200",
                  isRetryLogicOpen && "rotate-90"
                )}
              />
              <span className="text-sm font-semibold text-foreground">
                Retry Logic
              </span>
              {isRetryLogicConfigured() && (
                <Badge variant="secondary" className="text-xs">
                  ✓
                </Badge>
              )}
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="py-3 space-y-7">
              <RetryLogicEditor
                maxAttempts={maxAttempts}
                counterText={counterText}
                failRoute={failRoute}
                onMaxAttemptsChange={handleMaxAttemptsChange}
                onCounterTextChange={handleCounterTextChange}
                onFailRouteChange={handleFailRouteChange}
                nodes={nodes}
                availableVariables={[]}
                errors={errorDict}
              />
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>

      {/* Footer removed - Save is now handled globally via unified Save Flow button */}
    </div>
  );
}
