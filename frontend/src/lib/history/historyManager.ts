import type { Command } from './commands';
import type { Flow } from '@/lib/types';
import { applyPatches } from './patchUtils';

const MAX_HISTORY_SIZE = 50;
const COALESCE_THRESHOLD_MS = 200; // Merge commands within this time window

export interface FlowHistory {
  past: Command[];    // Undo stack (most recent first)
  future: Command[];  // Redo stack (most recent first)
}

export interface HistoryManager {
  // State
  getHistory: (flowId: string) => FlowHistory;

  // Actions
  record: (flowId: string, command: Command) => void;
  undo: (flowId: string, currentState: Flow) => Flow | null;
  redo: (flowId: string, currentState: Flow) => Flow | null;

  // Queries
  canUndo: (flowId: string) => boolean;
  canRedo: (flowId: string) => boolean;

  // Lifecycle
  clearHistory: (flowId: string) => void;
  clearAllHistory: () => void;

  // For triggering re-renders
  getVersion: () => number;
}

export function createHistoryManager(): HistoryManager {
  const histories = new Map<string, FlowHistory>();
  let version = 0;

  const getOrCreateHistory = (flowId: string): FlowHistory => {
    if (!histories.has(flowId)) {
      histories.set(flowId, { past: [], future: [] });
    }
    return histories.get(flowId)!;
  };

  return {
    getHistory: (flowId: string): FlowHistory => {
      return getOrCreateHistory(flowId);
    },

    record: (flowId: string, command: Command): void => {
      const history = getOrCreateHistory(flowId);

      // Clear future (can't redo after new action)
      history.future = [];

      // Check if we should coalesce with the most recent command
      const lastCommand = history.past[0];
      if (
        lastCommand &&
        command.timestamp - lastCommand.timestamp < COALESCE_THRESHOLD_MS
      ) {
        // Merge commands: keep first's inverse patches, use combined forward patches
        // This allows undoing both operations in one step
        const mergedCommand: Command = {
          id: command.id,
          timestamp: command.timestamp,
          type: command.type,
          flowId: command.flowId,
          description: command.description, // Use latest description
          // To go from A→C, apply first patches then second patches
          patches: [...lastCommand.patches, ...command.patches],
          // To go from C→A, apply second inverse then first inverse
          inversePatches: [...command.inversePatches, ...lastCommand.inversePatches],
          affectedNodeIds: [
            ...(lastCommand.affectedNodeIds || []),
            ...(command.affectedNodeIds || []),
          ],
        };

        // Replace the last command with merged one
        history.past = [mergedCommand, ...history.past.slice(1)].slice(0, MAX_HISTORY_SIZE);
      } else {
        // Add as new entry
        history.past = [command, ...history.past].slice(0, MAX_HISTORY_SIZE);
      }

      histories.set(flowId, history);
      version++;
    },

    undo: (flowId: string, currentState: Flow): Flow | null => {
      const history = getOrCreateHistory(flowId);

      if (history.past.length === 0) {
        return null;
      }

      // Pop the most recent command from past
      const [command, ...remainingPast] = history.past;

      // Apply inverse patches to current state
      const newState = applyPatches(currentState, command.inversePatches);

      if (newState === null) {
        console.error('Failed to apply inverse patches for undo');
        return null;
      }

      // Move command to future stack
      history.past = remainingPast;
      history.future = [command, ...history.future];

      histories.set(flowId, history);
      version++;

      return newState;
    },

    redo: (flowId: string, currentState: Flow): Flow | null => {
      const history = getOrCreateHistory(flowId);

      if (history.future.length === 0) {
        return null;
      }

      // Pop the most recent command from future
      const [command, ...remainingFuture] = history.future;

      // Apply forward patches to current state
      const newState = applyPatches(currentState, command.patches);

      if (newState === null) {
        console.error('Failed to apply patches for redo');
        return null;
      }

      // Move command back to past stack
      history.future = remainingFuture;
      history.past = [command, ...history.past];

      histories.set(flowId, history);
      version++;

      return newState;
    },

    canUndo: (flowId: string): boolean => {
      const history = histories.get(flowId);
      return history ? history.past.length > 0 : false;
    },

    canRedo: (flowId: string): boolean => {
      const history = histories.get(flowId);
      return history ? history.future.length > 0 : false;
    },

    clearHistory: (flowId: string): void => {
      histories.delete(flowId);
      version++;
    },

    clearAllHistory: (): void => {
      histories.clear();
      version++;
    },

    getVersion: (): number => {
      return version;
    },
  };
}
