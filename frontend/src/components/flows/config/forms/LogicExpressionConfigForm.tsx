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
  nodeNameInputRef?: React.RefObject<HTMLInputElement>;
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
            Click the <span className="font-medium text-foreground">+</span> button to add conditional routes.
          </p>
        </div>

        {/* Expression Reference */}
        <div className="rounded-lg border border-border bg-muted/30 p-5 space-y-8">
          <p className="text-xs font-medium text-foreground">Expression Reference</p>

          {/* Operators */}
          <div className="text-xs space-y-3">
            <p className="font-medium text-muted-foreground">Operators</p>
            <div className="space-y-2 ml-2">
              <div className="flex justify-between">
                <code className="text-foreground">==</code>
                <span className="text-muted-foreground">is equal to</span>
              </div>
              <div className="flex justify-between">
                <code className="text-foreground">!=</code>
                <span className="text-muted-foreground">is not equal to</span>
              </div>
              <div className="flex justify-between">
                <code className="text-foreground">&gt;</code>
                <span className="text-muted-foreground">is greater than</span>
              </div>
              <div className="flex justify-between">
                <code className="text-foreground">&gt;=</code>
                <span className="text-muted-foreground">is greater than or equal to</span>
              </div>
              <div className="flex justify-between">
                <code className="text-foreground">&lt;</code>
                <span className="text-muted-foreground">is less than</span>
              </div>
              <div className="flex justify-between">
                <code className="text-foreground">&lt;=</code>
                <span className="text-muted-foreground">is less than or equal to</span>
              </div>
              <div className="flex justify-between">
                <code className="text-foreground">&&</code>
                <span className="text-muted-foreground">and (both must be true)</span>
              </div>
              <div className="flex justify-between">
                <code className="text-foreground">||</code>
                <span className="text-muted-foreground">or (either can be true)</span>
              </div>
            </div>
          </div>

          {/* Keywords */}
          <div className="text-xs space-y-3">
            <p className="font-medium text-muted-foreground">Keywords</p>
            <div className="space-y-2 ml-2">
              <div className="flex justify-between">
                <code className="text-foreground">true</code>
                <span className="text-muted-foreground">always matches (default route)</span>
              </div>
              <div className="flex justify-between">
                <code className="text-foreground">false</code>
                <span className="text-muted-foreground">never matches</span>
              </div>
              <div className="flex justify-between">
                <code className="text-foreground">success</code>
                <span className="text-muted-foreground">previous API call succeeded</span>
              </div>
              <div className="flex justify-between">
                <code className="text-foreground">error</code>
                <span className="text-muted-foreground">previous API call failed</span>
              </div>
              <div className="flex justify-between">
                <code className="text-foreground">null</code>
                <span className="text-muted-foreground">value does not exist</span>
              </div>
            </div>
          </div>

          {/* Variables */}
          <div className="text-xs space-y-3">
            <p className="font-medium text-muted-foreground">Variables</p>
            <p className="text-muted-foreground ml-2">
              Use <code className="text-foreground bg-muted px-1.5 py-0.5 rounded">context.</code> to access your flow variables.
              For example, if you have a variable called "age", use <code className="text-foreground bg-muted px-1.5 py-0.5 rounded">context.age</code>
            </p>
          </div>

          {/* Examples */}
          <div className="text-xs space-y-3">
            <p className="font-medium text-muted-foreground">Examples</p>
            <div className="space-y-4 ml-2">
              <div>
                <code className="text-foreground bg-muted px-1.5 py-0.5 rounded">context.age &gt; 18</code>
                <p className="text-muted-foreground mt-1">User is older than 18</p>
              </div>
              <div>
                <code className="text-foreground bg-muted px-1.5 py-0.5 rounded">context.status == "active"</code>
                <p className="text-muted-foreground mt-1">Status is exactly "active"</p>
              </div>
              <div>
                <code className="text-foreground bg-muted px-1.5 py-0.5 rounded">context.items.length &gt; 0</code>
                <p className="text-muted-foreground mt-1">Items list is not empty</p>
              </div>
              <div>
                <code className="text-foreground bg-muted px-1.5 py-0.5 rounded">context.verified && context.premium</code>
                <p className="text-muted-foreground mt-1">User is both verified and premium</p>
              </div>
              <div>
                <code className="text-foreground bg-muted px-1.5 py-0.5 rounded">context.role == "admin" || context.role == "mod"</code>
                <p className="text-muted-foreground mt-1">User is either admin or moderator</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
