<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import PortalEmptyCard from '@/components/portal/PortalEmptyCard.vue'
import PortalChangeRequestBanner from '@/components/portal/PortalChangeRequestBanner.vue'
import PortalChangeRequestResult from '@/components/portal/PortalChangeRequestResult.vue'
import PortalChangeRequestSheet from '@/components/portal/PortalChangeRequestSheet.vue'
import PortalNotice from '@/components/portal/PortalNotice.vue'
import ContactLink from '@/components/common/ContactLink.vue'
import { useChangeRequestsStore } from '@/stores/changeRequests'
import { usePortalStore } from '@/stores/portal'
import type { ChangeTarget } from '@/types/changeRequests'
import { fieldsFor } from '@/utils/changeRequestFields'

const portal = usePortalStore()
const requests = useChangeRequestsStore()
void requests.load()

const memberTarget = computed<ChangeTarget | null>(() => (data.value ? { kind: 'member', id: data.value.id } : null))
const parentTarget: ChangeTarget = { kind: 'parent' }
const editing = ref<ChangeTarget | null>(null)
const editingFields = computed(() => (editing.value ? fieldsFor(editing.value) : []))
const editingCurrent = computed<Record<string, string>>(() => {
  const source = (editing.value?.kind === 'parent' ? parent.value : data.value?.contact) as unknown as Record<string, string> | null | undefined
  return Object.fromEntries(editingFields.value.map(f => [f.field, source?.[f.key] ?? '']))
})
const editingTitle = computed(() => (editing.value?.kind === 'parent' ? 'Meine Kontaktdaten ändern' : `${data.value?.contact.first_name ?? 'Daten'} – Änderung beantragen`))
const editingExisting = computed(() => requests.openFor(editing.value))

function openForm(target: ChangeTarget | null) {
  if (!target) return
  requests.resetErrors()
  editing.value = target
}
async function sendRequest(fields: Record<string, string>) {
  if (editing.value && await requests.submit(editing.value, fields)) editing.value = null
}
function withdraw(id: number) { void requests.withdraw(id) }
const data = computed(() => portal.personData)
const parent = computed(() => portal.me?.parent ?? null)

watch(() => portal.selectedPersonId, id => { void portal.loadPerson(id) }, { immediate: true })

const dateFormat = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
function day(iso?: string | null) {
  if (!iso) return ''
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`)
  return Number.isNaN(d.getTime()) ? iso : dateFormat.format(d)
}
function monthYear(iso?: string | null) {
  const m = /^(\d{4})-(\d{2})/.exec(iso ?? '')
  return m ? `${m[2]}/${m[1]}` : ''
}
const address = (c: { street: string, zip_code: string, city: string }) =>
  [c.street, [c.zip_code, c.city].filter(Boolean).join(' ')].filter(Boolean).join(', ')

/** Rows with a contact kind render as tel:/mailto: links. */
interface DataRow { label: string, value: string, kind?: 'phone' | 'email' }

const contactRows = computed<DataRow[]>(() => {
  const c = data.value?.contact
  if (!c) return []
  return [
    { label: 'Name', value: `${c.first_name} ${c.last_name}`.trim() },
    ...(data.value?.birthday ? [{ label: 'Geburtstag', value: day(data.value.birthday) }] : []),
    { label: 'Adresse', value: address(c) },
    { label: 'Telefon', value: c.phone, kind: 'phone' as const },
    { label: 'Mobil', value: c.mobile, kind: 'phone' as const },
    { label: 'E-Mail', value: c.email, kind: 'email' as const },
  ].map(row => ({ ...row, value: row.value || '–' }))
})
const parentRows = computed<DataRow[]>(() => {
  const p = parent.value
  if (!p) return []
  return [
    { label: 'Name', value: `${p.first_name} ${p.last_name}`.trim() },
    { label: 'Adresse', value: address(p) },
    { label: 'Telefon', value: p.phone, kind: 'phone' as const },
    { label: 'Mobil', value: p.mobile, kind: 'phone' as const },
    { label: 'E-Mail', value: p.email, kind: 'email' as const },
    { label: 'Zweite E-Mail', value: p.email2, kind: 'email' as const },
  ].map(row => ({ ...row, value: row.value || '–' }))
})
const groupText = computed(() => {
  const g = data.value?.group
  if (!g) return ''
  return [g.group, g.departments.join(', ')].filter(Boolean).join(' · ') || '–'
})
const period = (start?: string | null, end?: string | null) =>
  [start && `ab ${day(start)}`, end && `bis ${day(end)}`].filter(Boolean).join(' ')
</script>

<template>
  <div class="page">
    <h1>Daten</h1>

    <section v-if="parent" class="card" aria-labelledby="own-title">
      <div class="card-head">
        <h2 id="own-title">Meine Kontaktdaten</h2>
        <span class="muted small">Elternteil</span>
      </div>
      <dl>
        <div v-for="row in parentRows" :key="row.label"><dt>{{ row.label }}</dt><dd><ContactLink v-if="row.kind" :kind="row.kind" :value="row.value === '–' ? '' : row.value" /><span v-else>{{ row.value }}</span></dd></div>
      </dl>
      <PortalChangeRequestBanner v-if="requests.openFor(parentTarget)" :request="requests.openFor(parentTarget)!" :busy="requests.busy" :error="requests.actionError" @edit="openForm(parentTarget)" @withdraw="withdraw(requests.openFor(parentTarget)!.id)" />
      <PortalChangeRequestResult v-else-if="requests.decidedFor(parentTarget)" :request="requests.decidedFor(parentTarget)!" />
      <Button :label="requests.openFor(parentTarget) ? 'Änderung beantragen (Antrag offen)' : 'Änderung beantragen'" severity="secondary" outlined :disabled="!!requests.openFor(parentTarget)" class="request" @click="openForm(parentTarget)" />
      <p class="muted small">Änderungen werden erst nach Freigabe durch die Jugendleitung übernommen.</p>
    </section>

    <p v-if="portal.personLoading" class="muted" role="status">Daten werden geladen …</p>

    <PortalEmptyCard v-else-if="portal.personError" icon="pi pi-exclamation-circle" title="Daten nicht verfügbar">
      {{ portal.personError.message }}
      <Button v-if="portal.personError.status !== 404" label="Erneut versuchen" severity="secondary" outlined size="small" class="retry" @click="portal.loadPerson(portal.selectedPersonId)" />
    </PortalEmptyCard>

    <PortalEmptyCard v-else-if="!data && !parent" icon="pi pi-id-card" title="Keine Person ausgewählt">
      Sobald ein Zugang mit einer Person verknüpft ist, siehst du hier die freigegebenen Daten.
    </PortalEmptyCard>

    <template v-else-if="data">
      <PortalChangeRequestBanner v-if="requests.openFor(memberTarget)" :request="requests.openFor(memberTarget)!" :busy="requests.busy" :error="requests.actionError" @edit="openForm(memberTarget)" @withdraw="withdraw(requests.openFor(memberTarget)!.id)" />
      <PortalChangeRequestResult v-else-if="requests.decidedFor(memberTarget)" :request="requests.decidedFor(memberTarget)!" />

      <section class="card" aria-labelledby="base-title">
        <div class="card-head">
          <h2 id="base-title">Name und Kontakt</h2>
          <span class="muted small">Stand heute</span>
        </div>
        <dl>
          <div v-for="row in contactRows" :key="row.label"><dt>{{ row.label }}</dt><dd><ContactLink v-if="row.kind" :kind="row.kind" :value="row.value === '–' ? '' : row.value" /><span v-else>{{ row.value }}</span></dd></div>
        </dl>
        <Button :label="requests.openFor(memberTarget) ? 'Änderung beantragen (Antrag offen)' : 'Änderung beantragen'" severity="secondary" outlined :disabled="!!requests.openFor(memberTarget)" class="request" @click="openForm(memberTarget)" />
        <p class="muted small">Änderungen werden erst nach Freigabe durch die Jugendleitung übernommen.</p>
      </section>

      <section v-if="data.group" class="card" aria-labelledby="group-title">
        <h2 id="group-title">Gruppe</h2>
        <p>{{ groupText }}</p>
      </section>

      <section v-if="data.qualifications" class="card" aria-labelledby="qual-title">
        <h2 id="qual-title">Qualifikationen</h2>
        <p v-if="!data.qualifications.length" class="muted">Keine Qualifikationen eingetragen.</p>
        <ul v-else class="list">
          <li v-for="(q, i) in data.qualifications" :key="i">
            <span class="item-title">{{ q.type }}</span>
            <span class="muted">
              <template v-if="q.acquired">seit {{ monthYear(q.acquired) }}</template>
              <template v-if="q.acquired && q.expires"> · </template>
              <template v-if="q.expires">gültig bis {{ monthYear(q.expires) }}</template>
            </span>
            <span v-if="!q.valid" class="expired"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> abgelaufen</span>
          </li>
        </ul>
        <p class="muted small">Nur lesbar. Nachweise pflegt die Jugendleitung.</p>
      </section>

      <section v-if="data.special_tasks" class="card" aria-labelledby="task-title">
        <h2 id="task-title">Sonderaufgaben</h2>
        <p v-if="!data.special_tasks.length" class="muted">Keine Sonderaufgaben eingetragen.</p>
        <ul v-else class="list">
          <li v-for="(t, i) in data.special_tasks" :key="i">
            <span class="item-title">{{ t.task }}</span>
            <span v-if="period(t.start, t.end)" class="muted">{{ period(t.start, t.end) }}</span>
          </li>
        </ul>
        <p class="muted small">Nur lesbar. Die Jugendleitung pflegt die Aufgaben.</p>
      </section>

      <section v-if="data.equipment" class="card" aria-labelledby="eq-title">
        <h2 id="eq-title">Ausrüstung</h2>
        <p v-if="!data.equipment.length" class="muted">Keine Ausrüstung eingetragen.</p>
        <ul v-else class="list">
          <li v-for="(e, i) in data.equipment" :key="i">
            <span class="item-title">{{ e.item }}<template v-if="e.variant"> · {{ e.variant }}</template></span>
            <span class="muted">{{ e.quantity }}×</span>
          </li>
        </ul>
        <p class="muted small">Nur lesbar. Die Ausgabe pflegt die Jugendleitung.</p>
      </section>

      <section v-if="data.membership" class="card" aria-labelledby="mem-title">
        <h2 id="mem-title">Mitgliedschaft</h2>
        <dl>
          <div><dt>Status</dt><dd>{{ data.membership.status }}</dd></div>
          <div v-if="data.membership.joined"><dt>Eintritt</dt><dd>{{ day(data.membership.joined) }}</dd></div>
        </dl>
      </section>

      <section v-if="data.identity" class="card" aria-labelledby="id-title">
        <h2 id="id-title">Ausweis</h2>
        <dl><div><dt>Ausweisnummer</dt><dd>{{ data.identity.card_number || '–' }}</dd></div></dl>
      </section>

      <section v-if="data.swimming" class="card" aria-labelledby="swim-title">
        <h2 id="swim-title">Schwimmfähigkeit</h2>
        <p>{{ data.swimming.can_swim ? 'Kann schwimmen' : 'Kann nicht schwimmen' }}</p>
      </section>

      <section v-if="data.other_parents" class="card" aria-labelledby="op-title">
        <h2 id="op-title">Weitere Kontaktpersonen</h2>
        <p v-if="!data.other_parents.length" class="muted">Keine weiteren Kontaktpersonen.</p>
        <ul v-else class="list">
          <li v-for="(o, i) in data.other_parents" :key="i">
            <span class="item-title">{{ o.name }}</span>
            <span v-if="o.phone || o.mobile" class="muted">
              <ContactLink v-if="o.phone" kind="phone" :value="o.phone" />
              <template v-if="o.phone && o.mobile"> · </template>
              <ContactLink v-if="o.mobile" kind="phone" :value="o.mobile" />
            </span>
            <span v-else class="muted">–</span>
          </li>
        </ul>
      </section>
    </template>

    <PortalChangeRequestSheet
      v-if="editing"
      :title="editingTitle"
      :fields="editingFields"
      :current="editingCurrent"
      :existing="editingExisting"
      :busy="requests.busy"
      :error="requests.formError"
      :field-errors="requests.fieldErrors"
      @close="editing = null"
      @submit="sendRequest"
    />

    <PortalNotice icon="pi pi-lock">
      Anwesenheiten, Notizen und Dienstbuch sind im Portal nicht einsehbar. Welche Daten sichtbar sind, legt die Jugendfeuerwehr fest.
    </PortalNotice>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
h1 { margin: 4px 0 0; font-size: 18px; font-weight: 700; }
h2 { margin: 0; font-size: 15px; font-weight: 700; }
p { margin: 0; font-size: 14px; }
.card { display: flex; flex-direction: column; gap: 10px; padding: 14px; border-radius: 14px; background: var(--p-content-background); border: 1px solid var(--p-content-border-color); }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.muted { color: var(--p-text-muted-color); }
.small { font-size: 12px; }
dl { margin: 0; display: flex; flex-direction: column; gap: 8px; font-size: 14px; }
dl > div { display: flex; justify-content: space-between; gap: 12px; }
dt { color: var(--p-text-muted-color); }
dd { margin: 0; text-align: right; overflow-wrap: anywhere; }
.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; font-size: 14px; }
.list li { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; }
.item-title { font-weight: 600; }
.expired { display: inline-flex; align-items: center; gap: 4px; color: var(--p-red-700); font-weight: 600; }
.app-dark .expired { color: var(--p-red-300); }
.request { min-height: 44px; border-radius: 10px; }
.retry { margin-top: 8px; min-height: 44px; }
</style>
