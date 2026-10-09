import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { inboxApi, type InboxCounts, type InboxEntry, type InboxFilters } from '@/api/inbox'
import { getApiErrorMessage } from '@/utils/apiError'

export const COUNTS_POLL_MS = 60_000

export const useInboxStore = defineStore('inbox', () => {
  const entries = ref<InboxEntry[]>([])
  const total = ref(0)
  const counts = ref<InboxCounts>({ open_tasks: 0, unread_notices: 0, total: 0, by_category: {} })
  const filters = ref<InboxFilters>({ type: '', category: '', department: null, unread: false, done: false })
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selected = ref<number[]>([])
  /** Latest entries for the header bell; separate from the inbox list so filters there stay untouched. */
  const latest = ref<InboxEntry[]>([])
  const latestLoading = ref(false)
  const latestError = ref<string | null>(null)
  /** Dashboard section: up to three open tasks and three unread notices. */
  const dashboardTasks = ref<InboxEntry[]>([])
  const dashboardNotices = ref<InboxEntry[]>([])
  const hasMore = computed(() => entries.value.length < total.value)
  let timer: ReturnType<typeof setInterval> | null = null
  let listRequest = 0

  async function fetchEntries(append = false) {
    const request = ++listRequest
    loading.value = true
    error.value = null
    try {
      const { data } = await inboxApi.list({ ...filters.value, offset: append ? entries.value.length : 0 })
      if (request !== listRequest) return
      entries.value = append ? [...entries.value, ...data.results] : data.results
      total.value = data.count
      if (!append) selected.value = []
    } catch (err) {
      if (request === listRequest) error.value = getApiErrorMessage(err, 'Der Eingang konnte nicht geladen werden.')
    } finally {
      if (request === listRequest) loading.value = false
    }
  }

  async function fetchCounts() {
    try {
      const { data } = await inboxApi.counts()
      counts.value = { ...data, by_category: data.by_category ?? {} }
    } catch {
      // The badge keeps its last value when the network is down.
    }
  }

  async function fetchLatest(limit = 5) {
    latestLoading.value = true
    latestError.value = null
    try {
      latest.value = (await inboxApi.list({})).data.results.slice(0, limit)
    } catch (err) {
      latestError.value = getApiErrorMessage(err, 'Die Benachrichtigungen konnten nicht geladen werden.')
    } finally {
      latestLoading.value = false
    }
  }

  /** Dashboard lists; a failure hides the section instead of showing an error. */
  async function fetchDashboard() {
    const [tasks, notices] = await Promise.allSettled([
      inboxApi.list({ type: 'task' }),
      inboxApi.list({ type: 'notice', unread: true }),
    ])
    dashboardTasks.value = tasks.status === 'fulfilled' ? tasks.value.data.results.slice(0, 3) : []
    dashboardNotices.value = notices.status === 'fulfilled' ? notices.value.data.results.slice(0, 3) : []
  }

  function setFilters(patch: Partial<InboxFilters>) {
    filters.value = { ...filters.value, ...patch }
    return fetchEntries()
  }

  function replace(entry: InboxEntry) {
    const index = entries.value.findIndex(e => e.id === entry.id)
    if (index >= 0) entries.value[index] = entry
    latest.value = latest.value.map(e => e.id === entry.id ? entry : e)
    dashboardNotices.value = dashboardNotices.value.filter(e => e.id !== entry.id || !entry.read)
  }

  async function markRead(id: number) {
    const { data } = await inboxApi.markRead(id)
    replace(data)
    await fetchCounts()
    return data
  }

  async function markReadBulk(ids: number[] = selected.value) {
    if (!ids.length) return 0
    const { data } = await inboxApi.markReadBulk(ids)
    entries.value = entries.value.map(e => ids.includes(e.id) ? { ...e, read: true } : e)
    selected.value = selected.value.filter(id => !ids.includes(id))
    await fetchCounts()
    return data.updated
  }

  async function markDone(id: number) {
    const { data } = await inboxApi.markDone(id)
    // Done entries disappear unless "erledigte anzeigen" is on.
    if (data.task_state === 'done' && !filters.value.done) entries.value = entries.value.filter(e => e.id !== id)
    else replace(data)
    await fetchCounts()
    return data
  }

  function toggleSelected(id: number) {
    selected.value = selected.value.includes(id) ? selected.value.filter(i => i !== id) : [...selected.value, id]
  }

  const visible = () => typeof document === 'undefined' || document.visibilityState === 'visible'
  function onVisibility() { if (visible()) void fetchCounts() }

  /** Refreshes counts now and every 60 s while the tab is visible. */
  function startPolling() {
    stopPolling()
    void fetchCounts()
    timer = setInterval(() => { if (visible()) void fetchCounts() }, COUNTS_POLL_MS)
    document.addEventListener('visibilitychange', onVisibility)
  }

  function stopPolling() {
    if (timer) clearInterval(timer)
    timer = null
    document.removeEventListener('visibilitychange', onVisibility)
  }

  return { entries, total, counts, filters, loading, error, selected, hasMore, latest, latestLoading, latestError, dashboardTasks, dashboardNotices, fetchEntries, fetchCounts, fetchLatest, fetchDashboard, setFilters, markRead, markReadBulk, markDone, toggleSelected, startPolling, stopPolling }
})
