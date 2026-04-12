<template>
  <div class="dashboard">
    <div class="mb-4">
      <h1 class="text-4xl font-bold mb-2">Übersicht</h1>
      <p class="text-surface-600">Willkommen zurück, {{ authStore.userFullName }}</p>
    </div>

    <div class="grid">
      <div class="col-4 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Mitglieder</div>
                <div class="text-3xl font-bold">{{ stats.totalMembers }}</div>
              </div>
              <i class="pi pi-users text-4xl text-primary"></i>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-4 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Eltern</div>
                <div class="text-3xl font-bold">{{ stats.totalParents }}</div>
              </div>
              <i class="pi pi-user text-4xl text-blue-500"></i>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-4 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Qualifikationen</div>
                <div class="text-3xl font-bold">{{ stats.totalQualifications }}</div>
                <div v-if="stats.expiringQualifications > 0" class="text-xs text-orange-500 mt-1">
                  {{ stats.expiringQualifications }} laufen bald ab
                </div>
              </div>
              <i class="pi pi-certificate text-4xl text-purple-500"></i>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-4 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Inventar</div>
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
          <template #title>Letzte Aktivitäten</template>
          <template #content>
            <div class="text-center text-surface-500 py-4">
              <i class="pi pi-info-circle text-3xl mb-2"></i>
              <p>Aktivitätsverfolgung kommt bald...</p>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-12 lg:col-4">
        <Card>
          <template #title>Schnellzugriff</template>
          <template #content>
            <div class="flex flex-column gap-2">
              <Button
                label="Mitglied hinzufügen"
                icon="pi pi-user-plus"
                @click="$router.push('/members')"
                outlined
                class="w-full"
              />
              <Button
                label="Elternteil hinzufügen"
                icon="pi pi-user-plus"
                @click="$router.push('/parents')"
                outlined
                class="w-full"
              />
              <Button
                label="Inventar anzeigen"
                icon="pi pi-box"
                @click="$router.push('/inventory')"
                outlined
                class="w-full"
              />
              <Button
                label="Neue Bestellung"
                icon="pi pi-shopping-cart"
                @click="$router.push('/orders')"
                outlined
                class="w-full"
              />
              <Button
                label="Qualifikationen"
                icon="pi pi-certificate"
                @click="$router.push('/qualifications')"
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
import { useQualificationsStore } from '@/stores/qualifications'
import Card from 'primevue/card'
import Button from 'primevue/button'

const authStore = useAuthStore()
const membersStore = useMembersStore()
const parentsStore = useParentsStore()
const qualificationsStore = useQualificationsStore()

const stats = ref({
  totalMembers: 0,
  totalParents: 0,
  totalQualifications: 0,
  expiringQualifications: 0
})

onMounted(async () => {
  try {
    await Promise.all([
      membersStore.fetchMembers(),
      parentsStore.fetchParents(),
      qualificationsStore.fetchStatistics()
    ])

    stats.value = {
      totalMembers: membersStore.pagination.count,
      totalParents: parentsStore.pagination.count,
      totalQualifications: qualificationsStore.statistics?.total_qualifications || 0,
      expiringQualifications: qualificationsStore.statistics?.expiring_qualifications || 0
    }
  } catch {
  }
})
</script>


