import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface KbdProps {
  children: ReactNode;
  className?: string;
}

export function Kbd({ children, className }: KbdProps) {
  return (
    <kbd
      className={cn(
        "px-1.5 py-1 h-5 bg-transparent text-foreground border border-gray-400 rounded text-xs font-mono flex items-center",
        className
      )}
    >
      {children}
    </kbd>
  );
}
