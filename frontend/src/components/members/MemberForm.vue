<template>
  <form @submit.prevent="handleSubmit">
    <div class="grid">
      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="name" class="block mb-2">Vorname *</label>
          <InputText
            id="name"
            v-model="formData.name"
            :invalid="submitted && !formData.name"
            fluid
          />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="lastname" class="block mb-2">Nachname *</label>
          <InputText
            id="lastname"
            v-model="formData.lastname"
            :invalid="submitted && !formData.lastname"
            fluid
          />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="birthday" class="block mb-2">Geburtstag *</label>
          <DatePicker
            id="birthday"
            v-model="formData.birthday"
            date-format="dd.mm.yy"
            :invalid="submitted && !formData.birthday"
            fluid
          />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="joined" class="block mb-2">Eingetreten</label>
          <DatePicker
            id="joined"
            v-model="formData.joined"
            date-format="dd.mm.yy"
            fluid
          />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="status" class="block mb-2">Status</label>
          <Select
            id="status"
            v-model="formData.status"
            :options="statuses"
            option-label="name"
            option-value="id"
            placeholder="Status wählen"
            fluid
          />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="group" class="block mb-2">Gruppe</label>
          <Select
            id="group"
            v-model="formData.group"
            :options="groups"
            option-label="name"
            option-value="id"
            placeholder="Gruppe wählen"
            fluid
          />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="email" class="block mb-2">E-Mail</label>
          <InputText id="email" v-model="formData.email" type="email" fluid />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="phone" class="block mb-2">Telefon</label>
          <InputText id="phone" v-model="formData.phone" fluid />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="mobile" class="block mb-2">Mobil</label>
          <InputText id="mobile" v-model="formData.mobile" fluid />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="identityCardNumber" class="block mb-2">Ausweis Nr.</label>
          <InputText id="identityCardNumber" v-model="formData.identityCardNumber" fluid />
        </div>
      </div>

      <div class="col-12">
        <div class="mb-3">
          <label for="street" class="block mb-2">Straße</label>
          <InputText id="street" v-model="formData.street" fluid />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="zip_code" class="block mb-2">PLZ</label>
          <InputText id="zip_code" v-model="formData.zip_code" fluid />
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label for="city" class="block mb-2">Ort</label>
          <InputText id="city" v-model="formData.city" fluid />
        </div>
      </div>

      <div class="col-12">
        <div class="mb-3">
          <div class="flex align-items-center">
            <Checkbox id="canSwimm" v-model="formData.canSwimm" :binary="true" />
            <label for="canSwimm" class="ml-2 mb-0">Kann schwimmen</label>
          </div>
        </div>
      </div>

      <div class="col-12">
        <div class="mb-3">
          <label for="notes" class="block mb-2">Bemerkungen</label>
          <Textarea id="notes" v-model="formData.notes" rows="3" fluid />
        </div>
      </div>
    </div>

    <div class="flex justify-content-end gap-2 mt-4">
      <Button label="Abbrechen" severity="secondary" @click="emit('cancel')" type="button" />
      <Button label="Speichern" type="submit" :loading="loading" />
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Member, Status, Group } from '@/types/api'
import { statusesApi } from '@/api/members'
import { groupsApi } from '@/api/members'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import Select from 'primevue/select'

interface Props {
  member?: Member | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  save: [member: Partial<Member>]
  cancel: []
}>()

interface FormData {
  name: string
  lastname: string
  birthday: Date | null
  joined: Date | null
  status: number | null
  group: number | null
  email: string
  phone: string
  mobile: string
  identityCardNumber: string
  street: string
  zip_code: string
  city: string
  canSwimm: boolean
  notes: string
}

const formData = ref<FormData>({
  name: '',
  lastname: '',
  birthday: null,
  joined: null,
  status: null,
  group: null,
  email: '',
  phone: '',
  mobile: '',
  identityCardNumber: '',
  street: '',
  zip_code: '',
  city: '',
  canSwimm: false,
  notes: ''
})

const statuses = ref<Status[]>([])
const groups = ref<Group[]>([])
const submitted = ref(false)
const loading = ref(false)

onMounted(async () => {
  // Load statuses and groups
  try {
    const [statusResponse, groupResponse] = await Promise.all([
      statusesApi.list(),
      groupsApi.list()
    ])
    statuses.value = statusResponse.data
    groups.value = groupResponse.data
  } catch (error) {
    console.error('Failed to load form data:', error)
  }

  if (props.member) {
    formData.value = {
      name: props.member.name,
      lastname: props.member.lastname,
      birthday: props.member.birthday ? new Date(props.member.birthday) : null,
      joined: props.member.joined ? new Date(props.member.joined) : null,
      status: typeof props.member.status === 'object' ? props.member.status?.id || null : props.member.status as number | null,
      group: typeof props.member.group === 'object' ? props.member.group?.id || null : props.member.group as number | null,
      email: props.member.email || '',
      phone: props.member.phone || '',
      mobile: props.member.mobile || '',
      identityCardNumber: props.member.identityCardNumber || '',
      street: props.member.street || '',
      zip_code: props.member.zip_code || '',
      city: props.member.city || '',
      canSwimm: props.member.canSwimm || false,
      notes: props.member.notes || ''
    }
  }
})

const handleSubmit = () => {
  submitted.value = true

  if (!formData.value.name || !formData.value.lastname || !formData.value.birthday) {
    return
  }

  loading.value = true

  // Convert Date objects back to strings and prepare data for API
  const submitData: any = {
    name: formData.value.name,
    lastname: formData.value.lastname,
    birthday: formData.value.birthday ? formData.value.birthday.toISOString().split('T')[0] : null,
    joined: formData.value.joined ? formData.value.joined.toISOString().split('T')[0] : null,
    status: formData.value.status,
    group: formData.value.group,
    email: formData.value.email,
    phone: formData.value.phone,
    mobile: formData.value.mobile,
    identityCardNumber: formData.value.identityCardNumber,
    street: formData.value.street,
    zip_code: formData.value.zip_code,
    city: formData.value.city,
    canSwimm: formData.value.canSwimm,
    notes: formData.value.notes
  }

  emit('save', submitData)
  loading.value = false
}
</script>
