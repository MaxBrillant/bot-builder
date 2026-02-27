import { useState, useEffect, useRef } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useCombobox } from "downshift";
import type { VariableInfo } from "@/lib/types";

interface JsonBodyEditorProps {
  value: any;
  onChange: (value: any) => void;
  error?: string;
  availableVariables?: VariableInfo[];
  nodeType?: "TEXT" | "PROMPT" | "MENU" | "API_ACTION" | "LOGIC_EXPRESSION" | "END";
  fieldContext?: "item_template" | "counter_text" | "default";
}

export function JsonBodyEditor({
  value,
  onChange,
  error,
  availableVariables = [],
  nodeType,
  fieldContext = "default",
}: JsonBodyEditorProps) {
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [autocompleteState, setAutocompleteState] = useState<{
    isOpen: boolean;
    query: string;
    startPos: number;
    cursorPos: { top: number; left: number };
  }>({
    isOpen: false,
    query: "",
    startPos: -1,
    cursorPos: { top: 0, left: 0 },
  });

  // Safely handle undefined/null availableVariables
  // Extract just the variable names for autocomplete
  const baseVariables = (availableVariables ?? []).map((v) => v.name);

  // Build context-aware special variables based on node type and field
  const contextSpecialVariables: string[] = [];

  // user.* variables are ONLY available in API_ACTION nodes (per backend spec)
  if (nodeType === "API_ACTION") {
    contextSpecialVariables.push("user.channel_id", "user.channel");
  }

  // item.* and index are ONLY available in MENU item_template field
  if (nodeType === "MENU" && fieldContext === "item_template") {
    contextSpecialVariables.push("item", "index");
  }

  // current_attempt and max_attempts are ONLY available in retry_logic counter_text
  if (fieldContext === "counter_text") {
    contextSpecialVariables.push("current_attempt", "max_attempts");
  }

  // Combine context-specific special variables with base variables
  const safeAvailableVariables = [...contextSpecialVariables, ...baseVariables];

  // Filter variables based on current query
  const filteredVariables = autocompleteState.isOpen
    ? safeAvailableVariables.filter((variable) =>
        variable.toLowerCase().includes(autocompleteState.query.toLowerCase())
      )
    : [];

  // Setup downshift combobox
  const {
    isOpen,
    getMenuProps,
    highlightedIndex,
    getItemProps,
    setHighlightedIndex,
  } = useCombobox({
    items: filteredVariables,
    isOpen: autocompleteState.isOpen,
    onIsOpenChange: ({ isOpen }) => {
      if (!isOpen) {
        setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
      }
    },
    onSelectedItemChange: ({ selectedItem }) => {
      if (selectedItem && textareaRef.current) {
        insertVariable(selectedItem);
      }
    },
    itemToString: (item) => item || "",
  });

  // Initialize from value
  useEffect(() => {
    try {
      if (value === undefined || value === null) {
        setJsonText("");
      } else if (typeof value === "string") {
        setJsonText(value);
      } else {
        setJsonText(JSON.stringify(value, null, 2));
      }
    } catch (e) {
      setJsonText("");
    }
  }, [value]);

  // Calculate cursor position in textarea for dropdown positioning
  const getCursorCoordinates = (
    element: HTMLTextAreaElement,
    position: number
  ): { top: number; left: number } => {
    const { offsetTop, offsetLeft, scrollTop, scrollLeft } = element;
    const div = document.createElement("div");
    const style = getComputedStyle(element);

    // Copy relevant styles
    [
      "fontFamily",
      "fontSize",
      "fontWeight",
      "letterSpacing",
      "lineHeight",
      "padding",
      "border",
      "boxSizing",
    ].forEach((prop) => {
      div.style[prop as any] = style[prop as any];
    });

    div.style.position = "absolute";
    div.style.visibility = "hidden";
    div.style.whiteSpace = "pre-wrap";
    div.style.wordWrap = "break-word";
    div.style.width = `${element.clientWidth}px`;

    const textBeforeCursor = element.value.substring(0, position);
    div.textContent = textBeforeCursor;

    const span = document.createElement("span");
    span.textContent = element.value.substring(position) || ".";
    div.appendChild(span);

    document.body.appendChild(div);

    const coordinates = {
      top: offsetTop + span.offsetTop - scrollTop + 20,
      left: offsetLeft + span.offsetLeft - scrollLeft,
    };

    document.body.removeChild(div);
    return coordinates;
  };

  // Insert selected variable
  const insertVariable = (variable: string) => {
    if (!textareaRef.current) return;

    const textarea = textareaRef.current;
    const startPos = autocompleteState.startPos;
    const cursorPos = textarea.selectionStart;

    // Replace from {{ to cursor with complete variable
    const beforeVariable = jsonText.substring(0, startPos);
    const afterCursor = jsonText.substring(cursorPos);
    const newValue = `${beforeVariable}{{${variable}}}${afterCursor}`;

    // Update text and trigger validation
    handleChange(newValue);

    // Set cursor position after inserted variable
    const newCursorPos = startPos + variable.length + 4; // {{ + variable + }}
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);

    // Close the autocomplete menu
    setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
  };

  const handleChange = (text: string) => {
    setJsonText(text);

    // Empty is valid
    if (!text.trim()) {
      setJsonError(null);
      onChange(undefined);
      return;
    }

    // Try to parse JSON to validate it
    try {
      JSON.parse(text);
      setJsonError(null);
      // Pass the raw JSON string (not the parsed object)
      onChange(text);
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : "Invalid JSON format";
      setJsonError(errorMsg);
      // Pass the invalid text so validation can catch it
      onChange(text);
    }
  };

  // Handle text change with autocomplete detection
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    const cursorPosition = e.target.selectionStart;

    handleChange(newValue);

    // Check if we're currently typing a variable
    const textBeforeCursor = newValue.substring(0, cursorPosition);
    const lastOpenBraces = textBeforeCursor.lastIndexOf("{{");
    const lastCloseBraces = textBeforeCursor.lastIndexOf("}}");

    // Only show autocomplete if {{ is after the last }} (or no }} exists)
    if (
      lastOpenBraces !== -1 &&
      lastOpenBraces > lastCloseBraces &&
      safeAvailableVariables.length > 0
    ) {
      const query = textBeforeCursor.substring(lastOpenBraces + 2);

      // Only show if query doesn't contain closing braces or newlines
      if (!query.includes("}}") && !query.includes("\n")) {
        const coordinates = getCursorCoordinates(e.target, cursorPosition);
        setAutocompleteState({
          isOpen: true,
          query,
          startPos: lastOpenBraces,
          cursorPos: coordinates,
        });
        return;
      }
    }

    // Close autocomplete if conditions aren't met
    if (autocompleteState.isOpen) {
      setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (autocompleteState.isOpen && filteredVariables.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        // Move to next item or wrap to first
        const nextIndex =
          highlightedIndex < filteredVariables.length - 1
            ? highlightedIndex + 1
            : 0;
        setHighlightedIndex(nextIndex);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        // Move to previous item or wrap to last
        const prevIndex =
          highlightedIndex > 0
            ? highlightedIndex - 1
            : filteredVariables.length - 1;
        setHighlightedIndex(prevIndex);
      } else if (e.key === "Enter" && highlightedIndex !== -1) {
        e.preventDefault();
        insertVariable(filteredVariables[highlightedIndex]);
      } else if (e.key === "Escape") {
        e.preventDefault();
        setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
      }
    }
  };

  const hasError = error || jsonError;

  return (
    <div className="relative">
      <Textarea
        ref={textareaRef}
        value={jsonText}
        onChange={handleTextChange}
        onKeyDown={handleKeyDown}
        placeholder={`{"key": "value", "user": "{{user_name}}"}`}
        className={cn(
          "min-h-[200px] font-mono text-sm",
          hasError && "border-destructive"
        )}
      />

      {/* Autocomplete Dropdown */}
      {isOpen && filteredVariables.length > 0 && (
        <div
          {...getMenuProps()}
          className="absolute z-50 min-w-[200px] max-w-[300px] bg-background border border-border rounded-md shadow-lg overflow-hidden"
          style={{
            top: `${autocompleteState.cursorPos.top}px`,
            left: `${autocompleteState.cursorPos.left}px`,
          }}
        >
          <div className="max-h-[200px] overflow-y-auto py-1">
            {filteredVariables.map((variable, index) => (
              <div
                key={variable}
                {...getItemProps({ item: variable, index })}
                className={cn(
                  "px-3 py-2 cursor-pointer text-sm font-mono",
                  highlightedIndex === index
                    ? "bg-accent text-foreground"
                    : "text-foreground hover:bg-muted/30"
                )}
              >
                {variable}
              </div>
            ))}
          </div>
        </div>
      )}

      {hasError && (
        <p className="text-sm text-destructive mt-1">
          {jsonError || error}
        </p>
      )}
    </div>
  );
}
