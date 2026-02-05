import { useState } from "react";
import { Plus, Bot as BotIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { EmptyState } from "@/components/ui/empty-state";
import BotCard from "@/components/bots/BotCard";
import CreateBotDialog from "@/components/bots/CreateBotDialog";
import EditBotDialog from "@/components/bots/EditBotDialog";
import DeleteBotDialog from "@/components/bots/DeleteBotDialog";
import { UserDropdown } from "@/components/auth/UserDropdown";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useBotsQuery } from "@/hooks/queries/useBotsQuery";
import { handleError } from "@/lib/errorHandler";
import type { Bot } from "@/lib/types";

export default function BotsPage() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedBot, setSelectedBot] = useState<Bot | null>(null);

  // Use React Query for bots data
  const { data: bots = [], isLoading, error } = useBotsQuery();

  // Handle error if query fails
  if (error) {
    handleError(error, 'Failed to fetch bots');
  }

  const handleEdit = (bot: Bot) => {
    setSelectedBot(bot);
    setEditDialogOpen(true);
  };

  const handleDelete = (bot: Bot) => {
    setSelectedBot(bot);
    setDeleteDialogOpen(true);
  };

  if (isLoading) {
    return (
      <div className="min-h-[calc(100vh-200px)] flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="lg" className="mx-auto mb-4" />
          <p className="text-muted-foreground">Loading your bots...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Bots</h1>
          <p className="text-base text-muted-foreground">
            Manage your conversational bots
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Bot
          </Button>
          <ThemeToggle />
          <UserDropdown />
        </div>
      </div>

      {/* Empty State */}
      {bots.length === 0 ? (
        <EmptyState
          icon={BotIcon}
          title="No bots yet"
          description="Create your first bot to start building conversational flows"
          action={
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Bot
            </Button>
          }
        />
      ) : (
        /* Bots Grid */
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {bots.map((bot) => (
            <BotCard
              key={bot.bot_id}
              bot={bot}
              onEdit={() => handleEdit(bot)}
              onDelete={() => handleDelete(bot)}
            />
          ))}
        </div>
      )}

      {/* Dialogs */}
      <CreateBotDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={() => {
          // React Query will auto-refetch, just close dialog
          setCreateDialogOpen(false);
        }}
      />

      <EditBotDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        bot={selectedBot}
        onSuccess={() => {
          // React Query will auto-refetch, just close dialog
          setEditDialogOpen(false);
        }}
      />

      <DeleteBotDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        bot={selectedBot}
        onSuccess={() => {
          // React Query will auto-refetch, just close dialog
          setDeleteDialogOpen(false);
        }}
      />
    </div>
  );
}
