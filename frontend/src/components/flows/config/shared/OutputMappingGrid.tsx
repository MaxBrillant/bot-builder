import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, X } from "lucide-react";
import { VariableSelect } from "./VariableSelect";
import { FieldHelp } from "./FieldHelp";
import type { MenuOutputMapping } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";
import { cn } from "@/lib/utils";

interface OutputMappingGridProps {
  value: MenuOutputMapping[];
  onChange: (value: MenuOutputMapping[]) => void;
  errors: Record<string, string>;
  variables: Array<{ name: string; type: string }>;
  onCreateVariable: (variable: {
    name: string;
    type: string;
    default: any;
  }) => Promise<void>;
}

export function OutputMappingGrid({
  value,
  onChange,
  errors = {},
  variables = [],
  onCreateVariable,
}: OutputMappingGridProps) {
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
      {/* Header Row */}
      {value.length > 0 && (
        <div className="grid grid-cols-[1fr_1fr_auto] gap-2 items-start px-1">
          <div className="text-xs font-medium text-muted-foreground">Extract From</div>
          <div className="text-xs font-medium text-muted-foreground">To Variable</div>
          <div className="w-9" />
        </div>
      )}

      {/* Mapping Rows */}
      {value.map((mapping, index) => {
        const sourceError = errors[`output_mapping[${index}].source_path`];
        const targetError = errors[`output_mapping[${index}].target_variable`];

        return (
          <div key={index} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-start">
            {/* Source Path */}
            <div className="min-w-0">
              <Input
                value={mapping.source_path}
                onChange={(e) => handleSourcePathChange(index, e.target.value)}
                placeholder="id"
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

            {/* Target Variable */}
            <div className="min-w-0">
              <VariableSelect
                value={mapping.target_variable}
                onValueChange={(value) =>
                  handleTargetVariableChange(index, value)
                }
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
        text="Save specific data from the selected menu item into variables"
        tooltip={
          <>
            <p className="mb-2">
              When the user picks a menu option, you can extract information from that selected item and save it to variables. For example, if they select a product, you can save the product's ID, price, or name.
            </p>
            <p className="text-xs font-medium mt-2">Example menu item:</p>
            <pre className="mt-1 text-xs bg-primary-foreground text-primary p-2 rounded overflow-x-auto">
              {`{
  "id": 42,
  "name": "Blue Shirt",
  "price": 29.99,
  "details": {
    "size": "M",
    "color": "blue"
  }
}`}
            </pre>
            <p className="text-xs font-medium mt-2">Paths to extract from above:</p>
            <ul className="list-none space-y-1 mt-1 text-xs">
              <li>
                <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">id</code> → Gets 42
              </li>
              <li>
                <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">name</code> → Gets "Blue Shirt"
              </li>
              <li>
                <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">price</code> → Gets 29.99
              </li>
              <li>
                <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">details.size</code> → Gets "M" (nested field)
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
        Add Extraction
      </Button>
    </div>
  );
}
