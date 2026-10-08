/** Planned duration as short German text, e.g. "25 Min." or "1 Std. 30 Min.". */
export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} Min.`
  const h = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest > 0 ? `${h} Std. ${rest} Min.` : `${h} Std.`
}
