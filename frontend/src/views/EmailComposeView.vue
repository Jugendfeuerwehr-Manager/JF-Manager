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
        <div class="email-form">
          <!-- Recipient Selection -->
          <div class="form-field">
            <label for="recipient-type">Empfänger</label>
            <Dropdown
              id="recipient-type"
              v-model="form.recipient_type"
              :options="recipientTypes"
              optionLabel="label"
              optionValue="value"
              placeholder="Empfängertyp auswählen"
              @change="onRecipientTypeChange"
              class="w-full"
            />
          </div>

          <!-- Group Selection -->
          <div v-if="form.recipient_type === 'group'" class="form-field">
            <label for="recipient-group">Gruppe</label>
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

          <!-- Member Selection - Single -->
          <div v-if="form.recipient_type === 'individual'" class="form-field">
            <label for="recipient-member">Mitglied</label>
            <Dropdown
              id="recipient-member"
              v-model="form.recipient_member"
              :options="membersStore.members"
              :optionLabel="(member: any) => member.full_name || `${member.name} ${member.lastname}`"
              optionValue="id"
              placeholder="Mitglied auswählen"
              filter
              @change="updateRecipientCount"
              class="w-full"
            />
          </div>

          <!-- Member Selection - Multiple -->
          <div v-if="form.recipient_type === 'multiple'" class="form-field">
            <label for="recipient-members">Mitglieder auswählen</label>
            <MultiSelect
              id="recipient-members"
              v-model="form.recipient_members"
              :options="membersStore.members"
              :optionLabel="(member: any) => member.full_name || `${member.name} ${member.lastname}`"
              optionValue="id"
              placeholder="Mitglieder auswählen..."
              filter
              @change="updateRecipientCount"
              class="w-full"
              display="chip"
            />
          </div>

          <!-- Recipient Count Display -->
          <div v-if="recipientCount !== null" class="recipient-count">
            <i class="pi pi-users"></i>
            <span>{{ recipientCount }} Empfänger {{ recipientCount === 1 ? 'wird' : 'werden' }} benachrichtigt</span>
          </div>

          <!-- Subject -->
          <div class="form-field">
            <label for="subject">Betreff</label>
            <InputText
              id="subject"
              v-model="form.subject"
              placeholder="E-Mail-Betreff"
              class="w-full"
            />
          </div>

          <!-- Email Body Editor -->
          <div class="form-field">
            <label>Nachricht</label>
            <TiptapEditor
              v-model="form.body_html"
              :template-variables="templateVariables"
              :show-variables="true"
              :signature="userSignature"
              :include-signature="includeSignature"
              placeholder="E-Mail-Text eingeben..."
            />
          </div>

          <!-- Signature Toggle -->
          <div v-if="userSignature" class="form-field signature-toggle">
            <Checkbox
              v-model="includeSignature"
              inputId="include-signature"
              binary
            />
            <label for="include-signature" class="checkbox-label">
              Signatur anhängen
            </label>
          </div>

          <!-- Attachments -->
          <div class="form-field">
            <label>Anhänge</label>
            <div
              class="attachment-drop-zone"
              :class="{ 'drop-zone-active': isDragging }"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
              @drop.prevent="handleDrop"
            >
              <i class="pi pi-cloud-upload"></i>
              <p>Dateien hierher ziehen</p>
              <span class="drop-zone-or">oder</span>
              <FileUpload
                mode="basic"
                :auto="false"
                multiple
                :maxFileSize="10000000"
                chooseLabel="Dateien auswählen"
                @select="handleFileSelect"
                class="attachment-file-upload"
              />
              <small>Max. 10 MB pro Datei &middot; Bilder, PDF, Office-Dokumente, CSV, TXT</small>
            </div>
            <div v-if="attachments.length" class="attachment-list">
              <div v-for="(file, index) in attachments" :key="index" class="attachment-item">
                <i :class="getFileIcon(file)"></i>
                <span class="attachment-name">{{ file.name }}</span>
                <span class="attachment-size">({{ formatFileSize(file.size) }})</span>
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

          <!-- Recipients List -->
          <RecipientsList
            :recipients="recipients"
            :loading="loadingRecipients"
          />

          <!-- Preview -->
          <div v-if="previewMember" class="form-field">
            <Button
              label="Vorschau für ausgewähltes Mitglied"
              icon="pi pi-eye"
              @click="showPreview"
              outlined
              :loading="emailsStore.loading"
            />
          </div>

          <!-- Action Buttons -->
          <div class="form-actions">
            <Button
              label="E-Mail senden"
              icon="pi pi-send"
              @click="sendEmail"
              :disabled="!canSend"
              :loading="emailsStore.loading"
              severity="primary"
            />
            <Button
              label="Abbrechen"
              icon="pi pi-times"
              @click="resetForm"
              outlined
              severity="secondary"
            />
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
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import MultiSelect from 'primevue/multiselect'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import Divider from 'primevue/divider'
import FileUpload, { type FileUploadSelectEvent } from 'primevue/fileupload'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import TiptapEditor from '@/components/emails/organisms/TiptapEditor.vue'
import RecipientsList from '@/components/emails/molecules/RecipientsList.vue'

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const authStore = useAuthStore()
const emailsStore = useEmailsStore()
const membersStore = useMembersStore()
const groupsStore = useGroupsStore()

const isMobile = ref(window.innerWidth < 768)
const showPreviewDialog = ref(false)
const previewData = ref<any>(null)
const recipientCount = ref<number | null>(null)
const templateVariables = ref<any[]>([])
const recipients = ref<any[]>([])
const loadingRecipients = ref(false)
const includeSignature = ref(true)
const userSignature = computed(() => authStore.user?.email_signature || '')
const attachments = ref<File[]>([])
const isDragging = ref(false)

const form = ref({
  subject: '',
  body_html: '',
  recipient_type: 'all' as 'all' | 'group' | 'individual' | 'multiple',
  recipient_group: null as number | null,
  recipient_member: null as number | null,
  recipient_members: [] as number[]
})

const recipientTypes = [
  { label: 'Alle Mitglieder', value: 'all' },
  { label: 'Gruppe', value: 'group' },
  { label: 'Mehrere Mitglieder', value: 'multiple' },
  { label: 'Einzelnes Mitglied', value: 'individual' }
]

const canSend = computed(() => {
  if (!form.value.subject || !form.value.body_html) return false
  if (form.value.recipient_type === 'group' && !form.value.recipient_group) return false
  if (form.value.recipient_type === 'individual' && !form.value.recipient_member) return false
  if (form.value.recipient_type === 'multiple' && form.value.recipient_members.length === 0) return false
  return true
})

const previewMember = computed(() => {
  if (form.value.recipient_type === 'individual' && form.value.recipient_member) {
    return membersStore.members.find(m => m.id === form.value.recipient_member)
  }
  if (form.value.recipient_type === 'multiple' && form.value.recipient_members.length > 0) {
    return membersStore.members.find(m => m.id === form.value.recipient_members[0])
  }
  return membersStore.members[0] || null
})

onMounted(async () => {
  // Load members and groups
  await Promise.all([
    membersStore.fetchMembers({ limit: 1000 }),
    groupsStore.fetchGroups({ page_size: 100 }),
    emailsStore.fetchTemplateVariables()
  ])
  
  templateVariables.value = emailsStore.templateVariables
  
  // Initial recipient count
  updateRecipientCount()
  
  window.addEventListener('resize', handleResize)
})

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
}

const onRecipientTypeChange = () => {
  form.value.recipient_group = null
  form.value.recipient_member = null
  form.value.recipient_members = []
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
      let allRecipients: any[] = []
      for (const memberId of form.value.recipient_members) {
        const response = await emailsStore.getRecipientCount({
          recipient_type: 'individual',
          recipient_member: memberId
        })
        allRecipients = [...allRecipients, ...response.recipients]
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
    
    const params: any = {
      recipient_type: form.value.recipient_type
    }
    
    if (form.value.recipient_type === 'group' && form.value.recipient_group) {
      params.recipient_group = form.value.recipient_group
    } else if (form.value.recipient_type === 'individual' && form.value.recipient_member) {
      params.recipient_member = form.value.recipient_member
    }
    
    const response = await emailsStore.getRecipientCount(params)
    recipientCount.value = response.count
    recipients.value = response.recipients || []
  } catch (error) {
    console.error('Error getting recipient count:', error)
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
      member_id: previewMember.value.id
    })
    
    previewData.value = response
    showPreviewDialog.value = true
  } catch (error: any) {
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
          // Standard behavior for all, group, or single individual
          const result = await emailsStore.sendEmail({
            subject: form.value.subject,
            body_html: emailBody,
            recipient_type: form.value.recipient_type,
            recipient_group: form.value.recipient_group || undefined,
            recipient_member: form.value.recipient_member || undefined,
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
      } catch (error: any) {
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
    recipient_member: null,
    recipient_members: []
  }
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

.email-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  font-weight: 600;
  color: var(--text-color);
}

.recipient-count {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--primary-50);
  border-radius: var(--border-radius);
  color: var(--primary-color);
  font-weight: 500;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1rem;
}

.signature-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.signature-toggle .checkbox-label {
  margin: 0;
  cursor: pointer;
  user-select: none;
}

.signature-preview {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
}

.signature-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.signature-content {
  padding: 0.75rem;
  background: white;
  border: 1px dashed var(--surface-border);
  border-radius: var(--border-radius);
  color: var(--text-color-secondary);
  font-style: italic;
}

@media (max-width: 768px) {
  .form-actions {
    flex-direction: column;
  }
  
  .form-actions button {
    width: 100%;
  }
}

.preview-content {
  padding: 1rem 0;
}

.preview-info {
  margin-bottom: 1rem;
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

/* Attachment Drop Zone */
.attachment-drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 1.5rem;
  border: 2px dashed var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-50);
  text-align: center;
  transition: border-color 0.2s, background-color 0.2s;
}

.attachment-drop-zone:hover {
  border-color: var(--primary-color);
  background: var(--primary-50);
}

.attachment-drop-zone.drop-zone-active {
  border-color: var(--primary-color);
  background: var(--primary-100);
}

.attachment-drop-zone .pi-cloud-upload {
  font-size: 2rem;
  color: var(--text-color-secondary);
}

.attachment-drop-zone p {
  margin: 0;
  color: var(--text-color-secondary);
  font-weight: 500;
}

.attachment-drop-zone small {
  color: var(--text-color-secondary);
  margin-top: 0.25rem;
}

.drop-zone-or {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.attachment-file-upload {
  margin: 0.25rem 0;
}

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
}

.attachment-item i:first-child {
  font-size: 1.25rem;
  color: var(--primary-color);
}

.attachment-name {
  flex: 1;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-size {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
  white-space: nowrap;
}
</style>
