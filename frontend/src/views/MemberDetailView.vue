<template>
  <div class="member-detail">
    <StateView v-if="loading" kind="loading" title="Mitglied wird geladen …" />

    <template v-else-if="member">
      <nav aria-label="Brotkrumen" class="breadcrumb">
        <router-link to="/members">Mitglieder</router-link>
        <i class="pi pi-angle-right" aria-hidden="true"></i>
        <span aria-current="page">{{ member.full_name }}</span>
      </nav>

      <section class="detail-card profile-head" aria-labelledby="member-name">
        <PrivateAvatar
          :image="member.avatar_url"
          :label="member.avatar_url ? undefined : initials"
          shape="circle"
          class="profile-head__avatar"
        />
        <div class="profile-head__info">
          <div class="profile-head__title">
            <h1 id="member-name">{{ member.full_name }}</h1>
            <MemberStatusBadge :status="member.status" />
            <StatusBadge v-if="expiringQualification" class="profile-head__mobile-only" severity="warning" :label="`${expiringQualification.type_name} läuft ab`" />
          </div>
          <ul class="profile-head__meta">
            <li v-if="member.birthday"><i class="pi pi-calendar" aria-hidden="true"></i><span>{{ member.age }} Jahre<span class="profile-head__extra"> · geb. {{ formatDate(member.birthday) }}</span></span></li>
            <li v-if="member.group"><i class="pi pi-users" aria-hidden="true"></i>{{ member.group.name }}</li>
            <li v-if="member.joined" class="profile-head__extra"><i class="pi pi-sign-in" aria-hidden="true"></i>Mitglied seit {{ formatDate(member.joined) }}</li>
          </ul>
        </div>
        <div class="profile-head__actions">
          <Button
            icon="pi pi-ellipsis-v"
            text
            severity="secondary"
            aria-label="Weitere Aktionen"
            aria-haspopup="true"
            aria-controls="member_actions_menu"
            @click="toggleMenu"
          />
          <Menu id="member_actions_menu" ref="menu" :model="menuItems" :popup="true" />
          <Button label="Bearbeiten" icon="pi pi-pencil" @click="navigateToEdit" />
        </div>
        <div v-if="primaryContact || primaryEmail" class="profile-head__quick">
          <a v-if="primaryContact" :href="`tel:${primaryContact.phone}`" class="quick-action quick-action--primary">
            <i class="pi pi-phone" aria-hidden="true"></i>{{ primaryContact.parent.name }} anrufen
          </a>
          <a v-if="primaryEmail" :href="`mailto:${primaryEmail}`" class="quick-action">
            <i class="pi pi-envelope" aria-hidden="true"></i>E-Mail
          </a>
        </div>
      </section>

      <section v-if="facts.length" class="facts" aria-label="Auf einen Blick">
        <button v-for="fact in facts" :key="fact.tab" type="button" class="detail-card fact" @click="activeTab = fact.tab">
          <span class="fact__label">{{ fact.label }}</span>
          <span class="fact__value">{{ fact.value }}</span>
          <StatusBadge :label="fact.note" :severity="fact.severity" />
        </button>
      </section>

      <div class="detail-columns">
        <section class="detail-card detail-tabs" aria-label="Bereiche">
          <Tabs v-model:value="activeTab" lazy scrollable>
            <TabList>
              <Tab v-for="tab in tabs" :key="tab.value" :value="tab.value">
                {{ tab.label }}<span v-if="tab.count" class="tab-count">{{ tab.count }}</span>
              </Tab>
            </TabList>
            <TabPanels>
              <TabPanel value="overview">
                <div class="overview">
                  <section v-if="sources.attendance.enabled" class="overview-block" aria-labelledby="attendance-heading">
                    <header class="overview-block__header">
                      <h2 id="attendance-heading">Teilnahme</h2>
                      <button type="button" class="text-link" @click="activeTab = 'attendance'">Alle Dienste</button>
                    </header>
                    <StateView v-if="sources.attendance.state" :kind="sources.attendance.state" class="compact-state" @retry="loadAttendance" />
                    <template v-else-if="recentAttendance.length">
                      <ol class="attendance-strip" :aria-label="attendanceSummaryText">
                        <li v-for="record in recentAttendance" :key="record.id" :class="`attendance-mark attendance-mark--${record.state ?? 'none'}`" :title="`${formatDate(record.service_date)}: ${record.state_display}`">
                          <span class="attendance-mark__box"><i :class="attendanceIcon(record.state)" aria-hidden="true"></i></span>
                          <span class="attendance-mark__day">{{ formatDay(record.service_date) }}</span>
                          <span class="visually-hidden">{{ record.state_display }}</span>
                        </li>
                      </ol>
                      <p class="muted">{{ attendanceSummaryText }}</p>
                    </template>
                    <p v-else class="muted">Noch keine Anwesenheiten erfasst.</p>
                  </section>

                  <section v-if="sources.qualifications.enabled" class="overview-block" aria-labelledby="qualifications-heading">
                    <header class="overview-block__header">
                      <h2 id="qualifications-heading">Qualifikationen</h2>
                      <button type="button" class="text-link" @click="activeTab = 'qualifications'">Verwalten</button>
                    </header>
                    <StateView v-if="sources.qualifications.state" :kind="sources.qualifications.state" class="compact-state" @retry="loadQualifications" />
                    <ul v-else-if="qualifications.length" class="row-list">
                      <li v-for="qualification in qualifications.slice(0, 5)" :key="qualification.id" class="row-list__item">
                        <span class="row-list__text">
                          <span class="row-list__title">{{ qualification.type_name }}</span>
                          <span class="row-list__meta">{{ qualificationMeta(qualification) }}</span>
                        </span>
                        <StatusBadge v-bind="qualificationStatus(qualification)" />
                      </li>
                    </ul>
                    <p v-else class="muted">Keine Qualifikationen hinterlegt.</p>
                  </section>

                  <section class="overview-block" aria-labelledby="events-heading">
                    <header class="overview-block__header">
                      <h2 id="events-heading">Einträge</h2>
                      <button type="button" class="text-link" @click="activeTab = 'events'">Alle Einträge</button>
                    </header>
                    <StateView v-if="sources.events.state" :kind="sources.events.state" class="compact-state" @retry="loadEvents" />
                    <ol v-else-if="events.length" class="row-list">
                      <li v-for="event in events.slice(0, 3)" :key="event.id" class="row-list__item row-list__item--dated">
                        <span class="row-list__date">{{ formatDate(event.datetime) }}</span>
                        <span class="row-list__text">
                          <span class="row-list__title">{{ event.event_type?.name ?? 'Eintrag' }}</span>
                          <span v-if="event.notes" class="row-list__meta">{{ event.notes }}</span>
                        </span>
                      </li>
                    </ol>
                    <p v-else class="muted">Noch keine Einträge.</p>
                  </section>
                </div>
              </TabPanel>
              <TabPanel value="qualifications">
                <QualificationsManager :member-id="memberId" />
              </TabPanel>
              <TabPanel value="specialtasks">
                <SpecialTasksManager :member-id="memberId" />
              </TabPanel>
              <TabPanel value="events">
                <EventsManager :member-id="memberId" />
              </TabPanel>
              <TabPanel value="attendance">
                <AttendanceTab :member-id="memberId" />
              </TabPanel>
              <TabPanel value="equipment">
                <MemberEquipmentTab :member-id="memberId" />
              </TabPanel>
              <TabPanel value="attachments">
                <AttachmentsManager :member-id="memberId" />
              </TabPanel>
            </TabPanels>
          </Tabs>
        </section>

        <aside class="detail-aside">
          <section class="detail-card aside-card" aria-labelledby="emergency-heading">
            <h2 id="emergency-heading">Im Notfall erreichen</h2>
            <StateView v-if="loadingParents" kind="loading" title="Kontakte werden geladen …" class="compact-state" />
            <ul v-else-if="parents.length" class="contact-list">
              <li v-for="parent in parents" :key="parent.id" class="contact">
                <span class="contact__text">
                  <span class="contact__name">{{ parent.full_name }}</span>
                  <span class="contact__meta">{{ reachableNumber(parent) || 'Keine Telefonnummer hinterlegt' }}</span>
                </span>
                <a
                  v-if="reachableNumber(parent)"
                  :href="`tel:${reachableNumber(parent)}`"
                  class="contact__action contact__action--call"
                  :aria-label="`${parent.full_name} anrufen`"
                ><i class="pi pi-phone" aria-hidden="true"></i><span>Anrufen</span></a>
                <router-link
                  v-else
                  :to="`/parents/${parent.id}/edit`"
                  class="contact__action"
                  :aria-label="`Telefonnummer für ${parent.full_name} ergänzen`"
                >Nummer ergänzen</router-link>
              </li>
            </ul>
            <p v-else class="muted">Keine Elternkontakte hinterlegt.</p>
            <router-link :to="`/members/${memberId}/edit`" class="text-link">Kontakte verwalten</router-link>
          </section>

          <section class="detail-card aside-card" aria-labelledby="master-data-heading">
            <h2 id="master-data-heading">Stammdaten</h2>
            <dl class="kv">
              <dt>Anschrift</dt>
              <dd>{{ address || '–' }}</dd>
              <dt>E-Mail</dt>
              <dd><ContactLink kind="email" :value="member.email" /></dd>
              <dt>Telefon</dt>
              <dd><ContactLink kind="phone" :value="member.phone" /></dd>
              <dt>Mobil</dt>
              <dd><ContactLink kind="phone" :value="member.mobile" /></dd>
              <dt>Ausweis-Nr.</dt>
              <dd>{{ member.identityCardNumber || '–' }}</dd>
              <dt>Schwimmen</dt>
              <dd class="kv__flag">
                <i :class="member.canSwimm ? 'pi pi-check-circle kv__flag--yes' : 'pi pi-times-circle kv__flag--no'" aria-hidden="true"></i>
                {{ member.canSwimm ? 'Kann schwimmen' : 'Kann nicht schwimmen' }}
              </dd>
            </dl>
          </section>

          <section class="detail-card aside-card">
            <ChangeLogCard kind="member" :record-id="memberId" />
          </section>

          <section v-if="canLinkAccounts" class="detail-card aside-card">
            <AccountLinkCard kind="member" :record-id="memberId" :record-name="`${member.name} ${member.lastname}`" />
          </section>

          <section class="detail-card aside-card" aria-labelledby="notes-heading">
            <div class="aside-card__title">
              <i class="pi pi-shield" aria-hidden="true"></i>
              <h2 id="notes-heading">Hinweise und Bemerkungen</h2>
            </div>
            <template v-if="member.notes">
              <p v-if="!notesVisible" class="muted">Bemerkungen sind hinterlegt und bleiben ausgeblendet, bis du sie anzeigst.</p>
              <p v-else id="member-notes" class="notes">{{ member.notes }}</p>
              <Button
                :label="notesVisible ? 'Ausblenden' : 'Bemerkungen anzeigen'"
                severity="secondary"
                outlined
                class="aside-card__button"
                aria-controls="member-notes"
                :aria-expanded="notesVisible"
                @click="notesVisible = !notesVisible"
              />
            </template>
            <p v-else class="muted">Keine Bemerkungen hinterlegt.</p>
          </section>
        </aside>
      </div>
    </template>

    <MemberDeletionDialog
      v-model="showDeletionDialog"
      :member-name="deletionConflict.memberName"
      :transaction-count="deletionConflict.transactionCount"
      :loading="deletionLoading"
      @confirm="handleDeletionStrategy"
      @cancel="showDeletionDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
import ContactLink from '@/components/common/ContactLink.vue'
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { membersApi, parentsApi } from '@/api/members'
import { qualificationsApi } from '@/api/qualifications'
import { servicebookApi } from '@/api/servicebook'
import { useAuthStore } from '@/stores/auth'
import { classifyApiError } from '@/utils/apiError'
import type { Member, Parent } from '@/types/api'
import type { Event } from '@/types/events'
import type { Qualification } from '@/types/qualifications'
import type { Attendance, AttendanceSummary } from '@/types/servicebook'
import type { MemberDeletionStrategy } from '@/types/inventory'
import Button from 'primevue/button'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Menu from 'primevue/menu'
import PrivateAvatar from '@/components/common/PrivateAvatar.vue'
import AccountLinkCard from '@/components/members/organisms/AccountLinkCard.vue'
import ChangeLogCard from '@/components/members/organisms/ChangeLogCard.vue'
import StateView, { stateForError } from '@/components/common/StateView.vue'
import StatusBadge, { type StatusSeverity } from '@/components/common/StatusBadge.vue'
import MemberStatusBadge from '@/components/members/atoms/MemberStatusBadge.vue'
import EventsManager from '@/components/members/profile/EventsManager.vue'
import AttachmentsManager from '@/components/members/profile/AttachmentsManager.vue'
import QualificationsManager from '@/components/members/profile/QualificationsManager.vue'
import SpecialTasksManager from '@/components/members/profile/SpecialTasksManager.vue'
import MemberEquipmentTab from '@/components/members/profile/MemberEquipmentTab.vue'
import AttendanceTab from '@/components/members/profile/AttendanceTab.vue'
import MemberDeletionDialog from '@/components/members/molecules/MemberDeletionDialog.vue'

type SourceState = 'loading' | 'forbidden' | 'offline' | 'error' | null

const router = useRouter()
const route = useRoute()
const confirm = useConfirm()
const toast = useToast()
const authStore = useAuthStore()
// Account management links the member to the person's own staff account (PORTAL-04).
const canLinkAccounts = computed(() => authStore.hasPerm('users.change_customuser'))

const member = ref<Member | null>(null)
const parents = ref<Parent[]>([])
const loading = ref(true)
const loadingParents = ref(false)
const menu = ref()
const activeTab = ref('overview')
const notesVisible = ref(false)

const attendances = ref<Attendance[]>([])
const attendanceSummary = ref<AttendanceSummary | null>(null)
const qualifications = ref<Qualification[]>([])
const events = ref<Event[]>([])
const sources = reactive({
  attendance: { enabled: authStore.canAccessModule('view_service'), state: 'loading' as SourceState },
  qualifications: { enabled: authStore.canAccessModule('view_qualification'), state: 'loading' as SourceState },
  events: { enabled: true, state: 'loading' as SourceState },
})

const showDeletionDialog = ref(false)
const deletionLoading = ref(false)
const deletionConflict = ref({ memberName: '', transactionCount: 0 })

const memberId = Number(route.params.id)
const RECENT_SERVICES = 14

const menuItems = ref([
  {
    label: 'Aktionen',
    items: [
      {
        label: 'Löschen',
        icon: 'pi pi-trash',
        command: () => confirmDelete()
      }
    ]
  }
])

onMounted(async () => {
  await loadMember()
})

const loadMember = async () => {
  try {
    loading.value = true
    const response = await membersApi.get(memberId)
    member.value = response.data
    void loadOverview()
    await loadParents()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Mitglied konnte nicht geladen werden',
      life: 3000
    })
    router.push('/members')
  } finally {
    loading.value = false
  }
}

const loadParents = async () => {
  try {
    loadingParents.value = true
    const response = await membersApi.getParents(memberId)
    parents.value = response.data
  } catch {
  } finally {
    loadingParents.value = false
  }
}

/** Each overview source loads and fails on its own, so one outage never blanks the page. */
async function loadSource(key: keyof typeof sources, load: () => Promise<void>) {
  if (!sources[key].enabled) return
  sources[key].state = 'loading'
  try {
    await load()
    sources[key].state = null
  } catch (error) {
    sources[key].state = stateForError(classifyApiError(error))
  }
}

const loadAttendance = () => loadSource('attendance', async () => {
  const response = await servicebookApi.attendance.getByMember({ member_id: memberId, limit: RECENT_SERVICES })
  attendances.value = response.data.attendances
  attendanceSummary.value = response.data.summary
})

const loadQualifications = () => loadSource('qualifications', async () => {
  const response = await qualificationsApi.list({ member: memberId, page_size: 50 })
  qualifications.value = response.data.results
})

const loadEvents = () => loadSource('events', async () => {
  const response = await membersApi.getEvents(memberId)
  events.value = [...response.data].sort((a, b) => b.datetime.localeCompare(a.datetime))
})

function loadOverview() {
  return Promise.all([loadAttendance(), loadQualifications(), loadEvents()])
}

const initials = computed(() => {
  if (!member.value) return ''
  return `${member.value.name?.[0] ?? ''}${member.value.lastname?.[0] ?? ''}`.toUpperCase()
})

const address = computed(() => {
  if (!member.value) return ''
  const city = [member.value.zip_code, member.value.city].filter(Boolean).join(' ')
  return [member.value.street, city].filter(Boolean).join(', ')
})

const reachableNumber = (parent: Parent) => parent.mobile || parent.phone || ''

const primaryContact = computed(() => {
  const parent = parents.value.find((p) => reachableNumber(p))
  return parent ? { parent, phone: reachableNumber(parent) } : null
})

const primaryEmail = computed(() => parents.value.find((p) => p.email)?.email ?? member.value?.email ?? '')

/** Oldest first, so the strip reads left to right like a timeline. */
const recentAttendance = computed(() => [...attendances.value]
  .sort((a, b) => a.service_date.localeCompare(b.service_date))
  .slice(-RECENT_SERVICES))

const attendanceCounts = computed(() => {
  const counts = { A: 0, E: 0, F: 0 }
  for (const record of recentAttendance.value) {
    if (record.state) counts[record.state] += 1
  }
  return counts
})

const attendanceSummaryText = computed(() => {
  const { A, E, F } = attendanceCounts.value
  return `Letzte ${recentAttendance.value.length} Dienste: ${A} anwesend · ${E} entschuldigt · ${F} gefehlt`
})

const expiringQualification = computed(() => qualifications.value.find((q) => q.expires_soon && !q.is_expired) ?? null)

const facts = computed(() => {
  const list: { tab: string; label: string; value: string; note: string; severity: StatusSeverity }[] = []
  if (sources.attendance.enabled && !sources.attendance.state && recentAttendance.value.length) {
    const { A } = attendanceCounts.value
    const total = recentAttendance.value.length
    const rate = Math.round((A / total) * 100)
    list.push({
      tab: 'attendance',
      label: 'Teilnahme',
      value: `${rate} %`,
      note: `${A} von ${total} Diensten`,
      severity: rate >= 75 ? 'success' : rate >= 50 ? 'warning' : 'danger',
    })
  }
  if (sources.qualifications.enabled && !sources.qualifications.state) {
    const expired = qualifications.value.filter((q) => q.is_expired).length
    const soon = qualifications.value.filter((q) => q.expires_soon && !q.is_expired).length
    list.push({
      tab: 'qualifications',
      label: 'Qualifikationen',
      value: String(qualifications.value.length),
      note: expired ? `${expired} abgelaufen` : soon ? `${soon} läuft bald ab` : 'alle gültig',
      severity: expired ? 'danger' : soon ? 'warning' : 'success',
    })
  }
  if (!sources.events.state) {
    list.push({
      tab: 'events',
      label: 'Einträge',
      value: String(events.value.length),
      note: events.value[0] ? `zuletzt ${formatDate(events.value[0].datetime)}` : 'noch keine',
      severity: 'neutral',
    })
  }
  return list
})

const tabs = computed(() => [
  { value: 'overview', label: 'Übersicht' },
  { value: 'qualifications', label: 'Qualifikationen', count: sources.qualifications.state ? 0 : qualifications.value.length },
  { value: 'specialtasks', label: 'Sonderaufgaben' },
  { value: 'events', label: 'Einträge', count: sources.events.state ? 0 : events.value.length },
  { value: 'attendance', label: 'Anwesenheit' },
  { value: 'equipment', label: 'Ausrüstung' },
  { value: 'attachments', label: 'Anhänge' },
])

function qualificationStatus(qualification: Qualification): { label: string; severity: StatusSeverity } {
  if (qualification.is_expired) return { label: 'Abgelaufen', severity: 'danger' }
  if (qualification.expires_soon && qualification.date_expires) return { label: `Läuft am ${formatDate(qualification.date_expires)} ab`, severity: 'warning' }
  return { label: 'Gültig', severity: 'success' }
}

function qualificationMeta(qualification: Qualification) {
  const acquired = `Erworben ${formatDate(qualification.date_acquired)}`
  return qualification.date_expires ? `${acquired} · gültig bis ${formatDate(qualification.date_expires)}` : `${acquired} · unbefristet`
}

function attendanceIcon(state: Attendance['state']) {
  if (state === 'A') return 'pi pi-check'
  if (state === 'E') return 'pi pi-clock'
  if (state === 'F') return 'pi pi-times'
  return 'pi pi-minus'
}

const formatDate = (dateString: string | null) => {
  if (!dateString) return '–'
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const formatDay = (dateString: string) => new Date(dateString).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })

const navigateToEdit = () => {
  router.push(`/members/${memberId}/edit`)
}

const toggleMenu = (event: MouseEvent) => {
  menu.value.toggle(event)
}

const confirmDelete = () => {
  // Identify parents that would become childless after this deletion
  const orphanedParents = parents.value.filter(
    (p) => p.children.length === 1 && p.children[0] === memberId
  )

  confirm.require({
    message: `Möchten Sie ${member.value?.full_name} wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await membersApi.delete(memberId)
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Mitglied wurde gelöscht',
          life: 3000
        })
        if (orphanedParents.length > 0) {
          const parentNames = orphanedParents.map((p) => p.full_name).join(', ')
          confirm.require({
            message: `${orphanedParents.length === 1 ? 'Der folgende Elternteil hat' : 'Die folgenden Elternteile haben'} nun kein verknüpftes Mitglied mehr: ${parentNames}. Möchten Sie ${orphanedParents.length === 1 ? 'diesen' : 'diese'} ebenfalls löschen?`,
            header: 'Eltern ohne Kind',
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: 'Ja, löschen',
            rejectLabel: 'Behalten',
            accept: async () => {
              try {
                await Promise.all(orphanedParents.map((p) => parentsApi.delete(p.id)))
                toast.add({
                  severity: 'success',
                  summary: 'Eltern gelöscht',
                  detail: `${orphanedParents.length === 1 ? 'Elternteil wurde' : 'Elternteile wurden'} gelöscht`,
                  life: 3000
                })
              } catch {
                toast.add({
                  severity: 'error',
                  summary: 'Fehler',
                  detail: 'Elternteile konnten nicht gelöscht werden',
                  life: 3000
                })
              } finally {
                router.push('/members')
              }
            },
            reject: () => {
              router.push('/members')
            }
          })
        } else {
          router.push('/members')
        }
      } catch (err: unknown) {
        const axiosErr = err as { response?: { status?: number; data?: { transaction_count?: number; member_name?: string } } }
        if (axiosErr.response?.status === 409 && axiosErr.response.data?.transaction_count !== undefined) {
          deletionConflict.value = {
            memberName: axiosErr.response.data.member_name ?? member.value?.full_name ?? '',
            transactionCount: axiosErr.response.data.transaction_count,
          }
          showDeletionDialog.value = true
        } else {
          toast.add({
            severity: 'error',
            summary: 'Fehler',
            detail: 'Mitglied konnte nicht gelöscht werden',
            life: 3000
          })
        }
      }
    }
  })
}

async function handleDeletionStrategy(strategy: MemberDeletionStrategy) {
  deletionLoading.value = true
  try {
    await membersApi.deleteWithStrategy(memberId, strategy)
    showDeletionDialog.value = false
    toast.add({ severity: 'success', summary: 'Erfolg', detail: 'Mitglied wurde gelöscht', life: 3000 })
    router.push('/members')
  } catch (error) {
    const response = error as { response?: { data?: { detail?: string } } }
    toast.add({ severity: 'error', summary: 'Fehler', detail: response.response?.data?.detail ?? 'Mitglied konnte nicht gelöscht werden', life: 5000 })
  } finally {
    deletionLoading.value = false
  }
}
</script>

<style scoped>
.member-detail {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  max-width: 1400px;
  margin: 0 auto;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.breadcrumb a {
  color: var(--jf-color-primary);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}

.breadcrumb i {
  font-size: 0.75rem;
}

.detail-card {
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: var(--jf-shadow-sm);
}

.profile-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-2) var(--jf-space-3);
  padding: var(--jf-space-3);
}

.profile-head__avatar {
  flex: none;
  width: 72px;
  height: 72px;
  background: var(--surface-hover);
  color: var(--p-surface-700);
  font-size: 1.5rem;
  font-weight: var(--jf-weight-bold);
}

.app-dark .profile-head__avatar {
  color: var(--p-surface-200);
}

.profile-head__info {
  flex: 1 1 320px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
}

.profile-head__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1) var(--jf-space-1-5);
}

.profile-head__title h1 {
  margin: 0;
  font-size: var(--jf-text-2xl);
  line-height: 1.2;
  letter-spacing: -0.015em;
}

.profile-head__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-0-5) var(--jf-space-3);
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.profile-head__meta li {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
}

.profile-head__actions {
  display: flex;
  gap: var(--jf-space-1);
}

.profile-head__quick,
.profile-head__mobile-only {
  display: none;
}

.quick-action {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--jf-space-1);
  min-height: 48px;
  padding: 0 var(--jf-space-2);
  border: 1px solid var(--p-surface-300);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}

.quick-action--primary {
  border-color: var(--jf-color-primary);
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
}

.facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--jf-space-2);
}

.fact {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: var(--jf-space-2);
  font: inherit;
  color: var(--jf-color-text);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--jf-duration), box-shadow var(--jf-duration);
}

.fact:hover {
  border-color: var(--p-surface-300);
  box-shadow: var(--jf-shadow-md);
}

.fact__label {
  font-size: 0.8125rem;
  font-weight: var(--jf-weight-medium);
  color: var(--jf-color-text-muted);
}

.fact__value {
  margin-bottom: var(--jf-space-0-5);
  font-size: 1.5rem;
  font-weight: var(--jf-weight-bold);
  line-height: 1.2;
}

.detail-columns {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--jf-space-3);
}

.detail-tabs {
  flex: 2 1 520px;
  min-width: 0;
  overflow: hidden;
}

.detail-tabs :deep(.p-tablist) {
  padding: 0 var(--jf-space-1-5);
  border-bottom: 1px solid var(--jf-color-border);
}

.detail-tabs :deep(.p-tablist-tab-list),
.detail-tabs :deep(.p-tablist-content),
.detail-tabs :deep(.p-tab) {
  background: transparent;
  border-color: transparent;
}

.detail-tabs :deep(.p-tab) {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  padding: 0 var(--jf-space-2);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  white-space: nowrap;
}

.detail-tabs :deep(.p-tabpanels) {
  padding: var(--jf-space-3);
  background: transparent;
}

.tab-count {
  display: inline-grid;
  place-items: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--surface-hover);
  color: var(--jf-color-text);
  font-size: var(--jf-text-xs);
}

.overview {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-3);
}

.overview-block {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
}

.overview-block__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-2);
}

.overview-block h2,
.aside-card h2 {
  margin: 0;
  font-size: var(--jf-text-lg);
  font-weight: var(--jf-weight-semibold);
}

.text-link {
  display: inline-flex;
  align-items: center;
  min-height: var(--jf-touch-target);
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-primary);
  text-decoration: none;
  cursor: pointer;
}

.muted {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.compact-state {
  padding: var(--jf-space-2);
}

.attendance-strip {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.attendance-mark {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--jf-space-0-5);
  font-size: 0.6875rem;
  color: var(--jf-color-text-muted);
}

.attendance-mark__box {
  display: grid;
  place-items: center;
  width: 100%;
  max-width: 32px;
  height: 32px;
  border-radius: 6px;
  background: var(--mark-bg, var(--surface-hover));
  color: var(--mark-fg, var(--jf-color-text-muted));
  font-size: 0.75rem;
}

.attendance-mark--A { --mark-bg: var(--p-green-100); --mark-fg: var(--p-green-800); }
.attendance-mark--E { --mark-bg: var(--p-amber-100); --mark-fg: var(--p-amber-800); }
.attendance-mark--F { --mark-bg: var(--p-red-100); --mark-fg: var(--p-red-800); }
.app-dark .attendance-mark--A { --mark-bg: color-mix(in srgb, var(--p-green-400), transparent 84%); --mark-fg: var(--p-green-300); }
.app-dark .attendance-mark--E { --mark-bg: color-mix(in srgb, var(--p-amber-400), transparent 84%); --mark-fg: var(--p-amber-300); }
.app-dark .attendance-mark--F { --mark-bg: color-mix(in srgb, var(--p-red-400), transparent 84%); --mark-fg: var(--p-red-300); }

.row-list {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.row-list__item {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-1-5) 0;
  border-top: 1px solid var(--jf-color-border);
}

.row-list__item--dated {
  align-items: flex-start;
  font-size: var(--jf-text-sm);
}

.row-list__date {
  flex: none;
  width: 84px;
  color: var(--jf-color-text-muted);
}

.row-list__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.row-list__title {
  font-weight: var(--jf-weight-semibold);
}

.row-list__meta {
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.detail-aside {
  flex: 1 1 320px;
  max-width: 420px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-3);
}

.aside-card {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-3);
}

.aside-card__title {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
}

.aside-card__title i {
  color: var(--jf-color-text-muted);
}

.aside-card__button {
  align-self: flex-start;
}

.contact-list {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.contact {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
}

.contact__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.contact__name {
  font-weight: var(--jf-weight-semibold);
}

.contact__meta {
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.contact__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  padding: 0 var(--jf-space-2);
  border: 1px solid var(--p-surface-300);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
  white-space: nowrap;
}

.contact__action--call {
  border-color: var(--jf-color-primary);
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
}

.kv {
  display: grid;
  grid-template-columns: minmax(100px, auto) 1fr;
  gap: 10px var(--jf-space-2);
  margin: 0;
  font-size: var(--jf-text-sm);
}

.kv dt {
  color: var(--jf-color-text-muted);
}

.kv dd {
  margin: 0;
  font-weight: var(--jf-weight-medium);
  overflow-wrap: anywhere;
}

.kv a {
  color: var(--jf-color-primary);
}

.kv__flag {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
}

.kv__flag--yes { color: var(--p-green-700); }
.kv__flag--no { color: var(--jf-color-text-muted); }
.app-dark .kv__flag--yes { color: var(--p-green-300); }

.notes {
  margin: 0;
  white-space: pre-wrap;
  font-size: var(--jf-text-sm);
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

@media (max-width: 767px) {
  .member-detail {
    gap: var(--jf-space-1-5);
  }

  .breadcrumb {
    display: none;
  }

  .profile-head {
    align-items: flex-start;
    padding: var(--jf-space-2);
    gap: var(--jf-space-1-5);
  }

  .profile-head__meta .profile-head__extra {
    display: none;
  }

  .profile-head__meta {
    gap: var(--jf-space-0-5) var(--jf-space-2);
  }

  .profile-head__avatar {
    width: 56px;
    height: 56px;
    font-size: 1.25rem;
  }

  .profile-head__info {
    flex: 1 1 0;
  }

  .profile-head__title h1 {
    font-size: var(--jf-text-xl);
  }

  .profile-head__actions {
    gap: 0;
  }

  .profile-head__actions :deep(.p-button:not(.p-button-icon-only)) {
    width: var(--jf-touch-target);
    padding: 0;
  }

  .profile-head__actions :deep(.p-button:not(.p-button-icon-only) .p-button-label) {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }

  .profile-head__quick {
    display: flex;
    flex: 1 1 100%;
    gap: var(--jf-space-1);
  }

  .quick-action {
    white-space: nowrap;
  }

  .quick-action--primary {
    flex: 2;
  }

  .attendance-strip {
    gap: 3px;
  }

  .attendance-mark__day {
    display: none;
  }

  .profile-head__mobile-only {
    display: inline-flex;
  }

  .facts {
    display: none;
  }

  .detail-tabs :deep(.p-tablist) {
    padding: var(--jf-space-1);
    border-bottom: 0;
  }

  .detail-tabs :deep(.p-tablist-active-bar) {
    display: none;
  }

  .detail-tabs :deep(.p-tab) {
    min-height: 40px;
    margin-right: var(--jf-space-1);
    border: 1px solid var(--p-surface-300);
    border-radius: 999px;
  }

  .detail-tabs :deep(.p-tab.p-tab-active) {
    border-color: var(--jf-color-text);
    background: var(--jf-color-text);
    color: var(--jf-color-card);
  }

  .detail-tabs :deep(.p-tabpanels) {
    padding: var(--jf-space-2);
  }

  .detail-aside {
    max-width: none;
    gap: var(--jf-space-1-5);
  }

  .aside-card {
    padding: var(--jf-space-2);
  }
}
</style>
