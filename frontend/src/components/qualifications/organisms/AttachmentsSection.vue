<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { useQualificationsStore } from '@/stores/qualifications'
import type { Attachment } from '@/types/qualifications'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import FileUpload, { type FileUploadSelectEvent } from 'primevue/fileupload'
import ProgressSpinner from 'primevue/progressspinner'
import Image from 'primevue/image'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'

interface Props {
  sourceId: number
  sourceType: 'qualification' | 'specialTask'
  title?: string
  allowManage?: boolean
  initialAttachments?: Attachment[] | null
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Anhänge',
  allowManage: true,
  initialAttachments: () => []
})

const toast = useToast()
const confirm = useConfirm()
const qualificationsStore = useQualificationsStore()

const showUploadDialog = ref(false)
const showPreviewDialog = ref(false)
const previewAttachment = ref<Attachment | null>(null)
const isDragging = ref(false)
const uploadForm = ref({
  name: '',
  description: ''
})
const selectedFile = ref<File | null>(null)
const formError = ref<string | null>(null)

const isQualification = computed(() => props.sourceType === 'qualification')

const attachments = computed<Attachment[]>(() => {
  const map = isQualification.value
    ? qualificationsStore.qualificationAttachments
    : qualificationsStore.specialTaskAttachments

  const fromStore = map[props.sourceId]
  return fromStore ?? props.initialAttachments ?? []
})

const loadingAttachments = computed(() => qualificationsStore.loadingAttachments)

async function ensureAttachmentsLoaded() {
  try {
    if (attachments.value.length === 0) {
      if (isQualification.value) {
        await qualificationsStore.fetchQualificationAttachments(props.sourceId)
      } else {
        await qualificationsStore.fetchSpecialTaskAttachments(props.sourceId)
      }
    }
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Anhänge',
      detail: error?.message || 'Anhänge konnten nicht geladen werden.',
      life: 4000
    })
  }
}

onMounted(() => {
  ensureAttachmentsLoaded()
})

watch(
  () => props.sourceId,
  () => {
    ensureAttachmentsLoaded()
  }
)

function openUploadDialog() {
  showUploadDialog.value = true
  formError.value = null
}

function closeUploadDialog() {
  showUploadDialog.value = false
  uploadForm.value = { name: '', description: '' }
  selectedFile.value = null
  formError.value = null
}

function handleFileSelect(event: FileUploadSelectEvent) {
  const file = event.files?.[0] as File | undefined
  selectedFile.value = file ?? null

  if (file && !uploadForm.value.name) {
    const baseName = file.name.split('.').slice(0, -1).join('.') || file.name
    uploadForm.value.name = baseName
  }
}

function handleDrop(event: DragEvent) {
  isDragging.value = false
  const files = event.dataTransfer?.files
  if (files && files.length > 0 && files[0]) {
    const file = files[0]
    selectedFile.value = file
    const baseName = file.name.split('.').slice(0, -1).join('.') || file.name
    uploadForm.value.name = baseName
    showUploadDialog.value = true
  }
}

function validateUpload(): boolean {
  formError.value = null

  if (!selectedFile.value) {
    formError.value = 'Bitte wählen Sie eine Datei aus.'
    return false
  }

  if (!uploadForm.value.name.trim()) {
    formError.value = 'Bitte geben Sie einen Namen an.'
    return false
  }

  return true
}

async function submitUpload() {
  if (!validateUpload()) {
    return
  }

  const formData = new FormData()
  formData.append('file', selectedFile.value!)
  formData.append('name', uploadForm.value.name.trim())
  if (uploadForm.value.description.trim()) {
    formData.append('description', uploadForm.value.description.trim())
  }

  try {
    if (isQualification.value) {
      await qualificationsStore.uploadQualificationAttachment(props.sourceId, formData)
    } else {
      await qualificationsStore.uploadSpecialTaskAttachment(props.sourceId, formData)
    }

    toast.add({
      severity: 'success',
      summary: 'Anhang hochgeladen',
      detail: 'Der Anhang wurde erfolgreich gespeichert.',
      life: 3000
    })

    closeUploadDialog()
  } catch (error: any) {
    formError.value = error?.message || 'Fehler beim Hochladen.'
  }
}

function handleView(attachment: Attachment) {
  const fileUrl = attachment.file_url || attachment.file
  if (fileUrl) {
    window.open(fileUrl, '_blank', 'noopener')
  }
}

function handlePreview(attachment: Attachment) {
  previewAttachment.value = attachment
  showPreviewDialog.value = true
}

async function handleDownload(attachment: Attachment) {
  const fileUrl = attachment.file_url || attachment.file
  if (fileUrl) {
    window.open(fileUrl, '_blank')
  }
}

function handleDelete(attachment: Attachment) {
  if (!props.allowManage) return

  confirm.require({
    message: `Soll der Anhang "${attachment.name}" wirklich gelöscht werden?`,
    header: 'Anhang löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        if (isQualification.value) {
          await qualificationsStore.deleteQualificationAttachment(props.sourceId, attachment.id)
        } else {
          await qualificationsStore.deleteSpecialTaskAttachment(props.sourceId, attachment.id)
        }

        toast.add({
          severity: 'success',
          summary: 'Anhang gelöscht',
          detail: 'Der Anhang wurde entfernt.',
          life: 3000
        })
      } catch (error: any) {
        toast.add({
          severity: 'error',
          summary: 'Löschen fehlgeschlagen',
          detail: error?.message || 'Der Anhang konnte nicht gelöscht werden.',
          life: 4000
        })
      }
    }
  })
}

function isImage(attachment: Attachment): boolean {
  const filename = (attachment.file_url || attachment.file || '').toLowerCase()
  return filename.endsWith('.jpg') || filename.endsWith('.jpeg') || 
         filename.endsWith('.png') || filename.endsWith('.gif') || filename.endsWith('.webp')
}

function isPDF(attachment: Attachment): boolean {
  const filename = (attachment.file_url || attachment.file || '').toLowerCase()
  return filename.endsWith('.pdf')
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<template>
  <Card class="attachments-card">
    <template #title>
      <div class="attachments-header">
        <span>{{ title }}</span>
        <Button
          v-if="allowManage"
          icon="pi pi-upload"
          label="Anhang hochladen"
          size="small"
          outlined
          @click="openUploadDialog"
        />
      </div>
    </template>

    <template #content>
      <div v-if="loadingAttachments" class="attachments-loading">
        <ProgressSpinner />
      </div>

      <div v-else>
        <!-- Drag and Drop Zone (shown when no attachments) -->
        <div 
          v-if="!attachments.length && allowManage"
          class="drop-zone"
          :class="{ 'drop-zone-active': isDragging }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
          @click="openUploadDialog"
        >
          <i class="pi pi-cloud-upload"></i>
          <p>Dateien hierher ziehen oder klicken zum Hochladen</p>
          <small>Max. 10 MB. PDF, Bilder, DOC, DOCX</small>
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
                    <span v-if="attachment.uploaded_by_name" class="meta-item">
                      <i class="pi pi-user"></i>
                      {{ attachment.uploaded_by_name }}
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
                    @click="handlePreview(attachment)"
                    v-tooltip.top="'Anzeigen'"
                  />
                  <Button 
                    icon="pi pi-download" 
                    text
                    rounded
                    size="small"
                    @click="handleDownload(attachment)"
                    v-tooltip.top="'Herunterladen'"
                  />
                  <Button 
                    v-if="allowManage"
                    icon="pi pi-trash" 
                    text
                    rounded
                    size="small"
                    severity="danger"
                    @click="handleDelete(attachment)"
                    v-tooltip.top="'Löschen'"
                  />
                </div>
              </div>
            </template>
          </Card>
        </div>

        <!-- Empty State -->
        <div v-else class="empty-state">
          <i class="pi pi-paperclip"></i>
          <p>Noch keine Anhänge vorhanden.</p>
        </div>
      </div>
    </template>
  </Card>

  <!-- Upload Dialog -->
  <Dialog
    v-model:visible="showUploadDialog"
    modal
    header="Anhang hochladen"
    :style="{ width: '28rem' }"
    @hide="closeUploadDialog"
  >
    <div class="upload-form">
      <div class="form-field">
        <label for="attachment-name">Name *</label>
        <InputText
          id="attachment-name"
          v-model="uploadForm.name"
          placeholder="z.B. Zertifikat, Nachweis"
          autocomplete="off"
        />
      </div>

      <div class="form-field">
        <label for="attachment-description">Beschreibung</label>
        <Textarea
          id="attachment-description"
          v-model="uploadForm.description"
          rows="3"
          placeholder="Optionale Beschreibung"
          autoResize
        />
      </div>

      <div class="form-field">
        <label>Datei *</label>
        <FileUpload
          mode="basic"
          chooseLabel="Datei auswählen"
          accept="application/pdf,image/*,.doc,.docx"
          :auto="false"
          :customUpload="true"
          @select="handleFileSelect"
        />
        <small v-if="selectedFile" class="file-info">
          Ausgewählt: {{ selectedFile.name }}
        </small>
      </div>

      <div v-if="formError" class="form-error">
        <i class="pi pi-exclamation-circle"></i>
        {{ formError }}
      </div>

      <div class="dialog-actions">
        <Button
          label="Abbrechen"
          icon="pi pi-times"
          severity="secondary"
          outlined
          @click="closeUploadDialog"
        />
        <Button
          label="Hochladen"
          icon="pi pi-upload"
          :loading="loadingAttachments"
          @click="submitUpload"
        />
      </div>
    </div>
  </Dialog>

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
        :src="previewAttachment.file_url || previewAttachment.file" 
        alt="Preview"
        width="100%"
        preview
      />
      <iframe 
        v-else-if="previewAttachment && isPDF(previewAttachment)"
        :src="previewAttachment.file_url || previewAttachment.file"
        width="100%"
        height="600px"
      ></iframe>
      <div v-else class="no-preview">
        <i class="pi pi-file"></i>
        <p>Keine Vorschau verfügbar</p>
        <Button 
          label="Herunterladen" 
          icon="pi pi-download" 
          @click="handleDownload(previewAttachment!)"
        />
      </div>
    </div>
  </Dialog>

</template>

<style scoped>
.attachments-card {
  width: 100%;
}

.attachments-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  font-size: 1.125rem;
  font-weight: 600;
}

.attachments-loading {
  display: flex;
  justify-content: center;
  padding: 2rem 0;
}

/* Drag and Drop Zone */
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
  font-weight: 500;
}

.drop-zone small {
  color: var(--text-color-secondary);
}

/* Attachments Grid */
.attachments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.attachment-card {
  transition: transform 0.2s, box-shadow 0.2s;
  height: 100%;
}

.attachment-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
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

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
  color: var(--text-color-secondary);
  text-align: center;
}

.empty-state i {
  font-size: 3rem;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
  font-style: italic;
}

/* Upload Form */
.upload-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  font-weight: 600;
  font-size: 0.875rem;
}

.file-info {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.form-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--red-50);
  color: var(--red-600);
  border-radius: var(--border-radius);
  font-size: 0.875rem;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

/* Preview */
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
  .attachments-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .attachments-grid {
    grid-template-columns: 1fr;
  }

  .dialog-actions {
    flex-direction: column-reverse;
  }

  .dialog-actions :deep(.p-button) {
    width: 100%;
    justify-content: center;
  }
}
</style>
