<template>
  <Badge :value="badgeText" :severity="badgeSeverity" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Badge from 'primevue/badge'
import type { BadgeSeverity } from '@/types/qualifications'

interface Props {
  isExpired: boolean
  expiresSoon: boolean
}

const props = defineProps<Props>()

const badgeText = computed(() => {
  if (props.isExpired) return 'Abgelaufen'
  if (props.expiresSoon) return 'Läuft bald ab'
  return 'Gültig'
})

const badgeSeverity = computed<BadgeSeverity>(() => {
  if (props.isExpired) return 'danger'
  if (props.expiresSoon) return 'warning'
  return 'success'
})
</script>
