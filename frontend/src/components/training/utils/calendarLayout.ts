/** Exercises per day cell when the cell height is unknown (tests, phones, growing rows). */
export const DEFAULT_SESSIONS_PER_CELL = 3
const MAX_SESSIONS_PER_CELL = 12

/**
 * How many entries fit into a day cell of fixed height (UX-09): large screens give
 * each day more room, so more exercises are listed before "+N weitere".
 */
export function sessionCapacity(availablePx: number, entryPx: number, gapPx = 2): number {
  if (!Number.isFinite(availablePx) || !Number.isFinite(entryPx) || entryPx <= 0) return DEFAULT_SESSIONS_PER_CELL
  const fit = Math.floor((availablePx + gapPx) / (entryPx + gapPx))
  return Math.max(1, Math.min(MAX_SESSIONS_PER_CELL, fit))
}

/** Entries shown in a cell: all when they fit, otherwise one row is kept for "+N weitere". */
export function visibleSessionCount(total: number, capacity: number): number {
  if (total <= capacity) return total
  return Math.max(1, capacity - 1)
}
