<template>
  <StatusBadge
    v-if="count === 0"
    severity="warning"
    label="Ohne Mitglied"
    v-tooltip.top="'Mit keinem sichtbaren Mitglied verknüpft'"
  />
  <StatusBadge v-else severity="neutral" icon="pi pi-users" :label="count === 1 ? '1 Mitglied' : `${count} Mitglieder`" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { Parent } from '@/types/parents'

const props = defineProps<{ parent: Pick<Parent, 'children'> }>()

const count = computed(() => props.parent.children?.length ?? 0)
</script>
