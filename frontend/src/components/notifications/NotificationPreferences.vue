<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import Message from 'primevue/message'
import ToggleSwitch from 'primevue/toggleswitch'
import { notificationPreferencesApi, type NotificationPreference } from '@/api/notificationPreferences'
import { getApiErrorMessage } from '@/utils/apiError'

const props = withDefaults(defineProps<{ portal?: boolean }>(), { portal: false })

const rows = ref<NotificationPreference[]>([])
const loading = ref(true)
const error = ref('')
const savingKind = ref<string | null>(null)

async function toggle(row: NotificationPreference, channel: 'email' | 'push', value: boolean) {
  const previous = row[channel]
  row[channel] = value
  savingKind.value = row.kind
  error.value = ''
  try {
    const { data } = await notificationPreferencesApi.save([{ kind: row.kind, email: row.email, push: row.push }])
    if (Array.isArray(data)) rows.value = data
  } catch (err) {
    row[channel] = previous
    error.value = getApiErrorMessage(err, `Die Einstellung für „${row.label}“ konnte nicht gespeichert werden.`)
  } finally {
    savingKind.value = null
  }
}

onMounted(async () => {
  try {
    const { data } = await notificationPreferencesApi.list()
    rows.value = data
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Die Mitteilungseinstellungen konnten nicht geladen werden.')
  } finally {
    loading.value = false
  }
  // Mail footers link to #mitteilungen; the content only exists after loading.
  if (window.location.hash === '#mitteilungen') {
    await nextTick()
    document.getElementById('mitteilungen')?.scrollIntoView?.({ block: 'start' })
  }
})
</script>

<template>
  <section id="mitteilungen" class="prefs" aria-labelledby="mitteilungen-heading">
    <h3 id="mitteilungen-heading"><i class="pi pi-bell" aria-hidden="true" /> Mitteilungen</h3>
    <p class="hint">
      <template v-if="props.portal">Bei Zuteilung, Warteliste, Nachrücken und neuen Diensten bekommst du standardmäßig E-Mail und Push.</template>
      <template v-else>Der Eingang bleibt immer aktiv. Hier legst du fest, worüber du zusätzlich per E-Mail oder Push informiert wirst.</template>
    </p>
    <p v-if="loading" class="hint" role="status">Lade Einstellungen …</p>
    <div v-else-if="rows.length" class="table" role="table" aria-label="Mitteilungen nach Art">
      <div class="row head" role="row">
        <span role="columnheader">Art</span><span role="columnheader">E-Mail</span><span role="columnheader">Push</span>
      </div>
      <div v-for="row in rows" :key="row.kind" class="row" role="row">
        <span class="label" role="cell">{{ row.label }}</span>
        <span class="cell" role="cell">
          <ToggleSwitch :model-value="row.email" :input-id="`pref-${row.kind}-email`" :aria-label="`E-Mail für ${row.label}`" :disabled="savingKind === row.kind" @update:model-value="toggle(row, 'email', $event as boolean)" />
        </span>
        <span class="cell" role="cell">
          <ToggleSwitch :model-value="row.push" :input-id="`pref-${row.kind}-push`" :aria-label="`Push für ${row.label}`" :disabled="savingKind === row.kind" @update:model-value="toggle(row, 'push', $event as boolean)" />
        </span>
      </div>
    </div>
    <Message v-if="error" severity="error" :closable="false" role="alert">{{ error }}</Message>
  </section>
</template>

<style scoped>
.prefs { display: grid; gap: .75rem; scroll-margin-top: 1rem; }
h3 { display: flex; align-items: center; gap: .5rem; margin: 0; }
.hint { margin: 0; color: var(--p-text-muted-color); font-size: .9rem; line-height: 1.5; }
.table { display: grid; border: 1px solid var(--p-content-border-color); border-radius: 12px; overflow: hidden; }
.row { display: grid; grid-template-columns: 1fr 4.5rem 4.5rem; align-items: center; gap: .5rem; min-height: 48px; padding: .25rem .75rem; border-top: 1px solid var(--p-content-border-color); }
.row:first-child { border-top: none; }
.head { min-height: 40px; font-size: .8rem; font-weight: 600; color: var(--p-text-muted-color); background: var(--p-content-hover-background, transparent); }
.head span:not(:first-child), .cell { justify-self: center; }
.cell { display: flex; align-items: center; justify-content: center; min-height: 44px; min-width: 44px; }
.label { overflow-wrap: anywhere; }
</style>
