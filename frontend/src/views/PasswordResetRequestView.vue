<template>
  <AuthPanel
    title="Passwort zurücksetzen"
    :description="submitted ? '' : 'Gib deine E-Mail-Adresse ein. Wir schicken dir einen Link zum Zurücksetzen.'"
    :icon="submitted ? 'pi pi-check' : 'pi pi-key'"
  >
    <form v-if="!submitted" novalidate :aria-busy="loading" @submit.prevent="handleSubmit">
      <Message v-if="error" id="reset-error" severity="error" role="alert">{{ error }}</Message>
      <div class="field">
        <label for="email">E-Mail-Adresse</label>
        <InputText
          id="email"
          v-model="email"
          type="email"
          autocomplete="email"
          :invalid="!!error"
          :aria-describedby="error ? 'reset-error' : undefined"
          :disabled="loading"
        />
      </div>
      <Button type="submit" label="Link anfordern" icon="pi pi-send" :loading="loading" />
      <router-link to="/login" class="auth-link">Zurück zur Anmeldung</router-link>
    </form>

    <div v-else role="status">
      <Message severity="success">
        Falls ein Konto mit dieser E-Mail-Adresse existiert, wurden Anweisungen zum Zurücksetzen versendet.
      </Message>
      <p class="hint">Keine E-Mail erhalten? Prüfe den Spam-Ordner oder versuche es erneut.</p>
      <router-link to="/login" class="auth-link">Zurück zur Anmeldung</router-link>
    </div>
  </AuthPanel>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { authApi } from '@/api/auth'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Message from 'primevue/message'
import AuthPanel from '@/components/auth/AuthPanel.vue'
import { getApiErrorMessage } from '@/utils/apiError'

const email = ref('')
const loading = ref(false)
const error = ref('')
const submitted = ref(false)

const handleSubmit = async () => {
  if (!email.value) {
    error.value = 'Bitte gib deine E-Mail-Adresse ein'
    return
  }

  loading.value = true
  error.value = ''

  try {
    await authApi.requestPasswordReset(email.value)
    submitted.value = true
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Reset-E-Mail konnte nicht versendet werden. Bitte versuche es erneut.')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.hint {
  color: var(--jf-color-text-muted);
  font-size: 0.9rem;
}
</style>
