import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchFlows,
  createFlow as createFlowAPI,
  updateFlow as updateFlowAPI,
  deleteFlow as deleteFlowAPI,
} from '@/lib/api';
import { handleError, handleSuccess } from '@/lib/errorHandler';
import type { Flow, FlowCreateRequest } from '@/lib/types';
import { botsKeys } from './useBotsQuery';

/**
 * Query key factory for flows
 */
export const flowsKeys = {
  all: ['flows'] as const,
  lists: () => [...flowsKeys.all, 'list'] as const,
  list: (botId: string) => [...flowsKeys.lists(), botId] as const,
  details: () => [...flowsKeys.all, 'detail'] as const,
  detail: (botId: string, flowId: string) => [...flowsKeys.details(), botId, flowId] as const,
};

/**
 * Hook to fetch all flows for a specific bot
 */
export function useFlowsQuery(botId: string | undefined) {
  return useQuery({
    queryKey: botId ? flowsKeys.list(botId) : ['flows', 'empty'],
    queryFn: async () => {
      if (!botId) return [];
      return await fetchFlows(botId);
    },
    enabled: !!botId, // Only run query if botId exists
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Hook to create a new flow
 */
export function useCreateFlowMutation(botId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (flowData: FlowCreateRequest) => createFlowAPI(botId, flowData),
    onSuccess: (newFlow) => {
      // Update the cache with the new flow
      const previousFlows = queryClient.getQueryData<Flow[]>(flowsKeys.list(botId));
      if (previousFlows) {
        queryClient.setQueryData<Flow[]>(flowsKeys.list(botId), [...previousFlows, newFlow]);
      } else {
        // If no cache, just invalidate
        queryClient.invalidateQueries({ queryKey: flowsKeys.list(botId) });
      }

      // Invalidate bots cache to update flow_count on bots page
      queryClient.invalidateQueries({ queryKey: botsKeys.lists() });

      handleSuccess('Flow created successfully', `Created "${newFlow.name}"`);
    },
    onError: (error: unknown) => {
      handleError(error, 'Failed to create flow');
    },
  });
}

/**
 * Hook to update an existing flow
 */
export function useUpdateFlowMutation(botId: string, flowId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (flowData: FlowCreateRequest) => updateFlowAPI(botId, flowId, flowData),
    onMutate: async (flowData) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: flowsKeys.list(botId) });

      // Snapshot the previous value
      const previousFlows = queryClient.getQueryData<Flow[]>(flowsKeys.list(botId));

      // Optimistically update to the new value
      if (previousFlows) {
        queryClient.setQueryData<Flow[]>(
          flowsKeys.list(botId),
          previousFlows.map((flow) =>
            flow.flow_id === flowId
              ? {
                  ...flow,
                  ...flowData,
                  updated_at: new Date().toISOString(),
                }
              : flow
          )
        );
      }

      // Return context with previous data
      return { previousFlows };
    },
    onError: (error: unknown, _variables, context) => {
      // Rollback to previous value on error
      if (context?.previousFlows) {
        queryClient.setQueryData(flowsKeys.list(botId), context.previousFlows);
      }
      handleError(error, 'Failed to update flow');
    },
    onSuccess: (updatedFlow) => {
      // Update cache with the server response
      const previousFlows = queryClient.getQueryData<Flow[]>(flowsKeys.list(botId));
      if (previousFlows) {
        queryClient.setQueryData<Flow[]>(
          flowsKeys.list(botId),
          previousFlows.map((flow) => (flow.flow_id === flowId ? updatedFlow : flow))
        );
      }
    },
  });
}

/**
 * Hook to delete a flow
 */
export function useDeleteFlowMutation(botId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (flowId: string) => deleteFlowAPI(botId, flowId),
    onMutate: async (flowId) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: flowsKeys.list(botId) });

      // Snapshot the previous value
      const previousFlows = queryClient.getQueryData<Flow[]>(flowsKeys.list(botId));

      // Optimistically remove the flow
      if (previousFlows) {
        queryClient.setQueryData<Flow[]>(
          flowsKeys.list(botId),
          previousFlows.filter((flow) => flow.flow_id !== flowId)
        );
      }

      // Return context with previous data
      return { previousFlows };
    },
    onError: (error: unknown, _variables, context) => {
      // Rollback to previous value on error
      if (context?.previousFlows) {
        queryClient.setQueryData(flowsKeys.list(botId), context.previousFlows);
      }
      handleError(error, 'Failed to delete flow');
    },
    onSuccess: () => {
      // Invalidate bots cache to update flow_count on bots page
      queryClient.invalidateQueries({ queryKey: botsKeys.lists() });

      handleSuccess('Flow deleted successfully');
    },
  });
}
