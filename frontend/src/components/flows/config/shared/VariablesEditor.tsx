import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2 } from "lucide-react";
import { FieldHelp } from "./FieldHelp";
import { SystemConstraints } from "@/lib/types";
import { cn } from "@/lib/utils";

interface FlowVariable {
  name: string;
  type: string;
  default: any;
  defaultError?: string | null;
}

interface VariablesEditorProps {
  value: FlowVariable[];
  onChange: (variables: FlowVariable[]) => void;
  errors: Record<string, string>;
}

export function VariablesEditor({ value, onChange, errors }: VariablesEditorProps) {
  const handleAdd = () => {
    onChange([...value, { name: "", type: "STRING", default: "", defaultError: null }]);
  };

  const handleRemove = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const handleUpdate = (index: number, field: keyof FlowVariable, fieldValue: any) => {
    const updated = [...value];
    updated[index] = { ...updated[index], [field]: fieldValue };

    // Validate default value when type or default changes
    if (field === "type" || field === "default") {
      const varType = field === "type" ? fieldValue : updated[index].type;
      const defaultValue = field === "default" ? fieldValue : updated[index].default;
      updated[index].defaultError = validateVariableDefault(varType, defaultValue);
    }

    onChange(updated);
  };

  const validateVariableDefault = (type: string, defaultValue: string): string | null => {
    if (defaultValue.trim() === "" || defaultValue.toLowerCase() === "null") {
      return null;
    }

    // Normalize type to uppercase for comparison
    const normalizedType = type.toUpperCase();

    if (normalizedType === "STRING") {
      if (defaultValue.length > SystemConstraints.MAX_VARIABLE_DEFAULT_LENGTH) {
        return `Must be ${SystemConstraints.MAX_VARIABLE_DEFAULT_LENGTH} characters or less`;
      }
      return null;
    }

    if (normalizedType === "NUMBER") {
      if (!/^-?\d+(\.\d+)?$/.test(defaultValue.trim())) {
        return "Must be a valid number";
      }
      return null;
    }

    if (normalizedType === "BOOLEAN") {
      const lower = defaultValue.toLowerCase().trim();
      if (!["true", "false"].includes(lower)) {
        return "Must be true or false";
      }
      return null;
    }

    if (normalizedType === "ARRAY") {
      try {
        const parsed = JSON.parse(defaultValue);
        if (!Array.isArray(parsed)) {
          return 'Must be a valid JSON array';
        }
        if (parsed.length > SystemConstraints.MAX_ARRAY_LENGTH) {
          return `Max ${SystemConstraints.MAX_ARRAY_LENGTH} items`;
        }
        return null;
      } catch {
        return "Invalid JSON array";
      }
    }

    return "Invalid type";
  };

  return (
    <div className="space-y-2">
      {/* Variables List */}
      {value.length > 0 && (
        <div className="space-y-2">
          {value.map((variable, index) => (
            <div key={index} className="border rounded-md p-3 space-y-3 bg-card">
              {/* Name Field with Delete Button */}
              <div className="space-y-1">
                <Label htmlFor={`var-name-${index}`} className="text-xs">
                  Name
                </Label>
                <div className="flex gap-2">
                  <Input
                    id={`var-name-${index}`}
                    value={variable.name}
                    onChange={(e) => handleUpdate(index, "name", e.target.value)}
                    placeholder="user_name"
                    className={cn(
                      "font-mono text-sm flex-1",
                      errors[`variables.${index}.name`] && "border-destructive"
                    )}
                  />
                  <Button
                    type="button"
                    onClick={() => handleRemove(index)}
                    size="sm"
                    variant="ghost"
                    className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                {errors[`variables.${index}.name`] && (
                  <p className="text-xs text-destructive">
                    {errors[`variables.${index}.name`]}
                  </p>
                )}
              </div>

              {/* Type and Default Row */}
              <div className="grid grid-cols-2 gap-2">
                {/* Type */}
                <div className="space-y-1">
                  <Label htmlFor={`var-type-${index}`} className="text-xs">
                    Type
                  </Label>
                  <Select
                    value={variable.type}
                    onValueChange={(val) => handleUpdate(index, "type", val)}
                  >
                    <SelectTrigger id={`var-type-${index}`} className="text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="STRING">STRING</SelectItem>
                      <SelectItem value="NUMBER">NUMBER</SelectItem>
                      <SelectItem value="BOOLEAN">BOOLEAN</SelectItem>
                      <SelectItem value="ARRAY">ARRAY</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Default Value */}
                <div className="space-y-1">
                  <Label htmlFor={`var-default-${index}`} className="text-xs">
                    Default
                  </Label>
                  <Input
                    id={`var-default-${index}`}
                    value={
                      variable.type === "ARRAY" && typeof variable.default !== "string"
                        ? JSON.stringify(variable.default, null, 0)
                        : variable.default
                    }
                    onChange={(e) => handleUpdate(index, "default", e.target.value)}
                    placeholder={
                      variable.type === "STRING" ? "text" :
                      variable.type === "NUMBER" ? "0" :
                      variable.type === "BOOLEAN" ? "false" :
                      "[]"
                    }
                    className={cn(
                      "font-mono text-sm",
                      variable.defaultError && "border-destructive"
                    )}
                  />
                  {variable.defaultError && (
                    <p className="text-xs text-destructive">
                      {variable.defaultError}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Help Text */}
      <FieldHelp
        text="Create places to store data during the conversation"
        tooltip={
          <>
            <p className="mb-2">
              Variables hold information like user answers, API data, or anything you want to remember and use later in the conversation.
            </p>
            <p className="text-xs font-medium mt-2">Naming rules:</p>
            <p className="mt-1 text-xs">
              Use letters, numbers, and underscores (like <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">user_name</code> or <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">order_count</code>)
            </p>
            <p className="text-xs font-medium mt-2">Types:</p>
            <p className="mt-1 text-xs">
              STRING = text, NUMBER = numbers, BOOLEAN = true/false, ARRAY = a list of items
            </p>
          </>
        }
      />

      {/* Add Button - at bottom like API Action */}
      <Button
        type="button"
        onClick={handleAdd}
        size="sm"
        variant="outline"
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Variable
      </Button>
    </div>
  );
}
