import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { TemplateInput } from "../shared/TemplateInput";
import { FieldHelp } from "../shared/FieldHelp";
import type { TextNodeConfig, ValidationError, VariableInfo } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";
import { cn } from "@/lib/utils";

interface TextConfigFormProps {
  config: TextNodeConfig;
  onChange: (config: TextNodeConfig) => void;
  errors: ValidationError[];
  availableVariables?: VariableInfo[];
  nodeName?: string;
  onNodeNameChange?: (name: string) => void;
  nodeNameError?: string;
  nodeNameInputRef?: React.RefObject<HTMLInputElement | null>;
}

export function TextConfigForm({
  config,
  onChange,
  errors,
  availableVariables,
  nodeName,
  onNodeNameChange,
  nodeNameError,
  nodeNameInputRef,
}: TextConfigFormProps) {
  const safeAvailableVariables = availableVariables ?? [];

  const getFieldError = (field: string) => {
    return errors.find((e) => e.field === field)?.message;
  };

  const handleTextChange = (text: string) => {
    onChange({ ...config, type: "TEXT", text });
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

      {/* Content */}
      <div className={cn(nodeName !== undefined && "mt-4", "mb-4")}>
        {/* Section Title */}
        {nodeName !== undefined && onNodeNameChange && (
          <span className="text-sm font-semibold text-foreground block mb-3">
            Configuration
          </span>
        )}

        <div className="space-y-3">
          {/* Text Message */}
          <div className="space-y-1">
            <TemplateInput
              value={config.text ?? ""}
              onChange={handleTextChange}
              error={getFieldError("text")}
              maxLength={SystemConstraints.MAX_MESSAGE_LENGTH}
              placeholder="Enter text message"
              rows={8}
              maxRows={20}
              availableVariables={safeAvailableVariables}
              nodeType="TEXT"
            />
            <FieldHelp
              text="Use {{variable_name}} to insert variable values"
              tooltip={
                <>
                  <p className="mb-2">
                    Insert any flow variable into your text message using double curly braces.
                  </p>
                  <p className="text-xs font-medium mt-2">Example:</p>
                  <p className="mt-1 text-xs">
                    Hello {"{{context.user_name}}"}, your order {"{{context.order_id}}"} is ready!
                  </p>
                  <p className="text-xs font-medium mt-2">Getting list size:</p>
                  <p className="mt-1 text-xs">
                    Use {"{{context.items.length}}"} to show how many items are in a list.
                  </p>
                </>
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
}
