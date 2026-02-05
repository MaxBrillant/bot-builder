import { useState, useEffect } from 'react';

/**
 * Hook for syncing state with localStorage
 * Automatically persists state changes to localStorage
 *
 * @param key - The localStorage key to use
 * @param initialValue - The initial value if no stored value exists
 * @returns Tuple of [value, setValue] similar to useState
 *
 * @example
 * ```typescript
 * const [theme, setTheme] = useLocalStorage<'light' | 'dark'>('theme', 'light');
 *
 * // Changes are automatically persisted
 * setTheme('dark');
 * ```
 */
export function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error(`Error saving to localStorage:`, error);
    }
  }, [key, value]);

  return [value, setValue] as const;
}
