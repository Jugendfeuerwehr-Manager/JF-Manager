<template>
  <div>
    <Message v-if="variables?.warning" severity="warn" :closable="false" class="mb-3">
      {{ variables.warning }}
    </Message>
    
    <div v-if="variables && variables.variables.length > 0" class="variables-list">
      <div
        v-for="variable in variables.variables"
        :key="variable.name"
        class="variable-item"
      >
        <code class="variable-name">{{ formatVariableName(variable.name) }}</code>
        <div class="variable-details">
          <span class="variable-type">{{ variable.type }}</span>
          <span class="variable-description">{{ variable.description }}</span>
        </div>
        <div v-if="variable.properties" class="variable-properties">
          <small>Eigenschaften:</small>
          <ul>
            <li v-for="prop in variable.properties" :key="prop">
              <code>{{ formatVariableProperty(variable.name, prop) }}</code>
            </li>
          </ul>
        </div>
      </div>
    </div>
    
    <div v-else-if="!variables" class="empty-state">
      <p class="text-sm">Wählen Sie einen Vorlagentyp aus</p>
    </div>
    
    <div v-else class="empty-state">
      <p class="text-sm">Keine Variablen für diesen Vorlagentyp definiert</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import Message from 'primevue/message'
import type { TemplateVariables } from '@/types/email-templates'

interface Props {
  variables: TemplateVariables | null
}

defineProps<Props>()

function formatVariableName(name: string): string {
  return `{{ ${name} }}`
}

function formatVariableProperty(name: string, prop: string): string {
  return `{{ ${name}.${prop} }}`
}
</script>

<style scoped>
.variables-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.variable-item {
  padding: 0.75rem;
  background-color: var(--p-surface-50);
  border-radius: var(--p-content-border-radius);
}

.variable-name {
  display: block;
  padding: 0.25rem 0.5rem;
  background-color: var(--p-surface-100);
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
  color: var(--p-primary-color);
  font-weight: 600;
  word-break: break-all;
}

.variable-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.variable-type {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}

.variable-description {
  font-size: 0.85rem;
}

.variable-properties {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--p-content-border-color);
}

.variable-properties small {
  font-weight: 600;
  color: var(--p-text-muted-color);
}

.variable-properties ul {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0 0;
}

.variable-properties li {
  margin-bottom: 0.25rem;
}

.variable-properties code {
  font-size: 0.75rem;
  padding: 0.125rem 0.25rem;
  background-color: var(--p-surface-100);
  border-radius: 2px;
  word-break: break-all;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
  color: var(--p-text-muted-color);
}

.empty-state p {
  margin: 0;
}
</style>
