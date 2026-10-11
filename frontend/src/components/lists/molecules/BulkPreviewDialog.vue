<template>
  <Dialog
    :visible="visible"
    :header="title"
    modal
    :closable="!busy"
    :style="{ width: 'min(520px, 95vw)' }"
    @update:visible="(value: boolean) => { if (!value) emit('cancel') }"
  >
    <div class="bulk-preview">
      <p class="bulk-preview__intro">{{ intro }}</p>
      <p v-if="note" class="bulk-preview__note"><i class="pi pi-info-circle" aria-hidden="true"></i>{{ note }}</p>
      <ul v-if="names.length" class="bulk-preview__names" :aria-label="`Betroffen: ${names.length}`">
        <li v-for="name in names" :key="name">{{ name }}</li>
      </ul>
      <p v-else class="bulk-preview__empty">Niemand ist betroffen. Es gibt nichts zu ändern.</p>
    </div>
    <template #footer>
      <Button label="Abbrechen" text :disabled="busy" @click="emit('cancel')" />
      <Button
        :label="confirmLabel"
        :icon="danger ? 'pi pi-exclamation-triangle' : 'pi pi-check'"
        :severity="danger ? 'danger' : undefined"
        :disabled="!names.length"
        :loading="busy"
        @click="emit('confirm')"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

/** Shows exactly who a bulk action changes before it runs (UX-03.1). */
withDefaults(
  defineProps<{
    visible: boolean
    title: string
    intro: string
    names: string[]
    confirmLabel: string
    note?: string
    danger?: boolean
    busy?: boolean
  }>(),
  { note: '', danger: false, busy: false },
)

const emit = defineEmits<{ confirm: []; cancel: [] }>()
</script>

<style scoped>
.bulk-preview {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
}
.bulk-preview__intro,
.bulk-preview__note,
.bulk-preview__empty { margin: 0; }
.bulk-preview__note {
  display: flex;
  gap: var(--jf-space-1);
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}
.bulk-preview__names {
  max-height: 40vh;
  overflow-y: auto;
  margin: 0;
  padding: var(--jf-space-1) var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
  columns: 2 180px;
  column-gap: var(--jf-space-3);
}
.bulk-preview__names li {
  padding: 2px 0;
  break-inside: avoid;
  overflow-wrap: anywhere;
}
.bulk-preview__empty { color: var(--jf-color-text-muted); }
</style>
