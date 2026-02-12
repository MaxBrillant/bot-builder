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
import { CONTEXT_CONFIGS } from "@/lib/expressionBuilderTypes";

interface LeftOperandSelectProps {
  value: LeftOperand;
  onChange: (value: LeftOperand) => void;
  context: ExpressionContext;
  availableVariables?: string[];
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

  // Add variables (not for success_expression - flow variables don't resolve in that context)
  if (context !== "success_expression") {
    for (const varName of availableVariables) {
      allOptions.push({ value: varName, label: varName });
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
  const getCustomDefault = () => {
    switch (context) {
      case "success_expression":
        return "response.body.";
      case "validation_expression":
        return "input.";
      case "route_logic":
        return "context.";
      default:
        return "context.";
    }
  };

  const handleSelectChange = (selectedValue: string) => {
    // Custom field selected - set default path to trigger input mode
    if (selectedValue === "__custom__") {
      onChange({ type: "property", path: getCustomDefault() });
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
    onChange({ type: "property", path });
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

          {/* Variables (not for success_expression) */}
          {context !== "success_expression" && availableVariables.length > 0 && (
            <>
              <SelectSeparator />
              {availableVariables.map((varName) => (
                <SelectItem key={`var-${varName}`} value={varName}>
                  {varName}
                </SelectItem>
              ))}
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
