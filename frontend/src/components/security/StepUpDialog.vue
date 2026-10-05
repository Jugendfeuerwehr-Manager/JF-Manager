<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import { setStepUpHandler } from '@/api'
import { cancelStepUp, confirmStepUp, requestStepUp, stepUpState } from '@/composables/useStepUp'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const password = ref('')
const code = ref('')

watch(() => stepUpState.visible, visible => {
  if (!visible) {
    // Never keep confirmation secrets in memory longer than needed.
    password.value = ''
    code.value = ''
  }
})

function onVisibleChange(visible: boolean) {
  if (!visible) cancelStepUp()
}

function submit() {
  void confirmStepUp(password.value, code.value)
}

function signInAgain() {
  cancelStepUp()
  void auth.loginWithOidc(route.fullPath)
}

onMounted(() => setStepUpHandler(() => requestStepUp(auth.user?.auth_source !== 'oidc')))
onUnmounted(() => setStepUpHandler(null))
</script>

<template>
  <Dialog
    :visible="stepUpState.visible"
    modal
    header="Aktion bestätigen"
    :style="{ width: 'min(28rem, 92vw)' }"
    @update:visible="onVisibleChange"
  >
    <form v-if="!stepUpState.ssoOnly" class="step-up-form" @submit.prevent="submit">
      <p class="hint">
        Diese Aktion erweitert Zugriffe oder gibt viele Personendaten aus. Bitte bestätige sie erneut.
        Die Bestätigung gilt fünf Minuten.
      </p>
      <div v-if="stepUpState.needsPassword" class="field">
        <label for="step-up-password">Passwort</label>
        <Password input-id="step-up-password" v-model="password" :feedback="false" toggle-mask autocomplete="current-password" required autofocus />
      </div>
      <div v-if="stepUpState.needsCode" class="field">
        <label for="step-up-code">Code aus der Authenticator-App oder Wiederherstellungscode</label>
        <InputText id="step-up-code" v-model="code" autocomplete="one-time-code" required />
      </div>
      <Message v-if="stepUpState.error" severity="error" role="alert">{{ stepUpState.error }}</Message>
      <div class="actions">
        <Button type="submit" label="Bestätigen" icon="pi pi-check" :loading="stepUpState.busy" />
        <Button type="button" label="Abbrechen" severity="secondary" text :disabled="stepUpState.busy" @click="cancelStepUp" />
      </div>
    </form>
    <div v-else class="step-up-form">
      <p class="hint">Dein Konto meldet sich über SSO an. Bitte melde dich dort erneut an und wiederhole danach die Aktion.</p>
      <div class="actions">
        <Button label="Erneut über SSO anmelden" icon="pi pi-sign-in" @click="signInAgain" />
        <Button label="Abbrechen" severity="secondary" text @click="cancelStepUp" />
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.step-up-form, .field { display: flex; flex-direction: column; gap: .75rem; }
.hint { color: var(--text-color-secondary); margin: 0; }
.field :deep(.p-password), .field :deep(input) { width: 100%; }
.actions { display: flex; flex-wrap: wrap; gap: .75rem; }
.actions :deep(.p-button) { min-height: 44px; }
</style>
