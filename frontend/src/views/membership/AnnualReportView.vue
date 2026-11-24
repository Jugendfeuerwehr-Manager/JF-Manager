<template>
  <div class="adm-page report">
    <header class="adm-page__head">
      <div>
        <h1>Jahresmeldung</h1>
        <p class="adm-page__lead">
          Zahlen für das Statistikportal der Deutschen Jugendfeuerwehr, Stichtag 31.12. Werte in derselben Reihenfolge
          wie im Portal; mit <i class="pi pi-copy" aria-hidden="true"></i> übernehmen.
        </p>
      </div>
      <div class="report__controls">
        <AdmField input-id="r-department" label="Abteilung">
          <select id="r-department" v-model.number="departmentId" class="adm-input">
            <option v-for="department in departments.departments" :key="department.id" :value="department.id">{{ department.name }}</option>
          </select>
        </AdmField>
        <AdmField input-id="r-year" label="Berichtsjahr">
          <select id="r-year" v-model.number="year" class="adm-input">
            <option v-for="option in years" :key="option" :value="option">{{ option }}</option>
          </select>
        </AdmField>
      </div>
    </header>

    <p v-if="store.error" class="adm-page__error" role="alert">{{ store.error }}</p>
    <p v-if="store.loading && !data" class="adm-page__lead">Berechne …</p>

    <template v-if="data">
      <section class="report__status" :data-ok="data.ok" aria-live="polite">
        <p class="report__verdict">
          <i :class="data.ok ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'" aria-hidden="true"></i>
          {{ data.ok ? 'Die Jahresmeldung ist plausibel.' : 'Die Jahresmeldung enthält Widersprüche.' }}
          <span v-if="isFinal" class="adm-badge" data-state="valid">Festgeschrieben {{ formatDate(store.report?.finalized_at) }}</span>
        </p>
        <ul v-if="!data.ok" class="report__checks">
          <li v-for="check in failedChecks" :key="check.rule">{{ check.message.replace('entspricht', 'entspricht nicht').replace('ergibt die', 'ergibt nicht die').replace('ergeben die', 'ergeben nicht die') }}</li>
        </ul>
        <p v-if="data.warnings.length" class="report__hint">
          {{ data.warnings.length }} Hinweise zu Mitgliedsdaten.
          <button type="button" class="report__link" @click="tab = 'warnings'">Anzeigen</button>
        </p>
        <div class="report__actions">
          <AdmButton icon="pi pi-file-excel" :loading="store.saving" @click="store.downloadXlsx(departmentId, year)">Excel</AdmButton>
          <AdmButton
            v-if="canFinalize && !isFinal"
            variant="primary"
            icon="pi pi-lock"
            :disabled="!data.ok || !afterReferenceDate"
            :title="!afterReferenceDate ? 'Erst nach dem Stichtag möglich' : !data.ok ? 'Erst die Widersprüche klären' : ''"
            @click="finalize"
          >
            Festschreiben
          </AdmButton>
        </div>
      </section>

      <nav class="adm-filters" aria-label="Bereiche der Jahresmeldung">
        <AdmButton v-for="entry in TABS" :key="entry.value" :aria-pressed="tab === entry.value" @click="tab = entry.value">
          {{ entry.label }}<template v-if="entry.value === 'warnings' && data.warnings.length"> ({{ data.warnings.length }})</template>
        </AdmButton>
      </nav>

      <section v-if="tab === 'members'" class="adm-table-wrap" aria-label="Mitglieder Berichtsjahr">
        <table class="adm-table report__table">
          <thead>
            <tr><th scope="col">Mitglieder Berichtsjahr</th><th scope="col">M</th><th scope="col">W</th><th scope="col">D</th><th scope="col">Gesamt</th><th scope="col"><span class="sr-only">Zeile kopieren</span></th></tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Anzahl Betreuer:innen <span class="report__hint">(Vorschlag: {{ data.suggestions.supervisors }} Personen mit Rolle)</span></th>
              <td v-for="gender in GENDERS" :key="gender">
                <input
                  v-if="!isFinal && canEdit"
                  v-model.number="supervisors[gender]"
                  type="number"
                  min="0"
                  class="adm-input report__number"
                  :aria-label="`Betreuer:innen ${gender.toUpperCase()}`"
                  @change="saveManual"
                />
                <CopyValue v-else :value="supervisors[gender]" />
              </td>
              <td><CopyValue :value="supervisors.m + supervisors.w + supervisors.d" /></td>
              <td><CopyRow :values="[supervisors.m, supervisors.w, supervisors.d]" /></td>
            </tr>
            <ReportLine label="Anzahl Mitglieder" :row="data.members" strong />
            <ReportLine v-for="row in data.movements" :key="row.key" :label="`Anzahl ${row.label}`" :row="row" />
            <tr v-for="reason in data.exit_reasons" :key="reason.key" class="report__sub">
              <th scope="row">davon Grund: {{ reason.label }}</th>
              <td colspan="3"></td>
              <td><CopyValue :value="reason.total" /></td>
              <td></td>
            </tr>
          </tbody>
        </table>
        <p class="report__foot">
          Vorjahr ({{ year - 1 }}): {{ data.previous.m }} m · {{ data.previous.w }} w · {{ data.previous.d }} d =
          {{ data.previous.total }}
          <span class="report__hint">({{ data.previous.source === 'snapshot' ? 'festgeschriebene Meldung' : 'aus den Daten berechnet' }})</span>
        </p>
      </section>

      <section v-else-if="tab === 'age'" class="adm-table-wrap" aria-label="Altersstruktur">
        <table class="adm-table report__table">
          <thead>
            <tr><th scope="col">Altersstruktur am 31.12.</th><th scope="col">M</th><th scope="col">W</th><th scope="col">D</th><th scope="col">Gesamt</th><th scope="col"><span class="sr-only">Zeile kopieren</span></th></tr>
          </thead>
          <tbody>
            <ReportLine v-for="row in data.age" :key="row.key" :label="`Anzahl mit Alter ${row.label}`" :row="row" />
          </tbody>
        </table>
        <p v-if="data.approximated_ages" class="report__foot report__hint">
          {{ data.approximated_ages }} anonymisierte ehemalige Mitglieder: Alter aus dem Geburtsjahr geschätzt.
        </p>
      </section>

      <section v-else-if="tab === 'activities'" class="adm-card" aria-label="Aktivitäten">
        <p class="adm-page__lead">
          Zählwerte, die das Portal unter „Aktivitäten“ abfragt. Im Dienstbuch stehen für {{ year }}
          {{ data.suggestions.services }} Dienste.
        </p>
        <div v-for="(activity, index) in activities" :key="index" class="report__activity">
          <input v-model="activity.label" class="adm-input" :disabled="isFinal || !canEdit" aria-label="Bezeichnung" placeholder="z. B. Anzahl Übungsdienste" @change="saveManual" />
          <input v-model.number="activity.value" type="number" min="0" class="adm-input report__number" :disabled="isFinal || !canEdit" aria-label="Wert" @change="saveManual" />
          <CopyValue :value="activity.value" />
          <AdmButton v-if="!isFinal && canEdit" variant="danger" icon="pi pi-times" aria-label="Entfernen" @click="removeActivity(index)" />
        </div>
        <AdmButton v-if="!isFinal && canEdit" icon="pi pi-plus" @click="activities.push({ label: '', value: 0 })">Wert hinzufügen</AdmButton>
      </section>

      <section v-else-if="tab === 'warnings'" class="adm-card" aria-label="Hinweise">
        <p v-if="!data.warnings.length" class="adm-page__lead">Keine Hinweise.</p>
        <ul class="report__warnings">
          <li v-for="(warning, index) in data.warnings" :key="index">
            <RouterLink :to="`/members/${warning.member}`">{{ warning.name }}</RouterLink>: {{ warning.message }}
          </li>
        </ul>
      </section>

      <section v-else class="adm-card" aria-label="Organisation">
        <form class="report__profile" @submit.prevent="saveProfile">
          <AdmField input-id="p-org" label="Organisations-ID (DJF)" hint="21 Zeichen, z. B. DE08215015001100001JF">
            <input id="p-org" v-model="profileDraft.djf_org_id" class="adm-input report__mono" maxlength="21" :disabled="!canEditProfile" />
          </AdmField>
          <AdmField input-id="p-kind" label="Art">
            <select id="p-kind" v-model="profileDraft.org_kind" class="adm-input" :disabled="!canEditProfile">
              <option value="JF">Jugendfeuerwehr</option>
              <option value="KF">Kinderfeuerwehr</option>
            </select>
          </AdmField>
          <AdmField input-id="p-founded" label="Gegründet am">
            <input id="p-founded" v-model="profileDraft.founded_on" type="date" class="adm-input" :disabled="!canEditProfile" />
          </AdmField>
          <fieldset class="report__categories">
            <legend>Als Mitglied zählen</legend>
            <label v-for="(label, value) in COUNTED" :key="value">
              <input v-model="profileDraft.include_status_categories" type="checkbox" class="adm-check" :value="value" :disabled="!canEditProfile" />
              {{ label }}
            </label>
          </fieldset>
          <AdmButton v-if="canEditProfile" variant="primary" type="submit" icon="pi pi-check" :loading="store.saving">Speichern</AdmButton>
        </form>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, reactive, ref, watch, type PropType } from 'vue'
import AdmButton from '@/components/admissions/atoms/AdmButton.vue'
import AdmField from '@/components/admissions/atoms/AdmField.vue'
import '@/components/admissions/atoms/admInput.css'
import '@/components/admissions/atoms/admPage.css'
import { useAnnualReportStore } from '@/stores/annualReport'
import { useAuthStore } from '@/stores/auth'
import { useDepartmentsStore } from '@/stores/departments'
import type { GenderCounts, StatisticsProfile } from '@/types/membership'

const GENDERS = ['m', 'w', 'd'] as const
const TABS = [
  { value: 'members', label: 'Mitglieder' },
  { value: 'age', label: 'Altersstruktur' },
  { value: 'activities', label: 'Aktivitäten' },
  { value: 'warnings', label: 'Hinweise' },
  { value: 'profile', label: 'Organisation' }
] as const
const COUNTED = { trial: 'Probezeit / Anwärter', active: 'Aktiv', passive: 'Passiv' }

const CopyValue = defineComponent({
  props: { value: { type: Number, default: 0 } },
  setup(props) {
    const copied = ref(false)
    async function copy() {
      await navigator.clipboard.writeText(String(props.value ?? 0))
      copied.value = true
      setTimeout(() => (copied.value = false), 1200)
    }
    return () =>
      h('button', { type: 'button', class: 'report__copy', title: 'Wert kopieren', 'aria-label': `${props.value} kopieren`, onClick: copy }, [
        h('span', String(props.value ?? 0)),
        h('i', { class: copied.value ? 'pi pi-check' : 'pi pi-copy', 'aria-hidden': 'true' })
      ])
  }
})

const CopyRow = defineComponent({
  props: { values: { type: Array as PropType<number[]>, required: true } },
  setup(props) {
    const copied = ref(false)
    async function copy() {
      // Tab-separated so the three values can be pasted into consecutive fields or a spreadsheet.
      await navigator.clipboard.writeText(props.values.join('\t'))
      copied.value = true
      setTimeout(() => (copied.value = false), 1200)
    }
    return () =>
      h('button', { type: 'button', class: 'report__copy report__copy--row', title: 'M, W, D kopieren', 'aria-label': 'Zeile kopieren', onClick: copy }, [
        h('i', { class: copied.value ? 'pi pi-check' : 'pi pi-clone', 'aria-hidden': 'true' })
      ])
  }
})

const ReportLine = defineComponent({
  props: { label: { type: String, required: true }, row: { type: Object as PropType<GenderCounts>, required: true }, strong: Boolean },
  setup(props) {
    return () =>
      h('tr', { class: props.strong ? 'report__strong' : '' }, [
        h('th', { scope: 'row' }, props.label),
        ...GENDERS.map((gender) => h('td', [h(CopyValue, { value: props.row[gender] })])),
        h('td', [h(CopyValue, { value: props.row.total })]),
        h('td', [h(CopyRow, { values: GENDERS.map((gender) => props.row[gender]) })])
      ])
  }
})

const store = useAnnualReportStore()
const auth = useAuthStore()
const departments = useDepartmentsStore()

const now = new Date()
const departmentId = ref<number>(departments.activeDepartmentId ?? departments.departments[0]?.id ?? 0)
// Reports are due early in the following year; until March the previous year is the one to report.
const year = ref(now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear())
const years = Array.from({ length: 6 }, (_, index) => now.getFullYear() - index)
const tab = ref<(typeof TABS)[number]['value']>('members')
const supervisors = reactive({ m: 0, w: 0, d: 0 })
const activities = ref<{ label: string; value: number }[]>([])
const profileDraft = reactive<Omit<StatisticsProfile, 'id' | 'department'>>({
  djf_org_id: '',
  org_kind: 'JF',
  founded_on: null,
  include_status_categories: ['trial', 'active']
})

const data = computed(() => store.report?.data ?? null)
const isFinal = computed(() => store.report?.state === 'final')
const failedChecks = computed(() => data.value?.checks.filter((check) => !check.ok) ?? [])
const afterReferenceDate = computed(() => new Date() > new Date(`${year.value}-12-31T23:59:59`))
const canEdit = computed(() => auth.hasPerm('membership.change_annualreport'))
const canFinalize = computed(() => auth.hasPerm('membership.finalize_annualreport'))
const canEditProfile = computed(() => auth.hasPerm('membership.change_statisticsprofile') || auth.hasPerm('membership.add_statisticsprofile'))

const formatDate = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString('de-DE') : '')

function load() {
  if (!departmentId.value) return
  store.load(departmentId.value, year.value)
}

async function saveManual() {
  if (isFinal.value) return
  await store
    .saveManual(departmentId.value, year.value, {
      supervisors: { ...supervisors, total: supervisors.m + supervisors.w + supervisors.d },
      activities: activities.value.filter((activity) => activity.label.trim())
    })
    .catch(() => undefined)
}

function removeActivity(index: number) {
  activities.value.splice(index, 1)
  saveManual()
}

async function finalize() {
  if (!window.confirm(`Jahresmeldung ${year.value} festschreiben? Die Zahlen werden versiegelt und ändern sich danach nicht mehr.`)) return
  await store.finalize(departmentId.value, year.value).catch(() => undefined)
}

async function saveProfile() {
  await store.saveProfile(departmentId.value, { ...profileDraft }).catch(() => undefined)
  load()
}

watch(data, (value) => {
  if (!value) return
  Object.assign(supervisors, { m: 0, w: 0, d: 0, ...(value.manual?.supervisors ?? {}) })
  activities.value = (value.manual?.activities ?? []).map((activity) => ({ ...activity }))
})
watch(
  () => store.profile,
  (profile) => {
    Object.assign(profileDraft, {
      djf_org_id: profile?.djf_org_id ?? '',
      org_kind: profile?.org_kind ?? 'JF',
      founded_on: profile?.founded_on ?? null,
      include_status_categories: [...(profile?.include_status_categories ?? ['trial', 'active'])]
    })
  }
)
watch([departmentId, year], load)
onMounted(load)
</script>

<style scoped>
.report__controls {
  display: flex;
  gap: var(--jf-space-1);
}

.report__status {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-danger-surface);
  color: var(--jf-color-danger);
}

.report__status[data-ok='true'] {
  background: var(--jf-color-success-surface);
  color: var(--jf-color-success);
}

.report__verdict {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1);
  margin: 0;
  font-weight: var(--jf-weight-semibold);
}

.report__checks {
  margin: 0;
  padding-left: 1.2rem;
}

.report__actions {
  display: flex;
  gap: var(--jf-space-1);
}

.report__hint {
  margin: 0;
  font-size: var(--jf-text-sm);
  font-weight: normal;
  color: var(--jf-color-text-muted);
}

.report__link {
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-decoration: underline;
  cursor: pointer;
}

.report__table td {
  white-space: nowrap;
}

.report__table :deep(.report__strong) th,
.report__table :deep(.report__strong) td {
  font-weight: var(--jf-weight-bold);
}

.report__sub th {
  padding-left: var(--jf-space-4);
  font-weight: normal;
}

.report__number {
  width: 5.5rem;
}

.report__foot {
  margin: 0;
  padding: var(--jf-space-1) var(--jf-space-1-5);
}

.report__activity {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  margin-bottom: var(--jf-space-1);
}

.report__warnings {
  margin: 0;
  padding-left: 1.2rem;
}

.report__profile {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  max-width: 32rem;
}

.report__categories {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-2);
  margin: 0;
  padding: var(--jf-space-1);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
}

.report__categories label {
  display: flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  min-height: var(--jf-touch-target, 44px);
}

.report__mono {
  font-family: var(--jf-font-mono);
}

:deep(.report__copy) {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 36px;
  padding: 0 0.5rem;
  border: 1px solid transparent;
  border-radius: var(--jf-radius-sm);
  background: none;
  color: inherit;
  font: inherit;
  font-variant-numeric: tabular-nums;
  cursor: pointer;
}

:deep(.report__copy:hover),
:deep(.report__copy:focus-visible) {
  border-color: var(--jf-color-border);
  background: var(--jf-color-ground);
  outline: none;
}

:deep(.report__copy i) {
  font-size: 0.75rem;
  color: var(--jf-color-text-muted);
}
</style>
