import { Label } from "@/components/ui/label";
import { FieldHelp } from "./FieldHelp";
import { ExpressionBuilder } from "./ExpressionBuilder";
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
              <ExpressionBuilder
                value={value.rule}
                onChange={handleRuleChange}
                error={errors["validation.rule"]}
                context="validation_expression"
                availableVariables={availableVariables}
              />
              <FieldHelp
                text="Build rules to check the user's input"
                tooltip={
                  <>
                    <p className="mb-2">
                      Select what to check from the dropdown and set the expected value.
                    </p>
                    <p className="text-xs font-medium mt-2">Available checks:</p>
                    <ul className="list-none space-y-1 mt-1 text-xs">
                      <li>• <strong>Input contains only letters</strong> - A-Z only</li>
                      <li>• <strong>Input is a number</strong> - Like 42 or -3.5</li>
                      <li>• <strong>Input contains only digits</strong> - 0-9 only</li>
                      <li>• <strong>Input length</strong> - Number of characters</li>
                    </ul>
                    <p className="text-xs font-medium mt-2">Example:</p>
                    <p className="mt-1 text-xs">
                      "Input contains only letters" AND "Input length" is at least 3
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
                text="Text pattern to match the user's input"
                tooltip={
                  <>
                    <p className="mb-2">
                      Define a pattern that the user's input must match exactly. This is useful for validating phone numbers, IDs, or specific formats.
                    </p>
                    <p className="text-xs font-medium mt-2">How it works:</p>
                    <p className="mt-1 text-xs mb-2">
                      The pattern must match the user's ENTIRE input. For example, if you want exactly 10 digits, use <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">[0-9]{"{10}"}</code>.
                    </p>
                    <p className="text-xs font-medium mt-2">Common patterns:</p>
                    <p className="mt-1 text-xs">
                      <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">[0-9]{"{10}"}</code> - Exactly 10 digits (like a phone number)
                    </p>
                    <p className="mt-1 text-xs">
                      <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                        .*@.*
                      </code> - Must contain @ (like an email)
                    </p>
                    <p className="mt-1 text-xs">
                      <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                        [A-Za-z]+
                      </code> - Letters only (one or more)
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
