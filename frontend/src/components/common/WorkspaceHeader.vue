<template>
  <header class="workspace-head">
    <div class="workspace-head__info">
      <p class="workspace-head__eyebrow">
        <router-link :to="backTo" class="workspace-head__back"><i class="pi pi-arrow-left" aria-hidden="true"></i>{{ backLabel }}</router-link>
        <span v-if="eyebrow"> · {{ eyebrow }}</span>
      </p>
      <input
        v-if="editing"
        ref="titleInput"
        v-model="draft"
        class="workspace-head__title workspace-head__title-input"
        type="text"
        maxlength="200"
        aria-label="Titel"
        @keydown.enter.prevent="commit"
        @keydown.esc.prevent="editing = false"
        @blur="commit"
      />
      <h1 v-else class="workspace-head__title">
        <button
          v-if="editable"
          type="button"
          class="workspace-head__title-btn"
          v-tooltip.bottom="'Titel bearbeiten'"
          @click="startEdit"
        >{{ title }}<i class="pi pi-pencil" aria-hidden="true"></i></button>
        <template v-else>{{ title }}</template>
      </h1>
      <div v-if="$slots.meta" class="workspace-head__meta"><slot name="meta" /></div>
    </div>
    <div class="workspace-head__actions">
      <slot name="status" />
      <Button
        :icon="navHidden ? 'pi pi-window-minimize' : 'pi pi-window-maximize'"
        severity="secondary"
        text
        class="workspace-head__nav-toggle"
        :aria-label="navHidden ? 'Navigation einblenden' : 'Navigation ausblenden, mehr Platz zum Bearbeiten'"
        :aria-pressed="navHidden"
        v-tooltip.bottom="navHidden ? 'Navigation einblenden' : 'Mehr Platz: Navigation ausblenden'"
        @click="toggleNav"
      />
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import Button from 'primevue/button'
import type { RouteLocationRaw } from 'vue-router'
import { useWorkspaceNavigation } from '@/composables/useWorkspaceNavigation'

/** Header for workspace routes (meta.workspace): back link, title and the shared "hide navigation" toggle. */
const props = defineProps<{
  title: string
  backTo: RouteLocationRaw
  backLabel: string
  eyebrow?: string
  /** Click on the title edits it inline; emits `rename` with the trimmed new title. */
  editable?: boolean
}>()
const emit = defineEmits<{ rename: [title: string] }>()

const editing = ref(false)
const draft = ref('')
const titleInput = ref<HTMLInputElement | null>(null)

async function startEdit() {
  draft.value = props.title
  editing.value = true
  await nextTick()
  titleInput.value?.select()
}

function commit() {
  if (!editing.value) return
  editing.value = false
  const next = draft.value.trim()
  if (next && next !== props.title) emit('rename', next)
}

const { navHidden, toggleNav } = useWorkspaceNavigation()
</script>

<style scoped>
.workspace-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1-5) var(--jf-space-3);
  padding: var(--jf-space-1-5) var(--jf-space-3);
  background: var(--jf-color-card);
  border-bottom: 1px solid var(--jf-color-border);
  flex-shrink: 0;
}
.workspace-head__info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.workspace-head__eyebrow {
  margin: 0;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--jf-color-text-muted);
}
.workspace-head__back {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  min-height: var(--jf-touch-target);
  color: var(--jf-color-primary);
  text-decoration: none;
}
.workspace-head__back i { font-size: 0.7rem; }
.workspace-head__title-btn {
  all: unset;
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
  max-width: 100%;
  cursor: text;
  border-radius: var(--jf-radius-sm);
}
.workspace-head__title-btn i { font-size: 0.7rem; opacity: 0; color: var(--jf-color-text-muted); }
.workspace-head__title-btn:hover i, .workspace-head__title-btn:focus-visible i { opacity: 1; }
.workspace-head__title-btn:focus-visible { outline: 2px solid var(--jf-color-primary); outline-offset: 2px; }
.workspace-head__title-input {
  font: inherit;
  width: min(100%, 40rem);
  color: inherit;
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-primary);
  border-radius: var(--jf-radius-sm);
  padding: 0 var(--jf-space-1);
}
.workspace-head__title {
  margin: 0;
  font-size: var(--jf-text-xl);
  line-height: var(--jf-leading-tight);
  letter-spacing: -0.015em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workspace-head__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1);
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}
.workspace-head__actions { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1); }
/* The navigation can only be hidden next to the desktop sidebar. */
@media (max-width: 1023px) { .workspace-head__nav-toggle { display: none; } }
@media (max-width: 480px) { .workspace-head { padding: var(--jf-space-1-5) var(--jf-space-2); } }
</style>
