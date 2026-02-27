import { ListEditor, type FieldDefinition, type CustomFieldProps } from "./list-editor";
import { Input } from "@/components/ui/input";
import { AutoResizeTextarea } from "@/components/ui/auto-resize-textarea";
import { cn } from "@/lib/utils";
import { SystemConstraints } from "@/lib/types";

interface FlowVariable {
  name: string;
  type: string;
  default: unknown; // Can be string, object, array, etc.
  defaultError?: string | null;
}

interface VariablesEditorProps {
  value: FlowVariable[];
  onChange: (variables: FlowVariable[]) => void;
  errors: Record<string, string>;
}

const VARIABLE_TYPES = [
  { value: "STRING", label: "STRING" },
  { value: "NUMBER", label: "NUMBER" },
  { value: "BOOLEAN", label: "BOOLEAN" },
  { value: "ARRAY", label: "ARRAY" },
];

function getDefaultPlaceholder(type: string): string {
  switch (type.toUpperCase()) {
    case "STRING": return "text";
    case "NUMBER": return "0";
    case "BOOLEAN": return "true or false";
    case "ARRAY": return '[\n  "item1",\n  "item2"\n]';
    default: return "";
  }
}

function DefaultValueField({ value, onChange, item, error }: CustomFieldProps<FlowVariable>) {
  const isArray = item.type.toUpperCase() === "ARRAY";
  const strValue = value === null || value === undefined ? "" : String(value);

  if (isArray) {
    return (
      <>
        <AutoResizeTextarea
          value={strValue}
          onChange={(e) => onChange(e.target.value)}
          placeholder={getDefaultPlaceholder(item.type)}
          minRows={3}
          maxRows={10}
          className={cn(
            "font-mono text-sm",
            error && "border-destructive"
          )}
        />
        {error && <p className="text-xs text-destructive mt-1">{error}</p>}
      </>
    );
  }

  return (
    <>
      <Input
        value={strValue}
        onChange={(e) => onChange(e.target.value)}
        placeholder={getDefaultPlaceholder(item.type)}
        className={cn(
          "font-mono text-sm",
          error && "border-destructive"
        )}
      />
      {error && <p className="text-xs text-destructive mt-1">{error}</p>}
    </>
  );
}

const fields: FieldDefinition<FlowVariable>[] = [
  {
    key: "name",
    label: "Name",
    type: "input",
    placeholder: "user_name",
    mono: true,
  },
  {
    key: "type",
    label: "Type",
    type: "select",
    options: VARIABLE_TYPES,
  },
  {
    key: "default",
    label: "Default Value",
    type: "custom",
    render: DefaultValueField,
  },
];

function formatDefaultValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function validateVariableDefault(type: string, defaultValue: unknown): string | null {
  const strValue = formatDefaultValue(defaultValue);
  if (strValue.trim() === "" || strValue.toLowerCase() === "null") {
    return null;
  }

  const normalizedType = type.toUpperCase();

  if (normalizedType === "STRING") {
    if (strValue.length > SystemConstraints.MAX_VARIABLE_DEFAULT_LENGTH) {
      return `Must be ${SystemConstraints.MAX_VARIABLE_DEFAULT_LENGTH} characters or less`;
    }
    return null;
  }

  if (normalizedType === "NUMBER") {
    if (!/^-?\d+(\.\d+)?$/.test(strValue.trim())) {
      return "Must be a valid number";
    }
    return null;
  }

  if (normalizedType === "BOOLEAN") {
    const lower = strValue.toLowerCase().trim();
    if (!["true", "false"].includes(lower)) {
      return "Must be true or false";
    }
    return null;
  }

  if (normalizedType === "ARRAY") {
    // Already an array object
    if (Array.isArray(defaultValue)) {
      if (defaultValue.length > SystemConstraints.MAX_ARRAY_LENGTH) {
        return `Max ${SystemConstraints.MAX_ARRAY_LENGTH} items`;
      }
      return null;
    }
    // Try to parse as JSON
    try {
      const parsed = JSON.parse(strValue);
      if (!Array.isArray(parsed)) {
        return "Must be a valid JSON array";
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
}

export function VariablesEditor({ value, onChange, errors }: VariablesEditorProps) {
  const handleChange = (variables: FlowVariable[]) => {
    // Validate defaults on any change
    const validated = variables.map((v) => ({
      ...v,
      defaultError: validateVariableDefault(v.type, v.default),
    }));
    onChange(validated);
  };

  // Normalize items for display - convert object defaults to strings
  const normalizedItems = value.map((v) => ({
    ...v,
    default: formatDefaultValue(v.default),
  }));

  // Merge defaultError into errors for display
  const mergedErrors = { ...errors };
  value.forEach((v, i) => {
    if (v.defaultError) {
      mergedErrors[`variables[${i}].default`] = v.defaultError;
    }
  });

  return (
    <ListEditor
      items={normalizedItems}
      onChange={handleChange}
      fields={fields}
      createEmpty={() => ({ name: "", type: "STRING", default: "", defaultError: null })}
      renderColumns={(variable) => {
        const defaultStr = formatDefaultValue(variable.default);
        const truncated = defaultStr.length > 15 ? defaultStr.substring(0, 12) + "..." : defaultStr;
        return [
          <span key="name" className="font-mono text-xs" title={variable.name && variable.name.length > 8 ? variable.name : undefined}>
            {variable.name || <span className="text-muted-foreground">name</span>}
          </span>,
          <span key="type" className="text-xs text-muted-foreground">
            {variable.type}
          </span>,
          <span key="default" className="font-mono text-xs" title={defaultStr && defaultStr.length > 8 ? defaultStr : undefined}>
            {truncated || <span className="text-muted-foreground">—</span>}
          </span>,
        ];
      }}
      listHeaders={["Name", "Type", "Default"]}
      addLabel="Add Variable"
      errorPrefix="variables"
      errors={mergedErrors}
      helpText="Create places to store data during the conversation"
      helpTooltip={
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
      editorSide="left"
    />
  );
}
