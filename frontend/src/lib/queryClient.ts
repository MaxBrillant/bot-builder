import { QueryClient } from '@tanstack/react-query';

/**
 * React Query client configuration
 * Configures global defaults for queries and mutations
 *
 * IMPORTANT: This instance is exported and used in multiple places:
 * - App.tsx (QueryClientProvider)
 * - AuthContext.tsx (clear cache on logout)
 * - api.ts (clear cache on 401 unauthorized)
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is considered fresh for 5 minutes
      staleTime: 1000 * 60 * 5,

      // Don't refetch on window focus (can be enabled per-query if needed)
      refetchOnWindowFocus: false,

      // Retry failed requests once
      retry: 1,

      // Don't retry on certain error codes
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      // Don't retry mutations - creates could duplicate, updates/deletes should not retry
      retry: false,
    },
  },
});
