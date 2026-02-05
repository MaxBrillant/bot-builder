import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getBots, createBot, updateBot, deleteBot, regenerateWebhookSecret } from '@/lib/api';
import { handleError, handleSuccess } from '@/lib/errorHandler';
import type { Bot } from '@/lib/types';

/**
 * Query key factory for bots
 */
export const botsKeys = {
  all: ['bots'] as const,
  lists: () => [...botsKeys.all, 'list'] as const,
  list: (filters?: string) => [...botsKeys.lists(), filters] as const,
  details: () => [...botsKeys.all, 'detail'] as const,
  detail: (id: string) => [...botsKeys.details(), id] as const,
};

/**
 * Hook to fetch all bots for the current user
 */
export function useBotsQuery() {
  return useQuery({
    queryKey: botsKeys.lists(),
    queryFn: async () => {
      const response = await getBots();
      return response.data.bots;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Hook to create a new bot
 */
export function useCreateBotMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { name: string; description?: string }) => createBot(data),
    onSuccess: (response) => {
      // Invalidate all bot-related queries to ensure consistency
      queryClient.invalidateQueries({ queryKey: botsKeys.all });
      handleSuccess('Bot created successfully', `Created "${response.data.name}"`);
    },
    onError: (error: unknown) => {
      handleError(error, 'Failed to create bot');
    },
  });
}

/**
 * Hook to update an existing bot
 */
export function useUpdateBotMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      botId,
      data,
    }: {
      botId: string;
      data: { name?: string; description?: string; status?: "ACTIVE" | "INACTIVE" };
    }) => updateBot(botId, data),
    onMutate: async ({ botId, data }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: botsKeys.lists() });

      // Snapshot the previous value
      const previousBots = queryClient.getQueryData<Bot[]>(botsKeys.lists());

      // Optimistically update to the new value
      if (previousBots) {
        queryClient.setQueryData<Bot[]>(
          botsKeys.lists(),
          previousBots.map((bot) =>
            bot.bot_id === botId ? { ...bot, ...data } : bot
          )
        );
      }

      // Return context with previous data
      return { previousBots };
    },
    onError: (error: unknown, _variables, context) => {
      // Rollback to previous value on error
      if (context?.previousBots) {
        queryClient.setQueryData(botsKeys.lists(), context.previousBots);
      }
      handleError(error, 'Failed to update bot');
    },
    onSuccess: (_response, variables) => {
      // Invalidate both list and detail caches to ensure consistency
      queryClient.invalidateQueries({ queryKey: botsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: botsKeys.detail(variables.botId) });
      handleSuccess('Bot updated successfully');
    },
  });
}

/**
 * Hook to delete a bot
 */
export function useDeleteBotMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (botId: string) => deleteBot(botId),
    onMutate: async (botId) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: botsKeys.lists() });

      // Snapshot the previous value
      const previousBots = queryClient.getQueryData<Bot[]>(botsKeys.lists());

      // Optimistically remove the bot
      if (previousBots) {
        queryClient.setQueryData<Bot[]>(
          botsKeys.lists(),
          previousBots.filter((bot) => bot.bot_id !== botId)
        );
      }

      // Return context with previous data
      return { previousBots };
    },
    onError: (error: unknown, _variables, context) => {
      // Rollback to previous value on error
      if (context?.previousBots) {
        queryClient.setQueryData(botsKeys.lists(), context.previousBots);
      }
      handleError(error, 'Failed to delete bot');
    },
    onSuccess: (_response, botId) => {
      // Invalidate caches to ensure deletion is reflected everywhere
      queryClient.invalidateQueries({ queryKey: botsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: botsKeys.detail(botId) });
      handleSuccess('Bot deleted successfully');
    },
  });
}

/**
 * Hook to regenerate webhook secret for a bot
 */
export function useRegenerateWebhookSecretMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (botId: string) => regenerateWebhookSecret(botId),
    onSuccess: (_response, botId) => {
      // Invalidate caches to fetch new secret from server
      queryClient.invalidateQueries({ queryKey: botsKeys.lists() });
      queryClient.invalidateQueries({ queryKey: botsKeys.detail(botId) });
      handleSuccess('Webhook secret regenerated');
    },
    onError: (error: unknown) => {
      handleError(error, 'Failed to regenerate webhook secret');
    },
  });
}
