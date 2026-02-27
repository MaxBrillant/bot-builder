import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TemplateInput } from "../TemplateInput";
import { VariableSelect } from "../VariableSelect";
import { cn } from "@/lib/utils";
import type { FieldDefinition } from "./types";
import type { VariableType, VariableInfo } from "@/lib/types";

// Safely convert any value to a string for display
function toStringValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

interface ListEditorFieldProps<T> {
  field: FieldDefinition<T>;
  value: unknown;
  onChange: (value: unknown) => void;
  onItemChange: (item: T) => void;
  item: T;
  context: Record<string, unknown>;
  error?: string;
}

export function ListEditorField<T>({
  field,
  value,
  onChange,
  onItemChange,
  item,
  context,
  error,
}: ListEditorFieldProps<T>) {
  const renderField = () => {
    switch (field.type) {
      case "input":
        return (
          <Input
            value={toStringValue(value)}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            maxLength={field.maxLength}
            className={cn(
              "text-sm",
              field.mono && "font-mono",
              error && "border-destructive"
            )}
          />
        );

      case "select": {
        const options =
          typeof field.options === "function"
            ? field.options(item, context)
            : field.options ?? [];

        return (
          <Select value={toStringValue(value)} onValueChange={onChange}>
            <SelectTrigger
              className={cn("text-sm", error && "border-destructive")}
            >
              <SelectValue placeholder={field.placeholder ?? "Select..."} />
            </SelectTrigger>
            <SelectContent>
              {options.length === 0 ? (
                <div className="px-2 py-2 text-sm text-muted-foreground">
                  No options available
                </div>
              ) : (
                options.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        );
      }

      case "template":
        return (
          <TemplateInput
            value={toStringValue(value)}
            onChange={onChange}
            placeholder={field.placeholder}
            maxLength={field.maxLength ?? 1000}
            availableVariables={
              (context.availableVariables as VariableInfo[]) ?? []
            }
            rows={1}
            maxRows={5}
            nodeType={context.nodeType as "TEXT" | "PROMPT" | "MENU" | "API_ACTION" | "LOGIC_EXPRESSION" | "END" | undefined}
            error={error}
          />
        );

      case "variable-select": {
        const variables = (context.variables as Array<{ name: string; type: VariableType }>) ?? [];
        const onCreateVariable = context.onCreateVariable as (v: {
          name: string;
          type: VariableType;
          default: unknown;
        }) => Promise<void>;

        return (
          <VariableSelect
            value={toStringValue(value)}
            onValueChange={onChange}
            variables={variables}
            onCreateVariable={onCreateVariable}
            placeholder={field.placeholder ?? "Select variable"}
            className={cn(
              "text-sm",
              field.mono && "font-mono",
              error && "border-destructive"
            )}
          />
        );
      }

      case "custom":
        if (!field.render) {
          return <div className="text-sm text-muted-foreground">No renderer</div>;
        }
        return field.render({ value, onChange, onItemChange, item, context, error });

      default:
        return null;
    }
  };

  return (
    <div className="space-y-1.5">
      {field.label && (
        <Label className="text-xs font-medium">{field.label}</Label>
      )}
      {renderField()}
      {error && field.type !== "template" && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
}
