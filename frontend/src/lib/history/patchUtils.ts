import { compare, applyPatch, type Operation } from 'fast-json-patch';

/**
 * Generate JSON Patch operations from old state to new state
 * @param oldState The original state
 * @param newState The updated state
 * @returns Array of JSON Patch operations
 */
export function generatePatches<T extends object>(oldState: T, newState: T): Operation[] {
  return compare(oldState, newState);
}

/**
 * Apply a set of patches to a state object
 * @param state The state to patch
 * @param patches The patches to apply
 * @returns The patched state, or null if patches are invalid
 */
export function applyPatches<T extends object>(state: T, patches: Operation[]): T | null {
  if (!patches || patches.length === 0) {
    return structuredClone(state);
  }

  try {
    // Clone the state to avoid mutation
    const clonedState = structuredClone(state);

    // Validate patches before applying
    for (const patch of patches) {
      if (!patch.op || !patch.path) {
        console.error('Invalid patch: missing op or path', patch);
        return null;
      }
    }

    // Apply patches
    const { newDocument } = applyPatch(clonedState, patches);

    return newDocument as T;
  } catch (error) {
    console.error('Failed to apply patches:', error);
    return null;
  }
}

/**
 * Generate patches and inverse patches in one call for efficiency
 * @param oldState The original state
 * @param newState The updated state
 * @returns Object containing both forward and inverse patches
 */
export function generatePatchPair<T extends object>(
  oldState: T,
  newState: T
): { patches: Operation[]; inversePatches: Operation[] } {
  const patches = generatePatches(oldState, newState);
  const inversePatches = generatePatches(newState, oldState);

  return { patches, inversePatches };
}
