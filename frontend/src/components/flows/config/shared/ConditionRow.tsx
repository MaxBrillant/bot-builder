import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { X } from "lucide-react";
import { LeftOperandSelect } from "./LeftOperandSelect";
import { TemplateInput } from "./TemplateInput";
import { cn } from "@/lib/utils";
import type { Condition, ComparisonOperator, ExpressionContext } from "@/lib/expressionBuilderTypes";
import { isBooleanMethod } from "@/lib/expressionBuilderTypes";

interface ConditionRowProps {
  condition: Condition;
  onChange: (condition: Condition) => void;
  onDelete: () => void;
  context: ExpressionContext;
  availableVariables?: string[];
  errors?: {
    left?: string;
    operator?: string;
    right?: string;
  };
}

export function ConditionRow({
  condition,
  onChange,
  onDelete,
  context,
  availableVariables = [],
  errors = {},
}: ConditionRowProps) {
  const isBooleanCheck = isBooleanMethod(condition.left.path);

  return (
    <div className={cn(
      "grid gap-2 items-start",
      isBooleanCheck
        ? "grid-cols-[1fr_auto]"
        : "grid-cols-[1fr_5rem_1fr_auto]"
    )}>
      {/* Left operand */}
      <div className="min-w-0">
        <LeftOperandSelect
          value={condition.left}
          onChange={(left) => onChange({ ...condition, left })}
          context={context}
          availableVariables={availableVariables}
          error={errors.left}
        />
      </div>

      {/* Operator - hidden for boolean methods */}
      {!isBooleanCheck && (
        <Select
          value={condition.operator}
          onValueChange={(op: ComparisonOperator) => onChange({ ...condition, operator: op })}
        >
          <SelectTrigger className={cn(
            "text-sm",
            errors.operator && "border-destructive"
          )}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="==">equals (=)</SelectItem>
            <SelectItem value="!=">not equal (≠)</SelectItem>
            <SelectItem value=">">more than (&gt;)</SelectItem>
            <SelectItem value="<">less than (&lt;)</SelectItem>
            <SelectItem value=">=">at least (≥)</SelectItem>
            <SelectItem value="<=">at most (≤)</SelectItem>
          </SelectContent>
        </Select>
      )}

      {/* Right operand - hidden for boolean methods */}
      {!isBooleanCheck && (
        <div className="min-w-0">
          <TemplateInput
            value={String(condition.right.literalValue || "")}
            onChange={(value) =>
              onChange({
                ...condition,
                right: { type: "literal", literalType: "string", literalValue: value },
              })
            }
            maxLength={500}
            placeholder={context === "success_expression" ? "value" : "value or {{variable}}"}
            rows={1}
            availableVariables={context === "success_expression" ? [] : availableVariables}
            error={errors.right}
          />
        </div>
      )}

      {/* Delete */}
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onDelete}
        className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive"
      >
        <X className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
