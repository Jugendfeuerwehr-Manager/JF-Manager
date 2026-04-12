<template>
  <Chip :label="typeName" class="qualification-type-chip" />
</template>

<script setup lang="ts">
import Chip from 'primevue/chip'

interface Props {
  typeName: string
}

defineProps<Props>()
</script>

<style scoped>
.qualification-type-chip {
  font-size: 0.875rem;
}
</style>
