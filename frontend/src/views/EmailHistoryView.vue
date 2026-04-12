<template>
  <div class="email-history-view">
    <OverviewHeader
      title="E-Mail-Verlauf"
      subtitle="Übersicht über gesendete E-Mails"
    >
      <template #actions>
        <Button
          :label="isMobile ? '' : 'Neue E-Mail'"
          icon="pi pi-plus"
          @click="navigateToCompose"
          severity="primary"
        />
      </template>
    </OverviewHeader>

    <!-- Filters -->
    <Card class="filters-card">
      <template #content>
        <div class="filters">
          <IconField icon-position="left" class="search-field">
            <InputIcon class="pi pi-search" />
            <InputText
              v-model="searchQuery"
              placeholder="Betreff suchen..."
              @input="handleSearch"
              class="w-full"
            />
          </IconField>

          <Dropdown
            v-model="statusFilter"
            :options="statusOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Status filtern"
            @change="onStatusFilterChange"
            :showClear="true"
            class="status-filter"
          />
        </div>
      </template>
    </Card>

    <!-- Loading State -->
    <div v-if="emailsStore.loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <!-- Desktop: DataTable -->
    <Card v-else-if="!isMobile" class="desktop-table-card">
      <template #content>
        <DataTable
          :value="emailsStore.emails"
          paginator
          :rows="currentRows"
          :first="tableFirst"
          :rows-per-page-options="[10, 20, 50]"
          :total-records="emailsStore.pagination.count"
          lazy
          @page="onPage"
          striped-rows
          class="emails-table"
        >
          <Column field="created_at" header="Datum" sortable>
            <template #body="{ data }">
              {{ formatDate(data.created_at) }}
            </template>
          </Column>
          <Column field="sender_name" header="Absender" />
          <Column field="subject" header="Betreff" />
          <Column field="recipient_type_display" header="Empfängertyp" />
          <Column header="Empfänger">
            <template #body="{ data }">
              <span v-if="data.recipient_type === 'individual' && data.recipient_member_name">
                {{ data.recipient_member_name }}
              </span>
              <span v-else-if="data.recipient_type === 'group' && data.recipient_group_name">
                {{ data.recipient_group_name }}
              </span>
              <span v-else-if="data.recipient_type === 'all'">
                -
              </span>
            </template>
          </Column>
          <Column header="Status">
            <template #body="{ data }">
              <Tag
                :value="data.status_display"
                :severity="getStatusSeverity(data.status)"
              />
            </template>
          </Column>
          <Column header="Statistik">
            <template #body="{ data }">
              <div class="stats">
                <span v-if="data.successful_sends > 0" class="success-count">
                  <i class="pi pi-check"></i> {{ data.successful_sends }}
                </span>
                <span v-if="data.failed_sends > 0" class="error-count">
                  <i class="pi pi-times"></i> {{ data.failed_sends }}
                </span>
              </div>
            </template>
          </Column>
          <Column header="Aktionen" style="width: 120px">
            <template #body="{ data }">
              <div class="table-actions">
                <Button
                  icon="pi pi-eye"
                  rounded
                  text
                  @click="viewEmail(data)"
                  :title="'Details anzeigen'"
                />
                <Button
                  v-if="data.failed_sends > 0"
                  icon="pi pi-refresh"
                  rounded
                  text
                  severity="warning"
                  @click="resendEmail(data)"
                  :title="'Fehlgeschlagene erneut senden'"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Mobile: List -->
    <div v-else class="mobile-list">
      <Card
        v-for="email in emailsStore.emails"
        :key="email.id"
        class="mobile-email-card"
        @click="viewEmail(email)"
      >
        <template #content>
          <div class="email-card-header">
            <h3>{{ email.subject }}</h3>
            <Tag
              :value="email.status_display"
              :severity="getStatusSeverity(email.status)"
            />
          </div>
          <div class="email-card-info">
            <p><strong>Absender:</strong> {{ email.sender_name }}</p>
            <p><strong>Empfängertyp:</strong> {{ email.recipient_type_display }}</p>
            <p v-if="email.recipient_type === 'individual' && email.recipient_member_name">
              <strong>Empfänger:</strong> {{ email.recipient_member_name }}
            </p>
            <p v-if="email.recipient_type === 'group' && email.recipient_group_name">
              <strong>Gruppe:</strong> {{ email.recipient_group_name }}
            </p>
            <p><strong>Datum:</strong> {{ formatDate(email.created_at) }}</p>
            <div class="stats">
              <span v-if="email.successful_sends > 0" class="success-count">
                <i class="pi pi-check"></i> {{ email.successful_sends }}
              </span>
              <span v-if="email.failed_sends > 0" class="error-count">
                <i class="pi pi-times"></i> {{ email.failed_sends }}
              </span>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Email Detail Dialog -->
    <Dialog
      v-model:visible="showDetailDialog"
      :header="currentEmail?.subject"
      :modal="true"
      :style="{ width: isMobile ? '95vw' : '70vw' }"
    >
      <div v-if="currentEmail" class="email-detail">
        <div class="detail-section">
          <h4>Informationen</h4>
          <p><strong>Absender:</strong> {{ currentEmail.sender_name }}</p>
          <p><strong>Empfänger:</strong> {{ currentEmail.recipient_type_display }}</p>
          <p v-if="currentEmail.recipient_group_name">
            <strong>Gruppe:</strong> {{ currentEmail.recipient_group_name }}
          </p>
          <p v-if="currentEmail.recipient_member_name">
            <strong>Mitglied:</strong> {{ currentEmail.recipient_member_name }}
          </p>
          <p v-if="currentEmail.recipient_type === 'individual' && currentEmail.total_recipients > 1">
            <strong>Empfänger:</strong> {{ currentEmail.total_recipients }} (Mitglied + Eltern)
          </p>
          <p><strong>Gesendet am:</strong> {{ formatDate(currentEmail.sent_at || currentEmail.created_at) }}</p>
          <p>
            <strong>Status:</strong>
            <Tag
              :value="currentEmail.status_display"
              :severity="getStatusSeverity(currentEmail.status)"
            />
          </p>
        </div>

        <Divider />

        <div class="detail-section">
          <h4>Statistik</h4>
          <div class="stats-grid">
            <div class="stat-item">
              <i class="pi pi-users"></i>
              <span>{{ currentEmail.total_recipients }} Empfänger</span>
            </div>
            <div class="stat-item success">
              <i class="pi pi-check"></i>
              <span>{{ currentEmail.successful_sends }} erfolgreich</span>
            </div>
            <div v-if="currentEmail.failed_sends > 0" class="stat-item error">
              <i class="pi pi-times"></i>
              <span>{{ currentEmail.failed_sends }} fehlgeschlagen</span>
            </div>
          </div>
        </div>

        <Divider />

        <div class="detail-section">
          <h4>Nachricht</h4>
          <div class="email-body" v-html="emailDetails?.body_html || currentEmail.body_html"></div>
        </div>

        <Divider v-if="emailDetails?.recipients && emailDetails.recipients.length > 0" />

        <div v-if="emailDetails?.recipients && emailDetails.recipients.length > 0" class="detail-section">
          <h4>Empfänger ({{ emailDetails.recipients.length }})</h4>
          <DataTable
            :value="emailDetails.recipients"
            :rows="10"
            :paginator="emailDetails.recipients.length > 10"
            class="recipients-table"
          >
            <Column field="recipient_name" header="Name" />
            <Column field="email_address" header="E-Mail" />
            <Column header="Status">
              <template #body="{ data }">
                <Tag
                  :value="data.status === 'sent' ? 'Gesendet' : data.status === 'failed' ? 'Fehlgeschlagen' : 'Ausstehend'"
                  :severity="data.status === 'sent' ? 'success' : data.status === 'failed' ? 'danger' : 'warning'"
                />
              </template>
            </Column>
            <Column v-if="emailDetails.recipients.some((r: any) => r.error_message)" field="error_message" header="Fehler" />
          </DataTable>
        </div>
      </div>

      <template #footer>
        <Button
          v-if="currentEmail && currentEmail.failed_sends > 0"
          label="Fehlgeschlagene erneut senden"
          icon="pi pi-refresh"
          @click="resendEmail(currentEmail)"
          severity="warning"
        />
        <Button label="Schließen" @click="showDetailDialog = false" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useEmailsStore } from '@/stores/emails'
import type { EmailMessage, EmailMessageDetail } from '@/types/emails'
import { useQueryTableState } from '@/composables/useQueryTableState'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import Divider from 'primevue/divider'
import ProgressSpinner from 'primevue/progressspinner'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const emailsStore = useEmailsStore()
const { getInt, getString, syncToUrl } = useQueryTableState()

const isMobile = ref(window.innerWidth < 768)
const searchQuery = ref(getString('search'))
const statusFilter = ref<'draft' | 'sending' | 'sent' | 'failed' | 'partial' | null>(
  (getString('status') as 'draft' | 'sending' | 'sent' | 'failed' | 'partial') || null
)
const currentPage = ref(getInt('page', 1))
const currentRows = ref(getInt('rows', 20))
const tableFirst = computed(() => (currentPage.value - 1) * currentRows.value)

const EMAIL_URL_DEFAULTS = { page: 1, rows: 20 }
const showDetailDialog = ref(false)
const currentEmail = ref<EmailMessage | null>(null)
const emailDetails = ref<EmailMessageDetail | null>(null)

const statusOptions = [
  { label: 'Gesendet', value: 'sent' },
  { label: 'Fehlgeschlagen', value: 'failed' },
  { label: 'Teilweise gesendet', value: 'partial' },
  { label: 'Wird gesendet', value: 'sending' }
]

onMounted(() => {
  fetchEmails()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
}

const fetchEmails = async () => {
  try {
    await emailsStore.fetchEmails({
      offset: (currentPage.value - 1) * currentRows.value,
      limit: currentRows.value,
      search: searchQuery.value || undefined,
      status: (statusFilter.value as EmailMessage['status']) || undefined,
      ordering: '-created_at'
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'E-Mails konnten nicht geladen werden',
      life: 3000
    })
  }
}

let searchTimeout: ReturnType<typeof setTimeout> | undefined
const handleSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    syncToUrl({ search: searchQuery.value, status: statusFilter.value, page: currentPage.value, rows: currentRows.value }, EMAIL_URL_DEFAULTS)
    fetchEmails()
  }, 500)
}

const onPage = (event: { page: number; rows: number }) => {
  currentPage.value = event.page + 1
  currentRows.value = event.rows
  syncToUrl({ search: searchQuery.value, status: statusFilter.value, page: currentPage.value, rows: currentRows.value }, EMAIL_URL_DEFAULTS)
  fetchEmails()
}

const onStatusFilterChange = () => {
  currentPage.value = 1
  syncToUrl({ search: searchQuery.value, status: statusFilter.value, page: currentPage.value, rows: currentRows.value }, EMAIL_URL_DEFAULTS)
  fetchEmails()
}

const viewEmail = async (email: EmailMessage) => {
  currentEmail.value = email
  
  try {
    emailDetails.value = await emailsStore.fetchEmailById(email.id)
    showDetailDialog.value = true
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'E-Mail-Details konnten nicht geladen werden',
      life: 3000
    })
  }
}

const resendEmail = async (email: EmailMessage) => {
  confirm.require({
    message: `Möchten Sie die fehlgeschlagenen E-Mails wirklich erneut senden?`,
    header: 'Erneut senden bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, erneut senden',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      try {
        const result = await emailsStore.resendEmail(email.id)
        
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: `${result.result.successful} E-Mail(s) erfolgreich gesendet`,
          life: 5000
        })

        if (result.result.failed > 0) {
          toast.add({
            severity: 'warn',
            summary: 'Teilweise fehlgeschlagen',
            detail: `${result.result.failed} E-Mail(s) konnten weiterhin nicht zugestellt werden`,
            life: 5000
          })
        }

        // Refresh list
        fetchEmails()
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'E-Mails konnten nicht erneut gesendet werden',
          life: 5000
        })
      }
    }
  })
}

const navigateToCompose = () => {
  router.push('/emails/compose')
}

const formatDate = (dateString: string) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getStatusSeverity = (status: string) => {
  switch (status) {
    case 'sent':
      return 'success'
    case 'failed':
      return 'danger'
    case 'partial':
      return 'warning'
    case 'sending':
      return 'info'
    default:
      return 'secondary'
  }
}
</script>

<style scoped>
.email-history-view {
  padding: 1rem;
}

.filters-card {
  margin-bottom: 1rem;
}

.filters {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.search-field {
  flex: 1;
}

.status-filter {
  min-width: 200px;
}

@media (max-width: 768px) {
  .filters {
    flex-direction: column;
  }

  .status-filter {
    width: 100%;
  }
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.table-actions {
  display: flex;
  gap: 0.5rem;
}

.stats {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.success-count {
  color: var(--green-500);
  font-weight: 600;
}

.error-count {
  color: var(--red-500);
  font-weight: 600;
}

.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.mobile-email-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.mobile-email-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.email-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.email-card-header h3 {
  margin: 0;
  font-size: 1.1rem;
  flex: 1;
}

.email-card-info p {
  margin: 0.5rem 0;
}

.email-detail {
  padding: 1rem 0;
}

.detail-section {
  margin: 1rem 0;
}

.detail-section h4 {
  margin: 0 0 1rem 0;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-section p {
  margin: 0.75rem 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: var(--border-radius);
}

.stat-item.success {
  background: var(--green-50);
  color: var(--green-700);
}

.stat-item.error {
  background: var(--red-50);
  color: var(--red-700);
}

.email-body {
  padding: 1rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-card);
  min-height: 200px;
}

.email-body :deep(p) {
  margin: 0.5rem 0;
}

.email-body :deep(h1),
.email-body :deep(h2),
.email-body :deep(h3) {
  margin: 1rem 0 0.5rem 0;
}

.recipients-table {
  margin-top: 1rem;
}
</style>
