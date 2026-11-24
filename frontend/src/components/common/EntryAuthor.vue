<template>
  <small v-if="label" class="entry-author">
    <i class="pi pi-user" aria-hidden="true"></i>
    <span>{{ label }}</span>
  </small>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { entryAuthorLabel } from '@/utils/entryAuthor'

interface Props {
  name?: string | null
  at?: string | null
}

const props = defineProps<Props>()
const label = computed(() => entryAuthorLabel(props.name, props.at))
</script>

<style scoped>
.entry-author {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--text-color-secondary);
  font-size: 0.8rem;
}

.entry-author .pi {
  font-size: 0.75rem;
}
</style>
