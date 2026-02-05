import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectSeparator,
} from "@/components/ui/select";
import { Plus } from "lucide-react";
import { CreateVariableDialog } from "./CreateVariableDialog";
import type { VariableType } from "@/lib/types";

interface VariableSelectProps {
  value: string;
  onValueChange: (value: string) => void;
  variables: Array<{ name: string; type: VariableType }>;
  onCreateVariable: (variable: {
    name: string;
    type: VariableType;
    default: any;
  }) => Promise<void>;
  placeholder?: string;
  typeFilter?: "string" | "number" | "boolean" | "array";
  className?: string;
  disabled?: boolean;
}

export function VariableSelect({
  value,
  onValueChange,
  variables,
  onCreateVariable,
  placeholder = "Select variable",
  typeFilter,
  className,
  disabled,
}: VariableSelectProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Filter variables by type if typeFilter is provided
  // Note: Backend returns uppercase types (STRING, NUMBER, etc), so we compare case-insensitively
  const filteredVariables = typeFilter
    ? variables.filter((v) => v.type.toLowerCase() === typeFilter.toLowerCase())
    : variables;

  // Handle value change from Select
  const handleValueChange = (newValue: string) => {
    if (newValue === "__create_new__") {
      // Open dialog instead of selecting this value
      setIsDialogOpen(true);
    } else {
      // Normal variable selection
      onValueChange(newValue);
    }
  };

  // Handle variable creation
  const handleCreateVariable = async (variable: {
    name: string;
    type: string;
    default: any;
  }) => {
    await onCreateVariable(variable as { name: string; type: VariableType; default: any });
    // Auto-select the newly created variable
    onValueChange(variable.name);
  };

  // Get existing variable names for validation
  const existingVariableNames = variables.map((v) => v.name);

  return (
    <>
      <Select
        value={value}
        onValueChange={handleValueChange}
        disabled={disabled}
      >
        <SelectTrigger className={className}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent className="max-h-60">
          {/* Existing variables */}
          {filteredVariables.length > 0 ? (
            filteredVariables.map((v) => (
              <SelectItem key={v.name} value={v.name}>
                {v.name}
              </SelectItem>
            ))
          ) : (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No variables available
            </div>
          )}

          {/* Separator + Create option */}
          <SelectSeparator />
          <SelectItem
            value="__create_new__"
            className="text-muted-foreground focus:text-muted-foreground"
          >
            <Plus className="inline mr-2 h-4 w-4" />
            Create New Variable
          </SelectItem>
        </SelectContent>
      </Select>

      {/* Internal dialog */}
      <CreateVariableDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        onCreateVariable={handleCreateVariable}
        existingVariableNames={existingVariableNames}
        defaultType={typeFilter}
      />
    </>
  );
}
