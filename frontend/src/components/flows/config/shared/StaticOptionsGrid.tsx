import { ListEditor, type FieldDefinition } from "./list-editor";
import type { MenuStaticOption } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";

interface StaticOptionsGridProps {
  value: MenuStaticOption[];
  onChange: (value: MenuStaticOption[]) => void;
  errors: Record<string, string>;
  availableVariables?: string[];
}

const fields: FieldDefinition<MenuStaticOption>[] = [
  {
    key: "label",
    label: "Option Label",
    type: "template",
    placeholder: "Option label",
    maxLength: SystemConstraints.MAX_OPTION_LABEL_LENGTH,
  },
];

export function StaticOptionsGrid({
  value,
  onChange,
  errors = {},
  availableVariables = [],
}: StaticOptionsGridProps) {
  return (
    <ListEditor
      items={value}
      onChange={onChange}
      fields={fields}
      createEmpty={() => ({ label: "" })}
      renderSummary={(option) => (
        <span className="text-sm truncate">
          {option.label || <span className="text-muted-foreground">Empty option</span>}
        </span>
      )}
      summaryPrefix={(_, index) => (
        <span className="text-sm font-medium w-4">{index + 1}.</span>
      )}
      maxItems={SystemConstraints.MAX_STATIC_MENU_OPTIONS}
      addLabel="Add Option"
      errorPrefix="static_options"
      errors={errors}
      context={{ availableVariables }}
      editorSide="left"
    />
  );
}
