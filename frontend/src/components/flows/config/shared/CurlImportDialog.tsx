/**
 * cURL Import Dialog
 *
 * Allows users to paste a cURL command and auto-populate API_ACTION node fields
 */

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { parseCurlCommand } from "@/utils/curlParser";
import type { APIActionNodeConfig, HTTPMethod, APIHeader } from "@/lib/types";

interface CurlImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport: (config: APIActionNodeConfig) => void;
}

export function CurlImportDialog({
  open,
  onOpenChange,
  onImport,
}: CurlImportDialogProps) {
  const [curlCommand, setCurlCommand] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleImport = async () => {
    const trimmedCommand = curlCommand.trim();

    if (!trimmedCommand) {
      setError("Please enter a cURL command");
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      // Parse curl command using custom parser
      const parsed = parseCurlCommand(trimmedCommand);

      // Validate method
      const validMethods: HTTPMethod[] = ["GET", "POST", "PUT", "DELETE", "PATCH"];
      const method = parsed.method.toUpperCase() as HTTPMethod;

      if (!validMethods.includes(method)) {
        throw new Error(`Unsupported HTTP method: ${parsed.method}. Supported: GET, POST, PUT, DELETE, PATCH`);
      }

      // Convert headers object to array
      const headers: APIHeader[] = Object.entries(parsed.headers).map(([name, value]) => ({
        name,
        value,
      }));

      // Build API Action config
      const config: APIActionNodeConfig = {
        type: "API_ACTION",
        request: {
          method,
          url: parsed.url,
          headers: headers.length > 0 ? headers : undefined,
          body: parsed.body,
        },
      };

      // Import successful
      onImport(config);
      onOpenChange(false);
      setCurlCommand("");
      setError(null);

      // Show success message with reminder about variables
      toast.success("cURL imported successfully", {
        description: "Replace literal values with {{variables}} where needed",
      });
    } catch (err: any) {
      const errorMessage = err.message || "Failed to parse cURL command";
      setError(errorMessage);
      console.error("cURL parsing error:", err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancel = () => {
    onOpenChange(false);
    setCurlCommand("");
    setError(null);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Import from cURL</DialogTitle>
          <DialogDescription>
            Paste a cURL command to automatically populate the API action configuration.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* Textarea for curl command */}
          <div className="space-y-2">
            <Textarea
              placeholder={`curl -X POST https://api.example.com/users \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer token123" \\
  -d '{"name": "John", "email": "john@example.com"}'`}
              value={curlCommand}
              onChange={(e) => {
                setCurlCommand(e.target.value);
                setError(null);
              }}
              disabled={isProcessing}
              className="min-h-[200px] font-mono text-sm"
            />
          </div>

          {/* Error display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Action buttons */}
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              onClick={handleCancel}
              disabled={isProcessing}
            >
              Cancel
            </Button>
            <Button
              onClick={handleImport}
              disabled={isProcessing || !curlCommand.trim()}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Importing...
                </>
              ) : (
                "Import"
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
