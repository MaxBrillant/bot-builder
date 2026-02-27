import { ListEditor, type FieldDefinition } from "./list-editor";
import type { APIResponseMapping, VariableType } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";

interface ResponseMappingEditorProps {
  value: APIResponseMapping[];
  onChange: (value: APIResponseMapping[]) => void;
  errors?: Record<string, string>;
  variables?: Array<{ name: string; type: VariableType }>;
  onCreateVariable: (variable: {
    name: string;
    type: VariableType;
    default: unknown;
  }) => Promise<void>;
}

const fields: FieldDefinition<APIResponseMapping>[] = [
  {
    key: "source_path",
    label: "Extract From (JSON Path)",
    type: "input",
    placeholder: "data.id",
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

export function ResponseMappingEditor({
  value,
  onChange,
  errors = {},
  variables = [],
  onCreateVariable,
}: ResponseMappingEditorProps) {
  return (
    <ListEditor
      items={value}
      onChange={onChange}
      fields={fields}
      createEmpty={() => ({ source_path: "", target_variable: "" })}
      renderColumns={(mapping) => [
        <span key="source" className="font-mono text-xs" title={mapping.source_path && mapping.source_path.length > 16 ? mapping.source_path : undefined}>
          {mapping.source_path || <span className="text-muted-foreground">path</span>}
        </span>,
        <span key="target" className="font-mono text-xs" title={mapping.target_variable && mapping.target_variable.length > 16 ? mapping.target_variable : undefined}>
          {mapping.target_variable || <span className="text-muted-foreground">variable</span>}
        </span>,
      ]}
      listHeaders={["Extract From", "To Variable"]}
      addLabel="Add Extraction"
      errorPrefix="response_map"
      errors={errors}
      context={{ variables, onCreateVariable }}
      helpText="Save data from the API response so you can use it later"
      helpTooltip={
        <>
          <p className="mb-2">
            When an API returns data, you can pick out the pieces you need and save them in variables. Then you can use those variables in messages, conditions, or other API calls.
          </p>
          <p className="text-xs font-medium mt-2">Example: If the API returns:</p>
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
          <p className="text-xs font-medium mt-2">You can extract:</p>
          <p className="mt-1 text-xs">
            <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">data.user_id</code> → Gets "123"
          </p>
          <p className="mt-1 text-xs">
            <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">data.name</code> → Gets "John"
          </p>
          <p className="mt-1 text-xs">
            <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">items.0.title</code> → Gets "First" (first item in the list)
          </p>
          <p className="text-xs mt-3 pt-2 border-t">
            <span className="font-medium">Tip:</span> If the API returns a list directly (not inside an object), use <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">*</code> to access it. For example, <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">*.0.id</code> gets the id from the first item.
          </p>
        </>
      }
      editorSide="left"
    />
  );
}
