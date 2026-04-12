<template>
  <div>
    <!-- Compact variant: list of buttons (used on member cards) -->
    <div v-if="variant === 'compact' && parentsList.length > 0" class="member-card-contacts">
      <div class="contacts-header">
        <i class="pi pi-users"></i>
        <span>Elternkontakt:</span>
      </div>
      <div class="contact-buttons">
        <Button
          v-for="parent in parentsList"
          :key="parent.id"
          :label="parent.full_name"
          icon="pi pi-phone"
          size="small"
          text
          @click="showContactOptions(parent)"
        />
      </div>
    </div>

    <!-- Detailed variant: full parent cards (used on Member Detail Parents tab / Details component) -->
    <div v-if="variant === 'detailed'">
      <div v-if="loading" class="loading-container">
        <i class="pi pi-spin pi-spinner" style="font-size: 2rem"></i>
      </div>
      <div v-else-if="parentsList.length === 0" class="empty-state">
        <i class="pi pi-users" style="font-size: 3rem; color: var(--text-color-secondary);"></i>
        <p>Keine Eltern hinterlegt</p>
      </div>
      <div v-else class="parents-grid">
        <Card v-for="parent in parentsList" :key="parent.id" class="parent-card">
          <template #title>
            {{ parent.full_name }}
          </template>
          <template #content>
            <div class="info-list">
              <div class="info-row">
                <span class="info-label">E-Mail:</span>
                <span class="info-value">
                  <a v-if="parent.email" :href="`mailto:${parent.email}`">{{ parent.email }}</a>
                  <span v-else class="text-muted">-</span>
                </span>
              </div>
              <div v-if="parent.email2" class="info-row">
                <span class="info-label">E-Mail 2:</span>
                <span class="info-value">
                  <a :href="`mailto:${parent.email2}`">{{ parent.email2 }}</a>
                </span>
              </div>
              <div class="info-row">
                <span class="info-label">Telefon:</span>
                <span class="info-value">
                  <a v-if="parent.phone" :href="`tel:${parent.phone}`">{{ parent.phone }}</a>
                  <span v-else class="text-muted">-</span>
                </span>
              </div>
              <div class="info-row">
                <span class="info-label">Mobil:</span>
                <span class="info-value">
                  <a v-if="parent.mobile" :href="`tel:${parent.mobile}`">{{ parent.mobile }}</a>
                  <span v-else class="text-muted">-</span>
                </span>
              </div>
              <div class="info-row">
                <span class="info-label">Adresse:</span>
                <span class="info-value">
                  {{ parent.street }}<br>
                  {{ parent.zip_code }} {{ parent.city }}
                </span>
              </div>
            </div>
            <Divider />
            <div class="parent-actions">
              <Button
                v-if="parent.mobile"
                label="WhatsApp"
                icon="pi pi-whatsapp"
                size="small"
                severity="success"
                outlined
                @click="openWhatsApp(parent.mobile)"
              />
              <Button
                v-if="parent.phone"
                label="Anrufen"
                icon="pi pi-phone"
                size="small"
                outlined
                @click="openPhone(parent.phone)"
              />
              <Button
                v-if="parent.email"
                label="E-Mail"
                icon="pi pi-envelope"
                size="small"
                severity="info"
                outlined
                @click="openEmail(parent.email)"
              />
            </div>
          </template>
        </Card>
      </div>
    </div>

    <Dialog
      v-model:visible="showContactDialog"
      :header="selectedParent ? `${selectedParent.full_name} kontaktieren` : 'Kontakt'
      "
      :modal="true"
      :style="{ width: '90vw', maxWidth: '400px' }"
    >
      <div v-if="selectedParent" class="contact-options">
        <Button
          v-if="selectedParent.mobile"
          label="WhatsApp"
          icon="pi pi-whatsapp"
          class="contact-option-btn"
          severity="success"
          @click="openWhatsApp(selectedParent.mobile)"
        />
        <Button
          v-if="selectedParent.phone"
          label="Anrufen"
          icon="pi pi-phone"
          class="contact-option-btn"
          @click="openPhone(selectedParent.phone)"
        />
        <Button
          v-if="selectedParent.email"
          label="E-Mail"
          icon="pi pi-envelope"
          class="contact-option-btn"
          severity="info"
          @click="openEmail(selectedParent.email)"
        />
        <Button
          v-if="selectedParent.email2"
          label="Alternative E-Mail"
          icon="pi pi-envelope"
          class="contact-option-btn"
          severity="info"
          @click="openEmail(selectedParent.email2)"
        />
      </div>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Parent, Member } from '@/types/api'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Divider from 'primevue/divider'
import Dialog from 'primevue/dialog'

interface Props {
  member?: Member | null
  parents?: Parent[]
  /** 'compact' shows small buttons list, 'detailed' shows full parent cards */
  variant?: 'compact' | 'detailed'
  loading?: boolean
}

const props = defineProps<Props>()

const showContactDialog = ref(false)
const selectedParent = ref<Parent | null>(null)

const variant = computed(() => props.variant || (props.member ? 'compact' : 'detailed'))

const parentsList = computed(() => {
  if (props.parents && props.parents.length >= 0) return props.parents
  return (props.member as Member | undefined)?.parents || []
})

const loading = computed(() => !!props.loading)

const showContactOptions = (parent: Parent) => {
  selectedParent.value = parent
  showContactDialog.value = true
}

const openWhatsApp = (phone: string) => {
  const cleanPhone = phone.replace(/\s/g, '')
  window.open(`https://wa.me/${cleanPhone}`, '_blank')
  showContactDialog.value = false
}

const openPhone = (phone: string) => {
  window.location.href = `tel:${phone}`
  showContactDialog.value = false
}

const openEmail = (email: string) => {
  window.location.href = `mailto:${email}`
  showContactDialog.value = false
}
</script>

<style scoped>
.member-card-contacts {
  margin-bottom: 1rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: var(--border-radius);
}
.contacts-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
  color: var(--text-color);
}
.contacts-header i {
  color: var(--primary-color);
}
.contact-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.contact-buttons :deep(.p-button) {
  justify-content: flex-start;
}
.contact-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.contact-option-btn {
  width: 100%;
  justify-content: flex-start;
}

/* Detailed variant styles (self-contained) */
.parents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.5rem;
}

.parent-card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.parent-card :deep(.p-card-title) {
  font-weight: 600;
  color: var(--text-color);
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
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

.parent-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2.5rem;
  text-align: center;
  gap: 1rem;
}

@media (max-width: 768px) {
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
