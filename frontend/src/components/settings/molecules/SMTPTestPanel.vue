<template>
  <section class="smtp-test-panel">
    <h3>Gespeicherte E-Mail-Konfiguration prüfen</h3>
    <p>
      Speichere Änderungen zuerst. Der Verbindungstest baut nur eine SMTP-Verbindung auf und sendet
      keine Nachricht.
    </p>
    <Button
      label="Verbindung testen"
      severity="secondary"
      outlined
      :disabled="!canEdit || busy"
      :loading="busy"
      @click="test(false)"
    />
    <details>
      <summary>Test-E-Mail ausdrücklich senden</summary>
      <label for="smtp-test-recipient">Empfänger der Test-E-Mail</label>
      <input
        id="smtp-test-recipient"
        v-model="recipient"
        type="email"
        autocomplete="off"
        :disabled="!canEdit || busy"
      />
      <label class="confirm-send"
        ><input v-model="confirmed" type="checkbox" :disabled="!canEdit || busy" />Ich bestätige den
        Versand einer Test-E-Mail an diese Adresse.</label
      >
      <Button
        label="Test-E-Mail senden"
        :disabled="!canEdit || busy || !confirmed || !recipient"
        @click="test(true)"
      />
    </details>
    <Message v-if="result" :severity="ok ? 'success' : 'error'" :closable="false">{{
      result
    }}</Message>
  </section>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import apiClient from '@/api'
import { configurationError } from '@/api/configuration'
defineProps<{ canEdit: boolean }>()
const busy = ref(false),
  recipient = ref(''),
  confirmed = ref(false),
  ok = ref(false),
  result = ref('')
async function test(send: boolean) {
  if (send && (!confirmed.value || !recipient.value)) return
  busy.value = true
  result.value = ''
  try {
    const response = await apiClient.post<{ ok: boolean; detail: string }>(
      send ? '/settings/email/send-test/' : '/settings/email/test-connection/',
      send ? { recipient: recipient.value, confirm_send: true } : {},
    )
    ok.value = response.data.ok
    result.value = response.data.detail
    if (send) confirmed.value = false
  } catch (err) {
    ok.value = false
    result.value = configurationError(err)
  } finally {
    busy.value = false
  }
}
</script>
<style scoped>
.smtp-test-panel {
  margin-top: 1.5rem;
  padding: 1.5rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 8px;
}
p {
  line-height: 1.6;
}
details {
  margin: 1.25rem 0;
}
summary {
  min-height: 44px;
  cursor: pointer;
}
label {
  display: block;
  margin: 0.75rem 0;
}
input[type='email'] {
  width: 100%;
  min-height: 44px;
  padding: 0.65rem;
  border-radius: 6px;
  border: 1px solid var(--p-form-field-border-color);
  color: var(--jf-color-text);
  background: var(--p-form-field-background);
}
.confirm-send {
  line-height: 1.6;
}
</style>
