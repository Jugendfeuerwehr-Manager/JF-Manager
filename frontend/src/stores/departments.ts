/**
 * Pinia store for multi-department support.
 *
 * Manages available departments, the "active" department filter,
 * and persists the selection to localStorage.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { departmentsApi } from '@/api/departments'
import type { Department } from '@/types/departments'
import type { UserInfo } from '@/types/common'

const STORAGE_KEY = 'activeDepartmentId'

export const useDepartmentsStore = defineStore('departments', () => {
  // State
  const departments = ref<Department[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Active department — null means "All Departments"
  const activeDepartmentId = ref<number | null>(
    (() => {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored ? Number(stored) : null
    })(),
  )

  // Computed
  const activeDepartment = computed<Department | null>(
    () => departments.value.find((d) => d.id === activeDepartmentId.value) ?? null,
  )

  const isAllDepartments = computed(() => activeDepartmentId.value === null)

  const activeDepartments = computed<Department[]>(() => {
    if (isAllDepartments.value) return departments.value
    return activeDepartment.value ? [activeDepartment.value] : []
  })

  // Actions
  async function fetchDepartments() {
    loading.value = true
    error.value = null
    try {
      const response = await departmentsApi.list()
      departments.value = response.data.results
    } catch (err) {
      error.value = 'Fehler beim Laden der Abteilungen'
      console.error('Failed to fetch departments:', err)
    } finally {
      loading.value = false
    }
  }

  function setActiveDepartment(id: number | null) {
    // The active department drives request context and permission evaluation.
    // It does not mean "hide central/shared records"; the backend may still
    // return department=NULL data for features that are globally visible.
    activeDepartmentId.value = id
    if (id === null) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      localStorage.setItem(STORAGE_KEY, String(id))
    }
  }

  /**
   * Set the default active department based on user info.
   *
   * Rules:
   * - Staff / org-wide users: default to "All Departments" (null), unless they
   *   have a favorite_department that exists in the loaded list.
   * - Dept-scoped users: use the stored localStorage value if it still maps to
   *   one of their accessible departments; otherwise fall back to their first dept.
   * - Only runs if no valid selection is already active.
   */
  function initializeActiveDepartment(user: UserInfo) {
    const isOrgWide = user.has_org_wide_access || user.is_superuser || user.is_staff

    if (isOrgWide) {
      const favId = user.favorite_department
      // If they have a favorite and it exists in the loaded list, use it
      if (favId !== null && favId !== undefined && departments.value.some((d) => d.id === favId)) {
        setActiveDepartment(favId)
      } else {
        // Default staff to "All Departments"
        setActiveDepartment(null)
      }
      return
    }

    // Dept-scoped user: validate stored value or fall back to first dept
    const accessibleDeptIds = user.department_roles.map((r) => r.department_id)
    if (accessibleDeptIds.length === 0) {
      setActiveDepartment(null)
      return
    }

    const stored = activeDepartmentId.value
    if (stored !== null && accessibleDeptIds.includes(stored)) {
      // Current stored value is valid — keep it
      return
    }

    // Fall back to first accessible department
    setActiveDepartment(accessibleDeptIds[0] ?? null)
  }

  function clearDepartments() {
    departments.value = []
    activeDepartmentId.value = null
    localStorage.removeItem(STORAGE_KEY)
  }

  return {
    // State
    departments,
    loading,
    error,
    activeDepartmentId,
    // Computed
    activeDepartment,
    isAllDepartments,
    activeDepartments,
    // Actions
    fetchDepartments,
    setActiveDepartment,
    initializeActiveDepartment,
    clearDepartments,
  }
})
