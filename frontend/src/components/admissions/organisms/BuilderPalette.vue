<template>
  <aside class="palette" aria-label="Bausteine">
    <label class="palette__search">
      <span>Baustein suchen</span>
      <input v-model="query" class="adm-input" type="search" placeholder="z. B. Schule, Foto …" />
    </label>

    <section v-for="group in groups" :key="group.name" class="palette__group" :aria-labelledby="`palette-${group.slug}`">
      <h3 :id="`palette-${group.slug}`" class="palette__title">{{ group.name }}</h3>
      <ul class="palette__list" :class="{ 'palette__list--grid': group.grid }">
        <li v-for="item in group.items" :key="item.id">
          <button
            type="button"
            class="palette__tile bld-draggable"
            :class="{ 'palette__tile--used': item.used }"
            :data-palette-id="item.id"
            :disabled="disabled || item.used"
            :title="item.used ? `${item.label} ist schon im Formular` : `${item.label}: ziehen oder antippen`"
            @click="pick(item)"
          >
            <i :class="item.used ? 'pi pi-check' : item.icon" aria-hidden="true"></i>
            <span>{{ item.label }}</span>
            <span v-if="item.used" class="sr-only">(schon verwendet)</span>
          </button>
        </li>
        <li v-if="group.name === 'Zusatzfelder'">
          <button type="button" class="palette__tile palette__tile--create" :disabled="disabled || !canCreateExtra" @click="emit('create-extra')">
            <i class="pi pi-plus" aria-hidden="true"></i>
            <span>Zusatzfeld anlegen</span>
          </button>
        </li>
      </ul>
    </section>
    <p class="palette__hint">Ausgegraut = schon im Formular. Diese Bausteine gibt es nur einmal.</p>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { BuilderReferences, FormSchema } from '@/types/admissions'
import { paletteItems, type PaletteGroup, type PaletteItem } from '@/utils/admissionSchema'
import '../atoms/admInput.css'

interface Props {
  schema: FormSchema
  references: BuilderReferences | null
  disabled?: boolean
  canCreateExtra?: boolean
}

const props = withDefaults(defineProps<Props>(), { disabled: false, canCreateExtra: false })
const emit = defineEmits<{
  (e: 'add', paletteId: string): void
  (e: 'create-extra'): void
  (e: 'pick-consent'): void
}>()

const GROUPS: { name: PaletteGroup; slug: string; grid: boolean }[] = [
  { name: 'Mitgliedsdaten', slug: 'member', grid: true },
  { name: 'Zusatzfelder', slug: 'extra', grid: false },
  { name: 'Personen & Rechtliches', slug: 'people', grid: false },
  { name: 'Inhalt', slug: 'content', grid: true }
]

const query = ref('')
const groups = computed(() => {
  const needle = query.value.trim().toLowerCase()
  const items = paletteItems(props.schema, props.references).filter(
    (item) => !needle || item.label.toLowerCase().includes(needle)
  )
  return GROUPS.map((group) => ({ ...group, items: items.filter((item) => item.group === group.name) })).filter(
    (group) => group.items.length || (group.name === 'Zusatzfelder' && !needle)
  )
})

function pick(item: PaletteItem) {
  // A consent needs a kind first; the dialog picks or creates one.
  if (item.id === 'consent') return emit('pick-consent')
  emit('add', item.id)
}
</script>

<style scoped>
.palette {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.palette__search {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
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
  grid-template-columns: minmax(0, 1fr);
  gap: var(--jf-space-0-5);
  list-style: none;
  margin: 0;
  padding: 0;
}

/* Short blocks as chips that keep whole words; long labels get a line of their own. */
.palette__list--grid {
  display: flex;
  flex-wrap: wrap;
}

.palette__list--grid .palette__tile {
  width: auto;
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
  overflow-wrap: break-word;
  hyphens: auto;
  cursor: grab;
  touch-action: none;
}

.palette__tile:hover:not(:disabled) {
  border-color: var(--jf-color-primary);
}

.palette__tile:focus-visible {
  outline: var(--jf-focus-ring);
  outline-offset: 2px;
}

.palette__tile--used {
  border-style: dashed;
  background: var(--jf-color-ground);
  color: var(--jf-color-text-muted);
  cursor: not-allowed;
}

.palette__tile:disabled:not(.palette__tile--used) {
  opacity: 0.55;
  cursor: not-allowed;
}

.palette__tile--create {
  border-style: dashed;
  color: var(--jf-color-primary);
  cursor: pointer;
  touch-action: auto;
}

.palette__hint {
  margin: 0;
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
