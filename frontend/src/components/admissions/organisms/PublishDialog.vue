<template>
  <dialog ref="dialog" class="adm-dialog" aria-labelledby="publish-title" @close="emit('close')">
    <form class="adm-dialog__body" @submit.prevent="emit('publish', note)">
      <h2 id="publish-title">Version {{ nextVersion }} veröffentlichen</h2>
      <p class="publish__lead">
        Neue Anträge nutzen ab sofort diese Fassung. Eingereichte Anträge behalten ihre Version und ihr Siegel.
      </p>

      <ul class="publish__checks">
        <li v-for="check in checks" :key="check.title" class="publish__check" :class="{ 'publish__check--open': !check.ok }">
          <span class="publish__mark" aria-hidden="true">{{ check.ok ? '✓' : '!' }}</span>
          <div>
            <strong>{{ check.title }}</strong>
            <p v-if="check.detail">{{ check.detail }}</p>
            <RouterLink v-if="check.link" :to="check.link.to" class="publish__link" @click="close">{{ check.link.label }} →</RouterLink>
          </div>
        </li>
      </ul>

      <AdmField input-id="change-note" label="Änderungshinweis (optional)">
        <input id="change-note" v-model="note" class="adm-input" maxlength="300" />
      </AdmField>
      <p v-if="error" class="publish__error" role="alert">{{ error }}</p>

      <div class="adm-dialog__actions">
        <AdmButton variant="ghost" @click="close">Abbrechen</AdmButton>
        <AdmButton variant="primary" type="submit" icon="pi pi-send" :loading="saving" :disabled="openCount > 0">
          {{ openCount ? `Erst ${openCount} ${openCount === 1 ? 'Punkt' : 'Punkte'} klären` : 'Veröffentlichen' }}
        </AdmButton>
      </div>
    </form>
  </dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import AdmButton from '../atoms/AdmButton.vue'
import AdmField from '../atoms/AdmField.vue'
import '../atoms/admInput.css'

export interface PublishCheck {
  ok: boolean
  title: string
  detail?: string
  link?: { to: RouteLocationRaw; label: string }
}

interface Props {
  open: boolean
  nextVersion: number
  checks: PublishCheck[]
  saving?: boolean
  error?: string | null
}

const props = withDefaults(defineProps<Props>(), { saving: false, error: null })
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'publish', note: string): void
}>()

const dialog = ref<HTMLDialogElement | null>(null)
const note = ref('')
const openCount = computed(() => props.checks.filter((check) => !check.ok).length)

watch(
  () => props.open,
  (open) => {
    if (!dialog.value) return
    if (!open) return dialog.value.open && dialog.value.close()
    note.value = ''
    dialog.value.showModal()
  }
)

function close() {
  dialog.value?.close()
}
</script>

<style scoped>
.adm-dialog {
  width: min(34rem, calc(100vw - 2rem));
  padding: 0;
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
}

.adm-dialog::backdrop {
  background: var(--jf-color-backdrop);
}

.adm-dialog__body {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-3);
}

.adm-dialog__body h2 {
  margin: 0;
  font-size: var(--jf-text-lg);
}

.publish__lead {
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.publish__checks {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  max-height: 22rem;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.publish__check {
  display: flex;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
}

.publish__check p {
  margin: var(--jf-space-0-5) 0 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.publish__check--open {
  border-color: var(--jf-color-warning);
  background: var(--jf-color-warning-surface);
}

.publish__check--open p {
  color: var(--jf-color-warning);
}

.publish__mark {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: var(--jf-color-success-surface);
  color: var(--jf-color-success);
  font-weight: var(--jf-weight-semibold);
}

.publish__check--open .publish__mark {
  background: var(--jf-color-card);
  color: var(--jf-color-warning);
}

.publish__link {
  display: inline-block;
  margin-top: var(--jf-space-0-5);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-primary);
}

.publish__error {
  margin: 0;
  color: var(--jf-color-danger);
}

.adm-dialog__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--jf-space-1);
}
</style>
