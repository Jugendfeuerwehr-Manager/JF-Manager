<template>
  <Tag class="duration-badge" :value="label" severity="secondary" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'
import { formatDuration } from '../utils/duration'

const props = defineProps<{ minutes: number }>()

// A duration is not a status: it stays neutral instead of turning red for long blocks.
const label = computed(() => formatDuration(props.minutes))
</script>

<style scoped>
.duration-badge { font-weight: var(--jf-weight-semibold); }
</style>
