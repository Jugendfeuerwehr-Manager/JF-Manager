<template>
  <section class="account-link-card" aria-labelledby="account-link-heading">
    <div class="head">
      <i class="pi pi-link" aria-hidden="true"></i>
      <h2 id="account-link-heading">Verwaltungskonto</h2>
    </div>

    <StateView v-if="store.loading" kind="loading" title="Verknüpfung wird geladen …" class="compact" />
    <StateView v-else-if="store.error" :kind="stateForError(store.error)" class="compact" @retry="reload" />
    <template v-else>
      <template v-if="link && link.status !== 'rejected'">
        <p class="account">
          <span class="account__name">{{ link.user.name }}</span>
          <span class="muted">{{ link.user.username }}</span>
        </p>
        <StatusBadge :label="statusLabel" :severity="statusSeverity" :icon="statusIcon" />
        <p class="muted">{{ statusText }}</p>
      </template>
      <template v-else>
        <p v-if="link?.status === 'rejected'" class="notice" role="status">
          <i class="pi pi-times-circle" aria-hidden="true"></i>
          {{ link.user.name }} hat die Verknüpfung abgelehnt. Bitte das richtige Konto wählen.
        </p>
        <p class="muted">{{ kind === 'member' ? 'Ist diese Person selbst Verwaltende/r, wird ihr Konto hier mit dem Mitgliedsdatensatz verbunden.' : 'Hat eine verwaltende Person hier Kinder, wird ihr Konto mit diesem Elterndatensatz verbunden.' }}</p>
      </template>

      <Message v-if="message" :severity="messageOk ? 'success' : 'error'" :closable="false">{{ message }}</Message>

      <div class="actions">
        <Button
          v-if="!link || link.status === 'rejected'"
          label="Konto verknüpfen"
          icon="pi pi-link"
          severity="secondary"
          outlined
          @click="openDialog"
        />
        <Button
          v-else
          label="Verknüpfung lösen"
          icon="pi pi-times"
          severity="secondary"
          outlined
          :loading="store.busy"
          @click="confirmUnlink"
        />
      </div>
    </template>

    <AccountLinkDialog
      v-if="dialogOpen"
      :kind="kind"
      :record-name="recordName"
      @close="dialogOpen = false"
      @linked="onLinked"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { useConfirm } from 'primevue/useconfirm'
import StateView, { stateForError } from '@/components/common/StateView.vue'
import StatusBadge, { type StatusSeverity } from '@/components/common/StatusBadge.vue'
import AccountLinkDialog from './AccountLinkDialog.vue'
import { useAccountLinksStore } from '@/stores/accountLinks'
import type { AccountLinkRecordKind } from '@/types/accountLinks'

const props = defineProps<{ kind: AccountLinkRecordKind, recordId: number, recordName: string }>()

const store = useAccountLinksStore()
const confirm = useConfirm()
const dialogOpen = ref(false)
const message = ref('')
const messageOk = ref(false)
const link = computed(() => store.link)

function reload() { void store.load(props.kind, props.recordId) }
watch(() => [props.kind, props.recordId], () => { message.value = ''; reload() }, { immediate: true })

const statusLabel = computed(() => (link.value?.status === 'confirmed' ? 'Bestätigt' : 'Bestätigung ausstehend'))
const statusSeverity = computed<StatusSeverity>(() => (link.value?.status === 'confirmed' ? 'success' : 'warning'))
const statusIcon = computed(() => (link.value?.status === 'confirmed' ? 'pi pi-check-circle' : 'pi pi-clock'))
const dateFormat = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
const statusText = computed(() => {
  const l = link.value
  if (!l) return ''
  if (l.status === 'confirmed' && l.confirmed_at) return `Vom Konto bestätigt am ${dateFormat.format(new Date(l.confirmed_at))}.`
  return `Verknüpft von ${l.linked_by || 'der Kontoverwaltung'}. Wirkt erst, wenn das Konto sie bei der nächsten Anmeldung bestätigt.`
})

function openDialog() {
  message.value = ''
  dialogOpen.value = true
}

function onLinked() {
  dialogOpen.value = false
  messageOk.value = true
  message.value = 'Verknüpft. Das Konto bestätigt bei der nächsten Anmeldung.'
}

function confirmUnlink() {
  confirm.require({
    header: 'Verknüpfung lösen?',
    message: 'Das Konto sieht danach keine eigenen Dienste und Daten mehr über diesen Datensatz. Bestehende Meldungen bleiben erhalten.',
    acceptLabel: 'Lösen',
    rejectLabel: 'Abbrechen',
    acceptProps: { severity: 'danger' },
    rejectProps: { severity: 'secondary', outlined: true },
    accept: async () => {
      const result = await store.unlink()
      messageOk.value = result.ok
      message.value = result.ok ? 'Verknüpfung gelöst.' : (result.message ?? 'Die Verknüpfung konnte nicht gelöst werden.')
    },
  })
}
</script>

<style scoped>
.account-link-card { display: flex; flex-direction: column; gap: var(--jf-space-1-5); }
.head { display: flex; align-items: center; gap: var(--jf-space-1); }
.head i { color: var(--jf-color-text-muted); }
h2 { margin: 0; font-size: var(--jf-text-lg); font-weight: var(--jf-weight-semibold); }
.account { display: flex; flex-direction: column; margin: 0; }
.account__name { font-weight: var(--jf-weight-semibold); }
.muted { margin: 0; font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.notice { display: flex; gap: var(--jf-space-1); align-items: flex-start; margin: 0; font-size: var(--jf-text-sm); }
.actions { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); }
.actions :deep(.p-button) { min-height: var(--jf-touch-target); }
.compact { padding: var(--jf-space-2); }
</style>
