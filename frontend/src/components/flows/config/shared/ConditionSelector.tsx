import { useState, useEffect } from "react";
import type { NodeType, NodeConfig } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";
import {
  getConditionInputType,
  getRouteConditionOptions,
  type RouteConditionOption,
} from "@/lib/routeConditionUtils";
import { ExpressionInput, type ExpressionContext } from "./ExpressionInput";
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
  availableVariables?: string[];
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
  // Map node type to expression context for better autocomplete
  const getExpressionContext = (): ExpressionContext => {
    switch (nodeType) {
      case "API_ACTION":
        return "route_api_action";
      case "MENU":
        return "route_menu";
      case "LOGIC_EXPRESSION":
        return "route_logic";
      case "PROMPT":
        return "route_prompt";
      default:
        return "route_logic";
    }
  };

  return (
    <ExpressionInput
      value={value}
      onChange={onChange}
      placeholder={
        placeholder || "Enter boolean expression (e.g., context.age > 18)"
      }
      maxLength={SystemConstraints.MAX_ROUTE_CONDITION_LENGTH}
      error={error}
      context={getExpressionContext()}
      availableVariables={availableVariables}
      onKeyDown={onKeyDown}
    />
  );
}
