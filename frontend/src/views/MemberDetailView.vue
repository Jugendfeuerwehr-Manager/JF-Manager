<template>
  <div class="member-profile-view">
    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <div v-else-if="member" class="profile-container">
      <!-- Header Section -->
      <Card class="profile-header-card">
        <template #content>
          <div class="profile-header">
            <div class="avatar-section">
              <Avatar
                v-if="member.avatar_url"
                :image="member.avatar_url"
                size="xlarge"
                shape="circle"
                class="member-avatar"
              />
              <Avatar
                v-else
                :label="getInitials(member.full_name)"
                size="xlarge"
                shape="circle"
                class="member-avatar"
                :style="{ backgroundColor: '#6366f1', color: 'white' }"
              />
            </div>
            
            <div class="header-info">
              <div class="name-section">
                <h1>{{ member.full_name }}</h1>
                <Tag
                  v-if="member.status"
                  :value="member.status.name"
                  :style="{ backgroundColor: member.status.color, color: 'white' }"
                />
              </div>
              
              <div class="quick-info">
                <div class="info-item">
                  <i class="pi pi-calendar"></i>
                  <span>{{ formatDate(member.birthday) }} ({{ member.age }} Jahre)</span>
                </div>
                <div v-if="member.group" class="info-item">
                  <i class="pi pi-users"></i>
                  <span>Gruppe {{ member.group.name }}</span>
                </div>
                <div v-if="member.joined" class="info-item">
                  <i class="pi pi-sign-in"></i>
                  <span>Beigetreten: {{ formatDate(member.joined) }}</span>
                </div>
              </div>
            </div>

            <div class="header-actions">
              <Button
                label="Bearbeiten"
                icon="pi pi-pencil"
                @click="navigateToEdit"
                severity="secondary"
                outlined
              />
              <Button
                icon="pi pi-ellipsis-v"
                text
                @click="toggleMenu"
                aria-haspopup="true"
                aria-controls="overlay_menu"
              />
              <Menu ref="menu" :model="menuItems" :popup="true" />
            </div>
          </div>
        </template>
      </Card>

      <!-- Main Content Tabs -->
      <TabView class="profile-tabs">
        <!-- Personal Information Tab -->
        <TabPanel value="0" header="Persönliche Daten">
          <div class="info-grid">
            <Card class="info-card">
              <template #title>
                <div class="card-title">
                  <i class="pi pi-user"></i>
                  <span>Kontaktinformationen</span>
                </div>
              </template>
              <template #content>
                <div class="info-list">
                  <div class="info-row">
                    <span class="info-label">E-Mail:</span>
                    <span class="info-value">
                      <a v-if="member.email" :href="`mailto:${member.email}`">{{ member.email }}</a>
                      <span v-else class="text-muted">Nicht angegeben</span>
                    </span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Telefon:</span>
                    <span class="info-value">
                      <a v-if="member.phone" :href="`tel:${member.phone}`">{{ member.phone }}</a>
                      <span v-else class="text-muted">Nicht angegeben</span>
                    </span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Mobil:</span>
                    <span class="info-value">
                      <a v-if="member.mobile" :href="`tel:${member.mobile}`">{{ member.mobile }}</a>
                      <span v-else class="text-muted">Nicht angegeben</span>
                    </span>
                  </div>
                </div>
              </template>
            </Card>

            <Card class="info-card">
              <template #title>
                <div class="card-title">
                  <i class="pi pi-map-marker"></i>
                  <span>Adresse</span>
                </div>
              </template>
              <template #content>
                <div class="info-list">
                  <div class="info-row">
                    <span class="info-label">Straße:</span>
                    <span class="info-value">{{ member.street || '-' }}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">PLZ / Ort:</span>
                    <span class="info-value">{{ member.zip_code }} {{ member.city }}</span>
                  </div>
                </div>
              </template>
            </Card>

            <Card class="info-card">
              <template #title>
                <div class="card-title">
                  <i class="pi pi-id-card"></i>
                  <span>Weitere Informationen</span>
                </div>
              </template>
              <template #content>
                <div class="info-list">
                  <div class="info-row">
                    <span class="info-label">Ausweisnummer:</span>
                    <span class="info-value">{{ member.identityCardNumber || '-' }}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Kann schwimmen:</span>
                    <span class="info-value">
                      <i :class="member.canSwimm ? 'pi pi-check text-green-500' : 'pi pi-times text-red-500'"></i>
                    </span>
                  </div>
                </div>
              </template>
            </Card>

            <Card v-if="member.notes" class="info-card full-width">
              <template #title>
                <div class="card-title">
                  <i class="pi pi-file-edit"></i>
                  <span>Notizen</span>
                </div>
              </template>
              <template #content>
                <p class="notes-content">{{ member.notes }}</p>
              </template>
            </Card>
          </div>
        </TabPanel>

        <!-- Parents Tab (reusable component) -->
        <TabPanel value="1" header="Eltern">
          <ParentContacts :parents="parents" :loading="loadingParents" variant="detailed" />
        </TabPanel>

        <!-- Inventory Tab -->
        <TabPanel value="2" header="Ausrüstung">
          <div class="coming-soon">
            <i class="pi pi-box" style="font-size: 3rem; color: var(--text-color-secondary);"></i>
            <p>Ausrüstungsverwaltung wird bald verfügbar sein</p>
            <small v-if="member.storage_location">Lagerort ID: {{ member.storage_location }}</small>
          </div>
        </TabPanel>

        <!-- Events Tab -->
        <TabPanel value="3" header="Einträge">
          <div v-if="loadingEvents" class="loading-container">
            <ProgressSpinner />
          </div>
          <div v-else-if="events.length === 0" class="empty-state">
            <i class="pi pi-calendar" style="font-size: 3rem; color: var(--text-color-secondary);"></i>
            <p>Keine Einträge vorhanden</p>
          </div>
          <div v-else>
            <DataTable :value="events" striped-rows paginator :rows="10">
              <Column field="datetime" header="Datum" sortable>
                <template #body="{ data }">
                  {{ formatDateTime(data.datetime) }}
                </template>
              </Column>
              <Column field="event_type.name" header="Typ" sortable />
              <Column field="notes" header="Notizen" />
            </DataTable>
          </div>
        </TabPanel>

        <!-- Qualifications Tab -->
        <TabPanel value="4" header="Qualifikationen">
          <div class="coming-soon">
            <i class="pi pi-graduation-cap" style="font-size: 3rem; color: var(--text-color-secondary);"></i>
            <p>Qualifikationsverwaltung wird bald verfügbar sein</p>
          </div>
        </TabPanel>

        <!-- Special Tasks Tab -->
        <TabPanel value="5" header="Sonderaufgaben">
          <div class="coming-soon">
            <i class="pi pi-star" style="font-size: 3rem; color: var(--text-color-secondary);"></i>
            <p>Sonderaufgaben werden bald verfügbar sein</p>
          </div>
        </TabPanel>

        <!-- Attachments Tab -->
        <TabPanel value="6" header="Anhänge">
          <div class="coming-soon">
            <i class="pi pi-paperclip" style="font-size: 3rem; color: var(--text-color-secondary);"></i>
            <p>Anhangsverwaltung wird bald verfügbar sein</p>
          </div>
        </TabPanel>
      </TabView>
    </div>

    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { membersApi, parentsApi, eventsApi } from '@/api/members'
import type { Member, Parent, Event } from '@/types/api'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import Tag from 'primevue/tag'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Menu from 'primevue/menu'
import Divider from 'primevue/divider'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import ParentContacts from '@/components/members/ParentContacts.vue'

const router = useRouter()
const route = useRoute()
const confirm = useConfirm()
const toast = useToast()

const member = ref<Member | null>(null)
const parents = ref<Parent[]>([])
const events = ref<Event[]>([])
const loading = ref(true)
const loadingParents = ref(false)
const loadingEvents = ref(false)
const menu = ref()

const memberId = Number(route.params.id)

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
    
    // Load related data
    await Promise.all([
      loadParents(),
      loadEvents()
    ])
  } catch (error) {
    console.error('Error loading member:', error)
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
  } catch (error) {
    console.error('Error loading parents:', error)
  } finally {
    loadingParents.value = false
  }
}

const loadEvents = async () => {
  try {
    loadingEvents.value = true
    const response = await eventsApi.list({ member: memberId })
    events.value = response.data.results || []
  } catch (error) {
    console.error('Error loading events:', error)
  } finally {
    loadingEvents.value = false
  }
}

const getInitials = (name: string) => {
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .substring(0, 2)
}

const formatDate = (dateString: string | null) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const formatDateTime = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const navigateToEdit = () => {
  router.push(`/members/${memberId}/edit`)
}

const toggleMenu = (event: any) => {
  menu.value.toggle(event)
}

const confirmDelete = () => {
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
        router.push('/members')
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Mitglied konnte nicht gelöscht werden',
          life: 3000
        })
      }
    }
  })
}

// Contact functions
const openWhatsApp = (phone: string) => {
  const cleanPhone = phone.replace(/\s/g, '')
  window.open(`https://wa.me/${cleanPhone}`, '_blank')
}

const openPhone = (phone: string) => {
  window.location.href = `tel:${phone}`
}

const openEmail = (email: string) => {
  window.location.href = `mailto:${email}`
}
</script>

<style scoped>
.member-profile-view {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

/* Profile Header */
.profile-header-card {
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.profile-header {
  display: flex;
  gap: 2rem;
  align-items: flex-start;
}

.avatar-section {
  flex-shrink: 0;
}

.member-avatar {
  width: 120px;
  height: 120px;
  font-size: 2.5rem;
}

.header-info {
  flex: 1;
  min-width: 0;
}

.name-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.name-section h1 {
  margin: 0;
  font-size: 2rem;
  font-weight: 600;
  color: var(--text-color);
}

.quick-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-color-secondary);
}

.info-item i {
  color: var(--primary-color);
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

/* Tabs */
.profile-tabs {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.profile-tabs :deep(.p-tabview-panels) {
  padding: 1.5rem;
}

/* Info Grid */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.info-card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.info-card.full-width {
  grid-column: 1 / -1;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-color);
}

.card-title i {
  color: var(--primary-color);
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.info-label {
  font-weight: 600;
  color: var(--text-color-secondary);
  min-width: 120px;
}

.info-value {
  color: var(--text-color);
  text-align: right;
  word-break: break-word;
}

.info-value a {
  color: var(--primary-color);
  text-decoration: none;
}

.info-value a:hover {
  text-decoration: underline;
}

.text-muted {
  color: var(--text-color-secondary);
}

.notes-content {
  white-space: pre-wrap;
  color: var(--text-color);
  margin: 0;
}

/* Parents Grid */
.parents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 1.5rem;
}

.parent-card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.parent-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
  gap: 1rem;
}

.empty-state p {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 1.1rem;
}

/* Coming Soon */
.coming-soon {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
  gap: 1rem;
}

.coming-soon p {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 1.1rem;
}

.coming-soon small {
  color: var(--text-color-secondary);
}

/* Responsive */
@media (max-width: 768px) {
  .member-profile-view {
    padding: 1rem;
  }

  .profile-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .header-info {
    width: 100%;
  }

  .name-section {
    flex-direction: column;
    align-items: center;
  }

  .quick-info {
    align-items: center;
  }

  .header-actions {
    width: 100%;
    justify-content: center;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .info-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .info-label {
    min-width: auto;
  }

  .info-value {
    text-align: left;
  }

  .parents-grid {
    grid-template-columns: 1fr;
  }

  .parent-actions {
    flex-direction: column;
  }

  .parent-actions :deep(.p-button) {
    width: 100%;
  }
}
</style>
