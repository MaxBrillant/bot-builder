import { HelpCircle } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface FieldHelpProps {
  text: string;
  tooltip: string | React.ReactNode;
}

export function FieldHelp({ text, tooltip }: FieldHelpProps) {
  return (
    <div className="flex items-center gap-1.5">
      <p className="text-xs text-muted-foreground">{text}</p>
      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger type="button" className="inline-flex cursor-help">
            <HelpCircle className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground transition-colors" />
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs">
            <div className="text-sm space-y-2">{tooltip}</div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}
