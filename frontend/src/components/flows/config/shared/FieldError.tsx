import { AlertCircle } from "lucide-react";

interface FieldErrorProps {
  error?: string;
}

export function FieldError({ error }: FieldErrorProps) {
  if (!error) return null;

  return (
    <div className="flex items-center gap-2 text-sm text-destructive mt-1">
      <AlertCircle className="h-4 w-4 flex-shrink-0" />
      <span>{error}</span>
    </div>
  );
}
