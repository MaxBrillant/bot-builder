import { createContext, useContext } from 'react';

interface EdgeHoverState {
  edgeId: string | null;
  isDragging: boolean;
}

/**
 * Context for tracking which edge is currently being hovered.
 * Includes whether it's from a drag operation or regular hover.
 */
export const EdgeHoverContext = createContext<EdgeHoverState>({ edgeId: null, isDragging: false });

/**
 * Hook to access edge hover state.
 * Returns { edgeId, isDragging }.
 */
export function useEdgeHover() {
  return useContext(EdgeHoverContext);
}
