import { Label } from "@/components/ui/label";
import { ExpressionBuilder } from "./ExpressionBuilder";
import { FieldHelp } from "./FieldHelp";
import { StatusCodesInput } from "./StatusCodesInput";
import type { APISuccessCheck } from "@/lib/types";

interface SuccessCheckEditorProps {
  value: APISuccessCheck | undefined;
  onChange: (value: APISuccessCheck | undefined) => void;
  errors?: Record<string, string>;
  availableVariables?: string[];
}

export function SuccessCheckEditor({
  value,
  onChange,
  errors = {},
  availableVariables = [],
}: SuccessCheckEditorProps) {
  const expression = value?.expression ?? "";

  const handleStatusCodesChange = (codes: number[] | undefined) => {
    if (!codes || codes.length === 0) {
      // Remove status_codes from the object
      const newValue = value ? { ...value } : {};
      delete newValue.status_codes;

      // Check if there are any meaningful values left
      const hasExpression =
        newValue.expression && newValue.expression.trim() !== "";
      if (!hasExpression) {
        onChange(undefined);
      } else {
        onChange(newValue);
      }
      return;
    }

    onChange({
      ...value,
      status_codes: codes,
    });
  };

  const handleExpressionChange = (text: string) => {
    if (!text.trim()) {
      // If field is empty and expression doesn't exist, no change needed
      if (!value?.expression) {
        return;
      }

      // Remove expression from the object
      const newValue = value ? { ...value } : {};
      delete newValue.expression;

      // Check if there are any meaningful values left
      const hasStatusCodes =
        newValue.status_codes && newValue.status_codes.length > 0;
      if (!hasStatusCodes) {
        onChange(undefined);
      } else {
        onChange(newValue);
      }
      return;
    }

    // Only call onChange if expression actually changed
    if (text !== value?.expression) {
      onChange({
        ...value,
        expression: text,
      });
    }
  };

  return (
    <div className="space-y-7">
      <StatusCodesInput
        value={value?.status_codes}
        onChange={handleStatusCodesChange}
        error={errors["success_check.status_codes"]}
      />

      <div className="space-y-1">
        <Label htmlFor="success-expression" className="text-xs">
          Expression (Optional)
        </Label>
        <ExpressionBuilder
          value={expression}
          onChange={handleExpressionChange}
          error={errors["success_check.expression"]}
          context="success_expression"
          availableVariables={availableVariables}
        />
        <FieldHelp
          text="Double-check that the API call actually worked"
          tooltip={
            <>
              <p className="mb-2">
                Sometimes an API says "OK" (status 200) but the response
                actually contains an error. This lets you check the response
                content to make sure it really worked.
              </p>
              <p className="text-xs font-medium mt-2">When to use this:</p>
              <ul className="list-none space-y-1 mt-1 text-xs">
                <li>• The API returns 200 but might have an error inside</li>
                <li>• You want to verify the response contains expected data</li>
              </ul>
              <p className="text-xs font-medium mt-2">Example:</p>
              <p className="mt-1 text-xs">
                "Response body status" equals "success"
              </p>
              <p className="text-xs font-medium mt-2">Tip:</p>
              <p className="mt-1 text-xs">
                Select <strong>Custom field</strong> for other response values (e.g. response.body.error)
              </p>
              <p className="text-xs font-medium mt-2">
                With status codes:
              </p>
              <p className="mt-1 text-xs">
                If you set both status codes and an expression, BOTH must pass
                for the API call to count as successful.
              </p>
            </>
          }
        />
      </div>
    </div>
  );
}
