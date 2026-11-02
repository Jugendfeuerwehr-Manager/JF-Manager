/**
 * Background cache warmup for the members and parents modules.
 *
 * Prefetches the default (first page) list for each module into their Pinia
 * stores so that navigating to /members or /parents can render from the
 * already-populated store instead of waiting on a network request.
 *
 * The servicebook is left out on purpose: its list is always time-scoped
 * (upcoming ascending, past descending), and an unscoped warmup response that
 * arrived late overwrote the upcoming list with all services, newest first.
 *
 * Warmup is scoped to the currently active department/realm because the
 * axios request interceptor (see `api/index.ts`) automatically attaches the
 * `department` query param read from localStorage. Re-run `warmupStores()`
 * whenever the active department changes so cached data matches the new realm.
 */
import { watch } from 'vue'
import { useMembersStore } from '@/stores/members'
import { useParentsStore } from '@/stores/parents'
import { useDepartmentsStore } from '@/stores/departments'
import { useAuthStore } from '@/stores/auth'

let warming = false
let watcherStarted = false

export function useWarmup() {
  async function warmupStores() {
    // Avoid overlapping warmup runs (e.g. rapid department switches)
    if (warming) return
    warming = true

    const membersStore = useMembersStore()
    const parentsStore = useParentsStore()

    try {
      await Promise.allSettled([
        membersStore.fetchMembers({ offset: 0, limit: 20, ordering: 'lastname' }),
        membersStore.fetchStatuses(),
        membersStore.fetchGroups(),
        parentsStore.fetchParents({ offset: 0, limit: 20 }),
      ])
    } finally {
      warming = false
    }
  }

  /**
   * Re-run warmup whenever the active department (realm) changes, so
   * cached data always matches the currently selected tenant scope.
   * Safe to call multiple times — only registers the watcher once.
   */
  function watchDepartmentChanges() {
    if (watcherStarted) return
    watcherStarted = true

    const departmentsStore = useDepartmentsStore()
    const authStore = useAuthStore()

    watch(
      () => departmentsStore.activeDepartmentId,
      () => {
        if (authStore.isAuthenticated) {
          warmupStores()
        }
      },
    )
  }

  return { warmupStores, watchDepartmentChanges }
}
