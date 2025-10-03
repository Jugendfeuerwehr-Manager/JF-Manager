<template>
  <div class="login-container">
    <Card class="login-card">
      <template #header>
        <div class="login-header">
          <i class="pi pi-shield text-6xl text-primary mb-3"></i>
          <h1 class="text-3xl font-bold">JF-Manager</h1>
          <p class="text-surface-500">Jugendfeuerwehr Management System</p>
        </div>
      </template>

      <template #content>
        <form @submit.prevent="handleLogin" class="login-form">
          <div class="field">
            <label for="username">Username</label>
            <InputText
              id="username"
              v-model="username"
              placeholder="Enter your username"
              class="w-full"
              :invalid="!!error"
              autofocus
            />
          </div>

          <div class="field">
            <label for="password">Password</label>
            <Password
              id="password"
              v-model="password"
              placeholder="Enter your password"
              :feedback="false"
              toggle-mask
              class="w-full"
              :invalid="!!error"
              input-class="w-full"
            />
          </div>

          <Message v-if="error" severity="error" class="w-full">{{ error }}</Message>

          <Button
            type="submit"
            label="Login"
            icon="pi pi-sign-in"
            :loading="loading"
            class="w-full"
          />
        </form>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  if (!username.value || !password.value) {
    error.value = 'Please enter username and password'
    return
  }

  loading.value = true
  error.value = ''

  try {
    await authStore.login(username.value, password.value)
    router.push('/')
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Login failed. Please check your credentials.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-600) 100%);
  padding: 1rem;
}

.login-card {
  width: 100%;
  max-width: 450px;
}

.login-header {
  text-align: center;
  padding: 3rem 2rem 1.5rem;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-600) 100%);
  color: white;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>
