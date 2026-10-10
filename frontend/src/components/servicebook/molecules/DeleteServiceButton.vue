<template>
  <Button v-if="allowed" label="Dienst löschen" icon="pi pi-trash" severity="danger" outlined :loading="deleting" :disabled="deleting || disabled" @click="confirmDelete" />
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useAuthStore } from '@/stores/auth'
import { useServicebookStore } from '@/stores/servicebook'
import { getApiErrorMessage } from '@/utils/apiError'

const props = defineProps<{ service: { id: number; topic?: string | null; department: number | null }; disabled?: boolean }>()
const auth = useAuthStore()
const store = useServicebookStore()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const deleting = ref(false)
const allowed = computed(() => {
  const user = auth.user
  if (!user) return false
  if (user.is_superuser) return true
  const has = (permissions: string[]) => permissions.includes('servicebook.delete_service') || permissions.includes('delete_service')
  return has(user.permissions) || user.department_roles.some(role => role.department_id === props.service.department && has(role.permissions))
})
function confirmDelete() {
  const id = props.service.id
  confirm.require({
    header: 'Dienst löschen',
    message: `„${props.service.topic || 'Dienst ohne Thema'}“ endgültig löschen? Die erfassten Anwesenheiten und Vorkommnisse werden ebenfalls gelöscht. Eine verknüpfte Übungsplanung bleibt erhalten.`,
    icon: 'pi pi-trash', rejectLabel: 'Abbrechen', acceptLabel: 'Endgültig löschen', acceptProps: { severity: 'danger' },
    accept: async () => {
      deleting.value = true
      try {
        await store.deleteService(id)
        toast.add({ severity: 'success', summary: 'Dienst gelöscht', life: 3000 })
        await router.push({ name: 'servicebook' })
      } catch (err) {
        toast.add({ severity: 'error', summary: 'Löschen fehlgeschlagen', detail: getApiErrorMessage(err, 'Bitte erneut versuchen.'), life: 5000 })
      } finally { deleting.value = false }
    },
  })
}
</script>
