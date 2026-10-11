<template>
  <Dialog
    :visible="visible"
    modal
    header="Vor dem Versand prüfen"
    class="email-send-review"
    :style="{ width: 'min(60rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '768px': '100vw' }"
    @update:visible="emit('update:visible', $event)"
  >
    <StateView v-if="loading && !check" kind="loading" title="Empfänger werden geprüft …" />
    <StateView v-else-if="error" kind="error" title="Prüfung fehlgeschlagen" :message="error" @retry="emit('retry')" />
    <div v-else-if="check" class="review">
      <section class="review-summary" aria-label="Zusammenfassung">
        <p class="review-count">
          <strong>{{ check.count }}</strong>
          {{ check.count === 1 ? 'E-Mail wird' : 'E-Mails werden' }} an
          {{ check.member_count }} {{ check.member_count === 1 ? 'Mitglied' : 'Mitglieder' }} und deren Eltern gesendet.
        </p>
        <div class="review-badges">
          <StatusBadge
            v-if="check.count > 0"
            severity="success"
            :label="`${check.count} ${check.count === 1 ? 'Empfänger' : 'Empfänger'} geprüft`"
          />
          <StatusBadge v-else severity="danger" label="Keine Empfänger" />
          <StatusBadge
            v-if="check.excluded.length"
            severity="warning"
            :label="`${check.excluded.length} ausgeschlossen`"
          />
          <StatusBadge
            v-if="check.personalized"
            severity="info"
            icon="pi pi-user-edit"
            label="Persönliche Anrede je Mitglied"
          />
        </div>
        <p v-if="check.merged_duplicates" class="review-hint">
          {{ check.merged_duplicates }} doppelte {{ check.merged_duplicates === 1 ? 'Adresse wurde' : 'Adressen wurden' }}
          zusammengefasst (gleiche Nachricht an dieselbe Adresse).
        </p>
        <p v-if="check.personalized" class="review-hint">
          Die Nachricht enthält Platzhalter. Geschwister mit derselben Eltern-Adresse erhalten deshalb je eine eigene E-Mail.
        </p>
      </section>

      <section v-if="check.excluded.length" class="review-section" aria-labelledby="review-excluded">
        <h3 id="review-excluded">Ausgeschlossen</h3>
        <ul class="review-list">
          <li v-for="(item, index) in check.excluded" :key="`${item.member_id}-${index}`" class="review-item">
            <div class="review-item-main">
              <strong>{{ item.member_name }}</strong>
              <span v-if="item.email" class="review-muted">{{ relationLabel(item.relation) }}: {{ item.email }}</span>
            </div>
            <StatusBadge severity="warning" :label="item.reason" />
          </li>
        </ul>
      </section>

      <section v-if="check.recipients.length" class="review-section" aria-labelledby="review-recipients">
        <details class="review-details">
          <summary>
            <h3 id="review-recipients">Empfängerliste ({{ check.recipients.length }})</h3>
          </summary>
          <ul class="review-list">
            <li v-for="(item, index) in check.recipients" :key="`${item.email}-${item.member_id}-${index}`" class="review-item">
              <div class="review-item-main">
                <strong>{{ item.name }}</strong>
                <span class="review-muted">{{ item.email }}</span>
              </div>
              <span class="review-muted">{{ relationLabel(item.relation) }} · {{ item.member_name }}</span>
            </li>
          </ul>
        </details>
      </section>

      <section class="review-section" aria-labelledby="review-preview">
        <div class="review-preview-head">
          <h3 id="review-preview">Vorschau</h3>
          <Select
            v-if="previewOptions.length > 1"
            :model-value="previewMemberId"
            :options="previewOptions"
            option-label="label"
            option-value="value"
            aria-label="Vorschau für Mitglied"
            class="review-preview-select"
            @update:model-value="emit('update:previewMemberId', $event)"
          />
        </div>
        <p class="review-subject"><span class="review-muted">Betreff:</span> {{ subject }}</p>
        <StateView v-if="previewLoading" kind="loading" title="Vorschau wird erstellt …" />
        <StateView
          v-else-if="previewError"
          kind="error"
          title="Vorschau nicht verfügbar"
          :message="previewError"
          @retry="emit('retryPreview')"
        />
        <SafeEmailPreview v-else-if="previewHtml !== null" class="review-frame" :html="previewHtml" />
        <p v-else class="review-muted">Für die Vorschau ist mindestens ein Empfänger nötig.</p>
      </section>
    </div>

    <template #footer>
      <div class="review-actions">
        <Button
          label="Zurück zum Bearbeiten"
          icon="pi pi-arrow-left"
          severity="secondary"
          outlined
          :disabled="sending"
          @click="emit('update:visible', false)"
        />
        <Button
          :label="sendLabel"
          icon="pi pi-send"
          :loading="sending"
          :disabled="!check || check.count === 0 || loading"
          @click="emit('send')"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import SafeEmailPreview from '@/components/common/SafeEmailPreview.vue'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { EmailRecipientCheckResponse } from '@/types/emails'

interface Props {
  visible: boolean
  check: EmailRecipientCheckResponse | null
  loading?: boolean
  error?: string | null
  subject: string
  previewHtml: string | null
  previewMemberId: number | null
  previewLoading?: boolean
  previewError?: string | null
  sending?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
  previewLoading: false,
  previewError: null,
  sending: false,
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'update:previewMemberId': [value: number]
  send: []
  retry: []
  retryPreview: []
}>()

/** One preview entry per member that actually receives the message. */
const previewOptions = computed(() => {
  const seen = new Map<number, string>()
  for (const recipient of props.check?.recipients ?? []) {
    if (!seen.has(recipient.member_id)) seen.set(recipient.member_id, recipient.member_name)
  }
  return [...seen].map(([value, label]) => ({ value, label }))
})

const sendLabel = computed(() => {
  const count = props.check?.count ?? 0
  return count === 1 ? '1 E-Mail senden' : `${count} E-Mails senden`
})

function relationLabel(relation: string) {
  if (relation === 'parent') return 'Eltern'
  if (relation === 'member') return 'Mitglied'
  return ''
}
</script>

<style scoped>
.review { display: flex; flex-direction: column; gap: var(--jf-space-3); }
.review-summary { display: flex; flex-direction: column; gap: var(--jf-space-1); }
.review-count { margin: 0; font-size: var(--jf-text-md); }
.review-badges { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); }
.review-hint, .review-muted { margin: 0; color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.review-section { display: flex; flex-direction: column; gap: var(--jf-space-1); }
.review-section h3 { margin: 0; font-size: var(--jf-text-md); display: inline; }
.review-details summary { min-height: var(--jf-touch-target); display: flex; align-items: center; cursor: pointer; gap: var(--jf-space-1); }
.review-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); max-height: 16rem; overflow-y: auto; }
.review-item { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--jf-space-1); padding: var(--jf-space-1) var(--jf-space-2); border-bottom: 1px solid var(--jf-color-border); min-height: var(--jf-touch-target); }
.review-item:last-child { border-bottom: 0; }
.review-item-main { display: flex; flex-direction: column; min-width: 0; overflow-wrap: anywhere; }
.review-preview-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--jf-space-1); }
.review-preview-select { min-width: 14rem; min-height: var(--jf-touch-target); }
.review-subject { margin: 0; overflow-wrap: anywhere; }
.review-frame { border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); }
.review-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: var(--jf-space-1); width: 100%; }
.review-actions :deep(.p-button) { min-height: var(--jf-touch-target); }
@media (max-width: 768px) {
  .review-actions :deep(.p-button) { flex: 1 1 100%; }
  .review-preview-select { width: 100%; }
}
</style>
