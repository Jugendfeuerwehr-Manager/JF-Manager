<template>
  <div class="run">
    <header class="run__header">
      <Button icon="pi pi-arrow-left" text rounded aria-label="Zurück" @click="goBack" />
      <div class="run__heading">
        <h1>{{ session?.title ?? 'Durchführung' }}</h1>
        <span v-if="session" class="run__muted">Plan Version {{ session.revision }} · {{ dateLabel }}</span>
      </div>
      <StatusBadge v-if="session" :label="phaseLabel" :severity="phaseSeverity" />
    </header>

    <p v-if="!online" class="run__banner run__banner--offline" role="status">
      <i class="pi pi-wifi" aria-hidden="true"></i>
      Keine Verbindung. Angezeigt wird der Stand von {{ loadedAt }}; Änderungen am Plan erscheinen erst nach Wiederverbindung.
    </p>
    <p v-else-if="updatedNotice" class="run__banner" role="status">
      <i class="pi pi-refresh" aria-hidden="true"></i>{{ updatedNotice }}
    </p>

    <p v-if="session?.status === 'cancelled'" class="run__banner run__banner--offline" role="alert">
      <i class="pi pi-ban" aria-hidden="true"></i>Diese Übung wurde abgesagt. Der Ablauf dient nur zur Ansicht.
    </p>

    <StateView v-if="!session" :kind="error ? 'error' : 'loading'" :message="error || undefined" @retry="load" />

    <main v-else class="run__body">
      <p v-if="!sections.length" class="run__empty">Für diese Übung sind noch keine Bausteine geplant.</p>
      <template v-else>
        <section class="run__hero" aria-labelledby="run-now">
          <div class="run__hero-top">
            <span id="run-now" class="run__eyebrow">{{ heroEyebrow }}</span>
            <span>{{ clock(shown!.start) }}–{{ clock(shown!.end) }}</span>
          </div>
          <span class="run__big">{{ heroMain }}</span>
          <div
            v-if="isLive"
            class="run__progress"
            role="progressbar"
            aria-label="Fortschritt des Abschnitts"
            :aria-valuemin="0"
            :aria-valuemax="shown!.end - shown!.start"
            :aria-valuenow="Math.floor(position.minute - shown!.start)"
          ><span :style="{ width: `${progress}%` }"></span></div>
          <span v-if="nextSection" class="run__hero-next">Danach: {{ nextSection.label }} ab {{ clock(nextSection.start) }}</span>
          <div class="run__browse">
            <Button icon="pi pi-chevron-left" text size="small" class="run__on-dark" aria-label="Vorheriger Abschnitt" :disabled="shownIndex === 0" @click="browse(-1)" />
            <span class="run__muted-dark">Abschnitt {{ shownIndex + 1 }} von {{ sections.length }}</span>
            <Button icon="pi pi-chevron-right" text size="small" class="run__on-dark" aria-label="Nächster Abschnitt" :disabled="shownIndex === sections.length - 1" @click="browse(1)" />
            <Button v-if="manualIndex !== null" label="Zur aktuellen Zeit" text size="small" class="run__on-dark" @click="manualIndex = null" />
          </div>
        </section>

        <SegmentedControl v-model="view" label="Ansicht" :options="viewOptions" />

        <ul v-if="view === 'all'" class="run__cards" aria-label="Stationen und Bausteine">
          <li v-for="card in cards" :key="card.key" class="run__card">
            <div class="run__card-top">
              <strong>{{ card.title }}</strong>
              <span class="run__group">{{ card.groupsNow }}</span>
            </div>
            <div class="run__facts">
              <span v-if="card.kind && card.kind !== 'block'">{{ BLOCK_KIND_LABELS[card.kind] }}</span>
              <span v-if="card.instructors.length"><i class="pi pi-user" aria-hidden="true"></i>{{ names(card.instructors) }}</span>
              <span v-if="card.location"><i class="pi pi-map-marker" aria-hidden="true"></i>{{ card.location }}</span>
              <span v-if="card.groupsNext"><i class="pi pi-arrow-right" aria-hidden="true"></i>danach {{ card.groupsNext }}</span>
            </div>
          </li>
        </ul>

        <template v-else>
          <p v-if="!mine" class="run__empty">
            Du bist in dieser Übung ab hier keiner Station als Ausbilder zugeordnet.
          </p>
          <section v-for="card in mine?.cards ?? []" :key="card.key" class="run__mine" :aria-label="`Deine Station ${card.title}`">
            <span class="run__eyebrow run__eyebrow--muted">
              {{ mine!.index === shownIndex ? 'Deine Station' : `Als Nächstes ab ${clock(sections[mine!.index]!.start)}` }}
            </span>
            <h2>{{ card.title }}</h2>
            <p class="run__muted">
              {{ [`Jetzt ${card.groupsNow}`, card.groupsNext && `danach ${card.groupsNext}`, card.location].filter(Boolean).join(' · ') }}
            </p>
            <div class="run__details">
              <template v-if="card.blocks[0]!.learning_objective">
                <strong>Lernziel</strong>
                <span>{{ card.blocks[0]!.learning_objective }}</span>
              </template>
              <template v-if="card.blocks[0]!.content">
                <strong>Ablauf</strong>
                <SafeHtml class="prose" :html="card.blocks[0]!.content" />
              </template>
              <template v-if="card.blocks[0]!.safety_notes">
                <strong class="run__safety">Sicherheit</strong>
                <span>{{ card.blocks[0]!.safety_notes }}</span>
              </template>
            </div>
            <fieldset v-if="materialLines(card).length" class="run__materials">
              <legend>Material bereitlegen</legend>
              <label v-for="(line, i) in materialLines(card)" :key="i" class="run__check">
                <input type="checkbox" :checked="isChecked(card.key, i)" @change="toggle(card.key, i)" />
                <span>{{ line.quantity }} × {{ line.label }}</span>
              </label>
              <p class="run__muted run__small">Abgehakt wird nur auf diesem Gerät, nicht im Plan.</p>
            </fieldset>
          </section>
        </template>

        <section v-if="session.can_manage_plan && session.publish_warnings?.length" class="run__hint" aria-label="Hinweise aus der Planung">
          <i class="pi pi-exclamation-triangle" aria-hidden="true"></i>
          <div>
            <strong>Hinweis aus der Planung</strong>
            <ul><li v-for="(text, i) in session.publish_warnings" :key="i">{{ text }}</li></ul>
          </div>
        </section>
        <p class="run__muted run__small">Stand {{ loadedAt }} · Zeiten nach Uhr dieses Geräts.</p>
      </template>
    </main>

    <footer v-if="session" class="run__footer">
      <router-link :to="{ name: 'training-mobile', params: { id: sessionId } }" class="run__action">
        <i class="pi pi-list" aria-hidden="true"></i>Ablauf
      </router-link>
      <button
        v-if="session.can_manage_plan && position.phase !== 'before' && (session.status === 'published' || session.status === 'completed')"
        type="button"
        class="run__action"
        @click="showDebrief = true"
      ><i class="pi pi-comment" aria-hidden="true"></i>Nachbereiten</button>
      <router-link
        v-if="session.linked_service_id"
        :to="{ name: 'service-attendance', params: { id: session.linked_service_id } }"
        class="run__action run__action--primary"
      ><i class="pi pi-check-square" aria-hidden="true"></i>Anwesenheit</router-link>
    </footer>
    <DebriefDialog v-if="session && showDebrief" v-model:visible="showDebrief" :session="session" @saved="load" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import SafeHtml from '@/components/common/SafeHtml.vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import DebriefDialog from '../molecules/DebriefDialog.vue'
import { trainingSessionsApi } from '@/api/training'
import { useAuthStore } from '@/stores/auth'
import { BLOCK_KIND_LABELS, type InstructorMini, type TrainingSessionDetail } from '@/types/training'
import { buildSections, materialLines, myNextCards, runPosition, sectionCards } from '../utils/runTimeline'

const props = defineProps<{ sessionId: number }>()
const router = useRouter()
const auth = useAuthStore()

const REFRESH_MS = 60_000
const session = ref<TrainingSessionDetail | null>(null)
const error = ref('')
const loadedAt = ref('')
const updatedNotice = ref('')
const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
const now = ref(new Date())
const manualIndex = ref<number | null>(null)
const showDebrief = ref(false)
const view = ref<'all' | 'mine'>('all')
const viewOptions = [{ value: 'all' as const, label: 'Alle Stationen' }, { value: 'mine' as const, label: 'Meine Station' }]

const sections = computed(() => buildSections(session.value?.blocks ?? []))
const position = computed(() => runPosition(sections.value, session.value?.date ?? '1970-01-01', session.value?.start_time ?? '00:00', now.value))
const shownIndex = computed(() => manualIndex.value ?? position.value.index)
const shown = computed(() => sections.value[shownIndex.value])
const nextSection = computed(() => sections.value[shownIndex.value + 1])
// Completed or cancelled exercises never count down, even while the clock is inside the plan.
const closed = computed(() => session.value?.status === 'completed' || session.value?.status === 'cancelled')
const isLive = computed(() => position.value.phase === 'running' && manualIndex.value === null && !closed.value)
const cards = computed(() => sectionCards(sections.value, shownIndex.value))
const mine = computed(() => myNextCards(sections.value, shownIndex.value, auth.user?.id ?? null))
const progress = computed(() => {
  const s = shown.value
  return s ? Math.min(100, Math.max(0, ((position.value.minute - s.start) / (s.end - s.start)) * 100)) : 0
})

// The stored status wins over the clock (a completed or cancelled exercise never "runs").
const phaseLabel = computed(() => {
  if (session.value?.status === 'completed') return 'Abgeschlossen'
  if (session.value?.status === 'cancelled') return 'Abgesagt'
  if (session.value?.status === 'draft') return 'Entwurf'
  return ({ before: 'Noch nicht begonnen', running: 'Läuft', after: 'Beendet' })[position.value.phase]
})
const phaseSeverity = computed(() => {
  if (session.value?.status === 'cancelled') return 'danger' as const
  if (session.value?.status === 'completed' || session.value?.status === 'draft') return 'neutral' as const
  return ({ before: 'info', running: 'success', after: 'neutral' } as const)[position.value.phase]
})
const dateLabel = computed(() => {
  if (!session.value) return ''
  const [y, m, d] = session.value.date.split('-').map(Number)
  return new Date(y!, m! - 1, d!).toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' })
})
const heroEyebrow = computed(() => {
  const label = shown.value?.label ?? ''
  if (manualIndex.value !== null || closed.value) return `Ansicht · ${label}`
  if (position.value.phase === 'running') return `Jetzt · ${label}`
  return position.value.phase === 'before' ? `Als Erstes · ${label}` : `Zuletzt · ${label}`
})
const heroMain = computed(() => {
  const p = position.value
  if (session.value?.status === 'completed') return 'Übung abgeschlossen'
  if (session.value?.status === 'cancelled') return 'Übung abgesagt'
  if (manualIndex.value !== null) return shown.value!.blocks.map((b) => b.title).filter((t, i, all) => all.indexOf(t) === i).join(' · ') || 'Übergang'
  if (p.phase === 'running') return `noch ${Math.max(1, Math.ceil(shown.value!.end - p.minute))} Min.`
  if (p.phase === 'after') return 'Übung beendet'
  if (p.daysAway > 0) return p.daysAway === 1 ? 'Beginnt morgen' : `Beginnt in ${p.daysAway} Tagen`
  const minutes = Math.ceil(-p.minute)
  return minutes >= 60 ? `Beginnt in ${Math.floor(minutes / 60)} Std. ${minutes % 60} Min.` : `Beginnt in ${minutes} Min.`
})

function clock(offset: number) {
  const [h, m] = (session.value?.start_time ?? '00:00').split(':').map(Number)
  const total = (h ?? 0) * 60 + (m ?? 0) + offset
  return `${String(Math.floor(total / 60) % 24).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

function names(list: InstructorMini[]) {
  return list.map((i) => i.name).join(', ')
}

function browse(delta: number) {
  const target = Math.min(sections.value.length - 1, Math.max(0, shownIndex.value + delta))
  manualIndex.value = target === position.value.index && position.value.phase === 'running' ? null : target
}

// Material checklist: only this device, never the plan.
const storageKey = (key: string) => `jf-run-materials:${props.sessionId}:${key}`
const checked = ref<Record<string, number[]>>({})
function isChecked(key: string, index: number) {
  if (!(key in checked.value)) {
    try { checked.value[key] = JSON.parse(localStorage.getItem(storageKey(key)) ?? '[]') } catch { checked.value[key] = [] }
  }
  return checked.value[key]!.includes(index)
}
function toggle(key: string, index: number) {
  const list = checked.value[key] ?? []
  checked.value[key] = list.includes(index) ? list.filter((i) => i !== index) : [...list, index]
  try { localStorage.setItem(storageKey(key), JSON.stringify(checked.value[key])) } catch { /* private mode: keep in memory */ }
}

async function load() {
  try {
    const data = (await trainingSessionsApi.plan(props.sessionId)).data
    if (session.value && data.revision !== session.value.revision) {
      updatedNotice.value = `Der Plan wurde geändert und auf Version ${data.revision} aktualisiert.`
    }
    session.value = data
    error.value = ''
    loadedAt.value = new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  } catch {
    if (!session.value) error.value = 'Die Übung konnte nicht geladen werden.'
  }
}

function goBack() {
  if (window.history.length > 1) router.back()
  else void router.push({ name: 'servicebook' })
}

let tick: ReturnType<typeof setInterval> | undefined
let refresh: ReturnType<typeof setInterval> | undefined
const setOnline = () => { online.value = true; void load() }
const setOffline = () => { online.value = false }
onMounted(() => {
  void load()
  tick = setInterval(() => { now.value = new Date() }, 15_000)
  refresh = setInterval(() => { if (online.value) void load() }, REFRESH_MS)
  window.addEventListener('online', setOnline)
  window.addEventListener('offline', setOffline)
})
onBeforeUnmount(() => {
  clearInterval(tick)
  clearInterval(refresh)
  window.removeEventListener('online', setOnline)
  window.removeEventListener('offline', setOffline)
})
watch(() => props.sessionId, () => { session.value = null; manualIndex.value = null; void load() })
// Leaving a section while browsing manually keeps the choice; reaching it again follows the clock.
watch(() => position.value.index, (index) => { if (manualIndex.value === index) manualIndex.value = null })

defineExpose({ load })
</script>

<style scoped>
.run { display: flex; flex-direction: column; min-height: 100svh; background: var(--jf-color-ground); color: var(--jf-color-text); }
.run__header { position: sticky; top: 0; z-index: 2; display: flex; align-items: center; gap: var(--jf-space-1); min-height: 56px; padding: 0 var(--jf-space-1); background: var(--jf-color-card); border-bottom: 1px solid var(--jf-color-border); }
.run__heading { flex: 1; min-width: 0; display: flex; flex-direction: column; line-height: var(--jf-leading-tight); }
.run__heading h1 { margin: 0; font-size: var(--jf-text-md); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.run__muted { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); margin: 0; }
.run__small { font-size: var(--jf-text-xs); }
.run__banner { display: flex; gap: var(--jf-space-1); align-items: center; margin: 0; padding: var(--jf-space-1) var(--jf-space-2); background: var(--jf-color-selected); color: var(--jf-color-selected-text); font-size: var(--jf-text-sm); }
.run__banner--offline { font-weight: var(--jf-weight-semibold); }
.run__body { flex: 1; width: 100%; max-width: 40rem; margin: 0 auto; box-sizing: border-box; padding: var(--jf-space-2); display: flex; flex-direction: column; gap: var(--jf-space-2); }
.run__empty { margin: 0; padding: var(--jf-space-2); border: 1px dashed var(--jf-color-border); border-radius: var(--jf-radius-md); color: var(--jf-color-text-muted); }
.run__hero { display: flex; flex-direction: column; gap: var(--jf-space-1); padding: var(--jf-space-2); border-radius: var(--jf-radius-lg); background: var(--jf-color-text); color: var(--jf-color-card); }
.run__hero-top { display: flex; justify-content: space-between; align-items: baseline; gap: var(--jf-space-1); font-size: var(--jf-text-sm); }
.run__eyebrow { font-size: var(--jf-text-xs); font-weight: var(--jf-weight-bold); letter-spacing: 0.08em; text-transform: uppercase; }
.run__eyebrow--muted { color: var(--jf-color-text-muted); }
.run__big { font-size: 1.75rem; font-weight: var(--jf-weight-bold); line-height: 1.15; }
.run__progress { height: 8px; border-radius: 999px; background: color-mix(in srgb, var(--jf-color-card) 18%, transparent); overflow: hidden; }
.run__progress span { display: block; height: 100%; border-radius: 999px; background: var(--jf-color-primary); }
.run__hero-next, .run__muted-dark { font-size: var(--jf-text-sm); opacity: 0.85; }
.run__browse { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-0-5); }
.run__on-dark { color: inherit !important; }
.run__cards { display: flex; flex-direction: column; gap: var(--jf-space-1); margin: 0; padding: 0; list-style: none; }
.run__card, .run__mine { display: flex; flex-direction: column; gap: var(--jf-space-1); padding: var(--jf-space-1-5) var(--jf-space-2); background: var(--jf-color-card); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); }
.run__card-top { display: flex; justify-content: space-between; align-items: center; gap: var(--jf-space-1); }
.run__group { padding: 2px 10px; border-radius: 999px; background: var(--jf-color-selected); color: var(--jf-color-selected-text); font-size: var(--jf-text-sm); font-weight: var(--jf-weight-bold); white-space: nowrap; }
.run__facts { display: flex; flex-wrap: wrap; gap: var(--jf-space-0-5) var(--jf-space-2); font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.run__facts .pi { margin-right: 0.3rem; font-size: 0.8em; }
.run__mine h2 { margin: 0; font-size: var(--jf-text-xl); }
.run__details { display: flex; flex-direction: column; gap: var(--jf-space-0-5); padding: var(--jf-space-1-5); border-radius: var(--jf-radius-md); background: var(--jf-color-ground); font-size: var(--jf-text-sm); }
.run__details strong { margin-top: var(--jf-space-0-5); }
.run__safety { color: var(--jf-color-primary); }
.run__materials { margin: 0; padding: 0; border: 0; display: flex; flex-direction: column; }
.run__materials legend { font-weight: var(--jf-weight-semibold); font-size: var(--jf-text-sm); margin-bottom: var(--jf-space-0-5); }
.run__check { display: flex; align-items: center; gap: var(--jf-space-1-5); min-height: var(--jf-touch-target); cursor: pointer; }
.run__check input { width: 1.4rem; height: 1.4rem; accent-color: var(--jf-color-primary); }
.run__hint { display: flex; gap: var(--jf-space-1-5); padding: var(--jf-space-1-5) var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); background: var(--jf-color-card); font-size: var(--jf-text-sm); }
.run__hint ul { margin: var(--jf-space-0-5) 0 0; padding-left: 1.1rem; }
.run__footer { position: sticky; bottom: 0; display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: var(--jf-space-1); padding: var(--jf-space-1-5) var(--jf-space-2) var(--jf-space-2); background: var(--jf-color-card); border-top: 1px solid var(--jf-color-border); }
.run__action { font: inherit; font-size: var(--jf-text-sm); background: var(--jf-color-card); cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; min-width: 0; min-height: 48px; padding: 0 var(--jf-space-1); text-align: center; border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); color: var(--jf-color-text); font-weight: var(--jf-weight-semibold); text-decoration: none; }
.run__action--primary { background: var(--jf-color-primary); border-color: var(--jf-color-primary); color: var(--jf-color-on-primary); }
.run__action:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
</style>
