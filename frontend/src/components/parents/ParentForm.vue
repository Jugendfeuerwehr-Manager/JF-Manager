<template>
  <form @submit.prevent="handleSubmit" class="parent-form">
    <div class="grid">
      <div class="col-12 md:col-6">
        <div class="field">
          <label for="name">Vorname *</label>
          <InputText
            id="name"
            v-model="formData.name"
            :invalid="submitted && !formData.name"
            class="w-full"
          />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="lastname">Nachname *</label>
          <InputText
            id="lastname"
            v-model="formData.lastname"
            :invalid="submitted && !formData.lastname"
            class="w-full"
          />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="email">E-Mail</label>
          <InputText id="email" v-model="formData.email" type="email" class="w-full" />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="phone">Telefon</label>
          <InputText id="phone" v-model="formData.phone" class="w-full" />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="mobile">Mobil</label>
          <InputText id="mobile" v-model="formData.mobile" class="w-full" />
        </div>
      </div>

      <div class="col-12">
        <div class="field">
          <label for="street">Straße</label>
          <InputText id="street" v-model="formData.street" class="w-full" />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="zip_code">PLZ</label>
          <InputText id="zip_code" v-model="formData.zip_code" class="w-full" />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="city">Ort</label>
          <InputText id="city" v-model="formData.city" class="w-full" />
        </div>
      </div>
    </div>

    <div class="flex justify-end gap-2 mt-4">
      <Button label="Abbrechen" severity="secondary" @click="emit('cancel')" type="button" />
      <Button label="Speichern" type="submit" :loading="loading" />
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Parent } from '@/api/members'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

interface Props {
  parent?: Parent | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  save: [parent: Partial<Parent>]
  cancel: []
}>()

const formData = ref<Partial<Parent>>({
  name: '',
  lastname: '',
  email: '',
  phone: '',
  mobile: '',
  street: '',
  zip_code: '',
  city: ''
})

const submitted = ref(false)
const loading = ref(false)

onMounted(() => {
  if (props.parent) {
    formData.value = { ...props.parent }
  }
})

const handleSubmit = () => {
  submitted.value = true

  if (!formData.value.name || !formData.value.lastname) {
    return
  }

  loading.value = true
  emit('save', formData.value)
  loading.value = false
}
</script>

<style scoped>
.parent-form .field {
  margin-bottom: 1rem;
}

.parent-form label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: var(--surface-900);
}
</style>
