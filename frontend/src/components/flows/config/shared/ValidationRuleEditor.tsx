import { Label } from "@/components/ui/label";
import { FieldHelp } from "./FieldHelp";
import { ExpressionInput } from "./ExpressionInput";
import { TemplateInput } from "./TemplateInput";
import type { ValidationRule } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";

interface ValidationRuleEditorProps {
  value?: ValidationRule;
  onChange: (value: ValidationRule | undefined) => void;
  errors?: Record<string, string>;
  availableVariables?: string[];
}

export function ValidationRuleEditor({
  value,
  onChange,
  errors = {},
  availableVariables = [],
}: ValidationRuleEditorProps) {
  const handleRuleChange = (rule: string) => {
    if (value) {
      onChange({ ...value, rule });
    }
  };

  const handleErrorMessageChange = (error_message: string) => {
    if (value) {
      onChange({ ...value, error_message });
    }
  };

  const maxRuleLength =
    value?.type === "REGEX"
      ? SystemConstraints.MAX_REGEX_LENGTH
      : SystemConstraints.MAX_EXPRESSION_LENGTH;

  return (
    <div className="space-y-7">
      {value?.type && (
        <>
          {value.type === "EXPRESSION" ? (
            <div className="space-y-1">
              <Label htmlFor="validation-rule" className="text-xs">
                Validation Rule
              </Label>
              <ExpressionInput
                value={value.rule}
                onChange={handleRuleChange}
                error={errors["validation.rule"]}
                maxLength={maxRuleLength}
                placeholder="e.g., input.isAlpha() && input.length >= 3"
                rows={3}
                context="validation_expression"
                availableVariables={availableVariables}
              />
              <FieldHelp
                text="Use input methods and logic operators"
                tooltip={
                  <>
                    <p className="mb-2">
                      Validate using built-in methods and comparisons.
                    </p>
                    <p className="text-xs font-medium mt-2">Available methods:</p>
                    <p className="mt-1 text-xs">
                      <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">input.isAlpha()</code>,{" "}
                      <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">input.isNumeric()</code>,{" "}
                      <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">input.isDigit()</code>,{" "}
                      <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">input.length</code>
                    </p>
                    <p className="text-xs font-medium mt-2">Example:</p>
                    <p className="mt-1 text-xs">
                      <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                        input.isAlpha() && input.length {">="}3
                      </code>
                    </p>
                  </>
                }
              />
            </div>
          ) : (
            <div className="space-y-1">
              <Label htmlFor="validation-rule" className="text-xs">
                Validation Rule
              </Label>
              <TemplateInput
                value={value.rule}
                onChange={handleRuleChange}
                error={errors["validation.rule"]}
                maxLength={maxRuleLength}
                placeholder="e.g., ^[0-9]{10}$ or ^.{1,{{context.max_length}}}$"
                rows={3}
                availableVariables={availableVariables}
              />
              <FieldHelp
                text="Regex pattern for full string match"
                tooltip={
                  <>
                    <p className="mb-2">
                      Use regex to match specific patterns. Supports template variables for dynamic patterns.
                    </p>
                    <p className="text-xs font-medium mt-2">Important:</p>
                    <p className="mt-1 text-xs mb-2">
                      Patterns match the ENTIRE input from start to finish. No need to add ^ and $ anchors - they're automatic. If you want partial matches, include .* at the start or end.
                    </p>
                    <p className="text-xs font-medium mt-2">Examples:</p>
                    <p className="mt-1 text-xs">
                      <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">[0-9]{"{10}"}</code> - Exactly 10 digits, nothing else
                    </p>
                    <p className="mt-1 text-xs">
                      <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                        .{"{1,"}{"{{context.max_length}}"}{"}"}
                      </code> - Any characters with dynamic length
                    </p>
                    <p className="mt-1 text-xs">
                      <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                        .*@.*
                      </code> - Contains @ symbol anywhere
                    </p>
                  </>
                }
              />
            </div>
          )}

          <div className="space-y-1">
            <Label htmlFor="validation-error-message" className="text-xs">
              Error Message
            </Label>
            <TemplateInput
              value={value.error_message}
              onChange={handleErrorMessageChange}
              error={errors["validation.error_message"]}
              maxLength={SystemConstraints.MAX_ERROR_MESSAGE_LENGTH}
              placeholder="Message shown when validation fails"
              rows={2}
              availableVariables={availableVariables}
            />
            <FieldHelp
              text="Custom error message for validation failure"
              tooltip={
                <>
                  <p className="mb-2">
                    This message is shown when the user's input doesn't match the validation rule. Use template variables to make it dynamic.
                  </p>
                  <p className="text-xs font-medium mt-2">Example:</p>
                  <p className="mt-1 text-xs">
                    Please enter a valid phone number (10 digits)
                  </p>
                </>
              }
            />
          </div>
        </>
      )}
    </div>
  );
}
