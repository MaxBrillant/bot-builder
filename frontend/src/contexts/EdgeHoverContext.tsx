import { createContext, useContext } from 'react';

/**
 * Context for tracking which edge is currently being hovered during drag operations.
 * This avoids recreating the entire edges array on every hover state change.
 */
export const EdgeHoverContext = createContext<string | null>(null);

/**
 * Hook to access the currently hovered edge ID.
 * Returns null if no edge is hovered.
 */
export function useEdgeHover() {
  return useContext(EdgeHoverContext);
}
