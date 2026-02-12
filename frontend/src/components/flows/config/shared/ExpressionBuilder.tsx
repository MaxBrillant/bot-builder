import { useEffect, useState, useRef, Fragment } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus } from "lucide-react";
import { ConditionRow } from "./ConditionRow";
import type {
  ExpressionDefinition,
  Condition,
  LogicalOperator,
  ExpressionContext,
} from "@/lib/expressionBuilderTypes";
import { isBooleanMethod } from "@/lib/expressionBuilderTypes";
import { parseExpression } from "@/lib/expressionParser";
import { serializeExpression } from "@/lib/expressionSerializer";

const MAX_CONDITIONS = 8;

interface ExpressionBuilderProps {
  value: string;
  onChange: (value: string) => void;
  context: ExpressionContext;
  availableVariables?: string[];
  error?: string;
}

interface ConditionErrors {
  left?: string;
  operator?: string;
  right?: string;
}

function validateCondition(condition: Condition): ConditionErrors {
  const errors: ConditionErrors = {};

  // Check left operand
  if (!condition.left.path || condition.left.path.trim() === "") {
    errors.left = "Required";
  }

  // Check right operand (only for non-boolean methods)
  if (!isBooleanMethod(condition.left.path)) {
    const rightValue = condition.right.literalValue;
    if (rightValue === undefined || rightValue === null || String(rightValue).trim() === "") {
      errors.right = "Required";
    }
  }

  return errors;
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

  // Sync with external value changes
  useEffect(() => {
    if (isInternalUpdate.current) {
      isInternalUpdate.current = false;
      return;
    }
    setExpression(parseExpression(value));
  }, [value]);

  const update = (newExpression: ExpressionDefinition) => {
    setExpression(newExpression);
    const serialized = serializeExpression(newExpression);
    // Only call onChange if the serialized value actually changed
    if (serialized !== value) {
      isInternalUpdate.current = true;
      onChange(serialized);
    }
  };

  const addCondition = () => {
    if (expression.conditions.length >= MAX_CONDITIONS) return;
    update({
      conditions: [
        ...expression.conditions,
        {
          left: { type: "variable", path: "" },
          operator: "==",
          right: { type: "literal", literalType: "string", literalValue: "" },
        },
      ],
    });
  };

  const updateCondition = (index: number, condition: Condition) => {
    const newConditions = [...expression.conditions];
    newConditions[index] = condition;
    update({ conditions: newConditions });
  };

  const deleteCondition = (index: number) => {
    update({ conditions: expression.conditions.filter((_, i) => i !== index) });
  };

  const updateLogicalOperator = (index: number, op: LogicalOperator) => {
    const newConditions = [...expression.conditions];
    newConditions[index] = { ...newConditions[index], logicalOperator: op };
    update({ conditions: newConditions });
  };

  // Determine if we should show headers (when there are non-boolean conditions)
  const hasNonBooleanConditions = expression.conditions.some(
    (c) => !c.left.path.endsWith("()")
  );

  return (
    <div className="space-y-2">
      {/* Column headers */}
      {expression.conditions.length > 0 && hasNonBooleanConditions && (
        <div className="grid grid-cols-[1fr_5rem_1fr_auto] gap-2 items-start px-1">
          <div className="text-xs font-medium text-muted-foreground">
            Condition
          </div>
          <div className="text-xs font-medium text-muted-foreground">
            Operator
          </div>
          <div className="text-xs font-medium text-muted-foreground">
            Value
          </div>
          <div className="w-9" />
        </div>
      )}

      {/* Condition rows with logical operators between them */}
      {expression.conditions.map((condition, index) => (
        <Fragment key={index}>
          <ConditionRow
            condition={condition}
            onChange={(c) => updateCondition(index, c)}
            onDelete={() => deleteCondition(index)}
            context={context}
            availableVariables={availableVariables}
            errors={validateCondition(condition)}
          />

          {/* Logical operator between rows */}
          {index < expression.conditions.length - 1 && (
            <div className="flex justify-center">
              <Select
                value={condition.logicalOperator || "AND"}
                onValueChange={(op: LogicalOperator) => updateLogicalOperator(index, op)}
              >
                <SelectTrigger className="w-20 h-7 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="AND">AND</SelectItem>
                  <SelectItem value="OR">OR</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </Fragment>
      ))}

      {/* Add button */}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={addCondition}
        disabled={expression.conditions.length >= MAX_CONDITIONS}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Condition
      </Button>

      {error && <p className="text-sm text-destructive mt-1">{error}</p>}
    </div>
  );
}
