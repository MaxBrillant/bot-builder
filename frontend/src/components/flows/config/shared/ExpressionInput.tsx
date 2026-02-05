import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Popover, PopoverContent, PopoverAnchor } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { useState, useRef, useEffect } from "react";

export type ExpressionContext =
  | "route_api_action"
  | "route_menu"
  | "route_logic"
  | "route_prompt"
  | "success_expression"
  | "validation_expression";

interface ExpressionInputProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  maxLength: number;
  placeholder?: string;
  rows?: number;
  maxRows?: number;
  context: ExpressionContext;
  availableVariables?: string[];
  onKeyDown?: (e: React.KeyboardEvent) => void;
}

interface Suggestion {
  value: string;
  description: string;
  category: string;
}

// Context-aware suggestion generator
const getContextSuggestions = (
  context: ExpressionContext,
  availableVariables: string[]
): Suggestion[] => {
  const suggestions: Suggestion[] = [];

  // Add context variables
  availableVariables.forEach((varName) => {
    suggestions.push({
      value: `context.${varName}`,
      description: `Flow variable: ${varName}`,
      category: "Variables",
    });
  });

  // Add special variables and keywords based on context
  switch (context) {
    case "route_api_action":
      suggestions.push(
        {
          value: "success",
          description: "API call succeeded",
          category: "API Status",
        },
        {
          value: "error",
          description: "API call failed",
          category: "API Status",
        },
        {
          value: "response.body.",
          description: "Access response body field",
          category: "Response",
        },
        {
          value: "response.status",
          description: "HTTP status code",
          category: "Response",
        },
        {
          value: "response.body.status",
          description: "Status field in body",
          category: "Response",
        },
        {
          value: "response.body.data",
          description: "Data field in body",
          category: "Response",
        }
      );
      break;

    case "route_menu":
      suggestions.push(
        {
          value: "selection",
          description: "Selected menu option number",
          category: "Menu",
        },
        {
          value: "selection == 1",
          description: "Option 1 selected",
          category: "Menu",
        },
        {
          value: "selection == 2",
          description: "Option 2 selected",
          category: "Menu",
        },
        {
          value: "selection >= 1 && selection <= 3",
          description: "Selection in range",
          category: "Menu",
        }
      );
      break;

    case "route_logic":
      suggestions.push(
        {
          value: "context.",
          description: "Access flow variable",
          category: "Variables",
        },
        {
          value: "context.items.length > 0",
          description: "Check array length",
          category: "Variables",
        }
      );
      break;

    case "route_prompt":
      suggestions.push(
        {
          value: "context.",
          description: "Access flow variable (includes saved value)",
          category: "Variables",
        }
      );
      break;

    case "success_expression":
      suggestions.push(
        {
          value: "response.body.",
          description: "Access response body field",
          category: "Response",
        },
        {
          value: "response.status",
          description: "HTTP status code",
          category: "Response",
        },
        {
          value: "response.body.status",
          description: "Status field in body",
          category: "Response",
        },
        {
          value: "response.body.data",
          description: "Data field in body",
          category: "Response",
        },
        {
          value: "response.status == 200",
          description: "Check status code",
          category: "Response",
        },
        {
          value: 'response.body.status == "success"',
          description: "Check body status",
          category: "Response",
        }
      );
      break;

    case "validation_expression":
      suggestions.push(
        {
          value: "input.isAlpha()",
          description: "Check if alphabetic",
          category: "Input Methods",
        },
        {
          value: "input.isNumeric()",
          description: "Check if numeric",
          category: "Input Methods",
        },
        {
          value: "input.isDigit()",
          description: "Check if digits only",
          category: "Input Methods",
        },
        {
          value: "input.length",
          description: "Input length",
          category: "Input Methods",
        },
        {
          value: "input.length >= 3",
          description: "Minimum length check",
          category: "Input Methods",
        },
        {
          value: "input.isAlpha() && input.length >= 3",
          description: "Alphabetic and min length",
          category: "Input Methods",
        },
        {
          value: "context.",
          description: "Access flow variable",
          category: "Variables",
        }
      );
      break;
  }

  // Add common operators and keywords
  if (!context.startsWith("validation")) {
    suggestions.push(
      {
        value: "true",
        description: "Boolean true (default route)",
        category: "Keywords",
      },
      { value: "false", description: "Boolean false", category: "Keywords" },
      { value: "null", description: "Null value", category: "Keywords" },
      { value: "== ", description: "Equals operator", category: "Operators" },
      {
        value: "!= ",
        description: "Not equals operator",
        category: "Operators",
      },
      { value: "> ", description: "Greater than", category: "Operators" },
      { value: "< ", description: "Less than", category: "Operators" },
      {
        value: ">= ",
        description: "Greater than or equal",
        category: "Operators",
      },
      {
        value: "<= ",
        description: "Less than or equal",
        category: "Operators",
      },
      { value: "&& ", description: "Logical AND", category: "Operators" },
      { value: "|| ", description: "Logical OR", category: "Operators" }
    );
  }

  return suggestions;
};

export function ExpressionInput({
  value,
  onChange,
  error,
  maxLength,
  placeholder,
  rows = 2,
  maxRows: _maxRows = 8,
  context,
  availableVariables = [],
  onKeyDown,
}: ExpressionInputProps) {
  const hasError = !!error;

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const highlightedItemRef = useRef<HTMLDivElement>(null);
  const [autocompleteState, setAutocompleteState] = useState({
    isOpen: false,
    query: "",
    startPos: -1,
    cursorPos: { top: 0, left: 0 },
  });

  const [highlightedIndex, setHighlightedIndex] = useState(0);

  // Auto-scroll highlighted item into view
  useEffect(() => {
    if (highlightedItemRef.current) {
      highlightedItemRef.current.scrollIntoView({
        block: "nearest",
        behavior: "smooth",
      });
    }
  }, [highlightedIndex]);

  // Get all suggestions for current context
  const allSuggestions = getContextSuggestions(context, availableVariables);

  // Filter suggestions based on current query
  const filteredSuggestions = autocompleteState.isOpen
    ? allSuggestions.filter(
        (suggestion) =>
          suggestion.value
            .toLowerCase()
            .includes(autocompleteState.query.toLowerCase()) ||
          suggestion.description
            .toLowerCase()
            .includes(autocompleteState.query.toLowerCase())
      )
    : [];

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

  // Detect typing and manage autocomplete state
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    const cursorPosition = e.target.selectionStart;

    onChange(newValue);

    // Trigger autocomplete on space or when starting to type
    const textBeforeCursor = newValue.substring(0, cursorPosition);
    const lastWord = textBeforeCursor.split(/[\s(),;]+/).pop() || "";

    // Show autocomplete if:
    // 1. User just typed a space and we have suggestions
    // 2. User is typing a word that could be a suggestion
    // 3. User typed a dot (for accessing properties)
    if (
      allSuggestions.length > 0 &&
      (lastWord.length > 0 ||
        textBeforeCursor.endsWith(" ") ||
        textBeforeCursor.endsWith("."))
    ) {
      const coordinates = getCursorCoordinates(e.target, cursorPosition);
      setAutocompleteState({
        isOpen: true,
        query: lastWord,
        startPos: cursorPosition - lastWord.length,
        cursorPos: coordinates,
      });
      setHighlightedIndex(0);
      return;
    }

    // Close autocomplete if conditions aren't met
    if (autocompleteState.isOpen) {
      setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
      setHighlightedIndex(0);
    }
  };

  // Insert selected suggestion
  const insertSuggestion = (suggestionValue: string) => {
    if (!textareaRef.current) return;

    const textarea = textareaRef.current;
    const startPos = autocompleteState.startPos;
    const cursorPos = textarea.selectionStart;

    // Replace from start of word to cursor with suggestion
    const beforeWord = value.substring(0, startPos);
    const afterCursor = value.substring(cursorPos);
    const newValue = `${beforeWord}${suggestionValue}${afterCursor}`;

    onChange(newValue);

    // Set cursor position after inserted suggestion
    const newCursorPos = startPos + suggestionValue.length;
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);

    // Close the autocomplete menu
    setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
    setHighlightedIndex(0);
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Handle autocomplete navigation when open
    if (autocompleteState.isOpen && filteredSuggestions.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlightedIndex(
          highlightedIndex < filteredSuggestions.length - 1 ? highlightedIndex + 1 : 0
        );
        return;
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlightedIndex(
          highlightedIndex > 0 ? highlightedIndex - 1 : filteredSuggestions.length - 1
        );
        return;
      } else if (e.key === "Enter" && highlightedIndex >= 0 && highlightedIndex < filteredSuggestions.length) {
        e.preventDefault();
        insertSuggestion(filteredSuggestions[highlightedIndex].value);
        return;
      } else if (e.key === "Escape") {
        e.preventDefault();
        setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
        setHighlightedIndex(0);
        return;
      } else if (e.key === "Tab" && highlightedIndex >= 0 && highlightedIndex < filteredSuggestions.length) {
        e.preventDefault();
        insertSuggestion(filteredSuggestions[highlightedIndex].value);
        return;
      }
    }

    // Pass through to parent onKeyDown for unhandled keys (like Ctrl+Enter)
    onKeyDown?.(e);
  };

  // Group suggestions by category
  const groupedSuggestions = filteredSuggestions.reduce(
    (groups, suggestion) => {
      const category = suggestion.category;
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(suggestion);
      return groups;
    },
    {} as Record<string, Suggestion[]>
  );

  return (
    <Popover open={autocompleteState.isOpen && filteredSuggestions.length > 0}>
      <div className="relative">
        {rows === 1 ? (
          <Input
            ref={textareaRef as any}
            value={value}
            onChange={handleTextChange as any}
            onKeyDown={handleKeyDown as any}
            placeholder={placeholder}
            maxLength={maxLength}
            className={cn(
              "font-mono text-sm",
              hasError && "border-destructive focus-visible:ring-destructive"
            )}
            aria-invalid={hasError}
          />
        ) : (
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={rows}
            maxLength={maxLength}
            className={cn(
              "font-mono text-sm resize-none",
              hasError && "border-destructive focus-visible:ring-destructive"
            )}
            aria-invalid={hasError}
          />
        )}

        <PopoverAnchor asChild>
          <span
            className="absolute pointer-events-none"
            style={{
              top: autocompleteState.cursorPos.top,
              left: autocompleteState.cursorPos.left,
              width: 0,
              height: 0,
            }}
          />
        </PopoverAnchor>

        {hasError && <p className="text-sm text-destructive mt-1">{error}</p>}
      </div>

      <PopoverContent
        className="w-[350px] p-0"
        align="start"
        side="bottom"
        sideOffset={4}
        onOpenAutoFocus={(e) => e.preventDefault()}
        onEscapeKeyDown={() => {
          setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
          setHighlightedIndex(0);
        }}
        onInteractOutside={() => {
          setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
          setHighlightedIndex(0);
        }}
      >
        <div className="max-h-[300px] overflow-y-auto">
          {Object.entries(groupedSuggestions).map(
            ([category, suggestions]) => (
              <div key={category}>
                <div className="px-3 py-1 bg-muted text-xs font-semibold text-muted-foreground sticky top-0">
                  {category}
                </div>
                {suggestions.map((suggestion) => {
                  const globalIndex = filteredSuggestions.indexOf(suggestion);
                  const isHighlighted = highlightedIndex === globalIndex;
                  return (
                    <div
                      key={`${category}-${suggestion.value}`}
                      ref={isHighlighted ? highlightedItemRef : null}
                      onClick={() => insertSuggestion(suggestion.value)}
                      className={cn(
                        "px-3 py-2 cursor-pointer text-sm",
                        isHighlighted
                          ? "bg-accent text-accent-foreground"
                          : "hover:bg-accent/50"
                      )}
                    >
                      <div className="font-mono text-sm font-medium">
                        {suggestion.value}
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {suggestion.description}
                      </div>
                    </div>
                  );
                })}
              </div>
            )
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
