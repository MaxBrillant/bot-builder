import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TemplateInput } from "./TemplateInput";
import { CharacterCounter } from "./CharacterCounter";
import { FieldHelp } from "./FieldHelp";
import { SystemConstraints, type VariableInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

interface RetryLogicEditorProps {
  maxAttempts: number;
  counterText: string;
  failRoute: string;
  onMaxAttemptsChange: (value: number) => void;
  onCounterTextChange: (value: string) => void;
  onFailRouteChange: (value: string) => void;
  nodes: Array<{ id: string; name: string }>;
  availableVariables: VariableInfo[];
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
          text="How many chances the user gets before giving up (1-10)"
          tooltip={
            <>
              <p className="mb-2">
                If a user enters something invalid (like letters when you asked for a number), they get this many chances to try again before the bot gives up and moves to the "fail" node.
              </p>
              <p className="text-xs font-medium mt-2">Example:</p>
              <p className="mt-1 text-xs">
                Set to 3 = user gets 3 tries to enter valid input
              </p>
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
          maxRows={1}
          availableVariables={availableVariables}
          fieldContext="counter_text"
        />
        <FieldHelp
          text="Message shown when asking the user to try again"
          tooltip={
            <>
              <p className="mb-2">
                This text appears when a user enters invalid input. You can show them how many tries they have left.
              </p>
              <p className="text-xs font-medium mt-2">You can use:</p>
              <p className="mt-1 text-xs">
                <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                  {"{{current_attempt}}"}
                </code> - Which attempt they're on (1, 2, 3...)
              </p>
              <p className="mt-1 text-xs">
                <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                  {"{{max_attempts}}"}
                </code> - Total attempts allowed
              </p>
              <p className="text-xs font-medium mt-2">Example result:</p>
              <p className="mt-1 text-xs">
                "(Attempt 2 of 3)"
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
        <Select value={failRoute || "__NONE__"} onValueChange={(value) => onFailRouteChange(value === "__NONE__" ? "" : value)}>
          <SelectTrigger
            id="fail-route"
            className={cn(errors["failRoute"] && "border-destructive")}
          >
            <SelectValue placeholder="Select a node" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__NONE__" className="text-muted-foreground">
              None (end conversation)
            </SelectItem>
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
          text="Where to go if the user runs out of attempts"
          tooltip={
            <>
              <p className="mb-2">
                If the user uses all their attempts without entering valid input, the conversation will jump to this node instead of continuing normally.
              </p>
              <p className="text-xs font-medium mt-2">Options:</p>
              <p className="mt-1 text-xs">
                • <strong>None</strong> - End the conversation immediately
              </p>
              <p className="mt-1 text-xs">
                • A TEXT node with an error message
              </p>
              <p className="mt-1 text-xs">
                • A node that loops back to try again
              </p>
            </>
          }
        />
      </div>
    </div>
  );
}
