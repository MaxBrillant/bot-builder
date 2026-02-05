import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ChevronRight } from "lucide-react";
import { TemplateInput } from "../shared/TemplateInput";
import { ValidationRuleEditor } from "../shared/ValidationRuleEditor";
import { InterruptsGrid } from "../shared/InterruptsGrid";
import { CharacterCounter } from "../shared/CharacterCounter";
import { FieldError } from "../shared/FieldError";
import { FieldHelp } from "../shared/FieldHelp";
import { VariableSelect } from "../shared/VariableSelect";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PromptNodeConfig, ValidationError } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";
import { cn } from "@/lib/utils";

interface PromptConfigFormProps {
  config: PromptNodeConfig;
  onChange: (config: PromptNodeConfig) => void;
  errors: ValidationError[];
  availableVariables?: string[];
  availableNodes?: Array<{ id: string; name: string }>;
  variables?: Array<{ name: string; type: string }>;
  onCreateVariable: (variable: {
    name: string;
    type: string;
    default: any;
  }) => Promise<void>;
  nodeName?: string;
  onNodeNameChange?: (name: string) => void;
  nodeNameError?: string;
  nodeNameInputRef?: React.RefObject<HTMLInputElement>;
}

export function PromptConfigForm({
  config,
  onChange,
  errors,
  availableVariables,
  availableNodes,
  variables = [],
  onCreateVariable,
  nodeName,
  onNodeNameChange,
  nodeNameError,
  nodeNameInputRef,
}: PromptConfigFormProps) {
  // Safely handle undefined/null arrays
  const safeAvailableVariables = availableVariables ?? [];
  const safeAvailableNodes = availableNodes ?? [];

  // Determine validation type based on config
  const getInitialValidationType = (): "none" | "regex" | "expression" => {
    if (!config.validation) return "none";
    return config.validation.type === "REGEX" ? "regex" : "expression";
  };

  const [validationType, setValidationType] = useState<
    "none" | "regex" | "expression"
  >(getInitialValidationType());

  // State for collapsible open/closed status
  const [isValidationOpen, setIsValidationOpen] = useState(false);
  const [isInterruptsOpen, setIsInterruptsOpen] = useState(false);

  // Update validation type when config changes
  useEffect(() => {
    setValidationType(getInitialValidationType());
  }, [config.validation]);

  // Auto-open collapsibles when they have data
  useEffect(() => {
    // Auto-open validation when validation type is not "none"
    if (validationType !== "none") {
      setIsValidationOpen(true);
    }
    // Auto-open interrupts when there are interrupts configured
    if (config.interrupts && config.interrupts.length > 0) {
      setIsInterruptsOpen(true);
    }
  }, [validationType, config.interrupts]);

  const getFieldError = (field: string) => {
    return errors.find((e) => e.field === field)?.message;
  };

  const getFieldErrors = (prefix: string): Record<string, string> => {
    const fieldErrors: Record<string, string> = {};
    errors.forEach((error) => {
      if (error.field.startsWith(prefix)) {
        fieldErrors[error.field] = error.message;
      }
    });
    return fieldErrors;
  };

  const handleTextChange = (text: string) => {
    onChange({ ...config, type: "PROMPT", text });
  };

  const handleVariableChange = (save_to_variable: string) => {
    onChange({ ...config, type: "PROMPT", save_to_variable });
  };

  const handleValidationChange = (validation: typeof config.validation) => {
    onChange({ ...config, type: "PROMPT", validation });
  };

  const handleInterruptsChange = (interrupts: typeof config.interrupts) => {
    onChange({ ...config, type: "PROMPT", interrupts });
  };

  const handleValidationTypeChange = (
    type: "none" | "regex" | "expression"
  ) => {
    setValidationType(type);

    if (type === "none") {
      // Remove validation
      const newConfig = { ...config, type: "PROMPT" as const };
      delete newConfig.validation;
      onChange(newConfig);
    } else {
      // Add validation with defaults based on type
      onChange({
        ...config,
        type: "PROMPT",
        validation: {
          type: type === "regex" ? "REGEX" : "EXPRESSION",
          rule: "",
          error_message: "",
        },
      });
    }
  };

  return (
    <div>
      {/* Node Name */}
      {nodeName !== undefined && onNodeNameChange && (
        <div className="space-y-2 mb-4">
          <Input
            ref={nodeNameInputRef}
            value={nodeName}
            onChange={(e) => onNodeNameChange(e.target.value)}
            placeholder="Enter node name"
            maxLength={50}
            className={cn(
              nodeNameError && "border-destructive focus-visible:ring-destructive"
            )}
          />
          {nodeNameError && (
            <p className="text-sm text-destructive">{nodeNameError}</p>
          )}
        </div>
      )}

      {nodeName !== undefined && onNodeNameChange && <Separator />}

      {/* Question */}
      <div className={cn(nodeName !== undefined && "mt-4", "mb-4")}>
        {/* Section Title */}
        {nodeName !== undefined && onNodeNameChange && (
          <span className="text-sm font-semibold text-foreground block mb-3">
            Configuration
          </span>
        )}

        <div className="space-y-3">
          {/* Prompt Text */}
          <div className="space-y-1">
            <TemplateInput
              value={config.text ?? ""}
              onChange={handleTextChange}
              error={getFieldError("text")}
              maxLength={SystemConstraints.MAX_MESSAGE_LENGTH}
              placeholder="Enter the prompt question to ask the user"
              rows={4}
              availableVariables={safeAvailableVariables}
              nodeType="PROMPT"
            />
            <FieldHelp
              text="Use {{variable_name}} to insert variable values"
              tooltip={
                <>
                  <p className="mb-2">
                    Insert any flow variable into your question using double curly braces.
                  </p>
                  <p className="text-xs font-medium mt-2">Example:</p>
                  <p className="mt-1 text-xs">
                    Hi {"{{user_name}}"}, how many seats do you need?
                  </p>
                  <p className="text-xs font-medium mt-2">Note:</p>
                  <p className="mt-1 text-xs">
                    Array length ({"{{items.length}}"}) doesn't work in prompts. To show counts, save the count in a separate variable first.
                  </p>
                </>
              }
            />
          </div>

          {/* Save to Variable Field */}
          <div className="space-y-1">
            <Label htmlFor="save-to-variable" className="text-xs">
              Save to Variable
            </Label>
            <VariableSelect
              value={config.save_to_variable ?? ""}
              onValueChange={handleVariableChange}
              variables={variables}
              onCreateVariable={onCreateVariable}
              placeholder="Select or type variable name"
              className={cn(
                "font-mono",
                getFieldError("save_to_variable") && "border-destructive"
              )}
            />
            {getFieldError("save_to_variable") && (
              <p className="text-sm text-destructive">{getFieldError("save_to_variable")}</p>
            )}
            <FieldHelp
              text="Variable to store user's response"
              tooltip={
                <>
                  <p className="mb-2">
                    Choose where to save the user's answer. This makes it available for use in later nodes.
                  </p>
                  <p className="text-xs font-medium mt-2">Examples:</p>
                  <p className="mt-1 text-xs">
                    <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">user_name</code>,{" "}
                    <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">phone_number</code>,{" "}
                    <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">order_id</code>
                  </p>
                  <p className="mt-2 text-xs">Use lowercase letters, numbers, and underscores only.</p>
                </>
              }
            />
          </div>
        </div>
      </div>

      <Separator />

      {/* Validation Section - Collapsible */}
      <Collapsible
        open={isValidationOpen}
        onOpenChange={setIsValidationOpen}
      >
        <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-2">
            <ChevronRight
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                isValidationOpen && "rotate-90"
              )}
            />
            <span className="text-sm font-semibold text-foreground">Validation</span>
            {validationType !== "none" && (
              <Badge variant="secondary" className="text-xs">
                ✓
              </Badge>
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="py-3 space-y-7">
            {/* Validation Type Selector */}
            <div className="space-y-1">
              <Select
                value={validationType}
                onValueChange={handleValidationTypeChange}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select validation type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No validation</SelectItem>
                  <SelectItem value="regex">Regex Pattern</SelectItem>
                  <SelectItem value="expression">Expression</SelectItem>
                </SelectContent>
              </Select>
              <FieldHelp
                text="Choose how to validate user input"
                tooltip={
                  <>
                    <p className="mb-2"><strong>No validation:</strong> Accept any input</p>
                    <p className="mb-2"><strong>Regex Pattern:</strong> Match against patterns like phone numbers, emails, or specific formats</p>
                    <p className="mb-2"><strong>Expression:</strong> Logic-based validation using length checks, character type validation, or custom rules</p>
                  </>
                }
              />
            </div>

            {/* Show validation fields only when not "none" */}
            {validationType !== "none" && (
              <ValidationRuleEditor
                value={config.validation}
                onChange={handleValidationChange}
                errors={getFieldErrors("validation")}
                availableVariables={safeAvailableVariables}
              />
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>

      <Separator />

      {/* Escape Keys Section - Collapsible */}
      <Collapsible
        open={isInterruptsOpen}
        onOpenChange={setIsInterruptsOpen}
      >
        <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-2">
            <ChevronRight
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                isInterruptsOpen && "rotate-90"
              )}
            />
            <span className="text-sm font-semibold text-foreground">Escape Keys</span>
            {config.interrupts && config.interrupts.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {config.interrupts.length}
              </Badge>
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="py-3 space-y-3">
            {/* InterruptsGrid for managing escape keys */}
            <InterruptsGrid
              value={config.interrupts || []}
              onChange={handleInterruptsChange}
              availableNodes={safeAvailableNodes}
              errors={getFieldErrors("interrupts")}
            />
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
