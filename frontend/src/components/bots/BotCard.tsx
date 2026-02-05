import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MoreVertical, Edit, Trash, ArrowRight, Bot as BotIcon, Power, PowerOff } from "lucide-react";
import { Card, CardContent, CardHeader, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { activateBot, deactivateBot } from "@/lib/api";
import WhatsAppStatusBadge from "./WhatsAppStatusBadge";
import type { Bot } from "@/lib/types";

interface BotCardProps {
  bot: Bot;
  onEdit: () => void;
  onDelete: () => void;
}

export default function BotCard({ bot, onEdit, onDelete }: BotCardProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleCardClick = () => {
    // Don't navigate if clicking on the dropdown menu
    if (isMenuOpen) return;
    navigate(`/bots/${bot.bot_id}`);
  };

  const handleMenuAction = (action: () => void) => {
    setIsMenuOpen(false);
    action();
  };

  // Mutation for toggling bot status
  const toggleStatusMutation = useMutation({
    mutationFn: (shouldActivate: boolean) =>
      shouldActivate ? activateBot(bot.bot_id) : deactivateBot(bot.bot_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bots"] });
      toast.success(`Bot ${bot.status === "ACTIVE" ? "deactivated" : "activated"} successfully`);
    },
    onError: (error) => {
      console.error("Failed to toggle bot status:", error);
      toast.error("Failed to update bot status");
    },
  });

  const handleToggleStatus = () => {
    const shouldActivate = bot.status !== "ACTIVE";
    toggleStatusMutation.mutate(shouldActivate);
  };

  return (
    <Card
      className="group cursor-pointer hover:shadow-md transition-shadow"
      onClick={handleCardClick}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="rounded-lg bg-muted p-2.5">
              <BotIcon className="h-5 w-5" />
            </div>
            <div className="space-y-1 flex-1 min-w-0">
              <h3 className="text-base font-semibold leading-none truncate">{bot.name}</h3>
              <div className="flex items-center gap-2 flex-wrap">
                <Badge
                  variant={bot.status === "ACTIVE" ? "default" : "secondary"}
                >
                  {bot.status}
                </Badge>
                <WhatsAppStatusBadge
                  status={bot.whatsapp_status}
                  phoneNumber={bot.whatsapp_phone_number}
                />
              </div>
            </div>
          </div>
          <DropdownMenu open={isMenuOpen} onOpenChange={setIsMenuOpen}>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              onClick={(e) => e.stopPropagation()}
            >
              <DropdownMenuItem onClick={() => handleMenuAction(onEdit)}>
                <Edit className="mr-2 h-4 w-4" />
                Edit Bot
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() =>
                  handleMenuAction(() => navigate(`/bots/${bot.bot_id}`))
                }
              >
                <ArrowRight className="mr-2 h-4 w-4" />
                View Flows
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => handleMenuAction(handleToggleStatus)}
                disabled={toggleStatusMutation.isPending}
              >
                {bot.status === "ACTIVE" ? (
                  <>
                    <PowerOff className="mr-2 h-4 w-4" />
                    Deactivate Bot
                  </>
                ) : (
                  <>
                    <Power className="mr-2 h-4 w-4" />
                    Activate Bot
                  </>
                )}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => handleMenuAction(onDelete)}
                className="text-destructive focus:text-destructive"
              >
                <Trash className="mr-2 h-4 w-4" />
                Delete Bot
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-2">
          {bot.description || "No description provided"}
        </p>
      </CardContent>
      <CardFooter className="text-xs text-muted-foreground">
        <div className="flex items-center justify-between w-full">
          <span>
            {bot.flow_count ?? 0} {bot.flow_count === 1 ? "flow" : "flows"}
          </span>
          <span>
            Created{" "}
            {formatDistanceToNow(new Date(bot.created_at), { addSuffix: true })}
          </span>
        </div>
      </CardFooter>
    </Card>
  );
}
