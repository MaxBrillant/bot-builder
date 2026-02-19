import { useState, Fragment, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Plus, X } from "lucide-react";
import { ListEditorRow } from "./ListEditorRow";
import { ListEditorField } from "./ListEditorField";
import { FieldHelp } from "../FieldHelp";
import type { ListEditorProps, FieldDefinition } from "./types";

export function ListEditor<T extends object>({
  items,
  onChange,
  fields,
  createEmpty,
  renderSummary,
  renderColumns,
  summaryPrefix,
  renderBetween,
  listHeaders,
  maxItems,
  addLabel = "Add Item",
  emptyLabel,
  errors = {},
  errorPrefix = "items",
  helpText,
  helpTooltip,
  context = {},
  editorWidth = 320,
  editorSide = "left",
}: ListEditorProps<T>) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const handleAdd = useCallback(() => {
    if (maxItems && items.length >= maxItems) return;
    const newItems = [...items, createEmpty()];
    onChange(newItems);
    // Open the new item for editing
    setActiveIndex(newItems.length - 1);
  }, [maxItems, items, onChange, createEmpty]);

  const handleDelete = useCallback((index: number) => {
    const newItems = items.filter((_, i) => i !== index);
    onChange(newItems);
    if (activeIndex === index) {
      setActiveIndex(null);
    } else if (activeIndex !== null && activeIndex > index) {
      setActiveIndex(activeIndex - 1);
    }
  }, [onChange, activeIndex, items]);

  const handleUpdate = useCallback((index: number, updates: Partial<T>) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], ...updates };
    onChange(newItems);
  }, [onChange, items]);

  const handleFieldChange = useCallback((index: number, field: FieldDefinition<T>, value: unknown) => {
    handleUpdate(index, { [field.key]: value } as Partial<T>);
  }, [handleUpdate]);

  const handleItemReplace = useCallback((index: number, newItem: T) => {
    const newItems = [...items];
    newItems[index] = newItem;
    onChange(newItems);
  }, [onChange, items]);

  const getFieldError = useCallback((index: number, fieldKey: keyof T): string | undefined => {
    // Try multiple error key formats
    const patterns = [
      `${errorPrefix}[${index}].${String(fieldKey)}`,
      `${errorPrefix}.${index}.${String(fieldKey)}`,
      `[${index}].${String(fieldKey)}`,
    ];
    for (const pattern of patterns) {
      if (errors[pattern]) return errors[pattern];
    }
    return undefined;
  }, [errorPrefix, errors]);

  const hasItemError = useCallback((index: number): boolean => {
    return fields.some((field) => getFieldError(index, field.key));
  }, [fields, getFieldError]);

  const canAdd = !maxItems || items.length < maxItems;

  return (
    <div className="space-y-2">
      {/* List Headers */}
      {listHeaders && listHeaders.length > 0 && items.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-1">
          <div className="flex-1 flex gap-2">
            {listHeaders.map((header, i) => (
              <span
                key={i}
                className="text-xs font-medium text-muted-foreground flex-1"
              >
                {header}
              </span>
            ))}
          </div>
          <div className="w-9" /> {/* Spacer for delete button */}
        </div>
      )}

      {/* List */}
      {items.length > 0 ? (
        <div className="space-y-1">
          {items.map((item, index) => (
            <Fragment key={index}>
              <Popover
                open={activeIndex === index}
                onOpenChange={(open) => setActiveIndex(open ? index : null)}
              >
                <PopoverTrigger asChild>
                  <div>
                    <ListEditorRow
                      summary={renderSummary?.(item, index)}
                      columns={renderColumns?.(item, index)}
                      prefix={summaryPrefix?.(item, index)}
                      isActive={activeIndex === index}
                      hasError={hasItemError(index)}
                      onClick={() => setActiveIndex(activeIndex === index ? null : index)}
                      onDelete={() => handleDelete(index)}
                    />
                  </div>
                </PopoverTrigger>
                <PopoverContent
                  side={editorSide}
                  align="start"
                  className="p-0"
                  style={{ width: editorWidth }}
                >
                  <div className="flex items-center justify-between px-3 py-2 border-b">
                    <span className="text-sm font-medium">Edit</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0"
                      onClick={() => setActiveIndex(null)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="p-3 space-y-4">
                    {fields.map((field) => (
                      <ListEditorField
                        key={String(field.key)}
                        field={field}
                        value={item[field.key]}
                        onChange={(value) => handleFieldChange(index, field, value)}
                        onItemChange={(newItem) => handleItemReplace(index, newItem)}
                        item={item}
                        context={context}
                        error={getFieldError(index, field.key)}
                      />
                    ))}
                  </div>
                </PopoverContent>
              </Popover>

              {/* Between-item content (e.g., AND/OR) */}
              {renderBetween && index < items.length - 1 && (
                <div className="flex justify-center py-1">
                  {renderBetween(index, item, items[index + 1], handleUpdate)}
                </div>
              )}
            </Fragment>
          ))}
        </div>
      ) : emptyLabel ? (
        <p className="text-sm text-muted-foreground py-2">{emptyLabel}</p>
      ) : null}

      {/* Help */}
      {helpText && <FieldHelp text={helpText} tooltip={helpTooltip} />}

      {/* Add Button */}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleAdd}
        disabled={!canAdd}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        {addLabel}
        {maxItems && ` (${items.length}/${maxItems})`}
      </Button>
    </div>
  );
}
