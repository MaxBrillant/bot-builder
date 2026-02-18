/**
 * Utility functions for managing flow-related localStorage
 */

const LAST_FLOW_KEY_PREFIX = 'bot_';
const LAST_FLOW_KEY_SUFFIX = '_lastFlowId';

/**
 * Get the last opened flow ID for a specific bot
 * @param botId The bot ID
 * @returns The flow ID or null if not found
 */
export function getLastOpenedFlowId(botId: string): string | null {
  try {
    const key = `${LAST_FLOW_KEY_PREFIX}${botId}${LAST_FLOW_KEY_SUFFIX}`;
    return localStorage.getItem(key);
  } catch (error) {
    console.error('Failed to get last opened flow from localStorage:', error);
    return null;
  }
}

/**
 * Set the last opened flow ID for a specific bot
 * @param botId The bot ID
 * @param flowId The flow ID to store
 */
export function setLastOpenedFlowId(botId: string, flowId: string): void {
  try {
    const key = `${LAST_FLOW_KEY_PREFIX}${botId}${LAST_FLOW_KEY_SUFFIX}`;
    localStorage.setItem(key, flowId);
  } catch (error) {
    console.error('Failed to set last opened flow in localStorage:', error);
  }
}
