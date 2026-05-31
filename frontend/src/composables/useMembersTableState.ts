import { reactive } from 'vue'
import { useQueryTableState } from '@/composables/useQueryTableState'
import { useMembersStore } from '@/stores/members'
import type { MemberFilters, MemberLazyParams } from '@/types/members'

const URL_DEFAULTS = { offset: 0, rows: 20, sortField: 'lastname', sortOrder: 1 }

let filterDebounce: ReturnType<typeof setTimeout> | null = null

export function useMembersTableState() {
  const membersStore = useMembersStore()
  const { getInt, getString, syncToUrl } = useQueryTableState()

  const filters = reactive<MemberFilters>({
    search: getString('search'),
    status: getInt('status', 0) || null,
    group: getInt('group', 0) || null,
    gender: getString('gender'),
  })

  const lazyParams = reactive<MemberLazyParams>({
    first: getInt('offset', 0),
    rows: getInt('rows', 20),
    sortField: getString('sortField', 'lastname'),
    sortOrder: (getInt('sortOrder', 1) as 1 | -1),
  })

  function buildOrdering() {
    if (!lazyParams.sortField) return undefined
    return lazyParams.sortOrder === -1 ? `-${lazyParams.sortField}` : lazyParams.sortField
  }

  function persist() {
    syncToUrl(
      {
        search: filters.search,
        status: filters.status,
        group: filters.group,
        gender: filters.gender,
        offset: lazyParams.first,
        rows: lazyParams.rows,
        sortField: lazyParams.sortField,
        sortOrder: lazyParams.sortOrder,
      },
      URL_DEFAULTS,
    )
  }

  function loadData() {
    membersStore.fetchMembers({
      offset: lazyParams.first,
      limit: lazyParams.rows,
      search: filters.search || undefined,
      status: filters.status || undefined,
      group: filters.group || undefined,
      gender: filters.gender || undefined,
      ordering: buildOrdering(),
    })
  }

  function onPage(event: { first: number; rows: number }) {
    lazyParams.first = event.first
    lazyParams.rows = event.rows
    persist()
    loadData()
  }

  function onSort(event: import('primevue/datatable').DataTableSortEvent) {
    const sf = event.sortField
    lazyParams.sortField = (typeof sf === 'string' ? sf : undefined) || 'lastname'
    lazyParams.sortOrder = (event.sortOrder as 1 | -1) || 1
    persist()
    loadData()
  }

  function onFilterChange() {
    if (filterDebounce) clearTimeout(filterDebounce)
    filterDebounce = setTimeout(() => {
      lazyParams.first = 0
      persist()
      loadData()
    }, 500)
  }

  return { filters, lazyParams, loadData, onPage, onSort, onFilterChange }
}
