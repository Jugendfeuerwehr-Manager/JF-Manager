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
                <div class="recipient-count">
                  <i class="pi pi-users"></i>
                  <span>{{ recipientCount }} {{ recipientCount === 1 ? 'Empfänger wird' : 'Empfänger werden' }} benachrichtigt</span>
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
                v-if="previewMember"
                label="Vorschau"
                icon="pi pi-eye"
                @click="showPreview"
                outlined
                class="w-full"
                :loading="emailsStore.loading"
              />
              <Button
                label="E-Mail senden"
                icon="pi pi-send"
                @click="sendEmail"
                :disabled="!canSend"
                :loading="emailsStore.loading"
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

    <!-- Preview Dialog -->
    <Dialog
      v-model:visible="showPreviewDialog"
      header="E-Mail-Vorschau"
      :modal="true"
      :style="{ width: isMobile ? '95vw' : '50vw' }"
    >
      <div v-if="previewData" class="preview-content">
        <div class="preview-info">
          <p><strong>Empfänger:</strong> {{ previewData.member_name }}</p>
          <p><strong>Anzahl Empfänger für dieses Mitglied:</strong> {{ previewData.recipient_count }}</p>
        </div>
        <Divider />
        <div class="preview-subject">
          <strong>Betreff:</strong> {{ form.subject }}
        </div>
        <Divider />
        <div class="preview-body" v-html="previewData.rendered_html"></div>
      </div>
      <template #footer>
        <Button label="Schließen" @click="showPreviewDialog = false" />
      </template>
    </Dialog>
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
import Dialog from 'primevue/dialog'
import Divider from 'primevue/divider'
import FileUpload, { type FileUploadSelectEvent } from 'primevue/fileupload'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import TiptapEditor from '@/components/emails/organisms/TiptapEditor.vue'
import RecipientsList from '@/components/emails/molecules/RecipientsList.vue'
import type { EmailPreviewResponse, EmailTemplateVariable } from '@/types/emails'
import type { Member } from '@/types/members'

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const authStore = useAuthStore()
const emailsStore = useEmailsStore()
const membersStore = useMembersStore()
const groupsStore = useGroupsStore()
const departmentsStore = useDepartmentsStore()

const isMobile = ref(window.innerWidth < 768)
const showPreviewDialog = ref(false)
const previewData = ref<EmailPreviewResponse | null>(null)
const recipientCount = ref<number | null>(null)
const templateVariables = ref<EmailTemplateVariable[]>([])
const recipients = ref<Array<{ name: string; email: string; source: string }>>([])
const loadingRecipients = ref(false)
const includeSignature = ref(true)
const userSignature = computed(() => authStore.user?.email_signature || '')
const attachments = ref<File[]>([])
const isDragging = ref(false)
const attachmentSectionRef = ref<HTMLElement | null>(null)
const attachmentFlash = ref(false)
const layout = ref('none')

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

const previewMember = computed(() => {
  if (form.value.recipient_type === 'multiple' && form.value.recipient_members.length > 0) {
    return selectedMemberObjects.value[0] || null
  }
  return membersStore.members[0] || null
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
  
  window.addEventListener('resize', handleResize)
})

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
}

const onRecipientTypeChange = () => {
  form.value.recipient_group = null
  form.value.recipient_members = []
  selectedMemberObjects.value = []
  updateRecipientCount()
}

const updateRecipientCount = async () => {
  if (!form.value.recipient_type) {
    recipientCount.value = null
    recipients.value = []
    return
  }

  try {
    loadingRecipients.value = true
    // For multiple members, calculate count client-side
    if (form.value.recipient_type === 'multiple') {
      if (form.value.recipient_members.length === 0) {
        recipientCount.value = 0
        recipients.value = []
        return
      }
      
      // Calculate total unique recipients for all selected members
      let allRecipients: Array<{ name: string; email: string; source: string }> = []
      for (const memberId of form.value.recipient_members) {
        const response = await emailsStore.getRecipientCount({
          recipient_type: 'individual',
          recipient_member: memberId
        })
        allRecipients = [...allRecipients, ...response.recipients.map(r => ({ name: r.name, email: r.email, source: 'Mitglied' }))]
      }
      
      // Deduplicate by email
      const uniqueMap = new Map()
      allRecipients.forEach(r => {
        if (!uniqueMap.has(r.email.toLowerCase())) {
          uniqueMap.set(r.email.toLowerCase(), r)
        }
      })
      
      recipients.value = Array.from(uniqueMap.values())
      recipientCount.value = recipients.value.length
      return
    }
    
    const params: { recipient_type: 'all' | 'group'; recipient_group?: number } = {
      recipient_type: form.value.recipient_type as 'all' | 'group'
    }
    
    if (form.value.recipient_type === 'group' && form.value.recipient_group) {
      params.recipient_group = form.value.recipient_group
    }
    
    const response = await emailsStore.getRecipientCount(params)
    recipientCount.value = response.count
    recipients.value = (response.recipients || []).map(r => ({ name: r.name, email: r.email, source: 'Mitglied' }))
  } catch {
    recipientCount.value = null
    recipients.value = []
  } finally {
    loadingRecipients.value = false
  }
}

const showPreview = async () => {
  if (!previewMember.value) {
    toast.add({
      severity: 'warn',
      summary: 'Warnung',
      detail: 'Kein Mitglied für Vorschau gefunden',
      life: 3000
    })
    return
  }

  try {
    // Prepare email body with signature if enabled
    let emailBody = form.value.body_html
    if (includeSignature.value && userSignature.value) {
      emailBody += '<br><br>---<br>' + userSignature.value
    }

    const response = await emailsStore.previewEmail({
      subject: form.value.subject,
      body_html: emailBody,
      member_id: previewMember.value.id,
      layout: layout.value
    })
    
    previewData.value = response
    showPreviewDialog.value = true
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Vorschau konnte nicht geladen werden',
      life: 3000
    })
  }
}

const sendEmail = async () => {
  confirm.require({
    message: `Möchten Sie die E-Mail wirklich an ${recipientCount.value} Empfänger senden?`,
    header: 'E-Mail senden bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, senden',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      try {
        // Prepare email body with signature if enabled
        let emailBody = form.value.body_html
        if (includeSignature.value && userSignature.value) {
          emailBody += '<br><br>---<br>' + userSignature.value
        }

        // For multiple members, send individual emails to each member
        if (form.value.recipient_type === 'multiple') {
          let totalSuccessful = 0
          let totalFailed = 0
          
          for (const memberId of form.value.recipient_members) {
            const result = await emailsStore.sendEmail({
              subject: form.value.subject,
              body_html: emailBody,
              layout: layout.value,
              recipient_type: 'individual',
              recipient_member: memberId,
              attachments: attachments.value.length > 0 ? attachments.value : undefined
            })
            totalSuccessful += result.result.successful
            totalFailed += result.result.failed
          }
          
          toast.add({
            severity: 'success',
            summary: 'Erfolg',
            detail: `E-Mail wurde an ${totalSuccessful} Empfänger gesendet`,
            life: 5000
          })
          
          if (totalFailed > 0) {
            toast.add({
              severity: 'warn',
              summary: 'Teilweise fehlgeschlagen',
              detail: `${totalFailed} E-Mail(s) konnten nicht zugestellt werden`,
              life: 5000
            })
          }
        } else {
          // Standard behavior for all or group
          const result = await emailsStore.sendEmail({
            subject: form.value.subject,
            body_html: emailBody,
            layout: layout.value,
            recipient_type: form.value.recipient_type,
            recipient_group: form.value.recipient_group || undefined,
            attachments: attachments.value.length > 0 ? attachments.value : undefined
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
        }

        resetForm()
        
        // Navigate to history to see the result
        setTimeout(() => {
          router.push('/emails/history')
        }, 1000)
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: emailsStore.error || 'E-Mail konnte nicht gesendet werden',
          life: 5000
        })
      }
    }
  })
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

const resetForm = () => {
  form.value = {
    subject: '',
    body_html: '',
    recipient_type: 'all',
    recipient_group: null,
    recipient_members: []
  }
  layout.value = 'none'
  selectedMemberObjects.value = []
  recipientCount.value = null
  recipients.value = []
  attachments.value = []
  updateRecipientCount()
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

/* Recipient count chip */
.recipient-count {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.625rem;
  background: var(--primary-50);
  border-radius: 1rem;
  color: var(--primary-600);
  font-size: 0.78rem;
  font-weight: 600;
  margin: 0.25rem 0;
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
  color: white;
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
  background: #fffbeb;
  border-bottom: 1px solid #fde68a;
  color: #92400e;
  font-size: 0.78rem;
  font-weight: 500;
}

.attachment-hint-warning .pi {
  color: #f59e0b;
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
  background: #fffbeb;
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
  border-color: #f59e0b !important;
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

/* Preview dialog */
.preview-content {
  padding: 1rem 0;
}

.preview-info p {
  margin: 0.5rem 0;
}

.preview-subject {
  font-size: 1.1rem;
  margin: 1rem 0;
}

.preview-body {
  padding: 1rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-card);
  min-height: 200px;
}

.preview-body :deep(p) {
  margin: 0.5rem 0;
}

.preview-body :deep(h1),
.preview-body :deep(h2),
.preview-body :deep(h3) {
  margin: 1rem 0 0.5rem 0;
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

