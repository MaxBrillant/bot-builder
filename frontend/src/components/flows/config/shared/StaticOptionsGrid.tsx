import { Button } from "@/components/ui/button";
import { Plus, X } from "lucide-react";
import { TemplateInput } from "./TemplateInput";
import type { MenuStaticOption } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";

interface StaticOptionsGridProps {
  value: MenuStaticOption[];
  onChange: (value: MenuStaticOption[]) => void;
  errors: Record<string, string>;
  availableVariables?: string[];
}

export function StaticOptionsGrid({
  value,
  onChange,
  errors = {},
  availableVariables = [],
}: StaticOptionsGridProps) {
  const handleAdd = () => {
    if (value.length >= SystemConstraints.MAX_STATIC_MENU_OPTIONS) return;
    onChange([...value, { label: "" }]);
  };

  const handleRemove = (index: number) => {
    const newValue = value.filter((_, i) => i !== index);
    onChange(newValue);
  };

  const handleLabelChange = (index: number, label: string) => {
    const newValue = [...value];
    newValue[index] = { label };
    onChange(newValue);
  };

  return (
    <div className="space-y-2">
      {/* Option Rows */}
      {value.map((option, index) => {
        const labelError = errors[`static_options[${index}].label`];

        return (
          <div key={index} className="grid grid-cols-[auto_1fr_auto] gap-3 items-start">
            {/* Index Number */}
            <div className="h-9 flex items-center text-sm text-muted-foreground">
              {index + 1}
            </div>

            {/* Label Input */}
            <div className="min-w-0">
              <TemplateInput
                value={option.label}
                onChange={(newValue) => handleLabelChange(index, newValue)}
                placeholder="Option label"
                maxLength={SystemConstraints.MAX_OPTION_LABEL_LENGTH}
                availableVariables={availableVariables}
                rows={1}
                maxRows={2}
                error={labelError}
              />
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

      {/* Add Button */}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleAdd}
        disabled={value.length >= SystemConstraints.MAX_STATIC_MENU_OPTIONS}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Option
      </Button>
    </div>
  );
}
