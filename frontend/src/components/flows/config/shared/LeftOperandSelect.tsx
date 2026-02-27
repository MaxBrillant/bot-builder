import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectSeparator,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { LeftOperand, ExpressionContext } from "@/lib/expressionBuilderTypes";
import type { VariableInfo } from "@/lib/types";
import { CONTEXT_CONFIGS } from "@/lib/expressionBuilderTypes";

interface LeftOperandSelectProps {
  value: LeftOperand;
  onChange: (value: LeftOperand) => void;
  context: ExpressionContext;
  availableVariables?: VariableInfo[];
  error?: string;
}

export function LeftOperandSelect({
  value,
  onChange,
  context,
  availableVariables = [],
  error,
}: LeftOperandSelectProps) {
  const config = CONTEXT_CONFIGS[context];

  // Build all selectable options
  const allOptions: { value: string; label: string }[] = [];

  // Add predefined options (skip separators and placeholders)
  for (const opt of config.leftOptions) {
    if (opt.type === "separator" || opt.type === "custom" || opt.value.startsWith("__")) {
      continue;
    }
    allOptions.push({ value: opt.value, label: opt.label });
  }

  // Add variables and their .length variants (not for success_expression - flow variables don't resolve in that context)
  if (context !== "success_expression") {
    for (const variable of availableVariables) {
      allOptions.push({ value: variable.name, label: variable.name });
      // Only show "Size of list" option for ARRAY type variables
      if (variable.type === "ARRAY") {
        allOptions.push({ value: `${variable.name}.length`, label: `Size of list '${variable.name}'` });
      }
    }
  }

  // Check if current value is in options
  const isKnownOption = allOptions.some((opt) => opt.value === value.path);

  // Show custom input when value isn't a known option (user entered custom path)
  const showCustomInput = !isKnownOption && value.path !== "";

  // Get context-appropriate placeholder for custom input
  const getCustomPlaceholder = () => {
    switch (context) {
      case "success_expression":
        return "response.body.field";
      case "validation_expression":
        return "e.g. input.length";
      case "route_logic":
        return "e.g. items.length, user.name";
      default:
        return "Enter path...";
    }
  };

  // Get default value when custom is selected
  // Note: Must be non-empty to trigger showCustomInput mode
  const getCustomDefault = () => {
    switch (context) {
      case "success_expression":
        return "response.body.";
      case "validation_expression":
        return "input.";
      case "route_logic":
        return "variable.path";
      default:
        return "variable.path";
    }
  };

  const handleSelectChange = (selectedValue: string) => {
    // Custom field selected - set default path to trigger input mode
    if (selectedValue === "__custom__") {
      const defaultPath = getCustomDefault();
      const type: LeftOperand["type"] =
        defaultPath.startsWith("input.") || defaultPath.startsWith("response.")
          ? "property"
          : "variable";
      onChange({ type, path: defaultPath });
      return;
    }

    // Determine type
    let type: LeftOperand["type"] = "variable";
    if (selectedValue.endsWith("()")) {
      type = "method";
    } else if (selectedValue.startsWith("input.") || selectedValue.startsWith("response.")) {
      type = "property";
    }

    onChange({ type, path: selectedValue });
  };

  const handleCustomInputChange = (path: string) => {
    // Determine type based on prefix - if starts with input./response., it's a property
    // Otherwise treat as variable so serializer adds context. prefix
    const type: LeftOperand["type"] =
      path.startsWith("input.") || path.startsWith("response.")
        ? "property"
        : "variable";
    onChange({ type, path });
  };

  // Custom input mode for custom paths
  if (showCustomInput) {
    return (
      <div>
        <Input
          value={value.path}
          onChange={(e) => handleCustomInputChange(e.target.value)}
          placeholder={getCustomPlaceholder()}
          className={cn(
            "text-sm font-mono",
            error && "border-destructive"
          )}
        />
        {error && <p className="text-sm text-destructive mt-1">{error}</p>}
      </div>
    );
  }

  return (
    <div>
      <Select value={value.path || ""} onValueChange={handleSelectChange}>
        <SelectTrigger className={cn(
          "text-sm",
          error && "border-destructive"
        )}>
          <SelectValue placeholder="Select..." />
        </SelectTrigger>
        <SelectContent className="max-h-60">
          {/* Predefined options */}
          {config.leftOptions.map((option, index) => {
            if (option.type === "separator") {
              return <SelectSeparator key={`sep-${index}`} />;
            }
            if (option.value === "__variables__" || option.value === "__custom__") {
              return null; // Added separately below
            }
            return (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            );
          })}

          {/* Variables and their .length variants (not for success_expression) */}
          {context !== "success_expression" && availableVariables.length > 0 && (
            <>
              <SelectSeparator />
              {availableVariables.flatMap((variable) => [
                <SelectItem key={`var-${variable.name}`} value={variable.name}>
                  {variable.name}
                </SelectItem>,
                // Only show "Size of list" option for ARRAY type variables
                ...(variable.type === "ARRAY" ? [
                  <SelectItem key={`var-${variable.name}-length`} value={`${variable.name}.length`}>
                    Size of list '{variable.name}'
                  </SelectItem>,
                ] : []),
              ])}
            </>
          )}

          {/* Custom field option - always at bottom */}
          {config.leftOptions.some((opt) => opt.value === "__custom__") && (
            <>
              <SelectSeparator />
              <SelectItem key="__custom__" value="__custom__">
                Custom field...
              </SelectItem>
            </>
          )}
        </SelectContent>
      </Select>
      {error && <p className="text-sm text-destructive mt-1">{error}</p>}
    </div>
  );
}
