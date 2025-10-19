<template>
  <Badge :value="isActive ? 'Aktiv' : 'Beendet'" :severity="isActive ? 'success' : 'secondary'" />
</template>

<script setup lang="ts">
import Badge from 'primevue/badge'

interface Props {
  isActive: boolean
}

defineProps<Props>()
</script>
