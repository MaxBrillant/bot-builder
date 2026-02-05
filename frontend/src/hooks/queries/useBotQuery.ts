import { useQuery } from '@tanstack/react-query';
import { getBot } from '@/lib/api';
import { botsKeys } from './useBotsQuery';

/**
 * Hook to fetch a single bot by ID
 */
export function useBotQuery(botId: string | undefined) {
  return useQuery({
    queryKey: botId ? botsKeys.detail(botId) : ['bot', 'empty'],
    queryFn: async () => {
      if (!botId) throw new Error('Bot ID is required');
      const response = await getBot(botId);
      return response.data;
    },
    enabled: !!botId, // Only run query if botId exists
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}
