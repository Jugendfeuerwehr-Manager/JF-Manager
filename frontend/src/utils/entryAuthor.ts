/**
 * "Angelegt von … am …" for entries on a member record (events, qualifications,
 * special tasks, attachments, membership history).
 */
export function entryAuthorLabel(name: string | null | undefined, at: string | null | undefined): string {
  const date = formatCreatedAt(at)
  if (!name && !date) return ''
  if (!name) return `Angelegt am ${date}`
  if (!date) return `Angelegt von ${name}`
  return `Angelegt von ${name} am ${date}`
}

function formatCreatedAt(at: string | null | undefined): string {
  if (!at) return ''
  const parsed = new Date(at)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}
