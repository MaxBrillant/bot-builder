import React, { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { X, RotateCcw, ChevronRight } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { useAuth } from "@/contexts/AuthContext";
import { sendTestMessage } from "@/lib/api";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  text: string;
  isBot: boolean;
  timestamp: Date;
}

interface ChatSimulatorProps {
  botId?: string;
  flowId?: string;
  webhookSecret?: string;
  onClose?: () => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  bot?: any;
  flow?: any;
  flows?: any[];
  flowUpdateTimestamp?: number; // Track when flow was last updated
}

export const ChatSimulator: React.FC<ChatSimulatorProps> = ({
  botId: propBotId,
  flowId: propFlowId,
  webhookSecret: propWebhookSecret,
  onClose: propOnClose,
  open,
  onOpenChange,
  bot,
  flow,
  flows = [],
  flowUpdateTimestamp,
}) => {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionTimestamp, setSessionTimestamp] = useState(Date.now());
  const [isTriggersOpen, setIsTriggersOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);

  // Derive actual values from either direct props or bot/flow objects
  const botId = propBotId || bot?.bot_id;
  const flowId = propFlowId || flow?.flow_id;
  const webhookSecret = propWebhookSecret || bot?.webhook_secret;
  const onClose = propOnClose || (() => onOpenChange?.(false));

  // Generate unique channel_user_id for this test session with timestamp
  // This ensures each restart creates a fresh session with latest flow changes
  const channelUserId = `test:${user?.user_id}at${sessionTimestamp}:${botId}:${flowId}`;

  // Auto-scroll to latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-reset session when flow is updated
  useEffect(() => {
    if (flowUpdateTimestamp && messages.length > 0) {
      setMessages([]);
      setSessionTimestamp(Date.now());
      toast.info("Flow updated - conversation reset with latest changes");
    }
  }, [flowUpdateTimestamp]);

  // Auto-focus input when simulator opens
  useEffect(() => {
    if (open) {
      const timer = setTimeout(() => {
        chatInputRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [open]);

  // Auto-focus input after bot responds
  useEffect(() => {
    if (!isLoading && messages.length > 0) {
      const timer = setTimeout(() => {
        chatInputRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isLoading, messages.length]);

  // Handle Escape key to close chat simulator
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && onOpenChange) {
        event.preventDefault();
        onOpenChange(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onOpenChange]);

  const handleSendMessage = async (messageText: string) => {
    // Check if webhook secret exists
    if (!webhookSecret) {
      toast.error("Bot has no webhook secret configured");
      return;
    }

    // Add user message to chat
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      text: messageText,
      isBot: false,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    setIsLoading(true);

    try {
      // Send message to bot webhook
      const response = await sendTestMessage(
        botId,
        webhookSecret,
        channelUserId,
        messageText
      );

      // Check for error response from webhook
      if (response.data.status === "error" && response.data.error) {
        const errorMessage: Message = {
          id: `bot-${Date.now()}`,
          text: response.data.error,
          isBot: true,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } else {
        // Add bot responses to chat (each message as separate bubble)
        const botMessages = response.data.messages || [];
        if (botMessages.length === 0) {
          const noResponseMessage: Message = {
            id: `bot-${Date.now()}`,
            text: "No response from bot",
            isBot: true,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, noResponseMessage]);
        } else {
          const newBotMessages: Message[] = botMessages.map((text: string, index: number) => ({
            id: `bot-${Date.now()}-${index}`,
            text,
            isBot: true,
            timestamp: new Date(),
          }));
          setMessages((prev) => [...prev, ...newBotMessages]);
        }
      }
    } catch (error: unknown) {
      console.error("Failed to send message:", error);
      const errorMessage = getErrorMessage(error) || "Failed to send message to bot";
      toast.error(errorMessage);

      // Add error message to chat
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        text: `Error: ${errorMessage}`,
        isBot: true,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRestart = () => {
    setMessages([]);
    setSessionTimestamp(Date.now()); // Generate new session ID for fresh session
    toast.success("Conversation restarted");

    // Focus input after restart
    setTimeout(() => {
      chatInputRef.current?.focus();
    }, 100);
  };

  // Don't render if not open
  if (!open) {
    return null;
  }

  return (
    <div className="fixed right-0 top-0 h-screen w-[400px] z-40 border-l border-border bg-background shadow-xl">
      <Card className="flex flex-col h-full w-full bg-background border-0 rounded-none shadow-none">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle>Chat Simulator</CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="icon-sm"
              onClick={handleRestart}
              title="Restart Conversation"
            >
              <RotateCcw className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="icon-sm"
              onClick={onClose}
              title="Close"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>

        {/* Available Trigger Keywords */}
        <div className="px-6 pb-3">
          <Collapsible open={isTriggersOpen} onOpenChange={setIsTriggersOpen}>
            <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors w-full">
              <ChevronRight className={cn("h-4 w-4 transition-transform", isTriggersOpen && "rotate-90")} />
              <span>Available Triggers</span>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2">
              {flows.length === 0 ? (
                <p className="text-xs text-muted-foreground ml-6">No flows configured yet</p>
              ) : (
                <div className="ml-6 border border-border rounded-md overflow-hidden">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border bg-muted/50">
                        <th className="text-left font-medium px-2 py-1.5">Flow</th>
                        <th className="text-left font-medium px-2 py-1.5">Triggers</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {flows.map((f) => (
                        <tr key={f.flow_id} className="hover:bg-muted/50 transition-colors">
                          <td className="px-2 py-1.5 font-medium text-foreground">
                            <div className="truncate max-w-[120px]" title={f.name}>
                              {f.name}
                            </div>
                          </td>
                          <td className="px-2 py-1.5">
                            <div className="flex flex-wrap gap-1">
                              {f.trigger_keywords?.length > 0 ? (
                                f.trigger_keywords.map((keyword: string) => (
                                  <Badge key={keyword} variant="secondary" className="text-xs py-0 px-1.5 h-5">
                                    {keyword}
                                  </Badge>
                                ))
                              ) : (
                                <span className="text-muted-foreground">No triggers</span>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CollapsibleContent>
          </Collapsible>
        </div>

        {/* Edge-to-edge chat messages - intentional p-0 for full-width UX */}
        <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto px-4 py-2">
            {messages.length === 0 && (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                Start a conversation by typing a message below
              </div>
            )}

            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg.text}
                isBot={msg.isBot}
                timestamp={msg.timestamp}
              />
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 text-muted-foreground mb-4">
                <LoadingSpinner size="sm" />
                <span className="text-sm">Bot is typing...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <ChatInput ref={chatInputRef} onSend={handleSendMessage} disabled={isLoading} />
        </CardContent>
      </Card>
    </div>
  );
};
