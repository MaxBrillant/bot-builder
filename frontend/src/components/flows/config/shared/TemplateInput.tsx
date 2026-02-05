import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Popover, PopoverContent, PopoverAnchor } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { useState, useRef, useEffect } from "react";

interface TemplateInputProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  maxLength: number;
  placeholder?: string;
  rows?: number;
  maxRows?: number;
  availableVariables?: string[];
  includeSpecialVariables?: boolean;
  nodeType?: "MESSAGE" | "PROMPT" | "MENU" | "API_ACTION" | "LOGIC_EXPRESSION" | "END";
  fieldContext?: "item_template" | "counter_text" | "default";
}

export function TemplateInput({
  value,
  onChange,
  error,
  maxLength,
  placeholder,
  rows = 1,
  maxRows = 3,
  availableVariables,
  includeSpecialVariables = true,
  nodeType,
  fieldContext = "default",
}: TemplateInputProps) {
  // Safely handle undefined/null availableVariables with nullish coalescing
  const baseVariables = availableVariables ?? [];

  // Build context-aware special variables based on node type and field
  const contextSpecialVariables: string[] = [];

  if (includeSpecialVariables) {
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
  }

  // Combine context-specific special variables with base variables
  const safeAvailableVariables = [...contextSpecialVariables, ...baseVariables];
  const hasError = !!error;

  const textareaRef = useRef<HTMLTextAreaElement | HTMLInputElement>(null);
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

  const filteredVariables = autocompleteState.isOpen
    ? safeAvailableVariables.filter((variable) =>
        variable.toLowerCase().includes(autocompleteState.query.toLowerCase())
      )
    : [];

  const getCursorCoordinates = (
    element: HTMLTextAreaElement | HTMLInputElement,
    position: number
  ): { top: number; left: number } => {
    const { offsetTop, offsetLeft, scrollLeft } = element;

    if (element instanceof HTMLInputElement) {
      const style = getComputedStyle(element);
      const paddingLeft = parseInt(style.paddingLeft);
      const textBeforeCursor = element.value.substring(0, position);

      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      if (context) {
        context.font = `${style.fontSize} ${style.fontFamily}`;
        const textWidth = context.measureText(textBeforeCursor).width;

        return {
          top: offsetTop + element.offsetHeight + 2,
          left: offsetLeft + paddingLeft + textWidth - scrollLeft,
        };
      }
    }

    const div = document.createElement("div");
    const style = getComputedStyle(element);

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
      top: offsetTop + span.offsetTop + 20,
      left: offsetLeft + span.offsetLeft - scrollLeft,
    };

    document.body.removeChild(div);
    return coordinates;
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    const cursorPosition = e.target.selectionStart;

    onChange(newValue);

    const textBeforeCursor = newValue.substring(0, cursorPosition);
    const lastOpenBraces = textBeforeCursor.lastIndexOf("{{");
    const lastCloseBraces = textBeforeCursor.lastIndexOf("}}");

    if (
      lastOpenBraces !== -1 &&
      lastOpenBraces > lastCloseBraces &&
      safeAvailableVariables.length > 0
    ) {
      const query = textBeforeCursor.substring(lastOpenBraces + 2);

      if (!query.includes("}}") && !query.includes("\n")) {
        const coordinates = getCursorCoordinates(e.target, cursorPosition);

        setAutocompleteState({
          isOpen: true,
          query,
          startPos: lastOpenBraces,
          cursorPos: coordinates,
        });
        setHighlightedIndex(0);
        return;
      }
    }

    if (autocompleteState.isOpen) {
      setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
      setHighlightedIndex(0);
    }
  };

  const insertVariable = (variable: string) => {
    if (!textareaRef.current) return;

    const textarea = textareaRef.current;
    const startPos = autocompleteState.startPos;
    const cursorPos = textarea.selectionStart;

    const beforeVariable = value.substring(0, startPos);
    const afterCursor = value.substring(cursorPos ?? 0);
    const newValue = `${beforeVariable}{{${variable}}}${afterCursor}`;

    onChange(newValue);

    const newCursorPos = startPos + variable.length + 4;
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);

    setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
    setHighlightedIndex(0);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (autocompleteState.isOpen && filteredVariables.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlightedIndex(
          highlightedIndex < filteredVariables.length - 1 ? highlightedIndex + 1 : 0
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlightedIndex(
          highlightedIndex > 0 ? highlightedIndex - 1 : filteredVariables.length - 1
        );
      } else if (e.key === "Enter" && highlightedIndex >= 0 && highlightedIndex < filteredVariables.length) {
        e.preventDefault();
        insertVariable(filteredVariables[highlightedIndex]);
      } else if (e.key === "Escape") {
        e.preventDefault();
        setAutocompleteState((prev) => ({ ...prev, isOpen: false }));
        setHighlightedIndex(0);
      }
    }
  };

  useEffect(() => {
    if (rows > 1 && textareaRef.current instanceof HTMLTextAreaElement) {
      const textarea = textareaRef.current;
      textarea.style.height = 'auto';

      const lineHeight = parseInt(getComputedStyle(textarea).lineHeight);
      const minHeight = lineHeight * rows;
      const maxHeight = lineHeight * maxRows;
      const newHeight = Math.max(minHeight, Math.min(textarea.scrollHeight, maxHeight));

      textarea.style.height = `${newHeight}px`;
    }
  }, [value, rows, maxRows]);

  return (
    <Popover open={autocompleteState.isOpen && filteredVariables.length > 0}>
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
            ref={textareaRef as React.RefObject<HTMLTextAreaElement>}
            value={value}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            maxLength={maxLength}
            style={{ overflow: 'hidden' }}
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
        className="w-[250px] p-0"
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
        <div className="max-h-[200px] overflow-y-auto py-1">
          {filteredVariables.map((variable, index) => {
            const isHighlighted = highlightedIndex === index;
            return (
              <div
                key={variable}
                ref={isHighlighted ? highlightedItemRef : null}
                onClick={() => insertVariable(variable)}
                className={cn(
                  "px-3 py-2 cursor-pointer text-sm font-mono",
                  isHighlighted
                    ? "bg-accent text-foreground"
                    : "text-foreground hover:bg-muted/30"
                )}
              >
                {variable}
              </div>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}
