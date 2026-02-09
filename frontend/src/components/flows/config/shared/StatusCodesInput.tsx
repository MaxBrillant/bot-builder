import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, X } from "lucide-react";
import { FieldHelp } from "./FieldHelp";
import { cn } from "@/lib/utils";

interface StatusCodesInputProps {
  value: number[] | undefined;
  onChange: (value: number[] | undefined) => void;
  error?: string;
  label?: string;
  placeholder?: string;
}

export function StatusCodesInput({
  value = [],
  onChange,
  error,
  label = "Status Codes (Optional)",
  placeholder = "e.g., 200, 201, 204",
}: StatusCodesInputProps) {
  const [input, setInput] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);

  const statusCodes = value || [];

  const handleAdd = () => {
    const trimmed = input.trim();
    if (!trimmed) {
      setInputError("Status code cannot be empty");
      return;
    }

    const code = parseInt(trimmed, 10);
    if (isNaN(code)) {
      setInputError("Status code must be a valid number");
      return;
    }

    if (code < 100 || code > 599) {
      setInputError("Status code must be between 100 and 599");
      return;
    }

    if (statusCodes.includes(code)) {
      setInputError("Status code already added");
      return;
    }

    onChange([...statusCodes, code]);
    setInput("");
    setInputError(null);
  };

  const handleRemove = (code: number) => {
    const newCodes = statusCodes.filter((c) => c !== code);
    onChange(newCodes.length > 0 ? newCodes : undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <div className="space-y-1">
      <Label htmlFor="status-codes" className="text-xs">
        {label}
      </Label>

      <div className="flex gap-2">
        <Input
          id="status-codes"
          type="text"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setInputError(null);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={cn(
            "text-sm",
            (inputError || error) && "border-destructive focus-visible:ring-destructive"
          )}
        />
        <Button
          type="button"
          onClick={handleAdd}
          size="sm"
          className="shrink-0"
        >
          <Plus className="h-4 w-4 mr-1" />
          Add
        </Button>
      </div>

      {inputError && (
        <p className="text-sm text-destructive">{inputError}</p>
      )}
      {error && !inputError && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      {/* Display added status codes */}
      {statusCodes.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-2">
          {statusCodes.map((code) => (
            <Badge
              key={code}
              variant="secondary"
              className="flex items-center gap-1 pl-2 pr-1"
            >
              {code}
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => handleRemove(code)}
                className="ml-1 h-5 w-5 hover:bg-muted"
              >
                <X className="h-3 w-3" />
              </Button>
            </Badge>
          ))}
        </div>
      )}

      <FieldHelp
        text="Which response codes mean the API call worked"
        tooltip={
          <>
            <p className="mb-2">
              APIs return a number code to indicate success or failure. If the API returns one of these codes, the call counts as successful. If no codes are specified, only 200 is considered success.
            </p>
            <p className="text-xs font-medium mt-2">Common success codes:</p>
            <p className="mt-1 text-xs">
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">200</code> - OK (the most common)
            </p>
            <p className="mt-1 text-xs">
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">201</code> - Created (something was created)
            </p>
            <p className="mt-1 text-xs">
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">204</code> - No Content (worked, but no data returned)
            </p>
          </>
        }
      />
    </div>
  );
}
