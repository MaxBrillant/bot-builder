import { MessageCircle, AlertCircle, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface WhatsAppStatusBadgeProps {
  status?: "DISCONNECTED" | "CONNECTING" | "CONNECTED" | "ERROR";
  phoneNumber?: string;
  className?: string;
}

export default function WhatsAppStatusBadge({
  status = "DISCONNECTED",
  phoneNumber,
  className = "",
}: WhatsAppStatusBadgeProps) {
  // Connected state
  if (status === "CONNECTED") {
    return (
      <Badge
        variant="success"
        className={`text-xs ${className}`}
      >
        <MessageCircle className="w-3 h-3 mr-1" />
        {phoneNumber || "Connected"}
      </Badge>
    );
  }

  // Connecting state (waiting for QR scan)
  if (status === "CONNECTING") {
    return (
      <Badge variant="secondary" className={`text-xs ${className}`}>
        <Clock className="w-3 h-3 mr-1" />
        Connecting...
      </Badge>
    );
  }

  // Error state
  if (status === "ERROR") {
    return (
      <Badge variant="destructive" className={`text-xs ${className}`}>
        <AlertCircle className="w-3 h-3 mr-1" />
        Error
      </Badge>
    );
  }

  // Disconnected state (default)
  return (
    <Badge variant="outline" className={`text-xs ${className}`}>
      <MessageCircle className="w-3 h-3 mr-1" />
      Not Connected
    </Badge>
  );
}
