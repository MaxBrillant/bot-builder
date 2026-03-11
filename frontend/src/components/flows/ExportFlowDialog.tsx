import { useState, useMemo, useEffect, useRef } from "react";
import { Copy, Check, Download } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Flow } from "@/lib/types";

interface ExportFlowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  flow: Flow | null;
}

export function ExportFlowDialog({ open, onOpenChange, flow }: ExportFlowDialogProps) {
  const [copied, setCopied] = useState(false);
  const copiedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear the "Copied" timer on unmount to avoid setState on unmounted component
  useEffect(() => {
    return () => {
      if (copiedTimerRef.current !== null) clearTimeout(copiedTimerRef.current);
    };
  }, []);

  // Reset "Copied" state when dialog closes
  useEffect(() => {
    if (!open) {
      if (copiedTimerRef.current !== null) clearTimeout(copiedTimerRef.current);
      setCopied(false);
    }
  }, [open]);

  const exportJson = useMemo(() => {
    if (!flow) return "";
    // Strip backend identity/timestamp fields — only portable definition fields
    const { flow_id: _flowId, bot_id: _botId, created_at: _createdAt, updated_at: _updatedAt, ...definition } = flow;
    return JSON.stringify(definition, null, 2);
  }, [flow]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(exportJson);
      if (copiedTimerRef.current !== null) clearTimeout(copiedTimerRef.current);
      setCopied(true);
      copiedTimerRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access denied or unavailable — do nothing, button stays as "Copy"
    }
  };

  const handleDownload = () => {
    const blob = new Blob([exportJson], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${flow?.name ?? "flow"}.json`;
    // Append to DOM for Firefox compatibility, then remove after click
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Export Flow</DialogTitle>
          <DialogDescription>
            Copy or download the JSON definition for "{flow?.name}".
          </DialogDescription>
        </DialogHeader>

        <Textarea
          readOnly
          value={exportJson}
          className="font-mono text-xs h-80 resize-none"
          onClick={(e) => (e.target as HTMLTextAreaElement).select()}
        />

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={handleCopy} className="gap-2">
            {copied ? (
              <>
                <Check className="w-4 h-4" />
                Copied
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy
              </>
            )}
          </Button>
          <Button onClick={handleDownload} className="gap-2">
            <Download className="w-4 h-4" />
            Download
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
