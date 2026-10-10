<template>
  <div class="email-compose-view">
    <OverviewHeader
      title="E-Mail senden"
      subtitle="E-Mail an Mitglieder und deren Eltern verschicken"
    >
      <template #actions>
        <Button
          label="Verlauf"
          icon="pi pi-history"
          @click="navigateToHistory"
          outlined
        />
      </template>
    </OverviewHeader>

    <Card>
      <template #content>
        <div class="composer-layout">

          <!-- ── LEFT: header fields + body ──────────────────────────── -->
          <div class="composer-main">

            <!-- Compact email-client-style header rows -->
            <div class="compose-header">
              <div class="compose-row">
                <span class="compose-row-label">Typ</span>
                <Dropdown
                  id="recipient-type"
                  v-model="form.recipient_type"
                  :options="recipientTypes"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Empfängertyp"
                  @change="onRecipientTypeChange"
                  class="w-full"
                />
              </div>

              <div v-if="form.recipient_type === 'group'" class="compose-row">
                <span class="compose-row-label">Gruppe</span>
                <Dropdown
                  id="recipient-group"
                  v-model="form.recipient_group"
                  :options="groupsStore.groups"
                  optionLabel="name"
                  optionValue="id"
                  placeholder="Gruppe auswählen"
                  @change="updateRecipientCount"
                  class="w-full"
                />
              </div>

              <div v-if="form.recipient_type === 'multiple'" class="compose-row compose-row-top">
                <span class="compose-row-label">An</span>
                <div class="w-full">
                  <AutoComplete
                    v-model="selectedMemberObjects"
                    :suggestions="filteredMembers"
                    @complete="onMemberSearch"
                    @keydown.enter="onRecipientEnter"
                    :optionLabel="(m: any) => m.full_name || `${m.name} ${m.lastname}`"
                    multiple
                    :forceSelection="true"
                    placeholder="Name eingeben..."
                    class="w-full recipient-autocomplete"
                    :delay="100"
                  />
                  <small v-if="selectedMemberObjects.length === 0" class="recipient-hint">
                    Name eingeben und aus der Liste auswählen
                  </small>
                </div>
              </div>

              <div v-if="recipientCount !== null" class="compose-row">
                <span class="compose-row-label"></span>
                <div class="recipient-summary" role="status">
                  <StatusBadge
                    :severity="recipientCount > 0 ? 'info' : 'warning'"
                    icon="pi pi-users"
                    :label="`${recipientCount} ${recipientCount === 1 ? 'Empfänger wird' : 'Empfänger werden'} benachrichtigt`"
                  />
                  <StatusBadge
                    v-if="excludedCount > 0"
                    severity="warning"
                    :label="`${excludedCount} ohne gültige Adresse`"
                  />
                </div>
              </div>

              <Divider class="compose-divider" />

              <div class="compose-row">
                <span class="compose-row-label">Betreff</span>
                <InputText
                  id="subject"
                  v-model="form.subject"
                  placeholder="E-Mail-Betreff"
                  class="w-full"
                />
              </div>
            </div>

            <!-- Body editor -->
            <div class="composer-body">
              <TiptapEditor
                v-model="form.body_html"
                :template-variables="templateVariables"
                :show-variables="true"
                :signature="userSignature"
                :include-signature="includeSignature"
                placeholder="E-Mail-Text eingeben..."
              />
            </div>

            <!-- Signature toggle -->
            <div v-if="userSignature" class="signature-toggle">
              <Checkbox v-model="includeSignature" inputId="include-signature" binary />
              <label for="include-signature" class="checkbox-label">Signatur anhängen</label>
            </div>
          </div>

          <!-- ── RIGHT: sidebar ───────────────────────────────────────── -->
          <div class="composer-sidebar">

            <!-- Attachments -->
            <div
              class="sidebar-section"
              ref="attachmentSectionRef"
              :class="{ 'attachment-shake': attachmentFlash }"
            >
              <div class="sidebar-section-header">
                <span><i class="pi pi-paperclip"></i> Anhänge</span>
                <span v-if="attachments.length" class="attachment-badge">{{ attachments.length }}</span>
              </div>

              <!-- Hint warning banner -->
              <div v-if="attachmentHintDetected && attachments.length === 0" class="attachment-hint-warning">
                <i class="pi pi-exclamation-triangle"></i>
                Text deutet auf einen Anhang hin – wurde etwas vergessen?
              </div>

              <div
                class="attachment-drop-zone"
                :class="{ 'drop-zone-active': isDragging, 'drop-zone-hint': attachmentHintDetected && attachments.length === 0 }"
                @dragover.prevent="isDragging = true"
                @dragleave.prevent="isDragging = false"
                @drop.prevent="handleDrop"
              >
                <i class="pi pi-cloud-upload"></i>
                <span>Hierher ziehen</span>
                <span class="drop-zone-or">oder</span>
                <FileUpload
                  mode="basic"
                  :auto="false"
                  multiple
                  :maxFileSize="10000000"
                  chooseLabel="Auswählen"
                  @select="handleFileSelect"
                  class="attachment-file-upload"
                />
                <small>Max. 10 MB · Bilder, PDF, Office, CSV, TXT</small>
              </div>

              <div v-if="attachments.length" class="attachment-list">
                <div v-for="(file, index) in attachments" :key="index" class="attachment-item">
                  <i :class="getFileIcon(file)"></i>
                  <span class="attachment-name">{{ file.name }}</span>
                  <span class="attachment-size">{{ formatFileSize(file.size) }}</span>
                  <Button
                    icon="pi pi-times"
                    text
                    rounded
                    size="small"
                    severity="danger"
                    @click="removeAttachment(index)"
                    v-tooltip.top="'Entfernen'"
                  />
                </div>
              </div>
            </div>

            <!-- Recipients preview -->
            <RecipientsList :recipients="recipients" :loading="loadingRecipients" />

            <!-- Layout selector -->
            <div class="sidebar-section">
              <div class="sidebar-section-header">
                <span><i class="pi pi-palette"></i> E-Mail-Layout</span>
              </div>
              <Dropdown
                v-model="layout"
                :options="layoutOptions"
                optionLabel="label"
                optionValue="value"
                class="w-full"
              />
            </div>

            <!-- Actions -->
            <div class="sidebar-actions">
              <Button
                label="Prüfen und senden"
                icon="pi pi-send"
                @click="openReview"
                :disabled="!canSend"
                severity="primary"
                class="w-full"
              />
              <Button
                label="Abbrechen"
                icon="pi pi-times"
                @click="resetForm"
                outlined
                severity="secondary"
                class="w-full"
              />
            </div>
          </div>

        </div>
      </template>
    </Card>

    <EmailSendReview
      v-model:visible="showReview"
      :check="emailsStore.recipientCheck"
      :loading="emailsStore.checkingRecipients"
      :error="emailsStore.recipientCheckError"
      :subject="form.subject"
      :preview-html="previewHtml"
      :preview-member-id="previewMemberId"
      :preview-loading="previewLoading"
      :preview-error="previewError"
      :sending="sending"
      @update:preview-member-id="selectPreviewMember"
      @retry="runReviewCheck"
      @retry-preview="loadPreview"
      @send="sendEmail"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useAuthStore } from '@/stores/auth'
import { useEmailsStore } from '@/stores/emails'
import { useMembersStore } from '@/stores/members'
import { useGroupsStore } from '@/stores/groups'
import { useDepartmentsStore } from '@/stores/departments'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import AutoComplete from 'primevue/autocomplete'
import Checkbox from 'primevue/checkbox'
import Divider from 'primevue/divider'
import FileUpload, { type FileUploadSelectEvent } from 'primevue/fileupload'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import TiptapEditor from '@/components/emails/organisms/TiptapEditor.vue'
import EmailSendReview from '@/components/emails/organisms/EmailSendReview.vue'
import RecipientsList from '@/components/emails/molecules/RecipientsList.vue'
import type { EmailRecipientCheckRequest, EmailTemplateVariable } from '@/types/emails'
import type { Member } from '@/types/members'
import { getApiErrorMessage } from '@/utils/apiError'

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const authStore = useAuthStore()
const emailsStore = useEmailsStore()
const membersStore = useMembersStore()
const groupsStore = useGroupsStore()
const departmentsStore = useDepartmentsStore()

const templateVariables = ref<EmailTemplateVariable[]>([])
const includeSignature = ref(true)
const userSignature = computed(() => authStore.user?.email_signature || '')
const attachments = ref<File[]>([])
const isDragging = ref(false)
const attachmentSectionRef = ref<HTMLElement | null>(null)
const attachmentFlash = ref(false)
const layout = ref('none')

// Review before sending (UX-07.1)
const showReview = ref(false)
const previewMemberId = ref<number | null>(null)
const previewHtml = ref<string | null>(null)
const previewLoading = ref(false)
const previewError = ref<string | null>(null)
const sending = ref(false)
let previewSequence = 0

const layoutOptions = [
  { value: 'none', label: 'Kein Layout' },
  { value: 'general', label: 'Allgemein (lila)' },
  { value: 'important', label: 'Wichtig (orange)' },
  { value: 'events', label: 'Veranstaltung (grün)' },
]

const form = ref({
  subject: '',
  body_html: '',
  recipient_type: 'all' as 'all' | 'group' | 'multiple',
  recipient_group: null as number | null,
  recipient_members: [] as number[]
})

// Recipient numbers in the sidebar come from the same check the review uses.
const recipientCount = computed(() => emailsStore.recipientCheck?.count ?? null)
const excludedCount = computed(() => emailsStore.recipientCheck?.excluded.length ?? 0)
const recipients = computed(() =>
  (emailsStore.recipientCheck?.recipients ?? []).map((r) => ({
    name: r.name,
    email: r.email,
    source: r.relation === 'parent' ? 'Eltern' : 'Mitglied',
  })),
)
const loadingRecipients = computed(() => emailsStore.checkingRecipients)

// German attachment hint detection
const ATTACHMENT_HINT_REGEX =
  /\b(anbei|im\s+anhang|als\s+anhang|anlagen?|beigefügt|beifüge\w*|angehängt|liegt\s+bei|in\s+der\s+anlage|finden\s+sie\s+beigefügt|findest\s+du\s+anbei)\b/i

const attachmentHintDetected = computed(() => {
  if (!form.value.body_html) return false
  const text = form.value.body_html.replace(/<[^>]*>/g, ' ')
  return ATTACHMENT_HINT_REGEX.test(text)
})

watch(attachmentHintDetected, (detected) => {
  if (detected && attachments.value.length === 0) {
    attachmentFlash.value = true
    attachmentSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    setTimeout(() => { attachmentFlash.value = false }, 600)
  }
})

const recipientTypes = [
  { label: 'Alle Mitglieder', value: 'all' },
  { label: 'Gruppe', value: 'group' },
  { label: 'Bestimmte Mitglieder', value: 'multiple' }
]

// AutoComplete state for member search
const filteredMembers = ref<Member[]>([])
const selectedMemberObjects = ref<Member[]>([])

const onMemberSearch = (event: { query: string }) => {
  const query = event.query.toLowerCase().trim()
  const already = new Set(selectedMemberObjects.value.map(m => m.id))
  if (!query) {
    filteredMembers.value = membersStore.members
      .filter(m => !already.has(m.id))
      .slice(0, 20)
    return
  }
  filteredMembers.value = membersStore.members.filter(m => {
    if (already.has(m.id)) return false
    const name = (m.full_name || `${m.name} ${m.lastname}`).toLowerCase()
    return name.includes(query)
  })
}

/** When exactly one suggestion is visible, pressing Enter selects it. */
function onRecipientEnter() {
  if (filteredMembers.value.length === 1) {
    const member = filteredMembers.value[0]!
    const alreadySelected = selectedMemberObjects.value.some((m) => m.id === member.id)
    if (!alreadySelected) {
      selectedMemberObjects.value = [...selectedMemberObjects.value, member]
    }
    filteredMembers.value = []
  }
}

watch(selectedMemberObjects, (members) => {
  form.value.recipient_members = members.map(m => m.id)
  updateRecipientCount()
}, { deep: true })

// Re-fetch members and refresh recipient count when the active department changes
watch(() => departmentsStore.activeDepartmentId, () => {
  membersStore.fetchMembers({ limit: 1000 })
  if (form.value.recipient_type !== 'multiple') {
    updateRecipientCount()
  }
})

const canSend = computed(() => {
  if (!form.value.subject || !form.value.body_html) return false
  if (form.value.recipient_type === 'group' && !form.value.recipient_group) return false
  if (form.value.recipient_type === 'multiple' && form.value.recipient_members.length === 0) return false
  return true
})

onMounted(async () => {
  // Load members, groups, and template variables
  await Promise.all([
    membersStore.fetchMembers({ limit: 1000 }),
    groupsStore.fetchGroups(),
    emailsStore.fetchTemplateVariables(),
  ])

  templateVariables.value = emailsStore.templateVariables

  // Pre-populate recipients from navigation state (e.g. from Lists feature)
  const state = (history.state ?? {}) as Record<string, unknown>
  if (Array.isArray(state.preselectedMemberIds) && state.preselectedMemberIds.length > 0) {
    form.value.recipient_type = 'multiple'
    const ids = state.preselectedMemberIds as number[]
    const preselected = membersStore.members.filter((m) => ids.includes(m.id))
    selectedMemberObjects.value = preselected
    form.value.recipient_members = preselected.map((m) => m.id)
  }

  // Initial recipient count
  updateRecipientCount()
})

const onRecipientTypeChange = () => {
  form.value.recipient_group = null
  form.value.recipient_members = []
  selectedMemberObjects.value = []
  updateRecipientCount()
}

/** Signature is appended in the browser, exactly as it will be sent. */
function composedBody() {
  let body = form.value.body_html
  if (includeSignature.value && userSignature.value) {
    body += '<br><br>---<br>' + userSignature.value
  }
  return body
}

function selection(withBody: boolean): EmailRecipientCheckRequest | null {
  const request: EmailRecipientCheckRequest = { recipient_type: form.value.recipient_type }
  if (form.value.recipient_type === 'group') {
    if (!form.value.recipient_group) return null
    request.recipient_group = form.value.recipient_group
  }
  if (form.value.recipient_type === 'multiple') {
    if (form.value.recipient_members.length === 0) return null
    request.recipient_members = form.value.recipient_members
  }
  if (withBody) request.body_html = composedBody()
  return request
}

const updateRecipientCount = async () => {
  const request = selection(false)
  if (!request) {
    emailsStore.clearRecipientCheck()
    return
  }
  try {
    await emailsStore.checkRecipients(request)
  } catch {
    // The store keeps the error; the sidebar simply shows no count.
  }
}

async function loadPreview() {
  const memberId = previewMemberId.value
  if (memberId === null) {
    previewHtml.value = null
    return
  }
  const sequence = ++previewSequence
  previewLoading.value = true
  previewError.value = null
  try {
    const response = await emailsStore.previewEmail({
      subject: form.value.subject,
      body_html: composedBody(),
      member_id: memberId,
      layout: layout.value
    })
    if (sequence === previewSequence) previewHtml.value = response.rendered_html
  } catch (err) {
    if (sequence === previewSequence) {
      previewHtml.value = null
      previewError.value = getApiErrorMessage(err, 'Die Vorschau konnte nicht erstellt werden.')
    }
  } finally {
    if (sequence === previewSequence) previewLoading.value = false
  }
}

function selectPreviewMember(memberId: number) {
  previewMemberId.value = memberId
  loadPreview()
}

async function runReviewCheck() {
  const request = selection(true)
  if (!request) return
  previewHtml.value = null
  previewError.value = null
  try {
    const check = await emailsStore.checkRecipients(request)
    previewMemberId.value = check.recipients[0]?.member_id ?? null
    await loadPreview()
  } catch {
    // Shown in the review dialog via the store error.
  }
}

async function openReview() {
  if (!canSend.value) return
  showReview.value = true
  await runReviewCheck()
}

const sendEmail = async () => {
  if (sending.value) return
  sending.value = true
  try {
    const base = {
      subject: form.value.subject,
      body_html: composedBody(),
      layout: layout.value,
      attachments: attachments.value.length > 0 ? attachments.value : undefined
    }
    // For multiple members, send one grouped email so history shows a single entry
    const result = form.value.recipient_type === 'multiple'
      ? await emailsStore.sendEmail({ ...base, recipient_type: 'multiple', recipient_members: form.value.recipient_members })
      : await emailsStore.sendEmail({
        ...base,
        recipient_type: form.value.recipient_type,
        recipient_group: form.value.recipient_group || undefined,
      })

    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: `E-Mail wurde an ${result.result.successful} Empfänger gesendet`,
      life: 5000
    })
    if (result.result.failed > 0) {
      toast.add({
        severity: 'warn',
        summary: 'Teilweise fehlgeschlagen',
        detail: `${result.result.failed} E-Mail(s) konnten nicht zugestellt werden`,
        life: 5000
      })
    }

    showReview.value = false
    clearForm()
    router.push('/emails/history')
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: emailsStore.error || 'E-Mail konnte nicht gesendet werden',
      life: 5000
    })
  } finally {
    sending.value = false
  }
}

const handleFileSelect = (event: FileUploadSelectEvent) => {
  if (event.files) {
    attachments.value.push(...Array.from(event.files as File[]))
  }
}

const handleDrop = (event: DragEvent) => {
  isDragging.value = false
  if (event.dataTransfer?.files) {
    attachments.value.push(...Array.from(event.dataTransfer.files))
  }
}

const removeAttachment = (index: number) => {
  attachments.value.splice(index, 1)
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const getFileIcon = (file: File): string => {
  if (file.type.startsWith('image/')) return 'pi pi-image'
  if (file.type === 'application/pdf') return 'pi pi-file-pdf'
  if (file.type.includes('word') || file.type.includes('document')) return 'pi pi-file-word'
  if (file.type.includes('sheet') || file.type.includes('excel')) return 'pi pi-file-excel'
  return 'pi pi-file'
}

function clearForm() {
  form.value = {
    subject: '',
    body_html: '',
    recipient_type: 'all',
    recipient_group: null,
    recipient_members: []
  }
  layout.value = 'none'
  selectedMemberObjects.value = []
  attachments.value = []
  previewMemberId.value = null
  previewHtml.value = null
  updateRecipientCount()
}

/** Discarding a draft is destructive and therefore confirmed. */
const resetForm = () => {
  if (!form.value.subject && !form.value.body_html && attachments.value.length === 0) {
    clearForm()
    return
  }
  confirm.require({
    message: 'Betreff, Text und Anhänge dieser E-Mail werden verworfen.',
    header: 'Entwurf verwerfen?',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Verwerfen',
    rejectLabel: 'Weiter bearbeiten',
    acceptClass: 'p-button-danger',
    accept: clearForm,
  })
}

const navigateToHistory = () => {
  router.push('/emails/history')
}

watch(() => form.value.recipient_type, updateRecipientCount)
</script>
<style scoped>
.email-compose-view {
  padding: 1rem;
}

/* Two-column grid: body left, sidebar right */
.composer-layout {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 1.5rem;
  align-items: start;
}

.composer-main {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
}

.composer-sidebar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: sticky;
  top: 1rem;
}

/* Email-client style header rows */
.compose-header {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  overflow: hidden;
}

.compose-row {
  display: grid;
  grid-template-columns: 64px 1fr;
  align-items: center;
  border-bottom: 1px solid var(--surface-100);
  min-height: 2.75rem;
}

.compose-row:last-child {
  border-bottom: none;
}

.compose-row-top {
  align-items: flex-start;
  padding-top: 0.5rem;
}

.compose-row-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0 0.75rem;
  user-select: none;
}

/* Remove PrimeVue borders/shadows inside compose header */
.compose-header :deep(.p-inputtext),
.compose-header :deep(.p-dropdown),
.compose-header :deep(.p-autocomplete-multiple-container) {
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
}

.compose-header :deep(.p-dropdown:focus-within),
.compose-header :deep(.p-inputtext:focus),
.compose-header :deep(.p-autocomplete-multiple-container:focus-within) {
  box-shadow: none !important;
  background: var(--surface-50) !important;
}

.compose-divider {
  margin: 0 !important;
}

/* Recipient summary (UX-07.1) */
.recipient-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1);
  margin: var(--jf-space-0-5) 0;
}

.app-dark .attachment-hint-warning,
.app-dark .attachment-drop-zone.drop-zone-hint {
  background: color-mix(in srgb, var(--p-amber-400), transparent 84%);
  color: var(--p-amber-300);
}

/* AutoComplete recipient chip field */
.recipient-hint {
  color: var(--text-color-secondary);
  font-size: 0.78rem;
  display: block;
  padding: 0.2rem 0.5rem 0.4rem;
}

.recipient-autocomplete :deep(.p-autocomplete-multiple-container) {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  padding: 0.375rem 0.5rem;
  border: none;
  border-radius: 0;
  background: transparent;
  cursor: text;
  width: 100%;
  align-items: center;
  box-shadow: none;
}

.recipient-autocomplete :deep(.p-autocomplete-token) {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background: var(--primary-100);
  color: var(--primary-700);
  border-radius: 1rem;
  padding: 0.2rem 0.6rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.recipient-autocomplete :deep(.p-autocomplete-token-icon) {
  cursor: pointer;
  font-size: 0.75rem;
  opacity: 0.7;
}

.recipient-autocomplete :deep(.p-autocomplete-token-icon:hover) {
  opacity: 1;
}

.recipient-autocomplete :deep(.p-autocomplete-input) {
  border: none;
  outline: none;
  box-shadow: none;
  background: transparent;
  padding: 0.1rem 0;
  min-width: 120px;
  flex: 1;
}

/* Signature toggle */
.signature-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.signature-toggle .checkbox-label {
  margin: 0;
  cursor: pointer;
  user-select: none;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

/* ── Sidebar sections ───────────────────────────────── */
.sidebar-section {
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  overflow: hidden;
  transition: border-color 0.25s;
}

.sidebar-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.55rem 0.75rem;
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-border);
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-color);
}

.attachment-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.4rem;
  height: 1.4rem;
  background: var(--primary-color);
  color: var(--jf-color-on-primary);
  border-radius: 1rem;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0 0.3rem;
}

/* Hint warning */
.attachment-hint-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.75rem;
  background: var(--p-amber-50);
  border-bottom: 1px solid var(--p-amber-200);
  color: var(--p-amber-800);
  font-size: 0.78rem;
  font-weight: 500;
}

.attachment-hint-warning .pi {
  color: var(--p-amber-500);
  flex-shrink: 0;
}

/* Compact drop zone */
.attachment-drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  padding: 0.875rem 0.75rem;
  background: var(--surface-50);
  text-align: center;
  transition: background-color 0.2s;
  cursor: default;
}

.attachment-drop-zone:hover {
  background: var(--primary-50);
}

.attachment-drop-zone.drop-zone-active {
  background: var(--primary-100);
}

.attachment-drop-zone.drop-zone-hint {
  background: var(--p-amber-50);
}

.attachment-drop-zone .pi-cloud-upload {
  font-size: 1.4rem;
  color: var(--text-color-secondary);
}

.attachment-drop-zone > span {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  font-weight: 500;
}

.drop-zone-or {
  font-size: 0.72rem;
  color: var(--text-color-secondary);
}

.attachment-drop-zone small {
  color: var(--text-color-secondary);
  font-size: 0.68rem;
}

.attachment-file-upload {
  margin: 0.1rem 0;
}

/* Attached file list */
.attachment-list {
  display: flex;
  flex-direction: column;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.75rem;
  border-top: 1px solid var(--surface-border);
  font-size: 0.8rem;
}

.attachment-item i:first-child {
  font-size: 1rem;
  color: var(--primary-color);
  flex-shrink: 0;
}

.attachment-name {
  flex: 1;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.attachment-size {
  color: var(--text-color-secondary);
  font-size: 0.72rem;
  white-space: nowrap;
}

/* Sidebar action buttons */
.sidebar-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Shake animation */
@keyframes attachment-shake {
  0%   { transform: translateX(0); }
  15%  { transform: translateX(-6px); }
  30%  { transform: translateX(6px); }
  45%  { transform: translateX(-4px); }
  60%  { transform: translateX(4px); }
  80%  { transform: translateX(-2px); }
  100% { transform: translateX(0); }
}

.attachment-shake {
  animation: attachment-shake 0.5s ease;
  border-color: var(--p-amber-500) !important;
}

/* Mobile: single column */
@media (max-width: 768px) {
  .composer-layout {
    grid-template-columns: 1fr;
  }

  .composer-sidebar {
    position: static;
  }

  .compose-row {
    grid-template-columns: 58px 1fr;
  }
}

/* Compose template dialogs */
.template-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem 1rem;
  color: var(--text-color-secondary);
}

.template-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 50vh;
  overflow-y: auto;
}

.template-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-50);
}

.template-item-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.template-item-name {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-item-subject {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-item-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}

.save-template-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>

