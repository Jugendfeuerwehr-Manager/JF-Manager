<template>
  <div class="attachments-manager">
    <div class="section-header">
      <Button 
        label="Hochladen" 
        icon="pi pi-upload" 
        @click="showUploadDialog = true"
        :disabled="attachmentsStore.loading"
      />
    </div>

    <!-- Upload Dialog -->
    <Dialog 
      v-model:visible="showUploadDialog" 
      header="Anhang hochladen" 
      :modal="true"
      :style="{ width: '50vw' }"
      :breakpoints="{ '960px': '75vw', '640px': '90vw' }"
    >
      <div class="upload-form">
        <div class="field">
          <label for="attachment-name">Name *</label>
          <InputText 
            id="attachment-name" 
            v-model="newAttachment.name" 
            :invalid="!!errors.name"
            placeholder="z.B. Anmeldung, Foto, etc."
          />
          <small v-if="errors.name" class="p-error">{{ errors.name }}</small>
        </div>

        <div class="field">
          <label for="attachment-description">Beschreibung</label>
          <Textarea 
            id="attachment-description" 
            v-model="newAttachment.description" 
            rows="3"
            placeholder="Optionale Beschreibung des Anhangs"
          />
        </div>

        <div class="field">
          <label>Datei *</label>
          <FileUpload
            mode="basic"
            :auto="false"
            accept="image/*,.pdf,.doc,.docx,.txt"
            :maxFileSize="10000000"
            chooseLabel="Datei auswählen"
            @select="onFileSelect"
            :disabled="uploading"
            class="file-upload-btn"
          />
          <small class="help-text">Max. 10 MB. Erlaubt: Bilder, PDF, DOC, DOCX, TXT</small>
          <small v-if="errors.file" class="p-error">{{ errors.file }}</small>
          
          <div v-if="selectedFile" class="selected-file">
            <i class="pi pi-file"></i>
            <span>{{ selectedFile.name }}</span>
            <span class="file-size">({{ formatFileSize(selectedFile.size) }})</span>
          </div>
        </div>
      </div>

      <template #footer>
        <Button 
          label="Abbrechen" 
          icon="pi pi-times" 
          @click="closeUploadDialog"
          severity="secondary"
          :disabled="uploading"
        />
        <Button 
          label="Hochladen" 
          icon="pi pi-upload" 
          @click="uploadAttachment"
          :loading="uploading"
        />
      </template>
    </Dialog>

    <!-- Drag and Drop Upload Area -->
    <div 
      v-if="!attachments.length && !attachmentsStore.loading"
      class="drop-zone"
      :class="{ 'drop-zone-active': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <i class="pi pi-cloud-upload"></i>
      <p>Dateien hierher ziehen oder auf "Hochladen" klicken</p>
      <small>Max. 10 MB pro Datei</small>
    </div>

    <!-- Attachments List -->
    <div v-if="attachmentsStore.loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <!-- Attachments Grid -->
    <div v-else-if="attachments.length" class="attachments-grid">
      <Card v-for="attachment in attachments" :key="attachment.id" class="attachment-card">
        <template #content>
          <div class="attachment-content">
            <div class="attachment-icon">
              <i 
                v-if="isImage(attachment)" 
                class="pi pi-image" 
                style="font-size: 2rem; color: var(--blue-500);"
              ></i>
              <i 
                v-else-if="isPDF(attachment)" 
                class="pi pi-file-pdf" 
                style="font-size: 2rem; color: var(--red-500);"
              ></i>
              <i 
                v-else 
                class="pi pi-file" 
                style="font-size: 2rem; color: var(--text-color-secondary);"
              ></i>
            </div>

            <div class="attachment-info">
              <h4 class="attachment-name">{{ attachment.name }}</h4>
              <p v-if="attachment.description" class="attachment-description">
                {{ attachment.description }}
              </p>
              
              <div class="attachment-meta">
                <span class="meta-item">
                  <i class="pi pi-calendar"></i>
                  {{ formatDate(attachment.uploaded_at) }}
                </span>
                <span v-if="attachment.file_size" class="meta-item">
                  <i class="pi pi-database"></i>
                  {{ formatFileSize(attachment.file_size) }}
                </span>
              </div>
            </div>

            <div class="attachment-actions">
              <Button 
                icon="pi pi-eye" 
                text
                rounded
                size="small"
                severity="info"
                @click="viewAttachment(attachment)"
                v-tooltip.top="'Anzeigen'"
              />
              <Button 
                icon="pi pi-download" 
                text
                rounded
                size="small"
                @click="downloadAttachment(attachment)"
                v-tooltip.top="'Herunterladen'"
              />
              <Button 
                icon="pi pi-trash" 
                text
                rounded
                size="small"
                severity="danger"
                @click="confirmDeleteAttachment(attachment)"
                v-tooltip.top="'Löschen'"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Preview Dialog -->
    <Dialog 
      v-model:visible="showPreviewDialog" 
      :header="previewAttachment?.name" 
      :modal="true"
      :style="{ width: '70vw' }"
      :breakpoints="{ '960px': '90vw' }"
    >
      <div class="preview-content">
        <Image 
          v-if="previewAttachment && isImage(previewAttachment)"
          :src="previewAttachment.file_url || ''" 
          alt="Preview"
          width="100%"
          preview
        />
        <iframe 
          v-else-if="previewAttachment && isPDF(previewAttachment)"
          :src="previewAttachment.file_url || ''"
          width="100%"
          height="600px"
        ></iframe>
        <div v-else class="no-preview">
          <i class="pi pi-file"></i>
          <p>Keine Vorschau verfügbar</p>
          <Button 
            label="Herunterladen" 
            icon="pi pi-download" 
            @click="downloadAttachment(previewAttachment!)"
          />
        </div>
      </div>
    </Dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useAttachmentsStore } from '@/stores/attachments'
import type { Attachment } from '@/types/api'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import FileUpload from 'primevue/fileupload'
import Card from 'primevue/card'
import Image from 'primevue/image'
import ProgressSpinner from 'primevue/progressspinner'
import { getApiErrorMessage } from '@/utils/apiError'

interface Props {
  memberId: number
}

const props = defineProps<Props>()
const toast = useToast()
const confirm = useConfirm()
const attachmentsStore = useAttachmentsStore()

const uploading = ref(false)
const showUploadDialog = ref(false)
const showPreviewDialog = ref(false)
const previewAttachment = ref<Attachment | null>(null)
const isDragging = ref(false)
const selectedFile = ref<File | null>(null)

const newAttachment = ref({
  name: '',
  description: '',
  file: null as File | null
})

const errors = ref({
  name: '',
  file: ''
})

const attachments = computed(() => attachmentsStore.getAttachmentsByMember(props.memberId))

onMounted(() => {
  loadAttachments()
})

const loadAttachments = async () => {
  try {
    await attachmentsStore.fetchAttachmentsForMember(props.memberId)
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Anhänge konnten nicht geladen werden',
      life: 3000
    })
  }
}

const onFileSelect = (event: { files: File[] }) => {
  const file = event.files[0]
  if (file) {
    selectedFile.value = file
    newAttachment.value.file = file
    if (!newAttachment.value.name) {
      newAttachment.value.name = file.name.split('.')[0] ?? ''
    }
    errors.value.file = ''
  }
}

const handleDrop = (event: DragEvent) => {
  isDragging.value = false
  const files = event.dataTransfer?.files
  if (files && files.length > 0 && files[0]) {
    const file = files[0]
    selectedFile.value = file
    newAttachment.value.file = file
    const namePart = file.name.split('.')[0]
    newAttachment.value.name = namePart || file.name
    showUploadDialog.value = true
  }
}

const validateForm = (): boolean => {
  errors.value = { name: '', file: '' }
  let isValid = true

  if (!newAttachment.value.name.trim()) {
    errors.value.name = 'Name ist erforderlich'
    isValid = false
  }

  if (!newAttachment.value.file) {
    errors.value.file = 'Datei ist erforderlich'
    isValid = false
  }

  return isValid
}

const uploadAttachment = async () => {
  if (!validateForm()) {
    return
  }

  uploading.value = true

  try {
    const formData = new FormData()
    formData.append('file', newAttachment.value.file!)
    formData.append('name', newAttachment.value.name)
    if (newAttachment.value.description) {
      formData.append('description', newAttachment.value.description)
    }
    // ContentType for Member model (ID: 19)
    formData.append('content_type', '19')
    formData.append('object_id', props.memberId.toString())

    await attachmentsStore.createAttachment(formData)
    
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: 'Anhang wurde hochgeladen',
      life: 3000
    })

    closeUploadDialog()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: getApiErrorMessage(error, 'Fehler beim Hochladen'),
      life: 3000
    })
  } finally {
    uploading.value = false
  }
}

const closeUploadDialog = () => {
  showUploadDialog.value = false
  newAttachment.value = { name: '', description: '', file: null }
  selectedFile.value = null
  errors.value = { name: '', file: '' }
}

const viewAttachment = (attachment: Attachment) => {
  previewAttachment.value = attachment
  showPreviewDialog.value = true
}

const downloadAttachment = async (attachment: Attachment) => {
  try {
    const responseData = await attachmentsStore.downloadAttachment(attachment.id)
    // Create blob with correct MIME type
    const blob = new Blob([responseData], { 
      type: attachment.mime_type || 'application/octet-stream' 
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    // Extract file extension if not in name
    let filename = attachment.name
    if (!filename.includes('.') && attachment.file_url) {
      const urlParts = attachment.file_url.split('.')
      const extension = urlParts[urlParts.length - 1]
      filename = `${filename}.${extension}`
    }
    
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Datei konnte nicht heruntergeladen werden',
      life: 3000
    })
  }
}

const confirmDeleteAttachment = (attachment: Attachment) => {
  confirm.require({
    message: `Möchten Sie "${attachment.name}" wirklich löschen?`,
    header: 'Anhang löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: () => deleteAttachment(attachment.id)
  })
}

const deleteAttachment = async (id: number) => {
  try {
    await attachmentsStore.deleteAttachment(id)
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: 'Anhang wurde gelöscht',
      life: 3000
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Anhang konnte nicht gelöscht werden',
      life: 3000
    })
  }
}

const isImage = (attachment: Attachment): boolean => {
  return attachment.mime_type?.startsWith('image/') || false
}

const isPDF = (attachment: Attachment): boolean => {
  return attachment.mime_type === 'application/pdf'
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}
</script>

<style scoped>
.attachments-manager {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.upload-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
}

.help-text {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.p-error {
  color: var(--red-500);
  font-size: 0.875rem;
}

.file-upload-btn {
  width: 100%;
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-100);
  border-radius: var(--border-radius);
  margin-top: 0.5rem;
}

.file-size {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  border: 2px dashed var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-50);
  text-align: center;
  transition: all 0.3s;
  cursor: pointer;
}

.drop-zone:hover,
.drop-zone-active {
  border-color: var(--primary-color);
  background: var(--primary-50);
}

.drop-zone i {
  font-size: 3rem;
  color: var(--text-color-secondary);
  margin-bottom: 1rem;
}

.drop-zone p {
  margin: 0.5rem 0;
  color: var(--text-color);
}

.drop-zone small {
  color: var(--text-color-secondary);
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

/* Attachments Grid */
.attachments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.attachment-card {
  transition: transform 0.2s, box-shadow 0.2s;
  height: 100%;
}




.attachment-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.attachment-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  background: var(--surface-100);
  border-radius: var(--border-radius);
  margin: 0 auto;
}

.attachment-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.attachment-name {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
  word-break: break-word;
}

.attachment-description {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  line-height: 1.5;
  word-break: break-word;
}

.attachment-meta {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-border);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.meta-item i {
  font-size: 0.75rem;
}

.attachment-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
}

.attachment-actions :deep(button) {
  position: relative !important;
  flex-shrink: 0;
}

.preview-content {
  padding: 1rem;
}

.no-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
  text-align: center;
}

.no-preview i {
  font-size: 3rem;
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
