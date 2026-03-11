import { ListEditor, type FieldDefinition } from "./list-editor";
import type { VariableAssignment, VariableType, VariableInfo } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";

interface AssignmentsGridProps {
  value: VariableAssignment[];
  onChange: (value: VariableAssignment[]) => void;
  errors: Record<string, string>;
  variables: Array<{ name: string; type: VariableType }>;
  onCreateVariable: (variable: {
    name: string;
    type: VariableType;
    default: unknown;
  }) => Promise<void>;
  availableVariables?: VariableInfo[];
}

const fields: FieldDefinition<VariableAssignment>[] = [
  {
    key: "variable",
    label: "Variable",
    type: "variable-select",
    placeholder: "Select variable",
    mono: true,
  },
  {
    key: "value",
    label: "Value",
    type: "template",
    placeholder: "Enter value or {{variable}}",
    maxLength: SystemConstraints.MAX_TEMPLATE_LENGTH,
  },
];

export function AssignmentsGrid({
  value,
  onChange,
  errors = {},
  variables = [],
  onCreateVariable,
  availableVariables = [],
}: AssignmentsGridProps) {
  return (
    <ListEditor
      items={value}
      onChange={onChange}
      fields={fields}
      createEmpty={() => ({ variable: "", value: "" })}
      renderColumns={(assignment) => [
        <span
          key="variable"
          className="font-mono text-xs"
          title={
            assignment.variable && assignment.variable.length > 16
              ? assignment.variable
              : undefined
          }
        >
          {assignment.variable || (
            <span className="text-muted-foreground">variable</span>
          )}
        </span>,
        <span
          key="value"
          className="font-mono text-xs truncate"
          title={
            assignment.value && assignment.value.length > 16
              ? assignment.value
              : undefined
          }
        >
          {assignment.value || (
            <span className="text-muted-foreground">value</span>
          )}
        </span>,
      ]}
      listHeaders={["Variable", "Value"]}
      maxItems={SystemConstraints.MAX_ASSIGNMENTS_PER_SET_VARIABLE}
      addLabel="Add Assignment"
      errorPrefix="assignments"
      errors={errors}
      context={{ variables, onCreateVariable, availableVariables, nodeType: "SET_VARIABLE" }}
      helpText="Give variables a specific value without asking the user"
      helpTooltip={
        <>
          <p className="mb-2">
            Each assignment sets a variable to a value you choose. The bot does this silently and moves on — the user never sees it happen.
          </p>
          <p className="text-xs font-medium mt-2">Example:</p>
          <ul className="list-none space-y-1 mt-1 text-xs">
            <li>
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">verified</code> → <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">true</code>
            </li>
            <li>
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">order_id</code> → <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">{"{{api.id}}"}</code>
            </li>
            <li>
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">greeting</code> → <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">{"Hello {{name}}!"}</code>
            </li>
          </ul>
          <p className="mt-2 text-xs">
            Values support template variables — wrap any variable name in{" "}
            <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">{"{{ }}"}</code>{" "}
            to use its current value.
          </p>
        </>
      }
      editorSide="left"
    />
  );
}
