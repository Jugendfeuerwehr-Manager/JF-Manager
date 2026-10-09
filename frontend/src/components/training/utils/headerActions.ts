/** Header widths (px) from which more secondary actions appear as buttons (UX-09). */
export const HEADER_TIERS = { sm: 0, md: 560, lg: 880, xl: 1400 } as const
export type HeaderTier = keyof typeof HEADER_TIERS

export interface HeaderAction {
  key: string
  label: string
  icon?: string
  /** Smallest header width tier showing the action as a button; 'menu' keeps it in the menu. */
  tier: HeaderTier | 'menu'
  visible: boolean
  disabled?: boolean
  /** Why it is disabled or what it does; tooltip on the button, suffix in the menu. */
  hint?: string
  /** Shown in the menu only while the action is disabled, e.g. "zuerst speichern". */
  disabledReason?: string
  iconOnly?: boolean
  text?: boolean
  outlined?: boolean
  expanded?: boolean
  pressed?: boolean
  command: () => void
}

const ORDER: HeaderTier[] = ['sm', 'md', 'lg', 'xl']

export function headerTier(width: number): HeaderTier {
  return [...ORDER].reverse().find((tier) => width >= HEADER_TIERS[tier]) ?? 'sm'
}

/** Splits visible secondary actions into buttons for this width and entries for the overflow menu. */
export function splitHeaderActions(actions: HeaderAction[], width: number) {
  const current = ORDER.indexOf(headerTier(width))
  const visible = actions.filter((action) => action.visible)
  const inline = visible.filter((action) => action.tier !== 'menu' && ORDER.indexOf(action.tier) <= current)
  const menu = visible.filter((action) => !inline.includes(action))
  return { inline, menu }
}

export function menuLabel(action: HeaderAction): string {
  return action.disabled && action.disabledReason ? `${action.label} (${action.disabledReason})` : action.label
}
