<template>
  <StateView
    v-if="!templates.length"
    kind="empty"
    title="Noch keine eigenen Vorlagen"
    message="Alle E-Mails nutzen die Standardvorlagen. Eine eigene Vorlage ersetzt die Standardvorlage ihres Typs."
  >
    <Button v-if="canCreate" label="Erste Vorlage erstellen" icon="pi pi-plus" @click="$emit('create')" />
  </StateView>
  <ul v-else class="template-list">
    <li v-for="template in templates" :key="template.id" class="template-row">
      <button type="button" class="template-row__main" :aria-label="`${template.template_type_display} bearbeiten`" @click="$emit('edit', template.id)">
        <span class="template-row__icon" aria-hidden="true"><i class="pi pi-envelope"></i></span>
        <span class="template-row__text">
          <span class="template-row__title">{{ template.template_type_display }}</span>
          <span class="template-row__meta">{{ template.name }} · {{ template.layout_display }} · geändert {{ formatDate(template.updated_at) }}</span>
        </span>
        <StatusBadge
          :label="template.is_active ? 'Aktiv' : 'Inaktiv'"
          :severity="template.is_active ? 'success' : 'neutral'"
        />
        <i class="pi pi-chevron-right template-row__chevron" aria-hidden="true"></i>
      </button>
      <Button
        icon="pi pi-trash"
        text
        severity="danger"
        class="template-row__delete"
        :aria-label="`${template.template_type_display} löschen`"
        v-tooltip.top="'Löschen'"
        @click="$emit('delete', template.id)"
      />
    </li>
  </ul>
</template>

<script setup lang="ts">
import { format } from 'date-fns'
import Button from 'primevue/button'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { EmailTemplateList } from '@/types/email-templates'

interface Props {
  templates: EmailTemplateList[]
  canCreate?: boolean
}

interface Emits {
  (e: 'edit', id: number): void
  (e: 'delete', id: number): void
  (e: 'create'): void
}

withDefaults(defineProps<Props>(), { canCreate: true })
defineEmits<Emits>()

function formatDate(dateString: string): string {
  return format(new Date(dateString), 'dd.MM.yyyy')
}
</script>

<style scoped>
.template-list {
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  overflow: hidden;
}

.template-row {
  display: flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  padding-right: var(--jf-space-1);
}

.template-row + .template-row { border-top: 1px solid var(--jf-color-border); }

.template-row__main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  min-height: 64px;
  padding: var(--jf-space-1) var(--jf-space-2);
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.template-row__main:hover { background: var(--surface-hover); }
.template-row__main:focus-visible { outline: var(--jf-focus-ring); outline-offset: -2px; }

.template-row__icon {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-selected);
  color: var(--jf-color-selected-text);
}

.template-row__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.template-row__title { font-weight: var(--jf-weight-semibold); }

.template-row__meta {
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-row__chevron { color: var(--jf-color-text-muted); font-size: 0.75rem; }
.template-row__delete { flex-shrink: 0; min-width: var(--jf-touch-target); min-height: var(--jf-touch-target); }

@media (max-width: 480px) {
  .template-row__main { padding: var(--jf-space-1) var(--jf-space-1-5); gap: var(--jf-space-1); }
  .template-row__icon, .template-row__chevron { display: none; }
}
</style>
