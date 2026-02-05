import { cn } from "@/lib/utils";

interface CharacterCounterProps {
  current: number;
  max: number;
  className?: string;
}

export function CharacterCounter({
  current,
  max,
  className,
}: CharacterCounterProps) {
  const percentage = (current / max) * 100;
  const isNearLimit = percentage >= 90;
  const isOverLimit = current > max;

  return (
    <div
      className={cn(
        "text-xs",
        isOverLimit
          ? "text-destructive font-medium"
          : isNearLimit
          ? "text-amber-600"
          : "text-muted-foreground",
        className
      )}
    >
      {current} / {max}
    </div>
  );
}
