<template>
  <div class="dashboard">
    <div class="mb-4">
      <h1 class="text-4xl font-bold mb-2">Dashboard</h1>
      <p class="text-surface-600">Welcome back, {{ authStore.userFullName }}</p>
    </div>

    <div class="grid">
      <div class="col-12 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Total Members</div>
                <div class="text-3xl font-bold">{{ stats.totalMembers }}</div>
              </div>
              <i class="pi pi-users text-4xl text-primary"></i>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-12 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Active Members</div>
                <div class="text-3xl font-bold">{{ stats.activeMembers }}</div>
              </div>
              <i class="pi pi-check-circle text-4xl text-green-500"></i>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-12 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Parents</div>
                <div class="text-3xl font-bold">{{ stats.totalParents }}</div>
              </div>
              <i class="pi pi-user text-4xl text-blue-500"></i>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-12 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Inventory Items</div>
                <div class="text-3xl font-bold">-</div>
              </div>
              <i class="pi pi-box text-4xl text-orange-500"></i>
            </div>
          </template>
        </Card>
      </div>
    </div>

    <div class="grid mt-4">
      <div class="col-12 lg:col-8">
        <Card>
          <template #title>Recent Activities</template>
          <template #content>
            <div class="text-center text-surface-500 py-4">
              <i class="pi pi-info-circle text-3xl mb-2"></i>
              <p>Activity tracking coming soon...</p>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-12 lg:col-4">
        <Card>
          <template #title>Quick Actions</template>
          <template #content>
            <div class="flex flex-column gap-2">
              <Button
                label="Add Member"
                icon="pi pi-user-plus"
                @click="$router.push('/members')"
                outlined
                class="w-full"
              />
              <Button
                label="Add Parent"
                icon="pi pi-user-plus"
                @click="$router.push('/parents')"
                outlined
                class="w-full"
              />
              <Button
                label="View Inventory"
                icon="pi pi-box"
                @click="$router.push('/inventory')"
                outlined
                class="w-full"
              />
              <Button
                label="New Order"
                icon="pi pi-shopping-cart"
                @click="$router.push('/orders')"
                outlined
                class="w-full"
              />
            </div>
          </template>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useMembersStore } from '@/stores/members'
import { useParentsStore } from '@/stores/parents'
import Card from 'primevue/card'
import Button from 'primevue/button'

const authStore = useAuthStore()
const membersStore = useMembersStore()
const parentsStore = useParentsStore()

const stats = ref({
  totalMembers: 0,
  activeMembers: 0,
  totalParents: 0
})

onMounted(async () => {
  try {
    await Promise.all([membersStore.fetchMembers(), parentsStore.fetchParents()])

    stats.value = {
      totalMembers: membersStore.pagination.count,
      activeMembers: membersStore.activeMembers.length,
      totalParents: parentsStore.pagination.count
    }
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
})
</script>


