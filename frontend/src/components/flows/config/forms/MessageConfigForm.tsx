import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { TemplateInput } from "../shared/TemplateInput";
import { FieldHelp } from "../shared/FieldHelp";
import type { MessageNodeConfig, ValidationError } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";
import { cn } from "@/lib/utils";

interface MessageConfigFormProps {
  config: MessageNodeConfig;
  onChange: (config: MessageNodeConfig) => void;
  errors: ValidationError[];
  availableVariables?: string[];
  nodeName?: string;
  onNodeNameChange?: (name: string) => void;
  nodeNameError?: string;
  nodeNameInputRef?: React.RefObject<HTMLInputElement>;
}

export function MessageConfigForm({
  config,
  onChange,
  errors,
  availableVariables,
  nodeName,
  onNodeNameChange,
  nodeNameError,
  nodeNameInputRef,
}: MessageConfigFormProps) {
  const safeAvailableVariables = availableVariables ?? [];

  const getFieldError = (field: string) => {
    return errors.find((e) => e.field === field)?.message;
  };

  const handleTextChange = (text: string) => {
    onChange({ ...config, type: "MESSAGE", text });
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
          {/* Message Text */}
          <div className="space-y-1">
            <TemplateInput
              value={config.text ?? ""}
              onChange={handleTextChange}
              error={getFieldError("text")}
              maxLength={SystemConstraints.MAX_MESSAGE_LENGTH}
              placeholder="Enter message text"
              rows={8}
              maxRows={20}
              availableVariables={safeAvailableVariables}
              nodeType="MESSAGE"
            />
            <FieldHelp
              text="Use {{variable_name}} to insert variable values"
              tooltip={
                <>
                  <p className="mb-2">
                    Insert any flow variable into your message using double curly braces.
                  </p>
                  <p className="text-xs font-medium mt-2">Example:</p>
                  <p className="mt-1 text-xs">
                    Hello {"{{user_name}}"}, your order {"{{order_id}}"} is ready!
                  </p>
                  <p className="text-xs font-medium mt-2">Note:</p>
                  <p className="mt-1 text-xs">
                    Array length ({"{{items.length}}"}) doesn't work in messages. To show counts, save the count in a separate variable first.
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
