import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, X } from "lucide-react";
import { VariableSelect } from "./VariableSelect";
import { FieldHelp } from "./FieldHelp";
import type { APIResponseMapping } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ResponseMappingEditorProps {
  value: APIResponseMapping[];
  onChange: (value: APIResponseMapping[]) => void;
  errors?: Record<string, string>;
  variables?: Array<{ name: string; type: string }>;
  onCreateVariable: (variable: {
    name: string;
    type: string;
    default: any;
  }) => Promise<void>;
}

export function ResponseMappingEditor({
  value,
  onChange,
  errors = {},
  variables = [],
  onCreateVariable,
}: ResponseMappingEditorProps) {
  const handleAdd = () => {
    onChange([...value, { source_path: "", target_variable: "" }]);
  };

  const handleRemove = (index: number) => {
    const newValue = value.filter((_, i) => i !== index);
    onChange(newValue);
  };

  const handleSourcePathChange = (index: number, source_path: string) => {
    const newValue = [...value];
    newValue[index] = { ...newValue[index], source_path };
    onChange(newValue);
  };

  const handleTargetVariableChange = (
    index: number,
    target_variable: string
  ) => {
    const newValue = [...value];
    newValue[index] = { ...newValue[index], target_variable };
    onChange(newValue);
  };

  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <div className="grid grid-cols-[1fr_1fr_auto] gap-2 items-start px-1">
          <div className="text-xs font-medium text-muted-foreground">
            Extract From
          </div>
          <div className="text-xs font-medium text-muted-foreground">
            To Variable
          </div>
          <div className="w-9" />
        </div>
      )}
      {value.map((mapping, index) => {
        const sourceError = errors[`response_map[${index}].source_path`];
        const targetError = errors[`response_map[${index}].target_variable`];

        return (
          <div key={index} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-start">
            <div className="min-w-0">
              <Input
                value={mapping.source_path}
                onChange={(e) => handleSourcePathChange(index, e.target.value)}
                placeholder="data.id"
                maxLength={SystemConstraints.MAX_SOURCE_PATH_LENGTH}
                className={cn(
                  "text-sm font-mono",
                  sourceError && "border-destructive"
                )}
              />
              {sourceError && (
                <p className="text-sm text-destructive mt-1">{sourceError}</p>
              )}
            </div>
            <div className="min-w-0">
              <VariableSelect
                value={mapping.target_variable}
                onValueChange={(value) => handleTargetVariableChange(index, value)}
                variables={variables}
                onCreateVariable={onCreateVariable}
                placeholder="Select variable"
                className={cn(
                  "text-sm font-mono",
                  targetError && "border-destructive"
                )}
              />
              {targetError && (
                <p className="text-sm text-destructive mt-1">{targetError}</p>
              )}
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

      {/* Help Text */}
      <FieldHelp
        text="Save data from the API response into variables you can use later"
        tooltip={
          <>
            <p className="mb-2">
              After calling the API, you can extract specific pieces of data from the response and store them in variables. This lets you use that data in later nodes.
            </p>
            <p className="text-xs font-medium mt-2">Example API response:</p>
            <pre className="mt-1 text-xs bg-primary-foreground text-primary p-2 rounded overflow-x-auto">
              {`{
  "data": {
    "user_id": "123",
    "name": "John"
  },
  "items": [
    {"id": 1, "title": "First"}
  ]
}`}
            </pre>
            <p className="text-xs font-medium mt-2">Paths to extract:</p>
            <p className="mt-1 text-xs">
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">data.user_id</code> → Gets "123"
            </p>
            <p className="mt-1 text-xs">
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">data.name</code> → Gets "John"
            </p>
            <p className="mt-1 text-xs">
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">items.0.title</code> → Gets "First"
            </p>
            <p className="text-xs mt-3 pt-2 border-t">
              <span className="font-medium">Array responses:</span> If the API returns an array directly, use <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">*</code> to access it (e.g., <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">*.0.id</code>)
            </p>
          </>
        }
      />

      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleAdd}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Extraction
      </Button>
    </div>
  );
}
