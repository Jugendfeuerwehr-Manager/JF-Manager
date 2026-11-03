<template>
  <aside class="palette" aria-label="Bausteine">
    <section v-for="group in groups" :key="group.name" class="palette__group">
      <h3 class="palette__title">{{ group.name }}</h3>
      <ul class="palette__list">
        <li v-for="entry in group.entries" :key="entry.type">
          <button
            type="button"
            class="palette__tile bld-draggable"
            :data-type="entry.type"
            :disabled="disabled"
            :title="`${entry.label}: ziehen oder antippen`"
            @click="emit('add', entry.type)"
          >
            <i :class="entry.icon" aria-hidden="true"></i>
            <span>{{ entry.label }}</span>
          </button>
        </li>
      </ul>
    </section>
  </aside>
</template>

<script setup lang="ts">
import type { ElementType } from '@/types/admissions'
import { PALETTE, type PaletteEntry } from '@/utils/admissionSchema'

withDefaults(defineProps<{ disabled?: boolean }>(), { disabled: false })
const emit = defineEmits<{ (e: 'add', type: ElementType): void }>()

const groups = (['Eingabe', 'Inhalt', 'Rechtliches', 'Personen'] as const).map((name) => ({
  name,
  entries: PALETTE.filter((entry: PaletteEntry) => entry.group === name)
}))
</script>

<style scoped>
.palette {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.palette__title {
  margin: 0 0 var(--jf-space-0-5);
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.palette__list {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--jf-space-0-5);
  list-style: none;
  margin: 0;
  padding: 0;
}

.palette__tile {
  display: flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  width: 100%;
  min-height: var(--jf-touch-target, 44px);
  padding: var(--jf-space-0-5) var(--jf-space-1);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
  font-size: var(--jf-text-sm);
  text-align: left;
  cursor: grab;
  touch-action: none;
}

.palette__tile:hover:not(:disabled) {
  border-color: var(--jf-color-primary);
}

.palette__tile:focus-visible {
  outline: none;
  outline: var(--jf-focus-ring);
  outline-offset: 2px;
}
</style>
