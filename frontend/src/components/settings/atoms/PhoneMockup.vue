<template>
  <div class="phone-mockup">
    <div class="phone-frame">
      <div class="phone-notch"></div>
      <div class="phone-screen">
        <div class="email-header">
          <div class="email-header-row">
            <i class="pi pi-arrow-left"></i>
            <span class="email-subject">{{ subject || '(Kein Betreff)' }}</span>
          </div>
          <div class="email-meta">
            <strong>JF-Manager</strong> &lt;noreply@jf-manager.de&gt;
          </div>
        </div>
        <div class="email-content">
          <iframe
            class="preview-iframe"
            sandbox="allow-same-origin allow-scripts"
            :srcdoc="htmlContent"
          ></iframe>
        </div>
      </div>
      <div class="phone-home-bar"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  subject?: string
  htmlContent: string
}

defineProps<Props>()
</script>

<style scoped>
.phone-mockup {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 1rem 0;
}

.phone-frame {
  width: 375px;
  height: 667px;
  background: linear-gradient(145deg, #2d2d2d, #1a1a1a);
  border-radius: 40px;
  padding: 12px;
  box-shadow: 
    0 20px 60px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.1) inset;
  position: relative;
}

.phone-notch {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 150px;
  height: 28px;
  background: #1a1a1a;
  border-radius: 0 0 20px 20px;
  z-index: 10;
}

.phone-notch::before {
  content: '';
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  width: 6px;
  height: 6px;
  background: #333;
  border-radius: 50%;
}

.phone-screen {
  width: 100%;
  height: 100%;
  background: white;
  border-radius: 32px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.email-header {
  background: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
  padding: 1rem;
  flex-shrink: 0;
}

.email-header-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.email-header-row i {
  font-size: 1.25rem;
  color: #007aff;
}

.email-subject {
  font-size: 1rem;
  font-weight: 600;
  color: #000;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.email-meta {
  font-size: 0.875rem;
  color: #666;
}

.email-meta strong {
  color: #000;
}

.email-content {
  flex: 1;
  overflow-y: auto;
  background: white;
}

.preview-iframe {
  width: 100%;
  min-height: 100%;
  border: none;
  background-color: white;
  display: block;
}

.phone-home-bar {
  position: absolute;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  width: 120px;
  height: 4px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
}
</style>
