import type { AccessState, InvitationState } from '@/api/portalAdmin'
import type { StatusSeverity } from '@/components/common/StatusBadge.vue'

export const accessStateMeta: Record<AccessState, { label: string, severity: StatusSeverity, icon: string }> = {
  none: { label: 'Kein Zugang', severity: 'neutral', icon: 'pi pi-minus-circle' },
  invited: { label: 'Eingeladen', severity: 'info', icon: 'pi pi-send' },
  expired: { label: 'Abgelaufen', severity: 'warning', icon: 'pi pi-clock' },
  active: { label: 'Aktiv', severity: 'success', icon: 'pi pi-check-circle' },
  suspended: { label: 'Gesperrt', severity: 'danger', icon: 'pi pi-ban' },
}

export const invitationStateMeta: Record<InvitationState, { label: string, severity: StatusSeverity, icon: string }> = {
  open: { label: 'Offen', severity: 'info', icon: 'pi pi-send' },
  expired: { label: 'Abgelaufen', severity: 'warning', icon: 'pi pi-clock' },
  accepted: { label: 'Angenommen', severity: 'success', icon: 'pi pi-check-circle' },
  revoked: { label: 'Widerrufen', severity: 'neutral', icon: 'pi pi-times-circle' },
}

export function formatDate(value: string | null | undefined, withTime = false): string {
  if (!value) return '–'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return withTime
    ? date.toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' })
    : date.toLocaleDateString('de-DE', { dateStyle: 'medium' })
}
