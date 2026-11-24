<template>
  <main class="verify">
    <div class="verify__card" aria-live="polite">
      <h1>Siegel prüfen</h1>
      <p class="verify__id">Siegel-ID <code>{{ publicId }}</code></p>
      <p v-if="store.loading">Prüfe …</p>
      <template v-else-if="result">
        <p class="verify__verdict" :class="result.valid ? 'verify__verdict--ok' : 'verify__verdict--bad'">
          <i :class="result.valid ? 'pi pi-verified' : 'pi pi-times-circle'" aria-hidden="true"></i>
          {{ result.valid ? 'Gültig: unverändert seit dem Versiegeln' : 'Ungültig: Inhalt oder Siegel wurde verändert' }}
        </p>
        <dl class="verify__facts">
          <dt>Art</dt>
          <dd>{{ result.kind }}</dd>
          <dt>Versiegelt am</dt>
          <dd>{{ new Date(result.sealed_at).toLocaleString('de-DE') }}</dd>
          <dt>Inhalt geprüft</dt>
          <dd>{{ result.content_checked ? 'Ja, mit dem gespeicherten Datensatz verglichen' : 'Nein, nur Signatur und Kette (Datensatz nicht mehr vorhanden oder Export)' }}</dd>
        </dl>
        <p class="verify__fine">Die Prüfung zeigt keine personenbezogenen Daten.</p>
      </template>
      <p v-else class="verify__verdict verify__verdict--bad">{{ store.error }}</p>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { usePublicAdmissionStore } from '@/stores/publicAdmission'

const route = useRoute()
const store = usePublicAdmissionStore()
const publicId = String(route.params.id ?? '')
const result = computed(() => store.sealCheck)

onMounted(() => store.verify(publicId))
</script>

<style scoped>
.verify {
  min-height: 100vh;
  padding: var(--jf-space-3) var(--jf-space-2);
  background: var(--jf-color-ground);
  color: var(--jf-color-text);
  font-family: var(--jf-font-sans);
}

.verify__card {
  max-width: 34rem;
  margin: 0 auto;
  padding: var(--jf-space-3);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  box-shadow: var(--jf-shadow-md);
}

.verify h1 {
  margin: 0 0 var(--jf-space-1);
}

.verify__id,
.verify__fine {
  color: var(--jf-color-text-muted);
}

.verify__verdict {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  padding: var(--jf-space-1-5);
  border-radius: var(--jf-radius-md);
  font-weight: var(--jf-weight-semibold);
}

.verify__verdict--ok {
  background: var(--jf-color-success-surface);
  color: var(--jf-color-success);
}

.verify__verdict--bad {
  background: var(--jf-color-danger-surface);
  color: var(--jf-color-danger);
}

.verify__facts {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--jf-space-0-5) var(--jf-space-2);
}

.verify__facts dt {
  color: var(--jf-color-text-muted);
}

.verify__facts dd {
  margin: 0;
}
</style>
