import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  AdminUser,
  AdminUserDetail,
  AdminUserWrite,
  AuthGroup,
  AuthGroupDetail,
  AuthGroupWrite,
  Permission,
  PermissionCategory,
} from '@/types/admin'
import { adminUsersApi, adminGroupsApi, adminPermissionsApi } from '@/api/admin'
import type { AdminUserListParams } from '@/api/admin'

const APP_LABEL_MAP: Record<string, { label: string; icon: string }> = {
  members: { label: 'Mitglieder', icon: 'pi pi-users' },
  orders: { label: 'Bestellungen', icon: 'pi pi-shopping-cart' },
  inventory: { label: 'Inventar', icon: 'pi pi-box' },
  training: { label: 'Training', icon: 'pi pi-calendar' },
  servicebook: { label: 'Dienstbuch', icon: 'pi pi-book' },
  qualifications: { label: 'Qualifikationen', icon: 'pi pi-crown' },
  users: { label: 'Benutzer', icon: 'pi pi-user' },
  auth: { label: 'Berechtigungen', icon: 'pi pi-lock' },
  settings_manager: { label: 'Einstellungen', icon: 'pi pi-cog' },
}

export const useAdminStore = defineStore('admin', () => {
  // Users state
  const users = ref<AdminUser[]>([])
  const usersLoading = ref(false)
  const usersTotalCount = ref(0)

  // Groups state
  const groups = ref<AuthGroup[]>([])
  const groupsLoading = ref(false)
  const groupsTotalCount = ref(0)

  // Permissions state
  const permissions = ref<Permission[]>([])
  const permissionsLoading = ref(false)

  // Computed
  const permissionCategories = computed<PermissionCategory[]>(() => {
    const categoryMap = new Map<string, Permission[]>()
    for (const perm of permissions.value) {
      const key = perm.app_label
      if (!categoryMap.has(key)) {
        categoryMap.set(key, [])
      }
      categoryMap.get(key)!.push(perm)
    }
    return Array.from(categoryMap.entries()).map(([key, perms]) => ({
      label: APP_LABEL_MAP[key]?.label ?? key,
      icon: APP_LABEL_MAP[key]?.icon ?? 'pi pi-cog',
      permissions: perms,
    }))
  })

  // User actions
  async function fetchUsers(params?: AdminUserListParams) {
    usersLoading.value = true
    try {
      const response = await adminUsersApi.list(params)
      users.value = response.data.results
      usersTotalCount.value = response.data.count
      return users.value
    } finally {
      usersLoading.value = false
    }
  }

  async function fetchUser(id: number): Promise<AdminUserDetail> {
    const response = await adminUsersApi.get(id)
    return response.data
  }

  async function createUser(data: AdminUserWrite) {
    const response = await adminUsersApi.create(data)
    return response.data
  }

  async function updateUser(id: number, data: Partial<AdminUserWrite>) {
    const response = await adminUsersApi.update(id, data)
    return response.data
  }

  async function deleteUser(id: number) {
    await adminUsersApi.delete(id)
  }

  async function setUserGroups(userId: number, groupIds: number[]) {
    const response = await adminUsersApi.setGroups(userId, groupIds)
    return response.data
  }

  // Group actions
  async function fetchGroups(params?: { search?: string; limit?: number; offset?: number }) {
    groupsLoading.value = true
    try {
      const response = await adminGroupsApi.list(params)
      groups.value = response.data.results
      groupsTotalCount.value = response.data.count
      return groups.value
    } finally {
      groupsLoading.value = false
    }
  }

  async function fetchGroup(id: number): Promise<AuthGroupDetail> {
    const response = await adminGroupsApi.get(id)
    return response.data
  }

  async function createGroup(data: AuthGroupWrite) {
    const response = await adminGroupsApi.create(data)
    return response.data
  }

  async function updateGroup(id: number, data: Partial<AuthGroupWrite>) {
    const response = await adminGroupsApi.update(id, data)
    return response.data
  }

  async function deleteGroup(id: number) {
    await adminGroupsApi.delete(id)
  }

  // Permission actions
  async function fetchPermissions() {
    if (permissions.value.length > 0) return permissions.value
    permissionsLoading.value = true
    try {
      const response = await adminPermissionsApi.list({ limit: 500 })
      permissions.value = response.data.results
      return permissions.value
    } finally {
      permissionsLoading.value = false
    }
  }

  return {
    // Users
    users,
    usersLoading,
    usersTotalCount,
    fetchUsers,
    fetchUser,
    createUser,
    updateUser,
    deleteUser,
    setUserGroups,

    // Groups
    groups,
    groupsLoading,
    groupsTotalCount,
    fetchGroups,
    fetchGroup,
    createGroup,
    updateGroup,
    deleteGroup,

    // Permissions
    permissions,
    permissionsLoading,
    permissionCategories,
    fetchPermissions,
  }
})
