<script setup lang="ts">
import { onMounted } from 'vue'
import PortalSessionList from '@/components/portal/PortalSessionList.vue'
import { usePortalStore } from '@/stores/portal'

const portal = usePortalStore()
onMounted(() => { if (!portal.me && !portal.loading) void portal.fetchMe() })
</script>

<template>
  <div class="page">
    <div class="heading">
      <h1>Termine</h1>
      <span v-if="portal.selectedPerson" class="for">für {{ portal.selectedPerson.relation === 'self' ? 'dich' : portal.selectedPerson.first_name }}</span>
    </div>
    <PortalSessionList grouped />
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
.heading { display: flex; align-items: baseline; justify-content: space-between; margin-top: 4px; }
h1 { margin: 0; font-size: 18px; font-weight: 700; }
.for { font-size: 13px; color: var(--p-text-muted-color); }
</style>
