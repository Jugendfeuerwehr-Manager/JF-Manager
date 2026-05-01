<template>
  <div class="mobile-planner-page">
    <MobileTrainingPlanner :session-id="sessionId" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MobileTrainingPlanner from '@/components/training/organisms/MobileTrainingPlanner.vue'

const route = useRoute()
const sessionId = computed(() => Number(route.params.id))
</script>

<style scoped>
.mobile-planner-page {
  min-height: 100svh;
  background: var(--p-content-background);
}
</style>
