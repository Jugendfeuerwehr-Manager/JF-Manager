<template>
  <div class="login-container">
    <!-- Animated Background Elements -->
    <div class="background-animation">
      <div class="flame flame-1"></div>
      <div class="flame flame-2"></div>
      <div class="flame flame-3"></div>
      <div class="flame flame-4"></div>
      <div class="flame flame-5"></div>
      <div class="particle-container">
        <div v-for="i in 20" :key="i" class="particle" :style="particleStyle(i)"></div>
      </div>
    </div>

    <!-- Login Card with Glassmorphism -->
    <div class="login-card-wrapper">
      <Card class="login-card glass-card">
        <template #header>
          <div class="login-header">
            <!-- Animated Shield Icon -->
            <div class="icon-container">
              <div class="icon-glow"></div>
              <i class="pi pi-shield shield-icon"></i>
              <div class="icon-ring ring-1"></div>
              <div class="icon-ring ring-2"></div>
              <div class="icon-ring ring-3"></div>
            </div>
            
            <h1 class="brand-title">
              <span class="title-fire">JF</span>-<span class="title-manager">Manager</span>
            </h1>
            <p class="brand-subtitle">Jugendfeuerwehr Verwaltungssystem</p>
            
            <!-- Decorative Line -->
            <div class="decorative-line">
              <div class="line-segment"></div>
              <div class="line-dot"></div>
              <div class="line-segment"></div>
            </div>
          </div>
        </template>

        <template #content>
          <form @submit.prevent="handleLogin" class="login-form">
            <!-- Username Field -->
            <div class="input-group" :class="{ 'has-error': !!error, 'is-focused': usernameFocused }">
              <label for="username" class="input-label">
                <i class="pi pi-user label-icon"></i>
                Benutzername
              </label>
              <div class="input-wrapper">
                <InputText
                  id="username"
                  v-model="username"
                  placeholder="Benutzername eingeben"
                  class="styled-input"
                  :invalid="!!error"
                  autofocus
                  @focus="usernameFocused = true"
                  @blur="usernameFocused = false"
                />
                <div class="input-underline"></div>
              </div>
            </div>

            <!-- Password Field -->
            <div class="input-group" :class="{ 'has-error': !!error, 'is-focused': passwordFocused }">
              <label for="password" class="input-label">
                <i class="pi pi-lock label-icon"></i>
                Passwort
              </label>
              <div class="input-wrapper">
                <Password
                  id="password"
                  v-model="password"
                  placeholder="Passwort eingeben"
                  :feedback="false"
                  toggle-mask
                  class="styled-password"
                  :invalid="!!error"
                  input-class="styled-input"
                  @focus="passwordFocused = true"
                  @blur="passwordFocused = false"
                />
                <div class="input-underline"></div>
              </div>
            </div>

            <!-- Error Message with Animation -->
            <Transition name="error-slide">
              <Message v-if="error" severity="error" class="error-message">
                <div class="error-content">
                  <i class="pi pi-exclamation-triangle error-icon"></i>
                  {{ error }}
                </div>
              </Message>
            </Transition>

            <!-- Login Button with Hover Effects -->
            <Button
              type="submit"
              label="Anmelden"
              icon="pi pi-sign-in"
              :loading="loading"
              class="login-button"
            >
              <template #icon>
                <i class="pi pi-sign-in button-icon"></i>
              </template>
            </Button>

            <!-- Forgot Password Link -->
            <div class="forgot-password">
              <router-link to="/forgot-password" class="forgot-link">
                <i class="pi pi-question-circle"></i>
                Passwort zurücksetzen
              </router-link>
            </div>

            <!-- Additional Info -->
            <div class="login-footer">
              <div class="footer-line"></div>
              <p class="footer-text">Sicherer Zugang</p>
              <div class="footer-line"></div>
            </div>
          </form>
        </template>
      </Card>
    </div>

    <!-- Version badge removed per design request -->

    <!-- Success Animation Overlay -->
    <Transition name="success-overlay">
      <div v-if="loginSuccess" class="success-overlay">
        <div class="success-content">
          <!-- Checkmark Animation -->
          <div class="checkmark-container">
            <svg class="checkmark" viewBox="0 0 52 52">
              <circle class="checkmark-circle" cx="26" cy="26" r="25" fill="none"/>
              <path class="checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
            </svg>
          </div>
          
          <!-- Success Text -->
          <h2 class="success-title">Willkommen zurück!</h2>
          <p class="success-subtitle">Anmeldung erfolgreich</p>
          
          <!-- Celebration Particles -->
          <div class="celebration-particles">
            <div v-for="i in 30" :key="i" class="celebration-particle" :style="celebrationStyle(i)"></div>
          </div>
          
          <!-- Firework Effects -->
          <div class="fireworks">
            <div class="firework firework-1"></div>
            <div class="firework firework-2"></div>
            <div class="firework firework-3"></div>
          </div>
        </div>
      </div>
    </Transition>
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
const usernameFocused = ref(false)
const passwordFocused = ref(false)
const loginSuccess = ref(false)

const particleStyle = (index: number) => ({
  '--delay': `${index * 0.3}s`,
  '--x': `${Math.random() * 100}%`,
  '--y': `${Math.random() * 100}%`,
  '--duration': `${15 + Math.random() * 10}s`
})

const celebrationStyle = (index: number) => {
  const angle = (index / 30) * 360
  const distance = 100 + Math.random() * 100
  return {
    '--angle': `${angle}deg`,
    '--distance': `${distance}px`,
    '--delay': `${index * 0.02}s`,
    '--duration': `${0.8 + Math.random() * 0.4}s`,
    '--size': `${4 + Math.random() * 6}px`
  }
}

const handleLogin = async () => {
  if (!username.value || !password.value) {
    error.value = 'Bitte gib Benutzername und Passwort ein'
    return
  }

  loading.value = true
  error.value = ''

  try {
    await authStore.login(username.value, password.value)
    
    // Show success animation
    loginSuccess.value = true
    
    // Wait for animation to complete before redirecting
    setTimeout(() => {
      router.push('/')
    }, 2000)
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Anmeldung fehlgeschlagen. Bitte überprüfe deine Zugangsdaten.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ==================== Container & Background ==================== */
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, 
    #c31432 0%, 
    #e74c3c 25%,
    #ff6b6b 50%,
    #ee5a6f 75%,
    #c31432 100%
  );
  background-size: 400% 400%;
  animation: gradientShift 15s ease infinite;
}

@keyframes gradientShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

/* ==================== Background Animation ==================== */
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
  background: radial-gradient(circle, rgba(255, 193, 7, 0.4) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(20px);
  animation: flameRise 8s ease-in-out infinite;
}

.flame-1 { left: 10%; animation-delay: 0s; }
.flame-2 { left: 25%; animation-delay: 2s; }
.flame-3 { left: 50%; animation-delay: 4s; }
.flame-4 { left: 75%; animation-delay: 1s; }
.flame-5 { left: 90%; animation-delay: 3s; }

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

/* ==================== Login Card ==================== */
.login-card-wrapper {
  width: 100%;
  max-width: 420px;
  animation: cardEntrance 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes cardEntrance {
  0% {
    opacity: 0;
    transform: translateY(50px) scale(0.9) rotateX(10deg);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1) rotateX(0);
  }
}

.glass-card {
  background: rgba(255, 255, 255, 0.15) !important;
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  box-shadow: 
    0 20px 60px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.4),
    0 0 100px rgba(255, 255, 255, 0.1);
  overflow: hidden;
  transition: all 0.3s ease;
}

.glass-card:hover {
  transform: translateY(-3px);
  box-shadow: 
    0 25px 70px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.5),
    0 0 110px rgba(255, 255, 255, 0.15);
}

/* ==================== Header ==================== */
.login-header {
  text-align: center;
  padding: 2rem 1.5rem 1.5rem;
  position: relative;
  color: white;
}

.icon-container {
  position: relative;
  display: inline-block;
  margin-bottom: 1rem;
  animation: iconFloat 3s ease-in-out infinite;
}

@keyframes iconFloat {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-8px) rotate(3deg); }
}

.shield-icon {
  font-size: 3.5rem;
  color: white;
  position: relative;
  z-index: 2;
  filter: drop-shadow(0 8px 15px rgba(0, 0, 0, 0.3));
  animation: shieldPulse 2s ease-in-out infinite;
}

@keyframes shieldPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.03); }
}

.icon-glow {
  position: absolute;
  inset: -20px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.4) 0%, transparent 70%);
  border-radius: 50%;
  animation: glowPulse 2s ease-in-out infinite;
  z-index: 1;
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
.icon-ring.ring-2 { animation-delay: 1s; }
.icon-ring.ring-3 { animation-delay: 2s; }

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
  font-size: 2.25rem;
  font-weight: 800;
  margin: 0 0 0.4rem;
  letter-spacing: 1.5px;
  text-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  animation: titleReveal 0.8s ease-out 0.3s backwards;
}

@keyframes titleReveal {
  0% {
    opacity: 0;
    transform: translateY(15px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.title-fire {
  background: linear-gradient(45deg, #fff, #ffd700);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: fireShimmer 3s ease-in-out infinite;
}

@keyframes fireShimmer {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.3); }
}

.title-manager {
  color: white;
}

.brand-subtitle {
  font-size: 0.9rem;
  font-weight: 300;
  color: rgba(255, 255, 255, 0.95);
  margin: 0;
  letter-spacing: 0.8px;
  animation: subtitleReveal 0.8s ease-out 0.5s backwards;
}

@keyframes subtitleReveal {
  0% {
    opacity: 0;
    transform: translateY(8px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.decorative-line {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  margin-top: 1.2rem;
}

.line-segment {
  width: 50px;
  height: 1.5px;
  background: linear-gradient(90deg, transparent, white, transparent);
  animation: lineGlow 2s ease-in-out infinite;
}

.line-dot {
  width: 6px;
  height: 6px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 0 15px rgba(255, 255, 255, 0.8);
  animation: dotPulse 2s ease-in-out infinite;
}

@keyframes lineGlow {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

@keyframes dotPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.3); }
}

/* ==================== Form ==================== */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 0.5rem;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  position: relative;
  transition: all 0.3s ease;
}

.input-group.is-focused {
  transform: translateY(-1px);
}

.input-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: white;
  letter-spacing: 0.4px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

.input-group.is-focused .input-label {
  color: #ffd700;
  transform: translateX(3px);
}

.label-icon {
  font-size: 1rem;
  animation: iconBounce 2s ease-in-out infinite;
}

@keyframes iconBounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-2px); }
}

.input-wrapper {
  position: relative;
}

:deep(.styled-input) {
  width: 100%;
  padding: 0.85rem 1rem;
  font-size: 0.95rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.95);
  transition: all 0.3s ease;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
}

:deep(.styled-input:focus) {
  border-color: #ffd700;
  background: white;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(255, 215, 0, 0.3);
  outline: none;
}

:deep(.styled-input::placeholder) {
  color: rgba(0, 0, 0, 0.4);
}

:deep(.styled-password) {
  width: 100%;
}

:deep(.styled-password .p-password-input) {
  width: 100%;
  padding: 0.85rem 1rem;
  font-size: 0.95rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.95);
  transition: all 0.3s ease;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
}

:deep(.styled-password .p-password-input:focus) {
  border-color: #ffd700;
  background: white;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(255, 215, 0, 0.3);
}

.input-underline {
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, #ffd700, #ffed4e);
  transform: translateX(-50%);
  transition: width 0.4s ease;
  border-radius: 2px;
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.5);
}

.input-group.is-focused .input-underline {
  width: 100%;
}

.input-group.has-error :deep(.styled-input),
.input-group.has-error :deep(.p-password-input) {
  border-color: #ff6b6b;
  animation: shake 0.4s ease;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-8px); }
  75% { transform: translateX(8px); }
}

/* ==================== Error Message ==================== */
.error-message {
  background: rgba(255, 107, 107, 0.95) !important;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 10px;
  box-shadow: 0 3px 12px rgba(255, 107, 107, 0.3);
}

.error-content {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  color: white;
  font-weight: 500;
  font-size: 0.9rem;
}

.error-icon {
  font-size: 1.1rem;
  animation: errorPulse 1s ease-in-out infinite;
}

@keyframes errorPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}

.error-slide-enter-active,
.error-slide-leave-active {
  transition: all 0.3s ease;
}

.error-slide-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.error-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ==================== Login Button ==================== */
:deep(.login-button) {
  width: 100%;
  padding: 1rem;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.8px;
  border-radius: 10px;
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  border: none;
  color: #c31432;
  box-shadow: 
    0 6px 16px rgba(255, 215, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

:deep(.login-button::before) {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.4);
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}

:deep(.login-button:hover) {
  transform: translateY(-2px);
  box-shadow: 
    0 10px 24px rgba(255, 215, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

:deep(.login-button:hover::before) {
  width: 300px;
  height: 300px;
}

:deep(.login-button:active) {
  transform: translateY(-1px);
}

.button-icon {
  margin-right: 0.4rem;
  animation: iconSlide 2s ease-in-out infinite;
}

@keyframes iconSlide {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(4px); }
}

/* ==================== Forgot Password ==================== */
.forgot-password {
  text-align: center;
  margin-top: 0.75rem;
}

.forgot-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: white;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.forgot-link:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
  box-shadow: 0 3px 12px rgba(255, 255, 255, 0.2);
}

.forgot-link i {
  font-size: 0.9rem;
  animation: questionBounce 2s ease-in-out infinite;
}

@keyframes questionBounce {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}

/* ==================== Footer ==================== */
.login-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  margin-top: 0.4rem;
}

.footer-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.5), transparent);
}

.footer-text {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
  letter-spacing: 0.8px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* ==================== Responsive Design ==================== */
@media (max-width: 768px) {
  .login-container {
    padding: 0.75rem;
  }

  .login-card-wrapper {
    max-width: 100%;
  }

  .glass-card {
    border-radius: 16px;
  }

  .login-header {
    padding: 1.5rem 1.25rem 1.25rem;
  }

  .shield-icon {
    font-size: 3rem;
  }

  .brand-title {
    font-size: 1.875rem;
  }

  .brand-subtitle {
    font-size: 0.825rem;
  }

  .login-form {
    gap: 1.25rem;
  }

  :deep(.styled-input),
  :deep(.p-password-input) {
    padding: 0.75rem 0.875rem;
    font-size: 0.9rem;
  }

  :deep(.login-button) {
    padding: 0.875rem;
    font-size: 0.95rem;
  }
}

@media (max-width: 480px) {
  .login-header {
    padding: 1.25rem 1rem 1rem;
  }

  .shield-icon {
    font-size: 2.5rem;
  }

  .brand-title {
    font-size: 1.625rem;
    letter-spacing: 1px;
  }

  .brand-subtitle {
    font-size: 0.75rem;
  }

  .decorative-line {
    gap: 0.6rem;
    margin-top: 1rem;
  }

  .line-segment {
    width: 40px;
  }

  .login-form {
    gap: 1rem;
  }

  .input-label {
    font-size: 0.85rem;
  }

  :deep(.styled-input),
  :deep(.p-password-input) {
    padding: 0.7rem 0.8rem;
    font-size: 0.875rem;
  }

  .forgot-link {
    font-size: 0.8rem;
    padding: 0.35rem 0.7rem;
  }
}

/* Ensure it fits on small MacBooks (13") */
@media (max-height: 800px) {
  .login-header {
    padding: 1.5rem 1.25rem 1.25rem;
  }

  .shield-icon {
    font-size: 3rem;
  }

  .brand-title {
    font-size: 2rem;
  }

  .icon-container {
    margin-bottom: 0.75rem;
  }

  .decorative-line {
    margin-top: 1rem;
  }

  .login-form {
    gap: 1.25rem;
  }
}

/* ==================== Dark Mode Support ==================== */
@media (prefers-color-scheme: dark) {
  .glass-card {
    background: rgba(0, 0, 0, 0.25) !important;
  }

  :deep(.styled-input),
  :deep(.p-password-input) {
    background: rgba(255, 255, 255, 0.9);
  }
}

/* ==================== Success Animation Overlay ==================== */
.success-overlay {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, 
    rgba(76, 175, 80, 0.95) 0%, 
    rgba(56, 142, 60, 0.95) 100%
  );
  backdrop-filter: blur(10px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.success-content {
  text-align: center;
  position: relative;
  animation: successContentZoom 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes successContentZoom {
  0% {
    opacity: 0;
    transform: scale(0.3);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

/* Checkmark Animation */
.checkmark-container {
  display: inline-block;
  margin-bottom: 2rem;
}

.checkmark {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: block;
  stroke-width: 3;
  stroke: white;
  stroke-miterlimit: 10;
  box-shadow: 
    inset 0 0 0 white,
    0 0 40px rgba(255, 255, 255, 0.5);
  animation: checkmarkFill 0.4s ease-in-out 0.4s forwards, checkmarkScale 0.3s ease-in-out 0.9s both;
}

@keyframes checkmarkFill {
  100% {
    box-shadow: inset 0 0 0 60px white;
  }
}

@keyframes checkmarkScale {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.checkmark-circle {
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  stroke-width: 3;
  stroke-miterlimit: 10;
  stroke: white;
  fill: none;
  animation: checkmarkStroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;
}

@keyframes checkmarkStroke {
  100% {
    stroke-dashoffset: 0;
  }
}

.checkmark-check {
  transform-origin: 50% 50%;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  stroke: #4caf50;
  stroke-width: 3;
  animation: checkmarkStroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.8s forwards;
}

/* Success Text */
.success-title {
  font-size: 3rem;
  font-weight: 800;
  color: white;
  margin: 0 0 0.5rem;
  text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  animation: successTextSlide 0.5s ease-out 0.8s backwards;
}

.success-subtitle {
  font-size: 1.5rem;
  font-weight: 300;
  color: rgba(255, 255, 255, 0.95);
  margin: 0;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  animation: successTextSlide 0.5s ease-out 1s backwards;
}

@keyframes successTextSlide {
  0% {
    opacity: 0;
    transform: translateY(20px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Celebration Particles */
.celebration-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.celebration-particle {
  position: absolute;
  top: 50%;
  left: 50%;
  width: var(--size);
  height: var(--size);
  background: white;
  border-radius: 50%;
  animation: celebrationBurst var(--duration) ease-out var(--delay) forwards;
  opacity: 0;
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
}

@keyframes celebrationBurst {
  0% {
    opacity: 1;
    transform: translate(-50%, -50%) rotate(var(--angle)) translateY(0) scale(0);
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    transform: translate(-50%, -50%) rotate(var(--angle)) translateY(var(--distance)) scale(1);
  }
}

/* Firework Effects */
.fireworks {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.firework {
  position: absolute;
  width: 4px;
  height: 4px;
  background: white;
  border-radius: 50%;
  box-shadow: 
    0 0 20px 2px white,
    0 0 40px 4px rgba(255, 215, 0, 0.8),
    0 0 60px 6px rgba(255, 193, 7, 0.6);
  animation: fireworkExplode 1s ease-out forwards;
}

.firework-1 {
  top: 20%;
  left: 20%;
  animation-delay: 0.5s;
}

.firework-2 {
  top: 30%;
  right: 20%;
  animation-delay: 0.7s;
}

.firework-3 {
  bottom: 30%;
  left: 30%;
  animation-delay: 0.9s;
}

@keyframes fireworkExplode {
  0% {
    opacity: 1;
    transform: scale(1);
    box-shadow: 
      0 0 20px 2px white,
      0 0 40px 4px rgba(255, 215, 0, 0.8),
      0 0 60px 6px rgba(255, 193, 7, 0.6);
  }
  50% {
    opacity: 1;
    transform: scale(30);
  }
  100% {
    opacity: 0;
    transform: scale(50);
    box-shadow: 
      0 0 40px 4px white,
      0 0 80px 8px rgba(255, 215, 0, 0.4),
      0 0 120px 12px rgba(255, 193, 7, 0.2);
  }
}

/* Success Overlay Transition */
.success-overlay-enter-active {
  animation: successOverlayEnter 0.4s ease-out;
}

.success-overlay-leave-active {
  animation: successOverlayLeave 0.4s ease-in;
}

@keyframes successOverlayEnter {
  0% {
    opacity: 0;
    transform: scale(0.8);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes successOverlayLeave {
  0% {
    opacity: 1;
    transform: scale(1);
  }
  100% {
    opacity: 0;
    transform: scale(1.2);
  }
}

/* ==================== Print Styles ==================== */
@media print {
  .background-animation,
  .version-badge,
  .decorative-line,
  .success-overlay {
    display: none;
  }
}
</style>
