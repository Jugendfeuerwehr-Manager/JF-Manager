<template>
  <div class="own-area">
    <OverviewHeader :title="title" eyebrow="Mein Bereich" :subtitle="subtitle" />

    <nav class="tabs" aria-label="Mein Bereich">
      <router-link v-if="auth.linkedPerson.member" to="/ich/dienste" class="tab" active-class="tab--active">
        <i class="pi pi-calendar" aria-hidden="true"></i>Meine Dienste
      </router-link>
      <router-link v-if="auth.linkedPerson.member" to="/ich/daten" class="tab" active-class="tab--active">
        <i class="pi pi-id-card" aria-hidden="true"></i>Meine Daten
      </router-link>
      <router-link v-if="auth.linkedPerson.children" to="/ich/kinder" class="tab" active-class="tab--active">
        <i class="pi pi-users" aria-hidden="true"></i>Meine Kinder
      </router-link>
    </nav>

    <StateView v-if="portal.loading && !portal.me" kind="loading" />
    <StateView v-else-if="portal.error" kind="error" :message="portal.error" @retry="portal.fetchMe()" />
    <StateView
      v-else-if="!person"
      kind="empty"
      :title="section === 'kinder' ? 'Keine Kinder verknüpft' : 'Kein Mitgliedsdatensatz verknüpft'"
      message="Die Kontoverwaltung verknüpft dein Konto mit deinen Datensätzen; du bestätigst die Verknüpfung nach der Anmeldung."
    />
    <template v-else>
      <div v-if="section === 'kinder' && children.length > 1" class="chips" role="tablist" aria-label="Kind wählen">
        <button
          v-for="child in children" :key="child.id" type="button" role="tab" class="chip"
          :aria-selected="portal.selectedPersonId === child.id" @click="portal.selectPerson(child.id)"
        >{{ child.first_name }}<template v-if="child.age !== undefined"> · {{ child.age }}</template></button>
      </div>

      <template v-if="section === 'daten'">
        <OwnDataPanel relation="self" />
        <section class="release" aria-labelledby="release-heading">
          <h2 id="release-heading">Verknüpfung</h2>
          <p class="muted">Ist das nicht (mehr) dein Datensatz? Die Kontoverwaltung löst die Verknüpfung auf deinen Antrag.</p>
          <Message v-if="releaseMessage" :severity="releaseOk ? 'success' : 'error'" :closable="false">{{ releaseMessage }}</Message>
          <Button label="Lösen beantragen" icon="pi pi-send" severity="secondary" outlined :loading="releasing" @click="requestRelease" />
        </section>
      </template>
      <template v-else>
        <h2 class="section-title">{{ section === 'kinder' ? `Dienste von ${person.first_name}` : 'Meine nächsten Dienste' }}</h2>
        <PortalSessionList grouped />
        <template v-if="section === 'kinder'">
          <h2 class="section-title">Daten von {{ person.first_name }}</h2>
          <OwnDataPanel relation="child" />
        </template>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import StateView from '@/components/common/StateView.vue'
import PortalSessionList from '@/components/portal/PortalSessionList.vue'
import OwnDataPanel from '@/components/own/OwnDataPanel.vue'
import { useAccountLinksStore } from '@/stores/accountLinks'
import { useAuthStore } from '@/stores/auth'
import { usePortalStore } from '@/stores/portal'

const props = defineProps<{ section: 'dienste' | 'daten' | 'kinder' }>()

const auth = useAuthStore()
const portal = usePortalStore()
const links = useAccountLinksStore()

const self = computed(() => portal.me?.people.find(p => p.relation === 'self') ?? null)
const children = computed(() => portal.me?.people.filter(p => p.relation === 'child') ?? [])
const person = computed(() => (props.section === 'kinder'
  ? children.value.find(c => c.id === portal.selectedPersonId) ?? null
  : self.value))

const title = computed(() => ({ dienste: 'Meine Dienste', daten: 'Meine Daten', kinder: 'Meine Kinder' })[props.section])
const subtitle = computed(() => ({
  dienste: 'An- und Abmelden für geplante Dienste – mit denselben Fristen wie im Portal.',
  daten: 'Dein Mitgliedsdatensatz. Nachweise pflegt eine andere Person.',
  kinder: 'Dienste und freigegebene Daten deiner Kinder.',
})[props.section])

portal.useOwnArea()

/** Selects the person of the current section once the overview is there. */
function choosePerson() {
  if (!portal.me) return
  const wanted = props.section === 'kinder'
    ? (children.value.some(c => c.id === portal.selectedPersonId) ? portal.selectedPersonId : children.value[0]?.id)
    : self.value?.id
  if (wanted !== undefined && wanted !== null) portal.selectPerson(wanted)
}

watch(() => props.section, async () => {
  if (!portal.me) await portal.fetchMe()
  choosePerson()
}, { immediate: true })

watch(() => [portal.selectedPersonId, props.section] as const, ([id, section]) => {
  if (section !== 'dienste' && id !== null) void portal.loadPerson(id)
}, { immediate: true })

const releasing = ref(false)
const releaseMessage = ref('')
const releaseOk = ref(false)
async function requestRelease() {
  releasing.value = true
  const result = await links.requestRelease()
  releasing.value = false
  releaseOk.value = result.ok
  releaseMessage.value = result.ok ? 'Antrag gesendet. Die Kontoverwaltung meldet sich.' : (result.message ?? 'Der Antrag konnte nicht gesendet werden.')
}
</script>

<style scoped>
.own-area { display: flex; flex-direction: column; gap: var(--jf-space-2); max-width: 48rem; }
.tabs { display: flex; gap: var(--jf-space-1); overflow-x: auto; }
.tab { display: inline-flex; align-items: center; gap: var(--jf-space-1); min-height: var(--jf-touch-target); padding: 0 var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: 999px; color: var(--jf-color-text); background: var(--jf-color-card); text-decoration: none; font-size: var(--jf-text-sm); font-weight: var(--jf-weight-medium); white-space: nowrap; }
.tab--active { background: var(--jf-color-selected); color: var(--jf-color-selected-text); border-color: var(--jf-color-primary); font-weight: var(--jf-weight-semibold); }
.tab:focus-visible, .chip:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
.chips { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); }
.chip { min-height: var(--jf-touch-target); padding: 0 var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: 999px; background: var(--jf-color-card); color: var(--jf-color-text); font: inherit; font-size: var(--jf-text-sm); cursor: pointer; }
.chip[aria-selected='true'] { background: var(--jf-color-selected); color: var(--jf-color-selected-text); border-color: var(--jf-color-primary); font-weight: var(--jf-weight-semibold); }
.section-title { margin: var(--jf-space-1) 0 0; font-size: var(--jf-text-md); font-weight: var(--jf-weight-semibold); }
.release { display: flex; flex-direction: column; gap: var(--jf-space-1); align-items: flex-start; padding: var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-card); }
.release h2 { margin: 0; font-size: var(--jf-text-md); font-weight: var(--jf-weight-semibold); }
.release :deep(.p-button) { min-height: var(--jf-touch-target); }
.muted { margin: 0; color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
</style>
