import { useState, useEffect, useRef, useCallback } from "react";
import {
  MessageCircle,
  Trash,
  Phone,
  Clock,
  AlertCircle,
  RefreshCw,
  CheckCircle,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { IconBadge } from "@/components/ui/icon-badge";
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
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import {
  connectWhatsApp,
  disconnectWhatsApp,
  reconnectWhatsApp,
  getWhatsAppStatus,
} from "@/lib/api";
import type { WhatsAppStatus } from "@/lib/types";

function getErrorMessage(err: unknown, fallback: string): string {
  if (
    err &&
    typeof err === "object" &&
    "response" in err &&
    err.response &&
    typeof err.response === "object" &&
    "data" in err.response &&
    err.response.data &&
    typeof err.response.data === "object" &&
    "detail" in err.response.data
  ) {
    return String(err.response.data.detail);
  }
  return fallback;
}

interface WhatsAppConnectionModalProps {
  botId: string;
  botName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConnected?: () => void;
}

/**
 * WhatsApp Connection Modal
 *
 * QR code is returned immediately from connect/reconnect endpoints.
 * Polls status to detect when user scans QR.
 */
export default function WhatsAppConnectionModal({
  botId,
  botName,
  open,
  onOpenChange,
  onConnected,
}: WhatsAppConnectionModalProps) {
  const [status, setStatus] = useState<WhatsAppStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [timeLeft, setTimeLeft] = useState(120);
  const [error, setError] = useState<string | null>(null);

  const statusPollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setError(null);
      const response = await getWhatsAppStatus(botId);
      setStatus((prev) => ({
        ...response.data,
        qr_code: prev?.qr_code // Preserve QR from connect response
      }));
    } catch (err) {
      console.error("Failed to fetch WhatsApp status:", err);
      setError(getErrorMessage(err, "Failed to fetch status"));
      setStatus((prev) => prev ?? { status: "DISCONNECTED" });
    }
  }, [botId]);

  // Fetch status on open, reset on close
  useEffect(() => {
    if (open) {
      fetchStatus();
    } else {
      setStatus(null);
      setError(null);
      setTimeLeft(120);
    }
  }, [open, fetchStatus]);

  // Poll status while connecting
  useEffect(() => {
    if (!open || !status || status.status !== "CONNECTING") {
      if (statusPollIntervalRef.current) {
        clearInterval(statusPollIntervalRef.current);
        statusPollIntervalRef.current = null;
      }
      return;
    }

    statusPollIntervalRef.current = setInterval(fetchStatus, 3000);

    return () => {
      if (statusPollIntervalRef.current) {
        clearInterval(statusPollIntervalRef.current);
        statusPollIntervalRef.current = null;
      }
    };
  }, [open, status?.status, fetchStatus]);

  // QR countdown timer
  useEffect(() => {
    if (!open || !status || status.status !== "CONNECTING") {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
      return;
    }

    timerIntervalRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          if (timerIntervalRef.current) {
            clearInterval(timerIntervalRef.current);
            timerIntervalRef.current = null;
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
    };
  }, [open, status?.status]);

  // Notify on connection success
  useEffect(() => {
    if (status?.status === "CONNECTED" && onConnected) {
      onConnected();
      toast.success("WhatsApp connected successfully!");
    }
  }, [status?.status, onConnected]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (statusPollIntervalRef.current) clearInterval(statusPollIntervalRef.current);
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, []);

  const handleConnect = async () => {
    try {
      setIsConnecting(true);
      setError(null);
      setTimeLeft(120);

      const response = await connectWhatsApp(botId);
      setStatus(response.data);

      if (response.data.qr_code) {
        toast.success("QR code ready - scan with WhatsApp");
      } else {
        toast.warning("QR code not available. Please try again.");
        setError("QR code not returned in response");
      }
    } catch (err: unknown) {
      const message = getErrorMessage(err, "Failed to connect");
      console.error("Failed to connect WhatsApp:", err);
      setError(message);
      toast.error(message);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      setIsDisconnecting(true);
      setError(null);
      await disconnectWhatsApp(botId);
      setStatus({ status: "DISCONNECTED" });
      toast.success("WhatsApp disconnected");
      setShowDeleteConfirm(false);
    } catch (err: unknown) {
      const message = getErrorMessage(err, "Failed to disconnect");
      console.error("Failed to disconnect WhatsApp:", err);
      setError(message);
      toast.error(message);
    } finally {
      setIsDisconnecting(false);
    }
  };

  const handleRefreshQR = async () => {
    try {
      setIsLoading(true);
      setError(null);
      setTimeLeft(120);

      const response = await reconnectWhatsApp(botId);
      setStatus(response.data);

      if (response.data.qr_code) {
        toast.success("New QR code generated");
      } else {
        toast.warning("QR code not available");
        setError("QR code not returned in response");
      }
    } catch (err: unknown) {
      const message = getErrorMessage(err, "Failed to refresh QR code");
      console.error("Failed to refresh QR code:", err);
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  // Loading state
  if (isLoading || (!status && open)) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl">
          <div className="flex flex-col items-center justify-center py-6">
            <LoadingSpinner size="lg" className="mb-4" />
            <p className="text-sm text-muted-foreground">Loading WhatsApp status...</p>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  // Disconnected state
  if (status?.status === "DISCONNECTED") {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Connect WhatsApp</DialogTitle>
            <DialogDescription>
              Connect {botName} to WhatsApp to send and receive messages
            </DialogDescription>
          </DialogHeader>

          <div className="py-8">
            <div className="flex flex-col items-center justify-center">
              <div className="w-20 h-20 bg-accent rounded-full flex items-center justify-center mb-6">
                <MessageCircle className="w-10 h-10 text-success" />
              </div>

              <h3 className="text-lg font-semibold text-foreground mb-2">
                Ready to Connect WhatsApp
              </h3>
              <p className="text-sm text-muted-foreground text-center mb-6 max-w-md">
                Click the button below to generate a QR code. Scan it with your
                WhatsApp mobile app to link this bot.
              </p>

              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button onClick={handleConnect} disabled={isConnecting} size="lg">
                {isConnecting ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Generating QR Code...
                  </>
                ) : (
                  <>
                    <MessageCircle className="w-5 h-5 mr-2" />
                    Connect WhatsApp
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  // Connecting state - show QR code
  if (status?.status === "CONNECTING") {
    const qrExpired = timeLeft === 0;

    return (
      <>
        <Dialog open={open} onOpenChange={onOpenChange}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Scan QR Code</DialogTitle>
              <DialogDescription>
                Connect {botName} to WhatsApp by scanning this QR code
              </DialogDescription>
            </DialogHeader>

            <div className="py-4">
              {qrExpired ? (
                <div className="flex flex-col items-center justify-center py-8">
                  <AlertCircle className="w-12 h-12 text-destructive mb-4" />
                  <p className="text-sm text-muted-foreground mb-2">QR code expired</p>
                  <p className="text-xs text-muted-foreground mb-4">
                    QR codes expire after 2 minutes for security
                  </p>
                  <Button onClick={handleRefreshQR} size="sm">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Generate New QR Code
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-4">
                  <div className="bg-background p-4 rounded-lg border-2 border-border mb-4">
                    {status.qr_code ? (
                      <img
                        src={status.qr_code}
                        alt="WhatsApp QR Code"
                        className="w-64 h-64"
                      />
                    ) : (
                      <div className="w-64 h-64 flex flex-col items-center justify-center bg-muted rounded">
                        <LoadingSpinner size="md" className="mb-3" />
                        <p className="text-xs text-muted-foreground">Waiting for QR code...</p>
                      </div>
                    )}
                  </div>

                  <div className="text-center mb-4">
                    <p className="text-sm font-medium text-foreground mb-1">
                      {status.qr_code ? "Scan with WhatsApp" : "Generating QR Code"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {status.qr_code ? (
                        <>
                          Open WhatsApp → <span className="font-semibold">Settings → Linked Devices</span>
                        </>
                      ) : (
                        "QR code will appear shortly..."
                      )}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
                      <span>{status.qr_code ? "Waiting for scan..." : "Generating..."}</span>
                    </div>
                    {status.qr_code && (
                      <>
                        <span>•</span>
                        <span>
                          Expires in {Math.floor(timeLeft / 60)}:{String(timeLeft % 60).padStart(2, "0")}
                        </span>
                      </>
                    )}
                  </div>

                  {status.qr_code && (
                    <Button onClick={handleRefreshQR} variant="ghost" size="sm" className="mt-4">
                      <RefreshCw className="w-3 h-3 mr-1" />
                      Refresh QR Code
                    </Button>
                  )}
                </div>
              )}

              <Separator className="my-6" />

              <div className="flex justify-end">
                <Button onClick={() => setShowDeleteConfirm(true)} variant="outline" size="sm">
                  Cancel Setup
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Cancel Setup?</AlertDialogTitle>
              <AlertDialogDescription>
                This will cancel the WhatsApp setup for {botName}. You can start again anytime.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDisconnect} className="bg-destructive hover:bg-destructive">
                Cancel Setup
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </>
    );
  }

  // Connected state
  if (status?.status === "CONNECTED") {
    return (
      <>
        <Dialog open={open} onOpenChange={onOpenChange}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>WhatsApp Connection</DialogTitle>
              <DialogDescription>Manage WhatsApp connection for {botName}</DialogDescription>
            </DialogHeader>

            <div className="py-4">
              <Alert className="mb-4 border-success bg-accent">
                <div className="flex items-start gap-4">
                  <IconBadge icon={CheckCircle} variant="green" size="lg" />
                  <div className="flex-1 min-w-0">
                    <AlertTitle className="text-foreground mb-1">WhatsApp Connected</AlertTitle>
                    <AlertDescription className="text-foreground">Your bot is connected to WhatsApp</AlertDescription>
                  </div>
                </div>
              </Alert>

              <div className="space-y-3">
                {status.phone_number && (
                  <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                    <Phone className="w-5 h-5 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-muted-foreground">Phone Number</p>
                      <p className="font-medium text-foreground">{status.phone_number}</p>
                    </div>
                  </div>
                )}

                {status.connected_at && (
                  <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                    <Clock className="w-5 h-5 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-muted-foreground">Connected</p>
                      <p className="font-medium text-foreground">
                        {formatDistanceToNow(new Date(status.connected_at), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              <Separator className="my-6" />

              <div className="flex justify-end">
                <Button
                  onClick={() => setShowDeleteConfirm(true)}
                  variant="destructive"
                  disabled={isDisconnecting}
                >
                  {isDisconnecting ? (
                    <>
                      <LoadingSpinner size="sm" variant="light" className="mr-2" />
                      Disconnecting...
                    </>
                  ) : (
                    <>
                      <Trash className="w-4 h-4 mr-2" />
                      Disconnect WhatsApp
                    </>
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Disconnect WhatsApp?</AlertDialogTitle>
              <AlertDialogDescription>
                This will disconnect WhatsApp from {botName}. You'll need to scan a QR code again.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDisconnect} className="bg-destructive hover:bg-destructive">
                Disconnect
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </>
    );
  }

  // Error state
  if (status?.status === "ERROR") {
    return (
      <>
        <Dialog open={open} onOpenChange={onOpenChange}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>WhatsApp Connection Error</DialogTitle>
              <DialogDescription>Failed to connect {botName} to WhatsApp</DialogDescription>
            </DialogHeader>

            <div className="py-4">
              <Alert variant="destructive" className="mb-4">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Connection Error</AlertTitle>
                <AlertDescription>{status.message || "Failed to connect"}</AlertDescription>
              </Alert>

              <div className="flex justify-end gap-2">
                <Button onClick={() => setShowDeleteConfirm(true)} variant="outline">
                  Remove Connection
                </Button>
                <Button onClick={handleConnect}>Try Again</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Remove Connection?</AlertDialogTitle>
              <AlertDialogDescription>
                This will remove the failed WhatsApp connection for {botName}.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDisconnect} className="bg-destructive hover:bg-destructive">
                Remove Connection
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </>
    );
  }

  return null;
}
