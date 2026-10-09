<template>
  <main class="confirm-page">
    <section class="confirm-card" aria-labelledby="confirm-heading">
      <p class="eyebrow">Nach der Anmeldung</p>
      <h1 id="confirm-heading">{{ heading }}</h1>

      <StateView v-if="links.pendingLoading" kind="loading" title="Verknüpfung wird geladen …" />
      <StateView v-else-if="links.pendingError" :kind="stateForError(links.pendingError)" @retry="links.loadPending()" />
      <template v-else-if="decided">
        <StatusBadge
          :label="decided === 'confirmed' ? 'Bestätigt' : 'Abgelehnt'"
          :severity="decided === 'confirmed' ? 'success' : 'neutral'"
          :icon="decided === 'confirmed' ? 'pi pi-check-circle' : 'pi pi-times-circle'"
        />
        <p class="lead" role="status">{{ decidedText }}</p>
        <Button label="Weiter" icon="pi pi-arrow-right" icon-pos="right" class="primary" @click="leave" />
      </template>
      <template v-else-if="link">
        <p class="lead">
          {{ link.linked_by || 'Die Kontoverwaltung' }} hat dein Konto mit {{ link.member && link.parent ? 'diesen Datensätzen' : 'diesem Datensatz' }} verknüpft.
          Bitte bestätige nur, wenn es wirklich deine Daten sind.
        </p>

        <article v-if="link.member" class="record" aria-labelledby="record-member">
          <h2 id="record-member"><i class="pi pi-user" aria-hidden="true"></i>Mitgliedsdatensatz</h2>
          <dl>
            <div><dt>Name</dt><dd>{{ link.member.name }}</dd></div>
            <div><dt>Geburtsjahr</dt><dd>{{ link.member.birth_year ?? 'nicht erfasst' }}</dd></div>
            <div><dt>Abteilung</dt><dd>{{ link.member.departments.join(', ') || '–' }}</dd></div>
            <div><dt>Gruppe</dt><dd>{{ link.member.group ?? '–' }}</dd></div>
          </dl>
        </article>

        <article v-if="link.parent" class="record" aria-labelledby="record-parent">
          <h2 id="record-parent"><i class="pi pi-users" aria-hidden="true"></i>Elterndatensatz</h2>
          <dl>
            <div><dt>Name</dt><dd>{{ link.parent.name }}</dd></div>
            <div>
              <dt>Kinder</dt>
              <dd>{{ link.parent.children.map(c => c.group ? `${c.first_name} (${c.group})` : c.first_name).join(', ') || '–' }}</dd>
            </div>
          </dl>
        </article>

        <p class="hint">
          Nach der Bestätigung siehst du unter „Mein Bereich“ deine Dienste und Daten{{ link.parent ? ' sowie deine Kinder' : '' }}.
          Eigene Qualifikationen und Sonderaufgaben pflegt weiterhin eine andere Person.
        </p>
        <Message v-if="links.decideError" severity="error" :closable="false">{{ links.decideError }}</Message>

        <div class="actions">
          <Button label="Ja, das bin ich" icon="pi pi-check" class="primary" :loading="links.deciding && choice === true" :disabled="links.deciding" @click="decide(true)" />
          <Button label="Nein, nicht meiner" icon="pi pi-times" severity="secondary" outlined :loading="links.deciding && choice === false" :disabled="links.deciding" @click="decide(false)" />
        </div>
        <button type="button" class="later" :disabled="links.deciding" @click="later">Später entscheiden</button>
      </template>
      <template v-else>
        <p class="lead">Es wartet keine Verknüpfung auf deine Bestätigung.</p>
        <Button label="Weiter" icon="pi pi-arrow-right" icon-pos="right" class="primary" @click="leave" />
      </template>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Message from 'primevue/message'
import StateView, { stateForError } from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useAccountLinksStore } from '@/stores/accountLinks'
import { useAuthStore } from '@/stores/auth'
import { safeReturnPath } from '@/utils/navigation'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const links = useAccountLinksStore()
const choice = ref<boolean | null>(null)
const decided = ref<'confirmed' | 'rejected' | null>(null)
const link = computed(() => links.pending)

const heading = computed(() => {
  if (decided.value) return decided.value === 'confirmed' ? 'Verknüpfung bestätigt' : 'Verknüpfung abgelehnt'
  if (link.value?.member && !link.value.parent) return 'Ist das dein Mitgliedsdatensatz?'
  if (link.value?.parent && !link.value.member) return 'Ist das dein Elterndatensatz?'
  return 'Sind das deine Datensätze?'
})
const decidedText = computed(() => (decided.value === 'confirmed'
  ? 'Unter „Mein Bereich“ findest du jetzt deine Dienste und Daten.'
  : 'Die Verknüpfung hat keine Wirkung. Die verknüpfende Person erhält einen Hinweis und prüft sie.'))

onMounted(() => { void links.loadPending() })

async function decide(accept: boolean) {
  choice.value = accept
  if (await links.decide(accept)) {
    decided.value = accept ? 'confirmed' : 'rejected'
    await auth.refreshSession().catch(() => undefined)
  }
}

function leave() {
  void router.replace(safeReturnPath(route.query.next))
}

function later() {
  auth.deferAccountLink()
  leave()
}
</script>

<style scoped>
.confirm-page { min-height: 100dvh; display: grid; place-items: start center; padding: var(--jf-space-4) var(--jf-space-2); background: var(--jf-color-ground); color: var(--jf-color-text); }
.confirm-card { width: 100%; max-width: 32rem; display: flex; flex-direction: column; gap: var(--jf-space-2); padding: var(--jf-space-3); background: var(--jf-color-card); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); box-shadow: var(--jf-shadow-sm); }
.eyebrow { margin: 0; font-size: var(--jf-text-xs); font-weight: var(--jf-weight-bold); text-transform: uppercase; letter-spacing: 0.08em; color: var(--jf-color-text-muted); }
h1 { margin: 0; font-size: var(--jf-text-2xl); line-height: 1.2; }
.lead { margin: 0; line-height: 1.5; }
.record { border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); padding: var(--jf-space-2); }
.record h2 { display: flex; align-items: center; gap: var(--jf-space-1); margin: 0 0 var(--jf-space-1); font-size: var(--jf-text-md); font-weight: var(--jf-weight-semibold); }
.record h2 i { color: var(--jf-color-text-muted); }
dl { display: grid; gap: var(--jf-space-1); margin: 0; }
dl div { display: grid; grid-template-columns: 8rem 1fr; gap: var(--jf-space-1); }
dt { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
dd { margin: 0; font-weight: var(--jf-weight-medium); overflow-wrap: anywhere; }
.hint { margin: 0; font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.actions { display: flex; flex-direction: column; gap: var(--jf-space-1); }
.actions :deep(.p-button), .primary { min-height: var(--jf-touch-target); width: 100%; }
.later { align-self: center; min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1); border: 0; background: none; color: var(--jf-color-primary); font: inherit; font-size: var(--jf-text-sm); text-decoration: underline; text-underline-offset: 3px; cursor: pointer; }
.later:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
@media (min-width: 640px) {
  .confirm-page { place-items: center; }
  .actions { flex-direction: row; }
  .actions :deep(.p-button) { width: auto; flex: 1; }
}
@media (max-width: 380px) { dl div { grid-template-columns: 1fr; gap: 0; } }
</style>
