<template>
  <form @submit.prevent="handleSubmit" class="parent-form">
    <div class="grid">
      <div class="col-12 md:col-6">
        <div class="field">
          <label for="first_name">First Name *</label>
          <InputText
            id="first_name"
            v-model="formData.first_name"
            :invalid="submitted && !formData.first_name"
            class="w-full"
          />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="last_name">Last Name *</label>
          <InputText
            id="last_name"
            v-model="formData.last_name"
            :invalid="submitted && !formData.last_name"
            class="w-full"
          />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="relation">Relation</label>
          <Dropdown
            id="relation"
            v-model="formData.relation"
            :options="relationOptions"
            placeholder="Select relation"
            class="w-full"
          />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="email">Email</label>
          <InputText id="email" v-model="formData.email" type="email" class="w-full" />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="phone">Phone</label>
          <InputText id="phone" v-model="formData.phone" class="w-full" />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="mobile">Mobile</label>
          <InputText id="mobile" v-model="formData.mobile" class="w-full" />
        </div>
      </div>

      <div class="col-12">
        <div class="field">
          <label for="address">Address</label>
          <InputText id="address" v-model="formData.address" class="w-full" />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="postal_code">Postal Code</label>
          <InputText id="postal_code" v-model="formData.postal_code" class="w-full" />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="field">
          <label for="city">City</label>
          <InputText id="city" v-model="formData.city" class="w-full" />
        </div>
      </div>
    </div>

    <div class="flex justify-end gap-2 mt-4">
      <Button label="Cancel" severity="secondary" @click="emit('cancel')" type="button" />
      <Button label="Save" type="submit" :loading="loading" />
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Parent } from '@/api/members'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
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
  first_name: '',
  last_name: '',
  relation: '',
  email: '',
  phone: '',
  mobile: '',
  address: '',
  postal_code: '',
  city: ''
})

const relationOptions = ['Mother', 'Father', 'Guardian', 'Other']

const submitted = ref(false)
const loading = ref(false)

onMounted(() => {
  if (props.parent) {
    formData.value = { ...props.parent }
  }
})

const handleSubmit = () => {
  submitted.value = true

  if (!formData.value.first_name || !formData.value.last_name) {
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
