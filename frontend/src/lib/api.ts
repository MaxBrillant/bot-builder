import axios from "axios";
import type {
  Flow,
  FlowResponse,
  FlowListResponse,
  FlowCreateRequest,
  FlowValidationResponse,
  BotListResponse,
} from "./types";
import { queryClient } from "./queryClient";

/**
 * API Client Configuration
 *
 * SECURITY: Authentication is handled via httpOnly cookies only.
 * - No tokens stored in localStorage (prevents XSS token theft)
 * - No Authorization header (token is in cookie)
 * - withCredentials: true ensures cookies are sent with requests
 */
const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  withCredentials: true, // SECURITY: Send httpOnly cookies with all requests
});

// Handle 401 responses (unauthorized) and 429 (rate limiting)
API.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Handle rate limiting
    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after'];
      const message = retryAfter
        ? `Too many requests. Please wait ${retryAfter} seconds.`
        : "Too many requests. Please try again later.";

      // Dynamically import toast to avoid circular dependency
      const { toast } = await import("sonner");
      toast.error(message);
    }

    // Handle unauthorized
    if (error.response?.status === 401) {
      // Clear React Query cache to prevent showing old user's data
      queryClient.clear();

      // Redirect to login if not already there
      if (
        window.location.pathname !== "/login" &&
        window.location.pathname !== "/" &&
        !window.location.pathname.startsWith("/auth/")
      ) {
        // Capture current path and append as redirect query parameter
        const currentPath = window.location.pathname + window.location.search;
        window.location.href = `/login?redirect=${encodeURIComponent(
          currentPath
        )}`;
      }
    }
    return Promise.reject(error);
  }
);

// Auth functions
export const login = (email: string, password: string) =>
  API.post("/auth/login", { email, password });

export const register = (email: string, password: string) =>
  API.post("/auth/register", { email, password });

export const logout = () => API.post("/auth/logout");

export const getCurrentUser = () => API.get("/auth/me");

export const deleteUserData = () => API.delete("/auth/me/data");

// Bot management
export const getBots = () => API.get<BotListResponse>("/bots");

export const getBot = (botId: string) => API.get(`/bots/${botId}`);

export const createBot = (data: { name: string; description?: string }) =>
  API.post("/bots", data);

export const updateBot = (
  botId: string,
  data: { name?: string; description?: string; status?: string }
) => API.put(`/bots/${botId}`, data);

export const deleteBot = (botId: string) => API.delete(`/bots/${botId}`);

export const regenerateWebhookSecret = (botId: string) =>
  API.post(`/bots/${botId}/regenerate-secret`);

export const activateBot = (botId: string) =>
  API.post(`/bots/${botId}/activate`);

export const deactivateBot = (botId: string) =>
  API.post(`/bots/${botId}/deactivate`);

// Flow management
/**
 * Transform FlowResponse from backend to Flow for frontend
 */
const transformFlowResponse = (response: FlowResponse): Flow => {
  return {
    flow_id: response.flow_id,
    bot_id: response.bot_id,
    name: response.flow_definition.name,
    trigger_keywords: response.flow_definition.trigger_keywords,
    // Normalize to {} to prevent undefined vs missing-key mismatch after JSON.parse(JSON.stringify())
    variables: response.flow_definition.variables ?? {},
    defaults: response.flow_definition.defaults,
    start_node_id: response.flow_definition.start_node_id,
    nodes: response.flow_definition.nodes,
    created_at: response.created_at,
    updated_at: response.updated_at,
  };
};


/**
 * Fetch all flows for a bot (oldest first)
 */
export const fetchFlows = async (botId: string): Promise<Flow[]> => {
  const response = await API.get<FlowListResponse>(`/bots/${botId}/flows?order_by=asc`);
  return response.data.flows.map(transformFlowResponse);
};

/**
 * Create a new flow
 */
export const createFlow = async (
  botId: string,
  flowData: FlowCreateRequest
): Promise<Flow> => {
  // First create the flow
  const createResponse = await API.post<FlowValidationResponse>(
    `/bots/${botId}/flows`,
    flowData
  );

  // Extract the flow_id from the validation response
  const flowId = createResponse.data.flow_id;

  // Check if flow_id exists before attempting to fetch
  if (!flowId) {
    throw new Error("Failed to create flow: no flow_id returned");
  }

  // Then fetch the full flow data
  const response = await API.get<FlowResponse>(
    `/bots/${botId}/flows/${flowId}`
  );
  return transformFlowResponse(response.data);
};

/**
 * Update an existing flow
 */
export const updateFlow = async (
  botId: string,
  flowId: string,
  flowData: FlowCreateRequest
): Promise<Flow> => {
  // First update the flow
  const updateResponse = await API.put<FlowValidationResponse>(
    `/bots/${botId}/flows/${flowId}`,
    flowData
  );

  // Check if validation succeeded
  if (updateResponse.data.status === "error") {
    // Extract error messages
    const errorMessages =
      updateResponse.data.errors?.map((err) => err.message).join("; ") ||
      "Validation failed";
    throw new Error(errorMessages);
  }

  // Then fetch the updated flow to get the full structure
  const response = await API.get<FlowResponse>(
    `/bots/${botId}/flows/${flowId}`
  );
  return transformFlowResponse(response.data);
};

/**
 * Delete a flow
 */
export const deleteFlow = async (
  botId: string,
  flowId: string
): Promise<void> => {
  await API.delete(`/bots/${botId}/flows/${flowId}`);
};

/**
 * Send a test message to the bot webhook
 * Returns raw Response for SSE streaming consumption
 *
 * The webhook returns Server-Sent Events (SSE) for real-time message delivery.
 * Each message is streamed as: data: {"message": "...", "index": 0}
 * Stream ends with: data: {"done": true, "session_id": "..."}
 */
export const sendTestMessage = async (
  botId: string,
  webhookSecret: string,
  channelUserId: string,
  messageText: string
): Promise<Response> => {
  const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  return fetch(`${baseURL}/webhook/${botId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Webhook-Secret": webhookSecret,
    },
    body: JSON.stringify({
      channel: "test",
      channel_user_id: channelUserId,
      message_text: messageText,
    }),
  });
};

// ============================================
// WHATSAPP CONNECTION MANAGEMENT (Evolution API v2.2.3)
// ============================================

/**
 * Connect bot to WhatsApp via Evolution API v2.2.3
 *
 * Returns QR code IMMEDIATELY in response - no polling needed!
 *
 * v2.2.3 improvements:
 * - QR code always returned in create instance response
 * - Webhook configuration included in create payload
 * - Uses nested webhook object with camelCase fields
 *
 * Response includes:
 * - status: "CONNECTING"
 * - qr_code: Base64 QR code ready to display
 * - instance_name: Evolution API instance ID
 */
export const connectWhatsApp = (botId: string) =>
  API.post(`/bots/${botId}/whatsapp/connect`);

/**
 * Get WhatsApp connection status for a bot
 *
 * Queries Evolution API for current connection state.
 * Returns: DISCONNECTED | CONNECTING | CONNECTED | ERROR
 *
 * Use this to poll for when user scans QR code (status changes to "CONNECTED")
 */
export const getWhatsAppStatus = (botId: string) =>
  API.get(`/bots/${botId}/whatsapp/status`);

/**
 * Disconnect WhatsApp from a bot
 *
 * Steps performed:
 * 1. Logout from Evolution API (disconnects WhatsApp)
 * 2. Delete Evolution API instance
 * 3. Clear bot's WhatsApp fields
 *
 * This is destructive - bot will need new QR code to reconnect
 */
export const disconnectWhatsApp = (botId: string) =>
  API.post(`/bots/${botId}/whatsapp/disconnect`);

/**
 * Reconnect WhatsApp for a bot
 *
 * Convenience endpoint that combines disconnect + connect.
 * Returns new QR code immediately in response (v2.2.3 behavior).
 *
 * Useful for troubleshooting or switching WhatsApp numbers.
 */
export const reconnectWhatsApp = (botId: string) =>
  API.post(`/bots/${botId}/whatsapp/reconnect`);

export default API;
