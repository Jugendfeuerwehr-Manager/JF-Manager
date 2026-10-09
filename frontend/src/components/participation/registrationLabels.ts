import type { DisplayState, ReasonCategory } from '@/api/participation'
import type { StatusSeverity } from '@/components/common/StatusBadge.vue'

export interface StateLabel { label: string, severity: StatusSeverity, icon: string }

export function stateLabel(state: DisplayState, position: number | null = null): StateLabel {
  switch (state) {
    case 'registered': return { label: 'Angemeldet', severity: 'success', icon: 'pi pi-check-circle' }
    case 'waitlisted': return { label: position ? `Warteliste, Platz ${position}` : 'Warteliste', severity: 'info', icon: 'pi pi-hourglass' }
    case 'applied': return { label: 'Beworben', severity: 'info', icon: 'pi pi-send' }
    case 'assigned': return { label: 'Zugeteilt', severity: 'success', icon: 'pi pi-check-circle' }
    case 'not_selected': return { label: 'Nicht berücksichtigt', severity: 'neutral', icon: 'pi pi-minus-circle' }
    case 'cancelled': return { label: 'Abgemeldet', severity: 'danger', icon: 'pi pi-times-circle' }
    case 'expected': return { label: 'Erwartet', severity: 'neutral', icon: 'pi pi-clock' }
    default: return { label: 'Keine Rückmeldung', severity: 'warning', icon: 'pi pi-question-circle' }
  }
}

export const REASON_OPTIONS: Array<{ value: ReasonCategory, label: string }> = [
  { value: '', label: 'Kein Grund angegeben' },
  { value: 'krankheit', label: 'Krankheit' },
  { value: 'schule_beruf', label: 'Schule/Beruf' },
  { value: 'urlaub', label: 'Urlaub' },
  { value: 'familie', label: 'Familie' },
  { value: 'sonstiges', label: 'Sonstiges' },
]

export const reasonLabel = (category: ReasonCategory | undefined) =>
  REASON_OPTIONS.find(option => option.value === (category ?? ''))?.label ?? ''
