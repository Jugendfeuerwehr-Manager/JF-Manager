<script setup lang="ts">
import { computed } from 'vue'
import { usePortalStore } from '@/stores/portal'

const portal = usePortalStore()
const people = computed(() => portal.me?.people ?? [])

function initials(first: string, last: string) {
  return `${first.charAt(0)}${last.charAt(0)}`.toUpperCase()
}
// Age is not part of /portal/me/ yet, so only the first name is shown.
function label(person: { relation: string, first_name: string }) {
  return person.relation === 'self' ? 'Ich' : person.first_name
}
</script>

<template>
  <div v-if="people.length > 1" role="tablist" aria-label="Person wählen" class="switcher">
    <button
      v-for="person in people" :key="person.id" type="button" role="tab" class="chip"
      :class="{ active: portal.selectedPersonId === person.id }"
      :aria-selected="portal.selectedPersonId === person.id"
      @click="portal.selectPerson(person.id)"
    >
      <span v-if="person.relation !== 'self'" class="avatar" aria-hidden="true">{{ initials(person.first_name, person.last_name) }}</span>
      {{ label(person) }}
    </button>
  </div>
</template>

<style scoped>
.switcher { display: flex; gap: 8px; overflow-x: auto; padding: 2px; margin: -2px; }
.chip { flex: none; display: inline-flex; align-items: center; gap: 8px; height: 44px; padding: 0 14px; border-radius: 22px; border: 1px solid var(--p-content-border-color); background: var(--p-content-background); color: var(--p-text-color); font: inherit; font-size: 14px; cursor: pointer; box-sizing: border-box; }
.chip.active { border: 2px solid var(--p-primary-color); padding: 0 13px; background: color-mix(in srgb, var(--p-primary-color), transparent 90%); font-weight: 650; }
.avatar { width: 24px; height: 24px; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; background: var(--p-surface-200); color: var(--p-text-color); }
.chip.active .avatar { background: var(--p-primary-color); color: var(--p-primary-contrast-color); }
.app-dark .avatar { background: var(--p-surface-700); }
.app-dark .chip.active .avatar { background: var(--p-primary-color); }
</style>
