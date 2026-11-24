<template>
  <div class="forms">
    <header class="forms__head">
      <div>
        <h1>Aufnahmeformulare</h1>
        <p class="forms__lead">
          Digitale Aufnahmeanträge gestalten. Antragstellende erreichen ein Formular über einen Voucher-Code oder einen
          öffentlichen Link.
        </p>
      </div>
      <AdmButton v-if="canCreate" variant="primary" icon="pi pi-plus" @click="createDialog?.showModal()">Neues Formular</AdmButton>
    </header>

    <p v-if="store.error" class="forms__error" role="alert">{{ store.error }}</p>
    <p v-if="store.loading" class="forms__state">Lade Formulare …</p>
    <p v-else-if="!store.forms.length" class="forms__state">
      Noch kein Formular. Lege eines an. Die Vorlage „Jugendfeuerwehr“ enthält bereits alle üblichen Abschnitte.
    </p>

    <ul v-else class="forms__list">
      <li v-for="form in store.forms" :key="form.id" class="forms__card">
        <RouterLink :to="{ name: 'admission-form-builder', params: { id: form.id } }" class="forms__link">
          <span class="forms__title">{{ form.title }}</span>
          <span class="forms__meta">
            {{ form.department === null ? 'Ganze Organisation' : departmentName(form.department) }} ·
            {{ form.access === 'public' ? 'öffentlich' : 'nur Voucher' }} ·
            {{ form.current_version ? `Version ${form.current_version.version}` : 'Entwurf' }}
            <template v-if="form.current_version && form.has_unpublished_changes"> · ungespeicherte Änderungen am Entwurf</template>
            <template v-if="!form.is_active"> · inaktiv</template>
          </span>
          <span v-if="form.draft_issues.length" class="forms__issues">{{ form.draft_issues.length }} Hinweise vor dem Veröffentlichen</span>
        </RouterLink>
      </li>
    </ul>

    <dialog ref="createDialog" class="forms__dialog" aria-labelledby="create-title">
      <form class="forms__dialog-body" @submit.prevent="create">
        <h2 id="create-title">Neues Aufnahmeformular</h2>
        <AdmField input-id="new-title" label="Titel" required>
          <input id="new-title" v-model="draft.title" class="adm-input" required maxlength="200" />
        </AdmField>
        <AdmField
          input-id="new-department"
          label="Gilt für"
          hint="Ein Formular der Organisation gilt für alle Abteilungen; wohin ein Antrag geht, entscheidet der Voucher oder die Auswahl im öffentlichen Formular."
        >
          <select id="new-department" v-model="draft.department" class="adm-input">
            <option :value="null">Ganze Organisation (alle Abteilungen)</option>
            <option v-for="department in departmentsStore.departments" :key="department.id" :value="department.id">
              {{ department.name }}
            </option>
          </select>
        </AdmField>
        <label class="forms__check">
          <input v-model="draft.from_template" type="checkbox" class="adm-check" />
          Mit Vorlage „Jugendfeuerwehr“ beginnen
        </label>
        <div class="forms__dialog-actions">
          <AdmButton variant="ghost" @click="createDialog?.close()">Abbrechen</AdmButton>
          <AdmButton variant="primary" type="submit" icon="pi pi-check" :loading="creating">Anlegen</AdmButton>
        </div>
      </form>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AdmButton from '@/components/admissions/atoms/AdmButton.vue'
import AdmField from '@/components/admissions/atoms/AdmField.vue'
import '@/components/admissions/atoms/admInput.css'
import { useAdmissionFormsStore } from '@/stores/admissionForms'
import { useAuthStore } from '@/stores/auth'
import { useDepartmentsStore } from '@/stores/departments'

const store = useAdmissionFormsStore()
const auth = useAuthStore()
const departmentsStore = useDepartmentsStore()
const router = useRouter()

const createDialog = ref<HTMLDialogElement | null>(null)
const creating = ref(false)
const draft = reactive<{ title: string; department: number | null; from_template: boolean }>({
  title: 'Aufnahmeantrag',
  department: null,
  from_template: true
})
const canCreate = computed(() => auth.hasPerm('admissions.add_admissionform'))

function departmentName(id: number) {
  return departmentsStore.departments.find((department) => department.id === id)?.name ?? 'Abteilung'
}

async function create() {
  creating.value = true
  try {
    const form = await store.createForm({ ...draft })
    createDialog.value?.close()
    router.push({ name: 'admission-form-builder', params: { id: form.id } })
  } catch {
    // store.error is shown above the list
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  store.fetchForms()
  draft.department = departmentsStore.activeDepartmentId ?? departmentsStore.departments[0]?.id ?? null
})
</script>

<style scoped>
.forms {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  font-family: var(--jf-font-sans);
  color: var(--jf-color-text);
}

.forms__head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--jf-space-2);
}

.forms__head h1 {
  margin: 0;
  font-size: var(--jf-text-2xl);
}

.forms__lead,
.forms__state,
.forms__meta {
  margin: 0;
  color: var(--jf-color-text-muted);
}

.forms__error {
  margin: 0;
  color: var(--jf-color-danger);
}

.forms__list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
  gap: var(--jf-space-1-5);
  list-style: none;
  margin: 0;
  padding: 0;
}

.forms__card {
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}

.forms__card:hover {
  border-color: var(--jf-color-primary);
}

.forms__link {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  padding: var(--jf-space-2);
  color: inherit;
  text-decoration: none;
}

.forms__title {
  font-weight: var(--jf-weight-semibold);
  font-size: var(--jf-text-md);
}

.forms__meta {
  font-size: var(--jf-text-sm);
}

.forms__issues {
  font-size: var(--jf-text-sm);
  color: var(--jf-color-warning);
}

.forms__dialog {
  max-width: 30rem;
  width: calc(100vw - 2rem);
  padding: 0;
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
}

.forms__dialog::backdrop {
  background: var(--jf-color-backdrop);
}

.forms__dialog-body {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-3);
}

.forms__dialog-body h2 {
  margin: 0;
  font-size: var(--jf-text-lg);
}

.forms__check {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target, 44px);
}

.forms__dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--jf-space-1);
}
</style>
