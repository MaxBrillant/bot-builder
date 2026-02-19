import { ListEditor, type FieldDefinition } from "./list-editor";
import type { MenuOutputMapping, VariableType } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";

interface OutputMappingGridProps {
  value: MenuOutputMapping[];
  onChange: (value: MenuOutputMapping[]) => void;
  errors: Record<string, string>;
  variables: Array<{ name: string; type: VariableType }>;
  onCreateVariable: (variable: {
    name: string;
    type: VariableType;
    default: unknown;
  }) => Promise<void>;
}

const fields: FieldDefinition<MenuOutputMapping>[] = [
  {
    key: "source_path",
    label: "Extract From",
    type: "input",
    placeholder: "id",
    maxLength: SystemConstraints.MAX_SOURCE_PATH_LENGTH,
    mono: true,
  },
  {
    key: "target_variable",
    label: "Save To Variable",
    type: "variable-select",
    placeholder: "Select variable",
    mono: true,
  },
];

export function OutputMappingGrid({
  value,
  onChange,
  errors = {},
  variables = [],
  onCreateVariable,
}: OutputMappingGridProps) {
  return (
    <ListEditor
      items={value}
      onChange={onChange}
      fields={fields}
      createEmpty={() => ({ source_path: "", target_variable: "" })}
      renderColumns={(mapping) => [
        <span key="source" className="font-mono text-xs">
          {mapping.source_path || <span className="text-muted-foreground">path</span>}
        </span>,
        <span key="target" className="font-mono text-xs">
          {mapping.target_variable || <span className="text-muted-foreground">variable</span>}
        </span>,
      ]}
      listHeaders={["Extract From", "To Variable"]}
      addLabel="Add Extraction"
      errorPrefix="output_mapping"
      errors={errors}
      context={{ variables, onCreateVariable }}
      helpText="Save data from the user's selection to use later"
      helpTooltip={
        <>
          <p className="mb-2">
            When the user picks an option from the menu, you can save information from that choice (like its ID or name) into a variable for use later.
          </p>
          <p className="text-xs font-medium mt-2">Example: If menu items look like this:</p>
          <pre className="mt-1 text-xs bg-primary-foreground text-primary p-2 rounded overflow-x-auto">
            {`{
  "id": 42,
  "name": "Blue Shirt",
  "price": 29.99
}`}
          </pre>
          <p className="text-xs font-medium mt-2">You can extract:</p>
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
          </ul>
        </>
      }
      editorSide="left"
    />
  );
}
