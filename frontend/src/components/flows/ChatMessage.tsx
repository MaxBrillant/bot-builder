import React from "react";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  message: string;
  isBot: boolean;
  timestamp: Date;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isBot,
  timestamp,
}) => {
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div
      className={cn(
        "flex w-full mb-4",
        isBot ? "justify-start" : "justify-end"
      )}
    >
      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-2 shadow-sm",
          isBot ? "bg-muted text-foreground" : "bg-primary text-primary-foreground"
        )}
      >
        <p className="text-sm whitespace-pre-wrap break-words">{message}</p>
        <p
          className={cn(
            "text-xs mt-1",
            isBot ? "text-muted-foreground" : "opacity-70"
          )}
        >
          {formatTime(timestamp)}
        </p>
      </div>
    </div>
  );
};
