import { useState, useEffect } from "react";
import type { NodeType, NodeConfig, VariableInfo } from "@/lib/types";
import {
  getConditionInputType,
  getRouteConditionOptions,
  type RouteConditionOption,
} from "@/lib/routeConditionUtils";
import { ExpressionBuilder } from "./ExpressionBuilder";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

interface ConditionSelectorProps {
  nodeType: NodeType;
  nodeConfig?: NodeConfig;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  placeholder?: string;
  disabled?: boolean;
  availableVariables?: VariableInfo[];
  onKeyDown?: (e: React.KeyboardEvent) => void;
}

export function ConditionSelector({
  nodeType,
  nodeConfig,
  value,
  onChange,
  error,
  placeholder = "Select condition",
  disabled = false,
  availableVariables = [],
  onKeyDown,
}: ConditionSelectorProps) {
  const inputType = getConditionInputType(nodeType);
  const [options, setOptions] = useState<RouteConditionOption[]>([]);

  // Update options when node type or config changes
  useEffect(() => {
    const newOptions = getRouteConditionOptions(nodeType, nodeConfig);
    setOptions(newOptions);
  }, [nodeType, nodeConfig]);

  // For dropdown-based node types
  if (inputType === "dropdown") {
    return (
      <div onKeyDown={onKeyDown}>
        <Select value={value} onValueChange={onChange} disabled={disabled}>
          <SelectTrigger
            className={cn(
              "text-sm",
              error && "border-destructive"
            )}
          >
            <SelectValue placeholder={placeholder} />
          </SelectTrigger>
          <SelectContent>
            {options.map((option) => (
              <SelectItem
                key={option.value}
                value={option.value}
                title={option.description}
              >
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {error && <p className="text-sm text-destructive mt-1">{error}</p>}
      </div>
    );
  }

  // For text input-based node types (LOGIC_EXPRESSION)
  const isFallback = value.trim().toLowerCase() === "true";

  // Store previous expression when switching to fallback
  const [previousExpression, setPreviousExpression] = useState("");

  const handleFallbackToggle = (checked: boolean) => {
    if (checked) {
      // Save current expression before switching to fallback
      if (!isFallback && value.trim()) {
        setPreviousExpression(value);
      }
      onChange("true");
    } else {
      // Restore previous expression
      onChange(previousExpression);
    }
  };

  const handleExpressionChange = (expression: string) => {
    // Don't allow setting to "true" via expression builder
    if (expression.trim().toLowerCase() === "true") {
      onChange("");
    } else {
      onChange(expression);
    }
  };

  return (
    <div className="space-y-3" onKeyDown={onKeyDown}>
      {/* Fallback toggle */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={isFallback}
          onChange={(e) => handleFallbackToggle(e.target.checked)}
          disabled={disabled}
          className="h-4 w-4 rounded border-input"
        />
        <span className="text-sm">Always match (fallback)</span>
      </label>

      {/* Expression builder - hidden when fallback is enabled */}
      {!isFallback && (
        <ExpressionBuilder
          value={value}
          onChange={handleExpressionChange}
          context="route_logic"
          availableVariables={availableVariables}
          error={error}
        />
      )}

      {/* Show error only when not using expression builder (it shows its own) */}
      {isFallback && error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
    </div>
  );
}
