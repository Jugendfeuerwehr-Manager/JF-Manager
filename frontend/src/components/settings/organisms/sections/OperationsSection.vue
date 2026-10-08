<template>
  <section class="operations-section">
    <router-link to="/settings">← Einstellungen</router-link>
    <h2>Betriebsstatus</h2>
    <p>
      Version, letzte Sicherung und Hintergrundaufgaben dieser Installation. Die Anzeige ist nur
      lesend; Änderungen erfolgen auf dem Server mit <code>jfctl</code>.
    </p>
    <p v-if="loading" role="status">Betriebsstatus wird geladen …</p>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <template v-if="status">
      <Message v-if="!status.available" severity="info" :closable="false">
        {{ unavailableText }}
      </Message>
      <template v-else>
        <Message
          v-for="warning in status.warnings"
          :key="warning.code"
          severity="warn"
          :closable="false"
          >{{ warning.text }}</Message
        >
        <dl class="operations-facts">
          <dt>Instanz</dt>
          <dd>{{ status.instance || '–' }}</dd>
          <dt>Betriebsart</dt>
          <dd>{{ modeLabel }}</dd>
          <dt>Version</dt>
          <dd>{{ status.version || '–' }}</dd>
          <dt>Letzte Sicherung</dt>
          <dd>
            <template v-if="status.last_backup">
              <Tag :severity="backupSeverity" :value="backupLabel" />
              {{ formatTime(status.last_backup.finished) }}
              <span v-if="status.last_backup.status === 'failed' && status.last_backup.message">
                – {{ status.last_backup.message }}
              </span>
            </template>
            <template v-else>Noch keine Sicherung erfasst</template>
          </dd>
          <dt>Letzte erfolgreiche Sicherung</dt>
          <dd>{{ formatTime(status.last_backup?.last_success) }}</dd>
          <dt>Hintergrundaufgaben</dt>
          <dd>
            <Tag
              :severity="status.workers_held ? 'warn' : 'success'"
              :value="status.workers_held ? 'Angehalten' : 'Laufen'"
            />
          </dd>
          <dt>Stand der Angaben</dt>
          <dd>{{ formatTime(status.updated) }}</dd>
        </dl>
      </template>
    </template>
    <Button label="Aktualisieren" icon="pi pi-refresh" text :loading="loading" @click="load" />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { configurationApi, configurationError, type OperationsStatus } from '@/api/configuration'

const status = ref<OperationsStatus | null>(null)
const loading = ref(false)
const error = ref('')

const MODES: Record<string, string> = { compose: 'Docker Compose', native: 'Debian nativ' }
const BACKUP_STATES: Record<string, string> = { ok: 'Erfolgreich', failed: 'Fehlgeschlagen' }

const unavailableText = computed(() => {
  switch (status.value?.reason) {
    case 'not_configured':
      return 'Diese Installation wird nicht mit jfctl betrieben (z. B. Entwicklung). Es liegen keine Betriebsdaten vor.'
    case 'missing':
      return 'jfctl hat noch keinen Status geschrieben. Er entsteht nach Installation, Sicherung oder Update.'
    default:
      return 'Die Statusdatei von jfctl ist nicht lesbar. Auf dem Server „jfctl status“ ausführen.'
  }
})
const modeLabel = computed(() => MODES[status.value?.mode || ''] || '–')
const backupLabel = computed(
  () => BACKUP_STATES[status.value?.last_backup?.status || ''] || 'Unbekannt',
)
const backupSeverity = computed(() =>
  status.value?.last_backup?.status === 'ok'
    ? 'success'
    : status.value?.last_backup?.status === 'failed'
      ? 'danger'
      : 'secondary',
)

function formatTime(value?: string | null) {
  if (!value) return '–'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    status.value = (await configurationApi.operations()).data
  } catch (err) {
    error.value = configurationError(err)
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<style scoped>
.operations-section {
  max-width: 850px;
  padding: 1.5rem;
}
p {
  line-height: 1.65;
}
.operations-facts {
  display: grid;
  grid-template-columns: minmax(10rem, max-content) 1fr;
  gap: 0.75rem 1.5rem;
  margin: 1.5rem 0;
  padding: 1.25rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 12px;
}
.operations-facts dt {
  font-weight: 600;
}
.operations-facts dd {
  margin: 0;
}
@media (max-width: 600px) {
  .operations-facts {
    grid-template-columns: 1fr;
  }
  .operations-facts dd {
    margin-bottom: 0.5rem;
  }
}
</style>
