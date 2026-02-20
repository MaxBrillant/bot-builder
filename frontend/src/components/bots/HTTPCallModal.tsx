import { useState, useEffect, useRef } from "react";
import { Copy, RotateCw, Key, Terminal, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useRegenerateWebhookSecretMutation } from "@/hooks/queries/useBotsQuery";

interface HTTPCallModalProps {
  botId: string;
  botName: string;
  webhookUrl: string;
  webhookSecret: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSecretRegenerated: (newSecret: string) => void;
}

export default function HTTPCallModal({
  botId,
  botName,
  webhookUrl,
  webhookSecret,
  open,
  onOpenChange,
  onSecretRegenerated,
}: HTTPCallModalProps) {
  const [showRegenerateDialog, setShowRegenerateDialog] = useState(false);
  const [copied, setCopied] = useState(false);
  const copyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const regenerateSecretMutation = useRegenerateWebhookSecretMutation();

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setCopied(false);
      setShowRegenerateDialog(false);
    }
  }, [open]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
    };
  }, []);

  const curlCommand = `curl -X POST "${webhookUrl}" \\
  -H "Content-Type: application/json" \\
  -H "X-Webhook-Secret: ${webhookSecret}" \\
  -d '{
    "channel": "http",
    "channel_user_id": "user-123",
    "message_text": "Hello"
  }'`;

  const handleCopyCurl = async () => {
    try {
      await navigator.clipboard.writeText(curlCommand);
      setCopied(true);
      toast.success("Curl command copied!");

      // Clear any existing timeout
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
      copyTimeoutRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy");
    }
  };

  const handleRegenerateSecret = async () => {
    regenerateSecretMutation.mutate(botId, {
      onSuccess: (response) => {
        const newSecret = response.data.webhook_secret;
        onSecretRegenerated(newSecret);
        setShowRegenerateDialog(false);
        toast.success("Webhook secret regenerated");
      },
      onError: () => {
        toast.error("Failed to regenerate webhook secret");
      },
    });
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>HTTP API</DialogTitle>
            <DialogDescription>
              Call {botName} directly via HTTP using the webhook endpoint
            </DialogDescription>
          </DialogHeader>

          <div className="py-4 overflow-hidden">
            {/* Example Request - Code Box */}
            <div className="rounded-lg border bg-zinc-950 overflow-hidden max-w-full">
              <div className="flex items-center justify-between px-4 py-2 bg-zinc-900 border-b border-zinc-800">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-zinc-400" />
                  <span className="text-sm text-zinc-400">Example Request</span>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleCopyCurl}
                  className="h-7 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
                >
                  {copied ? (
                    <>
                      <CheckCircle className="h-3.5 w-3.5 mr-1.5" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 mr-1.5" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
              <pre className="p-4 text-sm font-mono text-zinc-100 whitespace-pre-wrap break-words">
                {curlCommand}
              </pre>
            </div>

            {/* Request Body Format */}
            <div className="space-y-3 mt-6">
              <span className="font-medium text-foreground">Request Body</span>
              <div className="space-y-2">
                <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground">channel</p>
                    <p className="text-sm text-foreground">Identifier for the message source (e.g., "http", "test")</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground">channel_user_id</p>
                    <p className="text-sm text-foreground">Unique identifier for the user</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground">message_text</p>
                    <p className="text-sm text-foreground">The message content</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Response Format */}
            <div className="space-y-3 mt-6">
              <span className="font-medium text-foreground">Response Format (SSE)</span>
              <p className="text-sm text-muted-foreground">The response is a Server-Sent Events stream:</p>
              <div className="rounded-lg border bg-zinc-950 overflow-hidden max-w-full">
                <pre className="p-4 text-sm font-mono text-zinc-100 whitespace-pre-wrap break-words">
{`data: {"message": "Welcome!", "index": 0}

data: {"message": "What is your name?", "index": 1}

data: {"done": true, "session_id": "...", "session_active": true}`}
                </pre>
              </div>
            </div>

            <Separator className="my-6" />

            {/* Webhook Secret */}
            <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
              <Key className="w-5 h-5 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-muted-foreground">Webhook Secret</p>
                <p className="font-mono text-sm text-foreground break-all">{webhookSecret}</p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowRegenerateDialog(true)}
                disabled={regenerateSecretMutation.isPending}
              >
                <RotateCw className="h-4 w-4 mr-2" />
                Regenerate
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Regenerate Confirmation Dialog */}
      <AlertDialog
        open={showRegenerateDialog}
        onOpenChange={setShowRegenerateDialog}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Regenerate Webhook Secret?</AlertDialogTitle>
            <AlertDialogDescription>
              This will invalidate the current secret. Any integrations using
              the old secret will stop working.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={regenerateSecretMutation.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRegenerateSecret}
              disabled={regenerateSecretMutation.isPending}
            >
              {regenerateSecretMutation.isPending && (
                <LoadingSpinner size="sm" variant="light" className="mr-2" />
              )}
              Regenerate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
