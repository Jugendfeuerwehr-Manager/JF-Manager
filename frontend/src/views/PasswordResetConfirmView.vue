<template>
  <div class="password-reset-container">
    <!-- Animated Background -->
    <div class="background-animation">
      <div class="flame flame-1"></div>
      <div class="flame flame-2"></div>
      <div class="flame flame-3"></div>
      <div class="particle-container">
        <div v-for="i in 15" :key="i" class="particle" :style="particleStyle(i)"></div>
      </div>
    </div>

    <!-- Reset Card -->
    <div class="reset-card-wrapper">
      <Card class="reset-card glass-card">
        <template #header>
          <div class="reset-header">
            <div class="icon-container">
              <div class="icon-glow"></div>
              <i class="pi pi-lock shield-icon"></i>
              <div class="icon-ring ring-1"></div>
              <div class="icon-ring ring-2"></div>
            </div>
            
            <h1 class="brand-title">Neues Passwort festlegen</h1>
            <p class="brand-subtitle">Gib dein neues Passwort ein</p>
            
            <div class="decorative-line">
              <div class="line-segment"></div>
              <div class="line-dot"></div>
              <div class="line-segment"></div>
            </div>
          </div>
        </template>

        <template #content>
          <form v-if="!resetSuccess" @submit.prevent="handleSubmit" class="reset-form">
            <!-- New Password Field -->
            <div class="input-group" :class="{ 'is-focused': passwordFocused }">
              <label for="new-password" class="input-label">
                <i class="pi pi-lock label-icon"></i>
                Neues Passwort
              </label>
              <div class="input-wrapper">
                <Password
                  id="new-password"
                  v-model="newPassword"
                  placeholder="Neues Passwort eingeben"
                  :feedback="true"
                  toggle-mask
                  class="styled-password"
                  input-class="styled-input"
                  @focus="passwordFocused = true"
                  @blur="passwordFocused = false"
                />
                <div class="input-underline"></div>
              </div>
            </div>

            <!-- Confirm Password Field -->
            <div class="input-group" :class="{ 'is-focused': confirmFocused }">
              <label for="confirm-password" class="input-label">
                <i class="pi pi-lock label-icon"></i>
                Passwort bestätigen
              </label>
              <div class="input-wrapper">
                <Password
                  id="confirm-password"
                  v-model="confirmPassword"
                  placeholder="Neues Passwort bestätigen"
                  :feedback="false"
                  toggle-mask
                  class="styled-password"
                  input-class="styled-input"
                  @focus="confirmFocused = true"
                  @blur="confirmFocused = false"
                />
                <div class="input-underline"></div>
              </div>
            </div>

            <!-- Error Message -->
            <Transition name="error-slide">
              <Message v-if="error" severity="error" class="error-message">
                <div class="error-content">
                  <i class="pi pi-exclamation-triangle error-icon"></i>
                  {{ error }}
                </div>
              </Message>
            </Transition>

            <!-- Submit Button -->
            <Button
              type="submit"
              label="Passwort zurücksetzen"
              icon="pi pi-check"
              :loading="loading"
              class="reset-button"
            />

            <!-- Back to Login -->
            <div class="back-to-login">
              <router-link to="/login" class="back-link">
                <i class="pi pi-arrow-left"></i>
                Zurück zur Anmeldung
              </router-link>
            </div>
          </form>

          <!-- Success Message -->
          <div v-else class="success-content">
            <div class="success-icon-container">
              <i class="pi pi-check-circle success-icon"></i>
            </div>
            <h2 class="success-title">Passwort erfolgreich zurückgesetzt!</h2>
            <p class="success-message">
              Dein Passwort wurde erfolgreich zurückgesetzt. Du kannst dich jetzt mit deinem neuen Passwort anmelden.
            </p>
            <Button
              label="Zur Anmeldung"
              icon="pi pi-sign-in"
              class="login-button"
              @click="$router.push('/login')"
            />
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '@/api/auth'
import Card from 'primevue/card'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'

const route = useRoute()
const router = useRouter()

const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')
const passwordFocused = ref(false)
const confirmFocused = ref(false)
const resetSuccess = ref(false)

const uid = ref('')
const token = ref('')

const particleStyle = (index: number) => ({
  '--delay': `${index * 0.4}s`,
  '--x': `${Math.random() * 100}%`,
  '--y': `${Math.random() * 100}%`,
  '--duration': `${15 + Math.random() * 10}s`
})

onMounted(() => {
  // Get uid and token from route params
  uid.value = route.params.uid as string
  token.value = route.params.token as string

  if (!uid.value || !token.value) {
    error.value = 'Ungültiger Reset-Link'
  }
})

const handleSubmit = async () => {
  error.value = ''

  // Validation
  if (!newPassword.value || !confirmPassword.value) {
    error.value = 'Bitte fülle alle Felder aus'
    return
  }

  if (newPassword.value.length < 8) {
    error.value = 'Das Passwort muss mindestens 8 Zeichen lang sein'
    return
  }

  if (newPassword.value !== confirmPassword.value) {
    error.value = 'Die Passwörter stimmen nicht überein'
    return
  }

  loading.value = true

  try {
    await authApi.resetPassword({
      uid: uid.value,
      token: token.value,
      new_password: newPassword.value,
      new_password_confirm: confirmPassword.value
    })
    resetSuccess.value = true
  } catch (err: any) {
    error.value = err.response?.data?.error || 'Passwort konnte nicht zurückgesetzt werden. Der Link ist möglicherweise abgelaufen.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Reuse styles from PasswordResetRequestView */
.password-reset-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, 
    #11998e 0%, 
    #38ef7d 100%
  );
  background-size: 400% 400%;
  animation: gradientShift 15s ease infinite;
}

@keyframes gradientShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.background-animation {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.flame {
  position: absolute;
  bottom: -100px;
  width: 80px;
  height: 80px;
  background: radial-gradient(circle, rgba(56, 239, 125, 0.4) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(20px);
  animation: flameRise 8s ease-in-out infinite;
}

.flame-1 { left: 20%; animation-delay: 0s; }
.flame-2 { left: 50%; animation-delay: 2s; }
.flame-3 { left: 80%; animation-delay: 4s; }

@keyframes flameRise {
  0% {
    transform: translateY(0) scale(1);
    opacity: 0;
  }
  10% {
    opacity: 0.8;
  }
  100% {
    transform: translateY(-120vh) scale(1.5);
    opacity: 0;
  }
}

.particle-container {
  position: absolute;
  inset: 0;
}

.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 50%;
  left: var(--x);
  top: var(--y);
  animation: particleFloat var(--duration) ease-in-out infinite;
  animation-delay: var(--delay);
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
}

@keyframes particleFloat {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  50% {
    transform: translate(var(--random-x, 50px), var(--random-y, -100px)) scale(1.5);
    opacity: 0.8;
  }
  90% {
    opacity: 1;
  }
  100% {
    transform: translate(0, 0) scale(1);
    opacity: 0;
  }
}

.reset-card-wrapper {
  width: 100%;
  max-width: 480px;
  animation: cardEntrance 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes cardEntrance {
  0% {
    opacity: 0;
    transform: translateY(50px) scale(0.9);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.glass-card {
  background: rgba(255, 255, 255, 0.15) !important;
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 24px;
  box-shadow: 
    0 20px 60px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
  overflow: hidden;
  transition: all 0.3s ease;
}

.glass-card:hover {
  transform: translateY(-5px);
  box-shadow: 
    0 30px 80px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

.reset-header {
  text-align: center;
  padding: 3rem 2rem 2rem;
  color: white;
}

.icon-container {
  position: relative;
  display: inline-block;
  margin-bottom: 1.5rem;
  animation: iconFloat 3s ease-in-out infinite;
}

@keyframes iconFloat {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-10px) rotate(5deg); }
}

.shield-icon {
  font-size: 5rem;
  color: white;
  position: relative;
  z-index: 2;
  filter: drop-shadow(0 10px 20px rgba(0, 0, 0, 0.3));
  animation: shieldPulse 2s ease-in-out infinite;
}

@keyframes shieldPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.icon-glow {
  position: absolute;
  inset: -20px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.4) 0%, transparent 70%);
  border-radius: 50%;
  animation: glowPulse 2s ease-in-out infinite;
}

@keyframes glowPulse {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}

.icon-ring {
  position: absolute;
  inset: -10px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  animation: ringExpand 3s ease-out infinite;
}

.icon-ring.ring-1 { animation-delay: 0s; }
.icon-ring.ring-2 { animation-delay: 1.5s; }

@keyframes ringExpand {
  0% {
    transform: scale(0.8);
    opacity: 1;
  }
  100% {
    transform: scale(2);
    opacity: 0;
  }
}

.brand-title {
  font-size: 2.5rem;
  font-weight: 800;
  margin: 0 0 0.5rem;
  letter-spacing: 2px;
  text-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  color: white;
}

.brand-subtitle {
  font-size: 1rem;
  font-weight: 300;
  color: rgba(255, 255, 255, 0.95);
  margin: 0;
  letter-spacing: 0.5px;
}

.decorative-line {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
}

.line-segment {
  width: 60px;
  height: 2px;
  background: linear-gradient(90deg, transparent, white, transparent);
}

.line-dot {
  width: 8px;
  height: 8px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.8);
}

.reset-form {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 0.5rem;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  transition: all 0.3s ease;
}

.input-group.is-focused {
  transform: translateY(-2px);
}

.input-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: white;
  letter-spacing: 0.5px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.label-icon {
  font-size: 1.1rem;
}

.input-wrapper {
  position: relative;
}

:deep(.styled-password) {
  width: 100%;
}

:deep(.styled-password .p-password-input) {
  width: 100%;
  padding: 1rem 1.25rem;
  font-size: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.95);
  transition: all 0.3s ease;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

:deep(.styled-password .p-password-input:focus) {
  border-color: #11998e;
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(17, 153, 142, 0.3);
}

.input-underline {
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 3px;
  background: linear-gradient(90deg, #11998e, #38ef7d);
  transform: translateX(-50%);
  transition: width 0.4s ease;
  border-radius: 2px;
}

.input-group.is-focused .input-underline {
  width: 100%;
}

.error-message {
  background: rgba(255, 107, 107, 0.95) !important;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
}

.error-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: white;
  font-weight: 500;
}

.error-icon {
  font-size: 1.2rem;
}

.error-slide-enter-active,
.error-slide-leave-active {
  transition: all 0.3s ease;
}

.error-slide-enter-from,
.error-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

:deep(.reset-button) {
  width: 100%;
  padding: 1.25rem;
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 1px;
  border-radius: 12px;
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  border: none;
  color: white;
  box-shadow: 0 8px 20px rgba(17, 153, 142, 0.4);
  transition: all 0.3s ease;
}

:deep(.reset-button:hover) {
  transform: translateY(-3px);
  box-shadow: 0 12px 30px rgba(17, 153, 142, 0.5);
}

.back-to-login {
  text-align: center;
  margin-top: 0.5rem;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: white;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.3s ease;
  padding: 0.5rem 1rem;
  border-radius: 8px;
}

.back-link:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateX(-5px);
}

/* Success Content */
.success-content {
  text-align: center;
  padding: 2rem 1rem;
  animation: successFadeIn 0.6s ease-out;
}

@keyframes successFadeIn {
  0% {
    opacity: 0;
    transform: scale(0.9);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.success-icon-container {
  margin-bottom: 2rem;
}

.success-icon {
  font-size: 5rem;
  color: #4caf50;
  filter: drop-shadow(0 5px 15px rgba(76, 175, 80, 0.4));
  animation: successIconPop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes successIconPop {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.success-title {
  font-size: 2rem;
  font-weight: 700;
  color: white;
  margin: 0 0 1rem;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.success-message {
  color: rgba(255, 255, 255, 0.95);
  font-size: 1.1rem;
  line-height: 1.6;
  margin-bottom: 2rem;
}

:deep(.login-button) {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  border: none;
  color: white;
  padding: 1rem 2rem;
  font-size: 1.1rem;
  font-weight: 700;
}

:deep(.login-button:hover) {
  box-shadow: 0 8px 20px rgba(17, 153, 142, 0.4);
}

@media (max-width: 768px) {
  .reset-card-wrapper {
    max-width: 100%;
  }

  .brand-title {
    font-size: 2rem;
  }

  .shield-icon {
    font-size: 4rem;
  }
}
</style>
