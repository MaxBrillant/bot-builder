import * as React from "react";
import { cn } from "@/lib/utils";

export interface AutoResizeTextareaProps
  extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, "rows"> {
  minRows?: number;
  maxRows?: number;
}

const AutoResizeTextarea = React.forwardRef<
  HTMLTextAreaElement,
  AutoResizeTextareaProps
>(({ className, minRows = 1, maxRows = 10, onChange, ...props }, ref) => {
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);
  const [height, setHeight] = React.useState<string>('auto');

  // Combine refs
  React.useImperativeHandle(ref, () => textareaRef.current!);

  const updateHeight = React.useCallback(
    (target: HTMLTextAreaElement) => {
      // Reset height to get accurate scrollHeight
      target.style.height = '0px';

      const styles = window.getComputedStyle(target);

      // Get line height
      let lineHeight = parseInt(styles.lineHeight);
      if (isNaN(lineHeight) || styles.lineHeight === "normal") {
        const fontSize = parseInt(styles.fontSize || "14");
        lineHeight = Math.floor(fontSize * 1.25); // 1.25 matches leading-5
      }

      const paddingTop = parseInt(styles.paddingTop || "0");
      const paddingBottom = parseInt(styles.paddingBottom || "0");

      // Calculate min and max heights
      const minHeight = lineHeight * minRows + paddingTop + paddingBottom;
      const maxHeight = lineHeight * maxRows + paddingTop + paddingBottom;

      // Get the natural scrollHeight and clamp it
      const naturalHeight = target.scrollHeight;
      const newHeight = Math.max(minHeight, Math.min(maxHeight, naturalHeight));

      setHeight(`${newHeight}px`);
    },
    [minRows, maxRows]
  );

  const handleChange = React.useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      updateHeight(e.target);
      onChange?.(e);
    },
    [onChange, updateHeight]
  );

  // Update height on mount and when value changes externally
  React.useEffect(() => {
    if (textareaRef.current) {
      updateHeight(textareaRef.current);
    }
  }, [props.value, updateHeight]);

  return (
    <textarea
      className={cn(
        "flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm leading-5 ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 overflow-y-auto resize-none",
        className
      )}
      ref={textareaRef}
      style={{ height }}
      onChange={handleChange}
      {...props}
    />
  );
});

AutoResizeTextarea.displayName = "AutoResizeTextarea";

export { AutoResizeTextarea };
