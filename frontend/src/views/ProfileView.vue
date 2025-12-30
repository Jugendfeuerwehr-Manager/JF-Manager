<template>
  <div class="profile-view">
    <OverviewHeader
      title="Mein Profil"
      subtitle="Persönliche Einstellungen und Informationen"
    />

    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <Card v-else-if="user" class="profile-card">
      <template #content>
        <div class="profile-content">
          <!-- User Information -->
          <div class="profile-section">
            <h3>
              <i class="pi pi-user"></i>
              Benutzerinformationen
            </h3>
            <div class="info-grid">
              <div class="info-item">
                <label>Benutzername</label>
                <span>{{ user.username }}</span>
              </div>
              <div class="info-item">
                <label>Vollständiger Name</label>
                <span>{{ user.full_name || 'Nicht angegeben' }}</span>
              </div>
              <div class="info-item">
                <label>E-Mail</label>
                <span>{{ user.email || 'Nicht angegeben' }}</span>
              </div>
            </div>
          </div>

          <Divider />

          <!-- Email Signature -->
          <div class="profile-section">
            <h3>
              <i class="pi pi-envelope"></i>
              E-Mail-Signatur
            </h3>
            <p class="section-description">
              Ihre Signatur wird automatisch an alle E-Mails angehängt, die Sie über das System versenden.
            </p>
            <div class="form-field">
              <label for="signature">Signatur</label>
              <TiptapEditor
                v-model="signature"
                placeholder="Ihre E-Mail-Signatur eingeben..."
                :show-variables="false"
              />
            </div>
            <Button
              label="Signatur speichern"
              icon="pi pi-save"
              @click="saveSignature"
              :loading="saving"
              :disabled="signature === user.email_signature"
              severity="primary"
              class="mt-2"
            />
          </div>

          <Divider />

          <!-- Permissions -->
          <div class="profile-section" v-if="user.permissions && user.permissions.length > 0">
            <h3>
              <i class="pi pi-shield"></i>
              Berechtigungen
            </h3>
            <div class="permissions-list">
              <Tag
                v-for="permission in user.permissions"
                :key="permission"
                :value="permission"
                severity="secondary"
              />
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useAuthStore } from '@/stores/auth'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import TiptapEditor from '@/components/emails/organisms/TiptapEditor.vue'
import { userApi } from '@/api/user'

const toast = useToast()
const authStore = useAuthStore()

const user = ref(authStore.user)
const signature = ref(user.value?.email_signature || '')
const loading = ref(false)
const saving = ref(false)

const saveSignature = async () => {
  if (!user.value) return

  saving.value = true
  try {
    await userApi.updateProfile({
      email_signature: signature.value
    })

    // Update local user object
    if (user.value) {
      user.value.email_signature = signature.value
    }

    // Refresh user data in auth store
    await authStore.fetchUser()

    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: 'Signatur erfolgreich gespeichert',
      life: 3000
    })
  } catch (error) {
    console.error('Error saving signature:', error)
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Signatur konnte nicht gespeichert werden',
      life: 3000
    })
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (!user.value) {
    loading.value = true
    try {
      await authStore.fetchUser()
      user.value = authStore.user
      signature.value = user.value?.email_signature || ''
    } catch (error) {
      console.error('Error loading user:', error)
    } finally {
      loading.value = false
    }
  }
})
</script>

<style scoped>
.profile-view {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.profile-card {
  margin-top: 1rem;
}

.profile-content {
  padding: 1rem;
}

.profile-section {
  margin-bottom: 2rem;
}

.profile-section:last-child {
  margin-bottom: 0;
}

.profile-section h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-color);
  margin-bottom: 1rem;
}

.section-description {
  color: var(--text-color-secondary);
  margin-bottom: 1rem;
  font-size: 0.95rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-item label {
  font-weight: 600;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.info-item span {
  color: var(--text-color);
}

.form-field {
  margin-bottom: 1rem;
}

.form-field label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: var(--text-color);
}

.permissions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

@media (max-width: 768px) {
  .profile-content {
    padding: 0.5rem;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
