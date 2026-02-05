import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TemplateInput } from "./TemplateInput";
import { CharacterCounter } from "./CharacterCounter";
import { FieldHelp } from "./FieldHelp";
import { SystemConstraints } from "@/lib/types";
import { cn } from "@/lib/utils";

interface RetryLogicEditorProps {
  maxAttempts: number;
  counterText: string;
  failRoute: string;
  onMaxAttemptsChange: (value: number) => void;
  onCounterTextChange: (value: string) => void;
  onFailRouteChange: (value: string) => void;
  nodes: Array<{ id: string; name: string }>;
  availableVariables: string[];
  errors: Record<string, string>;
}

export function RetryLogicEditor({
  maxAttempts,
  counterText,
  failRoute,
  onMaxAttemptsChange,
  onCounterTextChange,
  onFailRouteChange,
  nodes,
  availableVariables,
  errors,
}: RetryLogicEditorProps) {
  return (
    <div className="space-y-7">
      {/* Max Attempts */}
      <div className="space-y-1">
        <Label htmlFor="max-attempts" className="text-xs">
          Maximum Attempts
        </Label>
        <Input
          id="max-attempts"
          type="number"
          min={1}
          max={10}
          value={maxAttempts}
          onChange={(e) => {
            const value = parseInt(e.target.value) || 1;
            onMaxAttemptsChange(Math.min(Math.max(value, 1), 10));
          }}
          className={cn(errors["maxAttempts"] && "border-destructive")}
        />
        {errors["maxAttempts"] && (
          <p className="text-sm text-destructive">{errors["maxAttempts"]}</p>
        )}
        <FieldHelp
          text="Number of validation retries before failing (1-10)"
          tooltip={
            <>
              <p className="mb-2">
                When a user provides invalid input to a PROMPT node, they'll be
                asked to retry up to this many times before routing to the fail node.
              </p>
              <p className="text-xs font-medium mt-2">Range:</p>
              <p className="mt-1 text-xs">1-10 attempts</p>
            </>
          }
        />
      </div>

      {/* Counter Text */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <Label htmlFor="counter-text" className="text-xs">
            Counter Text Template
          </Label>
          <CharacterCounter
            current={counterText.length}
            max={SystemConstraints.MAX_COUNTER_TEXT_LENGTH}
            className="text-xs"
          />
        </div>
        <TemplateInput
          value={counterText}
          onChange={onCounterTextChange}
          error={errors["counterText"]}
          maxLength={SystemConstraints.MAX_COUNTER_TEXT_LENGTH}
          placeholder="(Attempt {{current_attempt}} of {{max_attempts}})"
          rows={1}
          maxRows={3}
          availableVariables={availableVariables}
          fieldContext="counter_text"
        />
        <FieldHelp
          text="Message shown during retry attempts"
          tooltip={
            <>
              <p className="mb-2">
                This text appears along with the validation error message when
                a user needs to retry their input.
              </p>
              <p className="text-xs font-medium mt-2">Available variables:</p>
              <p className="mt-1 text-xs">
                <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                  {"{{current_attempt}}"}
                </code> - Current attempt number (1, 2, 3...)
              </p>
              <p className="mt-1 text-xs">
                <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                  {"{{max_attempts}}"}
                </code> - Maximum attempts allowed
              </p>
            </>
          }
        />
      </div>

      {/* Fail Route */}
      <div className="space-y-1">
        <Label htmlFor="fail-route" className="text-xs">
          Fail Route
        </Label>
        <Select value={failRoute} onValueChange={onFailRouteChange}>
          <SelectTrigger
            id="fail-route"
            className={cn(errors["failRoute"] && "border-destructive")}
          >
            <SelectValue placeholder="Select a node" />
          </SelectTrigger>
          <SelectContent>
            {nodes.length > 0 &&
              nodes
                .sort((a, b) => a.name.localeCompare(b.name))
                .map((node) => (
                  <SelectItem key={node.id} value={node.id}>
                    {node.name}
                  </SelectItem>
                ))}
          </SelectContent>
        </Select>
        {errors["failRoute"] && (
          <p className="text-sm text-destructive">{errors["failRoute"]}</p>
        )}
        <FieldHelp
          text="Node to navigate to when max attempts exceeded"
          tooltip={
            <>
              <p className="mb-2">
                When a user exceeds the maximum retry attempts, the conversation
                will automatically route to this node.
              </p>
              <p className="text-xs font-medium mt-2">Tip:</p>
              <p className="mt-1 text-xs">
                Usually you'd point this to an END node or an error handling flow.
              </p>
            </>
          }
        />
      </div>
    </div>
  );
}
