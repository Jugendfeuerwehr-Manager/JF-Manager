<template>
  <span v-if="status" class="member-status">
    <span class="member-status__dot" :style="{ backgroundColor: status.color || 'var(--jf-color-text-muted)' }" aria-hidden="true"></span>
    {{ status.name }}
  </span>
</template>

<script setup lang="ts">
import type { Status } from '@/types/members'

/** Organisation-defined status: the name carries the meaning, the colour only marks it. */
defineProps<{ status: Status | null }>()
</script>

<style scoped>
.member-status {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  padding: 2px var(--jf-space-1);
  border-radius: 999px;
  background: var(--surface-hover);
  color: var(--jf-color-text);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  line-height: 1.5;
  white-space: nowrap;
}

.member-status__dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  box-shadow: 0 0 0 1px rgba(23, 32, 51, 0.15);
}
</style>
