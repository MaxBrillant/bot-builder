import type { Operation } from 'fast-json-patch';

/**
 * Generate a unique ID for commands using crypto API
 */
function generateCommandId(): string {
  return crypto.randomUUID();
}

/**
 * Enum of all command types that can be recorded in history
 */
export enum CommandType {
  // Flow settings
  UPDATE_FLOW_SETTINGS = 'UPDATE_FLOW_SETTINGS',

  // Node content
  UPDATE_NODE_CONFIG = 'UPDATE_NODE_CONFIG',
  UPDATE_NODE_NAME = 'UPDATE_NODE_NAME',
  UPDATE_NODE_ROUTES = 'UPDATE_NODE_ROUTES',

  // Node position
  UPDATE_NODE_POSITION = 'UPDATE_NODE_POSITION',
  BATCH_UPDATE_POSITIONS = 'BATCH_UPDATE_POSITIONS',

  // Structural
  INSERT_NODE = 'INSERT_NODE',
  DELETE_NODE = 'DELETE_NODE',
  MOVE_NODE_LEFT = 'MOVE_NODE_LEFT',
  MOVE_NODE_RIGHT = 'MOVE_NODE_RIGHT',
  MOVE_NODE_BETWEEN = 'MOVE_NODE_BETWEEN',
}

/**
 * Command interface representing a reversible operation with inverse patches
 */
export interface Command {
  /** Unique command ID */
  id: string;

  /** When executed (timestamp) */
  timestamp: number;

  /** Action type enum */
  type: CommandType;

  /** Which flow this affects */
  flowId: string;

  /** Human-readable description (for UI) */
  description: string;

  /** JSON Patch operations (RFC 6902) */
  patches: Operation[];

  /** Reverse patches for undo */
  inversePatches: Operation[];

  /** Node IDs affected by this command (for highlighting) */
  affectedNodeIds?: string[];

  /** Fields changed (for context) */
  affectedFields?: string[];
}

/**
 * Helper function to create a new command
 */
export function createCommand(params: {
  type: CommandType;
  flowId: string;
  description: string;
  patches: Operation[];
  inversePatches: Operation[];
  affectedNodeIds?: string[];
  affectedFields?: string[];
}): Command {
  return {
    id: generateCommandId(),
    timestamp: Date.now(),
    ...params,
  };
}

