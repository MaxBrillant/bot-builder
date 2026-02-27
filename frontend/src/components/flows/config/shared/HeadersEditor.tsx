import React from "react";
import { ListEditor, type FieldDefinition, type CustomFieldProps } from "./list-editor";
import { Input } from "@/components/ui/input";
import { SystemConstraints, type APIHeader, type VariableInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

const COMMON_HEADERS = [
  "Authorization",
  "Content-Type",
  "Accept",
  "User-Agent",
  "X-API-Key",
];

interface HeadersEditorProps {
  value: APIHeader[];
  onChange: (value: APIHeader[]) => void;
  errors?: Record<string, string>;
  availableVariables?: VariableInfo[];
  nodeType?: "TEXT" | "PROMPT" | "MENU" | "API_ACTION" | "LOGIC_EXPRESSION" | "END";
}

// Custom renderer for header name with autocomplete suggestions
function HeaderNameInput({ value, onChange, error }: CustomFieldProps<APIHeader>) {
  const inputId = React.useId();
  return (
    <>
      <Input
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Authorization"
        maxLength={SystemConstraints.MAX_HEADER_NAME_LENGTH}
        list={inputId}
        className={cn("text-sm", error && "border-destructive")}
      />
      <datalist id={inputId}>
        {COMMON_HEADERS.map((h) => (
          <option key={h} value={h} />
        ))}
      </datalist>
      {error && <p className="text-xs text-destructive mt-1">{error}</p>}
    </>
  );
}

const fields: FieldDefinition<APIHeader>[] = [
  {
    key: "name",
    label: "Header Name",
    type: "custom",
    render: HeaderNameInput,
  },
  {
    key: "value",
    label: "Header Value",
    type: "template",
    placeholder: "Bearer {{token}}",
    maxLength: SystemConstraints.MAX_HEADER_VALUE_LENGTH,
  },
];

export function HeadersEditor({
  value,
  onChange,
  errors = {},
  availableVariables = [],
  nodeType,
}: HeadersEditorProps) {
  return (
    <ListEditor
      items={value}
      onChange={onChange}
      fields={fields}
      createEmpty={() => ({ name: "", value: "" })}
      renderColumns={(header) => [
        <span key="name" className="font-mono text-xs" title={header.name && header.name.length > 16 ? header.name : undefined}>
          {header.name || <span className="text-muted-foreground">name</span>}
        </span>,
        <span key="value" className="font-mono text-xs truncate" title={header.value && header.value.length > 16 ? header.value : undefined}>
          {header.value || <span className="text-muted-foreground">value</span>}
        </span>,
      ]}
      listHeaders={["Name", "Value"]}
      maxItems={SystemConstraints.MAX_HEADERS_PER_REQUEST}
      addLabel="Add Header"
      errorPrefix="request.headers"
      errors={errors}
      context={{ availableVariables, nodeType }}
      editorSide="left"
    />
  );
}
