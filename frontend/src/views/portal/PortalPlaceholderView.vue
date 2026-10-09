<script setup lang="ts">
import { useRoute } from 'vue-router'
import PortalEmptyCard from '@/components/portal/PortalEmptyCard.vue'

defineProps<{ icon: string, title: string, text: string }>()

const route = useRoute()
</script>

<template>
  <div class="page">
    <h1>{{ title }}</h1>
    <PortalEmptyCard :icon="icon" :title="route?.name === 'portal-sessions' ? 'Noch keine Termine' : title">
      {{ route?.name === 'portal-sessions' ? 'Sobald Dienste veröffentlicht sind, kannst du hier an- und abmelden.' : text }}
    </PortalEmptyCard>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
h1 { margin: 4px 0 0; font-size: 18px; font-weight: 700; }
h2 { margin: 0; font-size: 15px; font-weight: 700; }
</style>
