import { useEffect, useState, useRef } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ListEditor, type FieldDefinition, type CustomFieldProps } from "./list-editor";
import { LeftOperandSelect } from "./LeftOperandSelect";
import { TemplateInput } from "./TemplateInput";
import type {
  ExpressionDefinition,
  Condition,
  LogicalOperator,
  ExpressionContext,
  ComparisonOperator,
} from "@/lib/expressionBuilderTypes";
import { isBooleanMethod } from "@/lib/expressionBuilderTypes";
import { parseExpression } from "@/lib/expressionParser";
import { serializeExpression } from "@/lib/expressionSerializer";
import type { VariableInfo } from "@/lib/types";

const MAX_CONDITIONS = 8;

interface ExpressionBuilderProps {
  value: string;
  onChange: (value: string) => void;
  context: ExpressionContext;
  availableVariables?: VariableInfo[];
  error?: string;
}

interface ConditionErrors {
  left?: string;
  operator?: string;
  right?: string;
}

function validateCondition(condition: Condition): ConditionErrors {
  const errors: ConditionErrors = {};

  if (!condition.left.path || condition.left.path.trim() === "") {
    errors.left = "Required";
  }

  if (!isBooleanMethod(condition.left.path)) {
    const rightValue = condition.right.literalValue;
    if (rightValue === undefined || rightValue === null || String(rightValue).trim() === "") {
      errors.right = "Required";
    }
  }

  return errors;
}

function formatConditionSummary(condition: Condition): string {
  const left = condition.left.path;

  // For boolean methods, just show the method name
  if (isBooleanMethod(left)) {
    if (left === "input.isAlpha()") return "Input is letters only";
    if (left === "input.isNumeric()") return "Input is a number";
    if (left === "input.isDigit()") return "Input is digits only";
    return left;
  }

  // For comparisons
  const operatorLabels: Record<string, string> = {
    "==": "=",
    "!=": "≠",
    ">": ">",
    "<": "<",
    ">=": "≥",
    "<=": "≤",
  };
  const op = operatorLabels[condition.operator] || condition.operator;
  const right = condition.right.literalValue ?? "";

  // Shorten long paths
  const leftShort = left.length > 15 ? left.substring(0, 12) + "..." : left;
  const rightShort = String(right).length > 10 ? String(right).substring(0, 7) + "..." : right;

  return `${leftShort} ${op} ${rightShort}`;
}

export function ExpressionBuilder({
  value,
  onChange,
  context,
  availableVariables = [],
  error,
}: ExpressionBuilderProps) {
  const [expression, setExpression] = useState<ExpressionDefinition>(() =>
    parseExpression(value)
  );
  const isInternalUpdate = useRef(false);

  // Sync with external value changes (controlled component pattern)
  useEffect(() => {
    if (isInternalUpdate.current) {
      isInternalUpdate.current = false;
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Necessary for controlled component sync
    setExpression(parseExpression(value));
  }, [value]);

  const update = (newExpression: ExpressionDefinition) => {
    setExpression(newExpression);
    const serialized = serializeExpression(newExpression);
    if (serialized !== value) {
      isInternalUpdate.current = true;
      onChange(serialized);
    }
  };

  const handleConditionsChange = (conditions: Condition[]) => {
    update({ conditions });
  };

  const createEmptyCondition = (): Condition => ({
    left: { type: "variable", path: "" },
    operator: "==",
    right: { type: "literal", literalType: "string", literalValue: "" },
  });

  // Custom field renderer for the entire condition
  const renderConditionFields = ({ item: cond, onItemChange }: CustomFieldProps<Condition>) => {
    const isBooleanCheck = isBooleanMethod(cond.left.path);
    const errors = validateCondition(cond);

    return (
      <div className="space-y-3">
        {/* Left operand */}
        <div>
          <label className="text-xs font-medium mb-1.5 block">Condition</label>
          <LeftOperandSelect
            value={cond.left}
            onChange={(left) => onItemChange({ ...cond, left })}
            context={context}
            availableVariables={availableVariables}
            error={errors.left}
          />
        </div>

        {/* Operator - only for non-boolean */}
        {!isBooleanCheck && (
          <div>
            <label className="text-xs font-medium mb-1.5 block">Operator</label>
            <Select
              value={cond.operator}
              onValueChange={(op: ComparisonOperator) =>
                onItemChange({ ...cond, operator: op })
              }
            >
              <SelectTrigger className="text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="==">is equal to (=)</SelectItem>
                <SelectItem value="!=">is not equal to (≠)</SelectItem>
                <SelectItem value=">">is more than (&gt;)</SelectItem>
                <SelectItem value="<">is less than (&lt;)</SelectItem>
                <SelectItem value=">=">is at least (≥)</SelectItem>
                <SelectItem value="<=">is at most (≤)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Right operand - only for non-boolean */}
        {!isBooleanCheck && (
          <div>
            <label className="text-xs font-medium mb-1.5 block">Value</label>
            <TemplateInput
              value={String(cond.right.literalValue || "")}
              onChange={(val) =>
                onItemChange({
                  ...cond,
                  right: { type: "literal", literalType: "string", literalValue: val },
                })
              }
              maxLength={500}
              placeholder={context === "success_expression" ? "value" : "value or {{variable}}"}
              rows={1}
              maxRows={1}
              availableVariables={context === "success_expression" ? [] : availableVariables}
              error={errors.right}
            />
          </div>
        )}
      </div>
    );
  };

  const fields: FieldDefinition<Condition>[] = [
    {
      key: "left", // This is a dummy key since we render everything in custom
      label: "",
      type: "custom",
      render: renderConditionFields,
    },
  ];

  return (
    <div className="space-y-2">
      <ListEditor
        items={expression.conditions}
        onChange={handleConditionsChange}
        fields={fields}
        createEmpty={createEmptyCondition}
        renderSummary={(condition) => {
          const summary = formatConditionSummary(condition);
          return (
            <span className="text-xs font-mono" title={summary && summary.length > 16 ? summary : undefined}>
              {summary || (
                <span className="text-muted-foreground">Empty condition</span>
              )}
            </span>
          );
        }}
        renderBetween={(index, item, _nextItem, handleUpdate) => (
          <Select
            value={item.logicalOperator || "AND"}
            onValueChange={(op: LogicalOperator) =>
              handleUpdate(index, { logicalOperator: op })
            }
          >
            <SelectTrigger className="w-20 h-7 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="AND">AND</SelectItem>
              <SelectItem value="OR">OR</SelectItem>
            </SelectContent>
          </Select>
        )}
        maxItems={MAX_CONDITIONS}
        addLabel="Add Condition"
        context={{ context, availableVariables }}
        editorSide="left"
        editorWidth={300}
      />

      {error && <p className="text-sm text-destructive mt-1">{error}</p>}
    </div>
  );
}
