import { Label } from "@/components/ui/label";
import { ExpressionInput } from "./ExpressionInput";
import { FieldHelp } from "./FieldHelp";
import { StatusCodesInput } from "./StatusCodesInput";
import type { APISuccessCheck } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";

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
      const hasExpression = newValue.expression && newValue.expression.trim() !== "";
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
      const hasStatusCodes = newValue.status_codes && newValue.status_codes.length > 0;
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
        <ExpressionInput
          value={expression}
          onChange={handleExpressionChange}
          error={errors["success_check.expression"]}
          maxLength={SystemConstraints.MAX_EXPRESSION_LENGTH}
          placeholder="response.body.status == 'success'"
          rows={2}
          maxRows={8}
          context="success_expression"
          availableVariables={availableVariables}
        />
        <FieldHelp
          text="Optional: Check the response data to verify success"
          tooltip={
            <>
              <p className="mb-2">
                Sometimes an API returns status code 200 but includes an error message in the response data. Use this to check the actual response content to ensure the call truly succeeded.
              </p>
              <p className="text-xs font-medium mt-2">When to use this:</p>
              <p className="mt-1 text-xs">
                • API returns 200 but has <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">{`{"error": "something"}`}</code> in the body
              </p>
              <p className="mt-1 text-xs">
                • You need to verify specific data exists in the response
              </p>
              <p className="text-xs font-medium mt-2">Examples:</p>
              <ul className="list-none space-y-1 mt-1 text-xs">
                <li>
                  <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">response.body.status == "success"</code>
                </li>
                <li>
                  <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">response.body.error == null</code>
                </li>
                <li>
                  <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">response.body.data.length {">"} 0</code>
                </li>
              </ul>
              <p className="text-xs font-medium mt-2">Important:</p>
              <p className="mt-1 text-xs">
                When you set both status codes and an expression, BOTH must be true for success. For example, if you specify status codes [200, 201] and expression "response.body.success == true", the call only succeeds if the status is 200 or 201 AND the body has success=true.
              </p>
            </>
          }
        />
      </div>
    </div>
  );
}
