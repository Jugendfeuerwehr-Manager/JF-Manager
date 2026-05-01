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
  /* Fixed overlay below the 70px topbar — most reliable for full-height planners */
  position: fixed;
  top: 70px;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background: var(--p-content-background);
  z-index: 1;
}
</style>
