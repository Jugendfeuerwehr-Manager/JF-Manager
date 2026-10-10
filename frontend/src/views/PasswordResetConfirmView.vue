<template>
  <AuthPanel
    title="Neues Passwort festlegen"
    :description="resetSuccess ? '' : 'Wähle ein neues Passwort mit mindestens 8 Zeichen.'"
    :icon="resetSuccess ? 'pi pi-check' : 'pi pi-lock'"
  >
    <form v-if="!resetSuccess" novalidate :aria-busy="loading" @submit.prevent="handleSubmit">
      <Message v-if="error" id="reset-error" severity="error" role="alert">{{ error }}</Message>
      <div class="field">
        <label for="new-password">Neues Passwort</label>
        <Password
          v-model="newPassword"
          input-id="new-password"
          toggle-mask
          :feedback="false"
          autocomplete="new-password"
          :invalid="!!error"
          :disabled="loading"
        />
      </div>
      <div class="field">
        <label for="confirm-password">Passwort wiederholen</label>
        <Password
          v-model="confirmPassword"
          input-id="confirm-password"
          toggle-mask
          :feedback="false"
          autocomplete="new-password"
          :invalid="!!error"
          :disabled="loading"
        />
      </div>
      <Button type="submit" label="Passwort speichern" icon="pi pi-check" :loading="loading" :disabled="!uid || !token" />
      <router-link to="/login" class="auth-link">Zurück zur Anmeldung</router-link>
    </form>

    <div v-else role="status">
      <Message severity="success">Dein Passwort wurde geändert. Du kannst dich jetzt anmelden.</Message>
      <router-link to="/login" class="auth-link">Zur Anmeldung</router-link>
    </div>
  </AuthPanel>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { authApi } from '@/api/auth'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'
import AuthPanel from '@/components/auth/AuthPanel.vue'
import { getApiErrorMessage } from '@/utils/apiError'

const route = useRoute()
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')
const resetSuccess = ref(false)

const uid = ref('')
const token = ref('')

onMounted(() => {
  uid.value = route.params.uid as string
  token.value = route.params.token as string

  if (!uid.value || !token.value) {
    error.value = 'Ungültiger Reset-Link'
  }
})

const handleSubmit = async () => {
  error.value = ''

  if (!newPassword.value || !confirmPassword.value) {
    error.value = 'Bitte fülle alle Felder aus'
    return
  }

  if (newPassword.value.length < 8) {
    error.value = 'Das Passwort muss mindestens 8 Zeichen lang sein'
    return
  }

  if (newPassword.value !== confirmPassword.value) {
    error.value = 'Die Passwörter stimmen nicht überein'
    return
  }

  loading.value = true

  try {
    await authApi.resetPassword({
      uid: uid.value,
      token: token.value,
      new_password: newPassword.value,
      new_password_confirm: confirmPassword.value
    })
    resetSuccess.value = true
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Passwort konnte nicht zurückgesetzt werden. Der Link ist möglicherweise abgelaufen.')
  } finally {
    loading.value = false
  }
}
</script>
