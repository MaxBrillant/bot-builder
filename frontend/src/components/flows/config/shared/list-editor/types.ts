import type { ReactNode } from "react";

export type FieldType =
  | "input"
  | "select"
  | "template"
  | "variable-select"
  | "custom";

export interface SelectOption {
  value: string;
  label: string;
}

export interface FieldDefinition<T> {
  key: keyof T;
  label: string;
  type: FieldType;
  placeholder?: string;
  options?: SelectOption[] | ((item: T, context: Record<string, unknown>) => SelectOption[]);
  maxLength?: number;
  mono?: boolean; // Use monospace font
  // For custom field rendering
  render?: (props: CustomFieldProps<T>) => ReactNode;
}

export interface CustomFieldProps<T> {
  value: unknown;
  onChange: (value: unknown) => void;
  onItemChange: (item: T) => void; // Replace the entire item
  item: T;
  context: Record<string, unknown>;
  error?: string;
}

export interface ListEditorProps<T> {
  items: T[];
  onChange: (items: T[]) => void;
  fields: FieldDefinition<T>[];
  createEmpty: () => T;
  // Either render a single summary or multiple columns (for alignment with headers)
  renderSummary?: (item: T, index: number) => ReactNode;
  renderColumns?: (item: T, index: number) => ReactNode[];
  summaryPrefix?: (item: T, index: number) => ReactNode;
  renderBetween?: (
    index: number,
    item: T,
    nextItem: T,
    onChange: (index: number, updates: Partial<T>) => void
  ) => ReactNode;
  // Column headers shown above the list (e.g., ["Name", "Value"])
  listHeaders?: string[];
  maxItems?: number;
  addLabel?: string;
  emptyLabel?: string;
  errors?: Record<string, string>;
  errorPrefix?: string; // e.g., "headers" for "headers[0].name"
  helpText?: string;
  helpTooltip?: ReactNode;
  context?: Record<string, unknown>;
  editorWidth?: number;
  editorSide?: "left" | "right";
}
