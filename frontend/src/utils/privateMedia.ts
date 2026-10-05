import apiClient from '@/api'

/** Only the configured API may receive credentials, never an imported image URL. */
export function privateMediaPath(source: string): string | null {
  const url = new URL(source, window.location.origin)
  const api = new URL(apiClient.defaults.baseURL ?? '/api/v1', window.location.origin)
  if (![api.origin, window.location.origin].includes(url.origin)) return null
  const match = url.pathname.match(/^\/api\/v1\/(private-media|attachment-preview)\//)
  return match ? url.pathname.slice('/api/v1'.length) + url.search : null
}

export async function mediaBlob(source: string, signal?: AbortSignal): Promise<Blob> {
  const path = privateMediaPath(source)
  if (path) return (await apiClient.get<Blob>(path, { responseType: 'blob', signal })).data
  const url = new URL(source, window.location.origin)
  if (!['https:', 'http:', 'blob:', 'data:'].includes(url.protocol)) throw new Error('Ungültige Medienadresse')
  const response = await fetch(url, { credentials: 'omit', referrerPolicy: 'no-referrer', signal })
  if (!response.ok) throw new Error('Datei konnte nicht geladen werden')
  return response.blob()
}

export async function downloadMedia(source: string, filename = 'Download'): Promise<void> {
  const blob = await mediaBlob(source)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
