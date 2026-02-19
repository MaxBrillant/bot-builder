import * as React from "react";
import { Input } from "./input";
import { cn } from "@/lib/utils";

export interface AutoResizeTextareaProps
  extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, "rows"> {
  minRows?: number;
  maxRows?: number;
}

const AutoResizeTextarea = React.forwardRef<
  HTMLTextAreaElement | HTMLInputElement,
  AutoResizeTextareaProps
>(({ className, minRows = 1, maxRows = 10, onChange, ...props }, ref) => {
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);
  const inputRef = React.useRef<HTMLInputElement | null>(null);

  // Single-line mode renders as input
  const isSingleLine = maxRows === 1;

  // Combine refs
  React.useImperativeHandle(ref, () =>
    isSingleLine ? inputRef.current! : textareaRef.current!
  );

  const calculateHeight = React.useCallback(
    (target: HTMLTextAreaElement): number => {
      const styles = window.getComputedStyle(target);

      // Get line height (fallback to 1.5x font size if "normal")
      let lineHeight = parseInt(styles.lineHeight);
      if (isNaN(lineHeight) || styles.lineHeight === "normal") {
        const fontSize = parseInt(styles.fontSize || "14");
        lineHeight = Math.floor(fontSize * 1.5);
      }

      const paddingTop = parseInt(styles.paddingTop || "0");
      const paddingBottom = parseInt(styles.paddingBottom || "0");
      const borderTop = parseInt(styles.borderTopWidth || "0");
      const borderBottom = parseInt(styles.borderBottomWidth || "0");

      // Calculate min and max heights
      const minHeight = lineHeight * minRows + paddingTop + paddingBottom + borderTop + borderBottom;
      const maxHeight = lineHeight * maxRows + paddingTop + paddingBottom + borderTop + borderBottom;

      // Temporarily set height to auto to get accurate scrollHeight
      const originalHeight = target.style.height;
      target.style.height = 'auto';
      const naturalHeight = target.scrollHeight + borderTop + borderBottom;
      target.style.height = originalHeight;

      return Math.max(minHeight, Math.min(maxHeight, naturalHeight));
    },
    [minRows, maxRows]
  );

  const updateHeight = React.useCallback(() => {
    const target = textareaRef.current;
    if (!target) return;

    const newHeight = calculateHeight(target);
    target.style.height = `${newHeight}px`;
  }, [calculateHeight]);

  const handleTextareaChange = React.useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange?.(e);
      // Update height after React processes the value change
      requestAnimationFrame(updateHeight);
    },
    [onChange, updateHeight]
  );

  // Update height on mount and when value changes externally
  React.useLayoutEffect(() => {
    if (!isSingleLine) {
      updateHeight();
    }
  }, [props.value, updateHeight, isSingleLine]);

  // Render as input for single-line mode
  if (isSingleLine) {
    return (
      <Input
        className={className}
        ref={inputRef}
        onChange={onChange as unknown as React.ChangeEventHandler<HTMLInputElement>}
        value={props.value as string}
        defaultValue={props.defaultValue as string}
        placeholder={props.placeholder}
        disabled={props.disabled}
        readOnly={props.readOnly}
        maxLength={props.maxLength}
        autoFocus={props.autoFocus}
        autoComplete={props.autoComplete}
        name={props.name}
        id={props.id}
        aria-invalid={props["aria-invalid"]}
        aria-describedby={props["aria-describedby"]}
        onKeyDown={props.onKeyDown as unknown as React.KeyboardEventHandler<HTMLInputElement>}
        onFocus={props.onFocus as unknown as React.FocusEventHandler<HTMLInputElement>}
        onBlur={props.onBlur as unknown as React.FocusEventHandler<HTMLInputElement>}
      />
    );
  }

  return (
    <textarea
      className={cn(
        "flex w-full rounded-md border border-input bg-muted px-3 py-2 text-base shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
        "overflow-y-auto resize-none",
        className
      )}
      ref={textareaRef}
      onChange={handleTextareaChange}
      {...props}
    />
  );
});

AutoResizeTextarea.displayName = "AutoResizeTextarea";

export { AutoResizeTextarea };
