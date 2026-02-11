import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, X } from "lucide-react";
import { TemplateInput } from "./TemplateInput";
import { SystemConstraints, type APIHeader } from "@/lib/types";
import { cn } from "@/lib/utils";

interface HeadersEditorProps {
  value: APIHeader[];
  onChange: (value: APIHeader[]) => void;
  errors?: Record<string, string>;
  availableVariables?: string[];
  nodeType?: "TEXT" | "PROMPT" | "MENU" | "API_ACTION" | "LOGIC_EXPRESSION" | "END";
}

export function HeadersEditor({
  value,
  onChange,
  errors = {},
  availableVariables = [],
  nodeType,
}: HeadersEditorProps) {
  const handleAdd = () => {
    if (value.length >= SystemConstraints.MAX_HEADERS_PER_REQUEST) return;
    onChange([...value, { name: "", value: "" }]);
  };

  const handleRemove = (index: number) => {
    const newValue = value.filter((_, i) => i !== index);
    onChange(newValue);
  };

  const handleNameChange = (index: number, name: string) => {
    const newValue = [...value];
    newValue[index] = { ...newValue[index], name };
    onChange(newValue);
  };

  const handleValueChange = (index: number, headerValue: string) => {
    const newValue = [...value];
    newValue[index] = { ...newValue[index], value: headerValue };
    onChange(newValue);
  };

  // Common header suggestions
  const commonHeaders = [
    "Authorization",
    "Content-Type",
    "Accept",
    "User-Agent",
    "X-API-Key",
  ];

  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <div className="grid grid-cols-[1fr_1fr_auto] gap-2 items-start px-1">
          <div className="text-xs font-medium text-muted-foreground">
            Name
          </div>
          <div className="text-xs font-medium text-muted-foreground">
            Value
          </div>
          <div className="w-9" />
        </div>
      )}
      {value.map((header, index) => {
        const nameError = errors[`request.headers[${index}].name`];
        const valueError = errors[`request.headers[${index}].value`];

        return (
          <div key={index} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-start">
            <div className="min-w-0">
              <Input
                value={header.name}
                onChange={(e) => handleNameChange(index, e.target.value)}
                placeholder="Authorization"
                maxLength={SystemConstraints.MAX_HEADER_NAME_LENGTH}
                list={`header-suggestions-${index}`}
                className={cn(
                  "text-sm",
                  nameError && "border-destructive"
                )}
              />
              <datalist id={`header-suggestions-${index}`}>
                {commonHeaders.map((h) => (
                  <option key={h} value={h} />
                ))}
              </datalist>
              {nameError && (
                <p className="text-sm text-destructive mt-1">{nameError}</p>
              )}
            </div>
            <div className="min-w-0">
              <TemplateInput
                value={header.value}
                onChange={(newValue) => handleValueChange(index, newValue)}
                placeholder="Bearer {{token}}"
                maxLength={SystemConstraints.MAX_HEADER_VALUE_LENGTH}
                availableVariables={availableVariables}
                rows={1}
                maxRows={3}
                nodeType={nodeType}
                error={valueError}
              />
            </div>
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

      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleAdd}
        disabled={value.length >= SystemConstraints.MAX_HEADERS_PER_REQUEST}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Header
      </Button>
    </div>
  );
}
