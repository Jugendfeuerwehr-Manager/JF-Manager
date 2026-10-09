<template>
  <main class="accept-page">
    <section class="accept-card" aria-labelledby="accept-title">
      <header class="accept-head">
        <i class="pi pi-lock head-icon" aria-hidden="true"></i>
        <h1 id="accept-title">Passwort festlegen</h1>
      </header>

      <div v-if="store.invitationLoading" class="state" role="status">
        <i class="pi pi-spin pi-spinner" aria-hidden="true"></i>
        <p>Einladung wird geprüft …</p>
      </div>

      <div v-else-if="store.accepted" class="state" role="status">
        <i class="pi pi-check-circle ok-icon" aria-hidden="true"></i>
        <h2>Dein Zugang ist eingerichtet.</h2>
        <p>Du kannst dich jetzt mit deiner E-Mail-Adresse und deinem Passwort anmelden.</p>
        <Button label="Zur Anmeldung" icon="pi pi-sign-in" class="touch" @click="router.push('/login')" />
      </div>

      <div v-else-if="store.invitationError" class="state" role="alert">
        <i class="pi pi-exclamation-triangle warn-icon" aria-hidden="true"></i>
        <h2>{{ store.invitationError.code === 'expired' ? 'Einladung abgelaufen' : 'Einladung nicht verfügbar' }}</h2>
        <p>{{ store.invitationError.message }}</p>
        <router-link to="/login" class="link touch">Zur Anmeldung</router-link>
      </div>

      <form v-else-if="store.invitation" class="form" novalidate @submit.prevent="submit">
        <p class="intro">Lege ein Passwort fest, um deinen Zugang zum Portal einzurichten.</p>

        <div class="field">
          <label for="accept-username">Benutzername (E-Mail-Adresse)</label>
          <InputText id="accept-username" :model-value="store.invitation.email" readonly autocomplete="username" class="touch" />
        </div>

        <div class="field">
          <label for="accept-password">Passwort</label>
          <Password
            v-model="password"
            input-id="accept-password"
            toggle-mask
            :feedback="false"
            autocomplete="new-password"
            :invalid="!!fieldError('password')"
            :aria-describedby="fieldError('password') ? 'accept-password-error' : undefined"
            fluid
            input-class="touch"
          />
          <small v-if="fieldError('password')" id="accept-password-error" class="err" role="alert">{{ fieldError('password') }}</small>
        </div>

        <div class="field">
          <label for="accept-password-confirm">Passwort wiederholen</label>
          <Password
            v-model="passwordConfirm"
            input-id="accept-password-confirm"
            toggle-mask
            :feedback="false"
            autocomplete="new-password"
            :invalid="!!fieldError('password_confirm')"
            :aria-describedby="fieldError('password_confirm') ? 'accept-confirm-error' : undefined"
            fluid
            input-class="touch"
          />
          <small v-if="fieldError('password_confirm')" id="accept-confirm-error" class="err" role="alert">{{ fieldError('password_confirm') }}</small>
        </div>

        <div class="field">
          <div class="check touch">
            <Checkbox
              v-model="privacy"
              input-id="accept-privacy"
              binary
              :invalid="!!fieldError('privacy_accepted')"
              :aria-describedby="fieldError('privacy_accepted') ? 'accept-privacy-error' : undefined"
            />
            <label for="accept-privacy">Ich habe den Datenschutzhinweis zur Kenntnis genommen und bin mit der Verarbeitung meiner Daten für die Organisation des Jugendfeuerwehrdienstes einverstanden.</label>
          </div>
          <small v-if="fieldError('privacy_accepted')" id="accept-privacy-error" class="err" role="alert">{{ fieldError('privacy_accepted') }}</small>
        </div>

        <Message v-if="store.acceptError" severity="error" :closable="false">{{ store.acceptError }}</Message>

        <Button type="submit" label="Zugang einrichten" icon="pi pi-check" :loading="store.accepting" class="touch submit" />
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import { usePortalStore } from '@/stores/portal'

const route = useRoute()
const router = useRouter()
const store = usePortalStore()

const password = ref('')
const passwordConfirm = ref('')
const privacy = ref(false)
const token = ref('')

function fieldError(name: string) {
  return store.acceptFieldErrors[name] ?? ''
}

onMounted(() => {
  const raw = route.query.token
  token.value = Array.isArray(raw) ? (raw[0] ?? '') : (raw ?? '')
  void store.loadInvitation(token.value)
})

async function submit() {
  await store.acceptInvitation({
    token: token.value,
    password: password.value,
    password_confirm: passwordConfirm.value,
    privacy_accepted: privacy.value,
  })
}
</script>

<style scoped>
.accept-page {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 1rem;
  background: var(--p-surface-50, var(--p-content-background));
  box-sizing: border-box;
}
.accept-card {
  width: 100%;
  max-width: 28rem;
  margin-top: 2rem;
  padding: 1.25rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  border: 1px solid var(--p-content-border-color);
  border-radius: 12px;
  box-sizing: border-box;
}
.accept-head { text-align: center; margin-bottom: 1rem; }
.accept-head h1 { margin: 0.25rem 0 0; font-size: 1.5rem; }
.head-icon { font-size: 2rem; color: var(--p-primary-color); }
.form { display: flex; flex-direction: column; gap: 1rem; }
.intro, .state p { margin: 0; color: var(--p-text-muted-color); }
.field { display: flex; flex-direction: column; gap: 0.35rem; min-width: 0; }
.field label { font-weight: 600; }
.check { display: flex; gap: 0.75rem; align-items: flex-start; min-height: 44px; }
.check label { font-weight: 400; overflow-wrap: anywhere; }
.err { color: var(--p-red-500); }
.state { display: flex; flex-direction: column; align-items: center; gap: 0.75rem; text-align: center; padding: 1rem 0; }
.state h2 { margin: 0; font-size: 1.25rem; }
.ok-icon { font-size: 2.5rem; color: var(--p-green-500); }
.warn-icon { font-size: 2.5rem; color: var(--p-orange-500); }
.link { display: inline-flex; align-items: center; color: var(--p-primary-color); }
.touch, :deep(.touch) { min-height: 44px; }
.submit { width: 100%; }
:deep(.p-password), :deep(.p-inputtext) { width: 100%; }
</style>
