import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, X } from "lucide-react";
import { FieldHelp } from "./FieldHelp";
import type { Interrupt } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";
import { cn } from "@/lib/utils";

interface InterruptsGridProps {
  value: Interrupt[];
  onChange: (value: Interrupt[]) => void;
  availableNodes: Array<{ id: string; name: string }>;
  errors: Record<string, string>;
}

export function InterruptsGrid({
  value,
  onChange,
  availableNodes,
  errors = {},
}: InterruptsGridProps) {
  const safeAvailableNodes = availableNodes ?? [];

  const handleAdd = () => {
    onChange([...value, { input: "", target_node: "" }]);
  };

  const handleRemove = (index: number) => {
    const newValue = value.filter((_, i) => i !== index);
    onChange(newValue);
  };

  const handleInputChange = (index: number, input: string) => {
    const newValue = [...value];
    newValue[index] = { ...newValue[index], input };
    onChange(newValue);
  };

  const handleTargetChange = (index: number, target_node: string) => {
    const newValue = [...value];
    newValue[index] = { ...newValue[index], target_node };
    onChange(newValue);
  };

  return (
    <div className="space-y-2">
      {/* Header Row */}
      {value.length > 0 && (
        <div className="grid grid-cols-[1fr_1fr_auto] gap-2 items-start px-1">
          <div className="text-xs font-medium text-muted-foreground">
            Keyword
          </div>
          <div className="text-xs font-medium text-muted-foreground">Node</div>
          <div className="w-9" />
        </div>
      )}

      {/* Interrupt Rows */}
      {value.map((interrupt, index) => {
        const inputError = errors[`interrupts[${index}].input`];
        const targetError = errors[`interrupts[${index}].target_node`];

        return (
          <div key={index} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-start">
            {/* Keyword Input */}
            <div className="min-w-0">
              <Input
                value={interrupt.input}
                onChange={(e) => handleInputChange(index, e.target.value)}
                placeholder="e.g., cancel, back, help"
                maxLength={SystemConstraints.MAX_INTERRUPT_KEYWORD_LENGTH}
                className={cn("text-sm", inputError && "border-destructive")}
              />
              {inputError && (
                <p className="text-sm text-destructive mt-1">{inputError}</p>
              )}
            </div>

            {/* Target Node Select */}
            <div className="min-w-0">
              <Select
                value={interrupt.target_node}
                onValueChange={(value) => handleTargetChange(index, value)}
              >
                <SelectTrigger
                  className={cn("text-sm", targetError && "border-destructive")}
                >
                  <SelectValue placeholder="Select node" />
                </SelectTrigger>
                <SelectContent>
                  {safeAvailableNodes.length === 0 ? (
                    <div className="px-2 py-2 text-sm text-muted-foreground">
                      No nodes available
                    </div>
                  ) : (
                    safeAvailableNodes
                      .sort((a, b) => a.name.localeCompare(b.name))
                      .map((node) => (
                        <SelectItem key={node.id} value={node.id}>
                          {node.name}
                        </SelectItem>
                      ))
                  )}
                </SelectContent>
              </Select>
              {targetError && (
                <p className="text-sm text-destructive mt-1">{targetError}</p>
              )}
            </div>

            {/* Delete Button */}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => handleRemove(index)}
              className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        );
      })}

      {/* Help Text */}
      <FieldHelp
        text="Keywords that jump to specific nodes, bypassing normal flow"
        tooltip={
          <>
            <p className="mb-2">
              When a user types these keywords, they'll immediately jump to the target node—skipping validation and normal routing. Matching is case-insensitive and works with phrases like "go back".
            </p>
            <p className="text-xs font-medium mt-2">Common uses:</p>
            <ul className="list-none space-y-1 mt-1 text-xs">
              <li>
                <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">cancel</code> - Exit to main menu
              </li>
              <li>
                <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">back</code> - Return to previous step
              </li>
              <li>
                <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">start over</code> - Restart conversation
              </li>
            </ul>
          </>
        }
      />

      {/* Add Button */}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleAdd}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Escape Key
      </Button>
    </div>
  );
}
