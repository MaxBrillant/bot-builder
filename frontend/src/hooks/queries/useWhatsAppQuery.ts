import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "@/lib/api";

/**
 * Query: Get WhatsApp connection status
 *
 * Polls backend for status updates:
 * - 3s interval during CONNECTING (to detect QR scan quickly)
 * - 30s interval otherwise (to detect disconnections)
 * - Only when enabled (modal open)
 */
export const useWhatsAppStatusQuery = (
  botId: string,
  enabled = true,
  isConnecting = false
) => {
  return useQuery({
    queryKey: ["whatsapp-status", botId],
    queryFn: () => api.getWhatsAppStatus(botId),
    select: (response) => response.data,
    enabled,
    // Dynamic polling: Fast during CONNECTING, slow otherwise
    refetchInterval: enabled ? (isConnecting ? 3000 : 30000) : false,
    refetchIntervalInBackground: false,
  });
};

/**
 * Mutation: Connect WhatsApp (Evolution API v2.2.3)
 *
 * Returns QR code IMMEDIATELY in mutation response.
 *
 * Usage:
 * ```tsx
 * const connectMutation = useConnectWhatsApp(botId);
 * const result = await connectMutation.mutateAsync();
 * const qrCode = result.data.qr_code; // Available immediately!
 * ```
 */
export const useConnectWhatsApp = (botId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.connectWhatsApp(botId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-status", botId] });
    },
  });
};

/**
 * Mutation: Disconnect WhatsApp
 */
export const useDisconnectWhatsApp = (botId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.disconnectWhatsApp(botId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-status", botId] });
      // Also invalidate bots query to update status badge
      queryClient.invalidateQueries({ queryKey: ["bots"] });
    },
  });
};

/**
 * Mutation: Reconnect WhatsApp
 *
 * Combines disconnect + connect. Returns new QR code immediately.
 */
export const useReconnectWhatsApp = (botId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.reconnectWhatsApp(botId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-status", botId] });
    },
  });
};
