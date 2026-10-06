<template>
  <div class="planner-page">
    <SwimlaneEditor :session-id="sessionId" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SwimlaneEditor from '@/components/training/organisms/SwimlaneEditor.vue'

const route = useRoute()
const router = useRouter()
const sessionId = computed(() => Number(route.params.id))

// Redirect mobile / touch-primary devices to the mobile-optimised read-only view
if (typeof window !== 'undefined' && window.matchMedia('(pointer: coarse)').matches) {
  router.replace({ name: 'training-mobile', params: { id: route.params.id } })
}
</script>

<style scoped>
.planner-page {
  /* Fills the content area next to the navigation; the route is marked full-width in the router. */
  height: calc(100dvh - var(--topbar-height, 64px));
  display: flex;
  flex-direction: column;
  background: var(--jf-color-ground);
}
</style>
