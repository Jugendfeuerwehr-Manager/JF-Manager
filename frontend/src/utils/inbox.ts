import type { InboxCategory, InboxDoneVia, InboxEntry } from '@/api/inbox'

const categories: Record<InboxCategory, string> = { requests: 'Anträge', registrations: 'Meldungen', staffing: 'Besetzung', accounts: 'Konten' }
export const categoryLabel = (category: InboxCategory) => categories[category] ?? category

const via: Record<InboxDoneVia, string> = { ui: 'in der Oberfläche', email_action: 'per E-Mail-Aktion', auto: 'automatisch' }

export function relativeTime(iso: string, now = new Date()): string {
  const minutes = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 60_000))
  if (minutes < 1) return 'gerade eben'
  if (minutes < 60) return `vor ${minutes} Min.`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `vor ${hours} Std.`
  return new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit' }).format(new Date(iso))
}

export function doneText(entry: InboxEntry, now = new Date()): string {
  const at = entry.done_at ? new Date(entry.done_at) : null
  let when = ''
  if (at) {
    const time = new Intl.DateTimeFormat('de-DE', { hour: '2-digit', minute: '2-digit' }).format(at)
    const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1)
    const day = at.toDateString() === now.toDateString() ? 'heute'
      : at.toDateString() === yesterday.toDateString() ? 'gestern'
        : new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit' }).format(at)
    when = ` ${day} ${time}`
  }
  const how = entry.done_via ? ` ${via[entry.done_via]}` : ''
  if (entry.done_via === 'auto') return `Automatisch erledigt${when}`
  return `Erledigt${entry.done_by ? ` von ${entry.done_by}` : ''}${when}${how === ' in der Oberfläche' ? '' : how}`
}
