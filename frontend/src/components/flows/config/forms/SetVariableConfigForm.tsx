import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronRight } from "lucide-react";
import { AssignmentsGrid } from "../shared/AssignmentsGrid";
import type {
  SetVariableNodeConfig,
  VariableAssignment,
  ValidationError,
  VariableInfo,
  VariableType,
} from "@/lib/types";
import { cn } from "@/lib/utils";

interface SetVariableConfigFormProps {
  config: SetVariableNodeConfig;
  onChange: (config: SetVariableNodeConfig) => void;
  errors: ValidationError[];
  availableVariables?: VariableInfo[];
  variables?: Array<{ name: string; type: VariableType }>;
  onCreateVariable: (variable: {
    name: string;
    type: VariableType;
    default: any;
  }) => Promise<void>;
  nodeName?: string;
  onNodeNameChange?: (name: string) => void;
  nodeNameError?: string;
  nodeNameInputRef?: React.RefObject<HTMLInputElement | null>;
}

export function SetVariableConfigForm({
  config,
  onChange,
  errors,
  availableVariables,
  variables = [],
  onCreateVariable,
  nodeName,
  onNodeNameChange,
  nodeNameError,
  nodeNameInputRef,
}: SetVariableConfigFormProps) {
  const [isAssignmentsOpen, setIsAssignmentsOpen] = useState(true);

  const errorDict: Record<string, string> = {};
  errors.forEach((error) => {
    errorDict[error.field] = error.message;
  });

  const handleAssignmentsChange = (assignments: VariableAssignment[]) => {
    onChange({ ...config, assignments });
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

      {/* Assignments Collapsible */}
      <Collapsible open={isAssignmentsOpen} onOpenChange={setIsAssignmentsOpen}>
        <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-2">
            <ChevronRight
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                isAssignmentsOpen && "rotate-90"
              )}
            />
            <span className="text-sm font-semibold text-foreground">
              Assignments
            </span>
            {config.assignments && config.assignments.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {config.assignments.length}
              </Badge>
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="py-3 space-y-3">
            {errorDict["assignments"] && (
              <p className="text-sm text-destructive">
                {errorDict["assignments"]}
              </p>
            )}
            <AssignmentsGrid
              value={config.assignments ?? []}
              onChange={handleAssignmentsChange}
              errors={errorDict}
              variables={variables}
              onCreateVariable={onCreateVariable}
              availableVariables={availableVariables}
            />
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
