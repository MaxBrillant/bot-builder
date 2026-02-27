import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Info } from "lucide-react";
import type { LogicExpressionNodeConfig, ValidationError } from "@/lib/types";
import { cn } from "@/lib/utils";

interface LogicExpressionConfigFormProps {
  config: LogicExpressionNodeConfig;
  onChange: (config: LogicExpressionNodeConfig) => void;
  errors: ValidationError[];
  nodeName?: string;
  onNodeNameChange?: (name: string) => void;
  nodeNameError?: string;
  nodeNameInputRef?: React.RefObject<HTMLInputElement | null>;
}

export function LogicExpressionConfigForm({
  nodeName,
  onNodeNameChange,
  nodeNameError,
  nodeNameInputRef,
}: LogicExpressionConfigFormProps) {
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

      {/* Info Card */}
      <div className={cn(nodeName !== undefined && "mt-4", "mb-4 space-y-3")}>
        {/* Header */}
        <div className="flex items-start gap-2 text-muted-foreground">
          <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <p className="text-sm">
            Click the <span className="font-medium text-foreground">+</span> button to decide where users go next based on variable values.
          </p>
        </div>

        {/* Quick Guide */}
        <div className="rounded-lg border border-border bg-muted/30 p-5 space-y-6">

          {/* Building conditions */}
          <div className="text-xs space-y-3">
            <p className="font-medium text-muted-foreground">Building conditions</p>
            <div className="space-y-2 ml-2 text-muted-foreground">
              <p>1. Select a variable from the dropdown</p>
              <p>2. Choose a comparison (equals, more than, etc.)</p>
              <p>3. Enter the value to compare against</p>
            </div>
          </div>

          {/* Special values */}
          <div className="text-xs space-y-3">
            <p className="font-medium text-muted-foreground">Special values</p>
            <div className="space-y-2 ml-2 text-muted-foreground">
              <p><span className="text-foreground font-medium">true</span> / <span className="text-foreground font-medium">false</span> — for yes/no checks</p>
              <p><span className="text-foreground font-medium">null</span> — to check if a value doesn't exist</p>
            </div>
          </div>

          {/* Multiple conditions */}
          <div className="text-xs space-y-3">
            <p className="font-medium text-muted-foreground">Multiple conditions</p>
            <div className="space-y-2 ml-2 text-muted-foreground">
              <p>Click "Add Condition" to combine checks:</p>
              <p><span className="text-foreground font-medium">AND</span> — all conditions must be true</p>
              <p><span className="text-foreground font-medium">OR</span> — any condition can be true</p>
            </div>
          </div>

          {/* Tips */}
          <div className="text-xs space-y-3">
            <p className="font-medium text-muted-foreground">Tips</p>
            <div className="space-y-2 ml-2 text-muted-foreground">
              <p>• Use <span className="text-foreground font-medium">Always match</span> to catch everything else</p>
              <p>• For nested values, select <span className="text-foreground font-medium">Custom field</span> and type the path (e.g. user.name)</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
