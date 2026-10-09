<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import { useAuthStore } from '@/stores/auth'
import { useQuickAction } from '@/composables/useQuickAction'
import { hardNavigate, isServerPath, safeReturnPath } from '@/utils/navigation'

/**
 * Landing page of a signed link from a notification (NOTIF-01.4, E12). Opening the link changes
 * nothing: the page signs in first, then resolves the token. Actions without consequences run
 * directly, everything else is confirmed here. Neutral full-screen layout for staff and portal.
 */
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const token = computed(() => String(route.params.token ?? ''))
const flow = useQuickAction(() => token.value)
const { phase, preview, result, error, busy, targetRoute } = flow

const choices = ref<Record<string, string>>({})
const redirecting = ref(false)

const steps = computed(() => [
  { label: 'Link geöffnet', active: false },
  { label: 'Angemeldet', active: false },
  { label: 'Bestätigen', active: phase.value === 'confirm' },
])

const heading = computed(() => {
  if (phase.value === 'confirm') return preview.value?.title ?? ''
  if (phase.value === 'result') return result.value?.state === 'done' ? 'Erledigt' : (preview.value?.title ?? 'Nicht verfügbar')
  if (phase.value === 'error') return errorTitle.value
  return 'Link wird geprüft …'
})

const errorTitle = computed(() => {
  switch (error.value?.code) {
    case 'wrong_account': return 'Anderes Konto'
    case 'expired': return 'Link abgelaufen'
    case 'gone': return 'Nicht mehr verfügbar'
    case 'invalid': return 'Ungültiger Link'
    default: return 'Das hat nicht geklappt'
  }
})

const target = computed(() => safeReturnPath(targetRoute.value))
const confirmLabel = computed(() => preview.value?.action === 'cancel' ? 'Abmelden' : 'Bestätigen')

async function leave(path: string, message?: string) {
  redirecting.value = true
  if (message) toast.add({ severity: 'success', summary: message, life: 4000 })
  if (isServerPath(path)) hardNavigate(path)
  else await router.replace(path)
}

async function run() {
  if (!auth.isAuthenticated) {
    // The login view returns here afterwards; only the relative path travels.
    await router.replace({ path: '/login', query: { next: `/a/${token.value}` } })
    return
  }
  await flow.start()
  // A direct action ends in the app; an undoable one stays so the undo is reachable.
  if (phase.value === 'result' && preview.value?.mode === 'direct' && result.value?.state !== 'not_available' && !result.value?.undo) {
    await leave(target.value, result.value?.message || 'Ansicht geöffnet')
  }
}

function confirm() {
  void flow.execute({ ...choices.value })
}

async function switchAccount() {
  await auth.logout(`/a/${token.value}`)
}

onMounted(run)
watch(token, () => { if (!redirecting.value) void run() })
</script>

<template>
  <div class="qa-screen">
    <header class="qa-header">
      <span class="qa-logo" aria-hidden="true">JF</span>
      <span class="qa-brand">Aktion aus E-Mail</span>
    </header>

    <main class="qa-main" :aria-busy="phase === 'loading'">
      <ol v-if="phase === 'confirm'" class="qa-steps" aria-label="Ablauf">
        <li v-for="step in steps" :key="step.label" :class="{ active: step.active }" :aria-current="step.active ? 'step' : undefined">
          <span class="bar" aria-hidden="true"></span>{{ step.label }}
        </li>
      </ol>

      <section class="qa-card" aria-labelledby="qa-title">
        <div v-if="phase === 'loading'" class="qa-loading" role="status">
          <ProgressSpinner style="width: 32px; height: 32px" aria-label="Link wird geprüft" />
          <h1 id="qa-title">Link wird geprüft …</h1>
        </div>

        <template v-else-if="phase === 'confirm' && preview">
          <h1 id="qa-title">{{ heading }}</h1>
          <ul class="qa-lines">
            <li v-for="line in preview.lines" :key="line">{{ line }}</li>
          </ul>
          <fieldset v-for="field in preview.payload_fields ?? []" :key="field.name" class="qa-field">
            <legend>{{ field.label }} <span v-if="field.optional" class="optional">(optional)</span></legend>
            <div class="chips">
              <label v-for="choice in field.choices" :key="choice.value" class="chip" :class="{ on: choices[field.name] === choice.value }">
                <input v-model="choices[field.name]" type="radio" :name="field.name" :value="choice.value" />{{ choice.label }}
              </label>
            </div>
          </fieldset>
          <div class="qa-note">
            <i class="pi pi-info-circle" aria-hidden="true"></i>
            <span>Die Aktion wirkt nur für dein angemeldetes Konto.</span>
          </div>
          <Button type="button" class="qa-primary" :label="confirmLabel" :loading="busy" :disabled="busy" @click="confirm" />
          <Button type="button" class="qa-secondary" label="Abbrechen" severity="secondary" text :disabled="busy" @click="leave(target)" />
        </template>

        <template v-else-if="phase === 'result' && result">
          <h1 id="qa-title" role="status">{{ heading }}</h1>
          <p v-if="result.message" class="qa-message">{{ result.message }}</p>
          <ul v-if="(result.lines ?? []).length" class="qa-lines">
            <li v-for="line in result.lines" :key="line">{{ line }}</li>
          </ul>
          <Button v-if="result.undo" type="button" class="qa-secondary" :label="result.undo.label" severity="secondary" outlined :loading="busy" @click="flow.undo()" />
          <Button type="button" class="qa-primary" label="Weiter" @click="leave(target)" />
        </template>

        <template v-else-if="phase === 'error' && error">
          <h1 id="qa-title">{{ heading }}</h1>
          <p class="qa-message" role="alert">{{ error.detail }}</p>
          <template v-if="error.code === 'wrong_account'">
            <p class="qa-message">Melde dich mit dem Konto an, an das die E-Mail ging.</p>
            <Button type="button" class="qa-primary" label="Mit anderem Konto anmelden" @click="switchAccount" />
            <Button type="button" class="qa-secondary" label="Zur Startseite" severity="secondary" text @click="leave(error.target_route)" />
          </template>
          <Button v-else type="button" class="qa-primary" :label="error.code === 'expired' ? 'Zur Übersicht' : 'Zur Startseite'" @click="leave(error.target_route)" />
        </template>
      </section>
    </main>
  </div>
</template>

<style scoped>
.qa-screen { min-height: 100dvh; display: flex; flex-direction: column; background: var(--p-surface-ground, var(--p-content-hover-background)); color: var(--p-text-color); }
.qa-header { height: 60px; padding: 0 16px; display: flex; align-items: center; gap: 10px; background: var(--p-content-background); border-bottom: 1px solid var(--p-content-border-color); }
.qa-logo { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; background: var(--p-primary-color); color: var(--p-primary-contrast-color); }
.qa-brand { font-size: 16px; font-weight: 650; }
.qa-main { flex: 1; width: 100%; max-width: 480px; margin: 0 auto; box-sizing: border-box; padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.qa-steps { margin: 0; padding: 0; list-style: none; display: flex; gap: 8px; font-size: 12px; color: var(--p-text-muted-color); }
.qa-steps li { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.qa-steps .bar { height: 4px; border-radius: 2px; background: var(--p-green-700); }
.qa-steps li.active { font-weight: 650; color: var(--p-text-color); }
.qa-steps li.active .bar { background: var(--p-primary-color); }
.qa-card { background: var(--p-content-background); border: 1px solid var(--p-content-border-color); border-radius: 16px; padding: 18px; display: flex; flex-direction: column; gap: 14px; }
h1 { margin: 0; font-size: 21px; font-weight: 700; line-height: 1.25; }
.qa-loading { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 24px 0; }
.qa-loading h1 { font-size: 16px; font-weight: 600; color: var(--p-text-muted-color); }
.qa-lines { margin: 0; padding: 0; list-style: none; border: 1px solid var(--p-content-border-color); border-radius: 12px; overflow: hidden; }
.qa-lines li { min-height: 44px; box-sizing: border-box; padding: 8px 12px; display: flex; align-items: center; font-size: 15px; }
.qa-lines li + li { border-top: 1px solid var(--p-content-border-color); }
.qa-message { margin: 0; font-size: 15px; }
.qa-field { border: none; margin: 0; padding: 0; }
.qa-field legend { font-size: 14px; font-weight: 600; margin-bottom: 8px; padding: 0; }
.optional { font-weight: 400; color: var(--p-text-muted-color); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { min-height: 44px; box-sizing: border-box; padding: 0 14px; border-radius: 22px; border: 1px solid var(--p-form-field-border-color, var(--p-content-border-color)); display: flex; align-items: center; gap: 6px; font-size: 14px; cursor: pointer; }
.chip input { margin: 0; accent-color: var(--p-primary-color); }
.chip.on { border: 2px solid var(--p-primary-color); background: var(--p-highlight-background); color: var(--p-highlight-color); font-weight: 600; }
.chip:focus-within { outline: 2px solid var(--p-primary-color); outline-offset: 2px; }
.qa-note { display: flex; gap: 8px; padding: 10px 12px; border-radius: 10px; background: var(--p-content-hover-background); font-size: 13px; color: var(--p-text-muted-color); }
.qa-note i { flex: none; margin-top: 2px; }
.qa-primary :deep(.p-button), .qa-primary { min-height: 52px; border-radius: 12px; font-weight: 650; font-size: 16px; }
.qa-secondary { min-height: 44px; }
</style>
